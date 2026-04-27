from __future__ import annotations

import hashlib
import json
import sqlite3
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import numpy as np
import psycopg2
from psycopg2.extras import Json


EMBEDDING_DIM = 384


def stable_embed(text: str, dim: int = EMBEDDING_DIM) -> np.ndarray:
    """
    Deterministic lightweight embedding for local and test environments.
    It avoids model downloads while preserving semantic-ish token overlap.
    """
    vec = np.zeros(dim, dtype=np.float32)
    tokens = [t for t in text.lower().split() if t]
    if not tokens:
        return vec
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


class BaseVectorStore:
    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        raise NotImplementedError

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        company_id: Optional[str] = None,
        department: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def delete_document(self, document_id: str) -> int:
        raise NotImplementedError

    def stats(self, company_id: Optional[str] = None, department: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError


class SQLiteVectorStore(BaseVectorStore):
    """Persistent vector store backed by SQLite — survives restarts, no extra services needed."""

    def __init__(self, db_path: str = "./dociq_vectors.db") -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    chunk_id   TEXT PRIMARY KEY,
                    file_id    TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    department TEXT NOT NULL,
                    filename   TEXT NOT NULL,
                    s3_url     TEXT,
                    text_content TEXT NOT NULL,
                    embedding  BLOB NOT NULL,
                    metadata   TEXT DEFAULT '{}'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_company_dept ON rag_chunks(company_id, department)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_id ON rag_chunks(file_id)")
            conn.commit()

    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        with self._conn() as conn:
            for chunk in chunks:
                emb = stable_embed(chunk["text"])
                conn.execute("""
                    INSERT INTO rag_chunks
                        (chunk_id, file_id, company_id, department, filename, s3_url, text_content, embedding, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(chunk_id) DO UPDATE SET
                        text_content = excluded.text_content,
                        embedding    = excluded.embedding,
                        metadata     = excluded.metadata
                """, (
                    chunk["chunk_id"],
                    chunk["file_id"],
                    chunk["company_id"],
                    chunk["department"],
                    chunk["filename"],
                    chunk.get("s3_url"),
                    chunk["text"],
                    emb.tobytes(),
                    json.dumps(chunk),
                ))
            conn.commit()
        return len(chunks)

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        company_id: Optional[str] = None,
        department: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q_vec = stable_embed(query)

        where = ["1=1"]
        params: List[Any] = []
        if company_id:
            where.append("company_id = ?")
            params.append(company_id)
        if department:
            where.append("department = ?")
            params.append(department)

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM rag_chunks WHERE {' AND '.join(where)}",
                params,
            ).fetchall()

        if not rows:
            return []

        scored = []
        for row in rows:
            emb = np.frombuffer(row["embedding"], dtype=np.float32)
            sim = float(np.dot(q_vec, emb))
            if sim > 0:
                scored.append((sim, row))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for sim, row in scored[:top_k]:
            meta = json.loads(row["metadata"] or "{}")
            results.append({
                **meta,
                "chunk_id": row["chunk_id"],
                "file_id": row["file_id"],
                "company_id": row["company_id"],
                "department": row["department"],
                "filename": row["filename"],
                "s3_url": row["s3_url"],
                "text": row["text_content"],
                "similarity": round(sim, 4),
            })
        return results

    def delete_document(self, document_id: str) -> int:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM rag_chunks WHERE file_id = ?", (document_id,))
            conn.commit()
            return cur.rowcount

    def stats(self, company_id: Optional[str] = None, department: Optional[str] = None) -> Dict[str, Any]:
        where = ["1=1"]
        params: List[Any] = []
        if company_id:
            where.append("company_id = ?")
            params.append(company_id)
        if department:
            where.append("department = ?")
            params.append(department)
        with self._conn() as conn:
            row = conn.execute(
                f"SELECT COUNT(*), COUNT(DISTINCT file_id) FROM rag_chunks WHERE {' AND '.join(where)}",
                params,
            ).fetchone()
        return {"total_chunks": row[0], "documents_indexed": row[1]}


