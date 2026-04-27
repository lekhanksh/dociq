CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_chunks (
  chunk_id TEXT PRIMARY KEY,
  file_id TEXT NOT NULL,
  company_id TEXT NOT NULL,
  department TEXT NOT NULL,
  filename TEXT NOT NULL,
  s3_url TEXT,
  text_content TEXT NOT NULL,
  embedding vector(384) NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_company_dept
  ON rag_chunks(company_id, department);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding_hnsw
  ON rag_chunks USING hnsw (embedding vector_cosine_ops);
