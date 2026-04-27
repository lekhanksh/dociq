from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Dict, Any

from database import get_db
from models import User, Document, QueryLog
from auth import get_current_user

router = APIRouter()
security = HTTPBearer()

class CollectionInfo(BaseModel):
    total_documents: int
    total_chunks: int
    department_counts: Dict[str, int]
    recent_queries: List[Dict[str, Any]]

@router.get("/info", response_model=CollectionInfo)
async def get_collection_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get information about the document collection."""
    user = get_current_user(db, credentials.credentials)
    
    # Get document counts by department
    dept_filter = "" if user.role == "admin" else "WHERE department = :dept"
    dept_params = {"company_id": user.company_id}
    if user.role != "admin":
        dept_params["dept"] = user.department
    
    dept_query = text(f"""
        SELECT department, COUNT(*) as count
        FROM documents
        WHERE company_id = :company_id
        {"" if user.role == "admin" else "AND department = :dept"}
        GROUP BY department
    """)
    
    dept_results = db.execute(dept_query, dept_params).fetchall()
    department_counts = {row.department: row.count for row in dept_results}
    
    # Get total documents
    total_docs_query = text(f"""
        SELECT COUNT(*) as count
        FROM documents
        WHERE company_id = :company_id
        {"" if user.role == "admin" else "AND department = :dept"}
    """)
    
    total_docs_result = db.execute(total_docs_query, dept_params).fetchone()
    total_documents = total_docs_result.count
    
    # Get total chunks
    total_chunks_query = text(f"""
        SELECT COUNT(*) as count
        FROM document_chunks
        WHERE company_id = :company_id
        {"" if user.role == "admin" else "AND department = :dept"}
    """)
    
    total_chunks_result = db.execute(total_chunks_query, dept_params).fetchone()
    total_chunks = total_chunks_result.count
    
    # Get recent queries
    recent_query = text(f"""
        SELECT question, created_at, response_time_ms
        FROM query_logs
        WHERE company_id = :company_id
        {"" if user.role == "admin" else "AND department = :dept"}
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    recent_results = db.execute(recent_query, dept_params).fetchall()
    recent_queries = [
        {
            "question": row.question,
            "created_at": row.created_at.isoformat(),
            "response_time_ms": row.response_time_ms
        }
        for row in recent_results
    ]
    
    return CollectionInfo(
        total_documents=total_documents,
        total_chunks=total_chunks,
        department_counts=department_counts,
        recent_queries=recent_queries
    )