# Keep InMemoryVectorStore as a fallback (no persistence)
class InMemoryVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: List[np.ndarray] = []

    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        for chunk in chunks:
            self.chunks.append(chunk)
            self.embeddings.append(stable_embed(chunk["text"]))
        return len(chunks)

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        company_id: Optional[str] = None,
        department: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []
        q_vec = stable_embed(query)
        scores: List[tuple[float, int]] = []
        for idx, emb in enumerate(self.embeddings):
            sim = float(np.dot(q_vec, emb))
            scores.append((sim, idx))
        scores.sort(key=lambda x: x[0], reverse=True)

        results: List[Dict[str, Any]] = []
        for sim, idx in scores[: top_k * 3]:
            chunk = self.chunks[idx]
            if company_id and chunk.get("company_id") != company_id:
                continue
            if department and chunk.get("department") != department:
                continue
            if sim <= 0:
                continue
            results.append({**chunk, "similarity": round(sim, 4)})
            if len(results) >= top_k:
                break
        return results

    def delete_document(self, document_id: str) -> int:
        kept_chunks, kept_embeddings, removed = [], [], 0
        for chunk, emb in zip(self.chunks, self.embeddings):
            if chunk.get("file_id") == document_id:
                removed += 1
            else:
                kept_chunks.append(chunk)
                kept_embeddings.append(emb)
        self.chunks = kept_chunks
        self.embeddings = kept_embeddings
        return removed

    def stats(self, company_id: Optional[str] = None, department: Optional[str] = None) -> Dict[str, Any]:
        filtered = [
            c for c in self.chunks
            if (not company_id or c.get("company_id") == company_id)
            and (not department or c.get("department") == department)
        ]
        return {"total_chunks": len(filtered), "documents_indexed": len({c.get("file_id") for c in filtered})}


class PgVectorStore(BaseVectorStore):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._ensure_schema()

    def _connect(self):
        parsed = urlparse(self.database_url)
        return psycopg2.connect(
            dbname=(parsed.path or "").lstrip("/"),
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            sslmode="require" if "rds.amazonaws.com" in (parsed.hostname or "") else "prefer",
        )

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS rag_chunks (
                      chunk_id TEXT PRIMARY KEY,
                      file_id TEXT NOT NULL,
                      company_id TEXT NOT NULL,
                      department TEXT NOT NULL,
                      filename TEXT NOT NULL,
                      s3_url TEXT,
                      text_content TEXT NOT NULL,
                      embedding vector({EMBEDDING_DIM}) NOT NULL,
                      metadata JSONB DEFAULT '{{}}'::jsonb
                    );
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_company_dept ON rag_chunks(company_id, department);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding ON rag_chunks USING hnsw (embedding vector_cosine_ops);")
            conn.commit()

    @staticmethod
    def _vector_literal(vec: np.ndarray) -> str:
        return "[" + ",".join(f"{x:.7f}" for x in vec.tolist()) + "]"

    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                for chunk in chunks:
                    emb = stable_embed(chunk["text"])
                    cur.execute(
                        """
                        INSERT INTO rag_chunks (
                          chunk_id, file_id, company_id, department, filename, s3_url,
                          text_content, embedding, metadata
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector,%s)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                          text_content = EXCLUDED.text_content,
                          embedding = EXCLUDED.embedding,
                          metadata = EXCLUDED.metadata;
                        """,
                        (
                            chunk["chunk_id"],
                            chunk["file_id"],
                            chunk["company_id"],
                            chunk["department"],
                            chunk["filename"],
                            chunk.get("s3_url"),
                            chunk["text"],
                            self._vector_literal(emb),
                            Json(chunk),
                        ),
                    )
            conn.commit()
        return len(chunks)

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        company_id: Optional[str] = None,
        department: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        vec = self._vector_literal(stable_embed(query))
        where = ["1=1"]
        params: List[Any] = []
        if company_id:
            where.append("company_id = %s")
            params.append(company_id)
        if department:
            where.append("department = %s")
            params.append(department)
        params.extend([vec, top_k])
        sql = f"""
            SELECT chunk_id, file_id, company_id, department, filename, s3_url, text_content, metadata,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM rag_chunks
            WHERE {" AND ".join(where)}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        # same query vector used for select and ordering
        params = [vec] + params
        rows: List[Dict[str, Any]] = []
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                for row in cur.fetchall():
                    metadata = row[7] or {}
                    rows.append(
                        {
                            "chunk_id": row[0],
                            "file_id": row[1],
                            "company_id": row[2],
                            "department": row[3],
                            "filename": row[4],
                            "s3_url": row[5],
                            "text": row[6],
                            "similarity": float(row[8]),
                            **metadata,
                        }
                    )
        return rows

    def delete_document(self, document_id: str) -> int:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rag_chunks WHERE file_id = %s", (document_id,))
                removed = cur.rowcount
            conn.commit()
        return removed

    def stats(self, company_id: Optional[str] = None, department: Optional[str] = None) -> Dict[str, Any]:
        where = ["1=1"]
        params: List[Any] = []
        if company_id:
            where.append("company_id = %s")
            params.append(company_id)
        if department:
            where.append("department = %s")
            params.append(department)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT COUNT(*), COUNT(DISTINCT file_id) FROM rag_chunks WHERE {' AND '.join(where)}",
                    params,
                )
                chunks, files = cur.fetchone()
        return {"total_chunks": chunks, "documents_indexed": files}


class PineconeVectorStore(BaseVectorStore):
    """
    Pay-as-you-go vector store backed by Pinecone serverless.

    Required env vars:
        PINECONE_API_KEY   — your Pinecone API key
        PINECONE_INDEX     — index name (default: dociq)
        PINECONE_CLOUD     — cloud provider (default: aws)
        PINECONE_REGION    — region (default: us-east-1)
    """

    INDEX_NAME = os.getenv("PINECONE_INDEX", "dociq")
    CLOUD = os.getenv("PINECONE_CLOUD", "aws")
    REGION = os.getenv("PINECONE_REGION", "us-east-1")

    def __init__(self, api_key: str) -> None:
        try:
            from pinecone import Pinecone, ServerlessSpec
        except ImportError:
            raise ImportError("pinecone-client is not installed. Run: pip install pinecone-client")

        self._pc = Pinecone(api_key=api_key)
        existing = [idx.name for idx in self._pc.list_indexes()]
        if self.INDEX_NAME not in existing:
            self._pc.create_index(
                name=self.INDEX_NAME,
                dimension=EMBEDDING_DIM,
                metric="cosine",
                spec=ServerlessSpec(cloud=self.CLOUD, region=self.REGION),
            )
            print(f"✅ Pinecone index '{self.INDEX_NAME}' created")
        else:
            print(f"✅ Pinecone index '{self.INDEX_NAME}' ready")

        self._index = self._pc.Index(self.INDEX_NAME)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _make_filter(company_id: Optional[str], department: Optional[str]) -> Optional[Dict[str, Any]]:
        f: Dict[str, Any] = {}
        if company_id:
            f["company_id"] = {"$eq": company_id}
        if department:
            f["department"] = {"$eq": department}
        return f if f else None

    # ------------------------------------------------------------------
    # Interface
    # ------------------------------------------------------------------
    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        vectors = []
        for chunk in chunks:
            emb = stable_embed(chunk["text"]).tolist()
            metadata = {
                "file_id": chunk["file_id"],
                "company_id": chunk["company_id"],
                "department": chunk["department"],
                "filename": chunk["filename"],
                "s3_url": chunk.get("s3_url", ""),
                "text": chunk["text"][:2000],  # Pinecone metadata limit
                "uploaded_at": chunk.get("uploaded_at", ""),
                "chunk_index": chunk.get("chunk_index", 0),
            }
            vectors.append({"id": chunk["chunk_id"], "values": emb, "metadata": metadata})

        # Pinecone recommends batches of ≤100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            self._index.upsert(vectors=vectors[i : i + batch_size])

        return len(chunks)

    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        company_id: Optional[str] = None,
        department: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q_vec = stable_embed(query).tolist()
        filter_ = self._make_filter(company_id, department)

        response = self._index.query(
            vector=q_vec,
            top_k=top_k,
            include_metadata=True,
            filter=filter_,
        )

        results = []
        for match in response.get("matches", []):
            meta = match.get("metadata", {})
            results.append({
                **meta,
                "chunk_id": match["id"],
                "similarity": round(float(match["score"]), 4),
            })
        return results

    def delete_document(self, document_id: str) -> int:
        # Pinecone doesn't support delete-by-metadata directly on serverless;
        # fetch matching IDs first via a dummy query filtered by file_id.
        try:
            response = self._index.query(
                vector=[0.0] * EMBEDDING_DIM,
                top_k=1000,
                include_metadata=False,
                filter={"file_id": {"$eq": document_id}},
            )
            ids = [m["id"] for m in response.get("matches", [])]
            if ids:
                self._index.delete(ids=ids)
            return len(ids)
        except Exception as e:
            print(f"⚠️ Pinecone delete_document error: {e}")
            return 0

    def stats(self, company_id: Optional[str] = None, department: Optional[str] = None) -> Dict[str, Any]:
        try:
            desc = self._index.describe_index_stats()
            total = desc.get("total_vector_count", 0)
            # Pinecone serverless doesn't expose per-filter counts cheaply,
            # so we return the index-level total.
            return {"total_chunks": total, "documents_indexed": total}
        except Exception as e:
            print(f"⚠️ Pinecone stats error: {e}")
            return {"total_chunks": 0, "documents_indexed": 0}
