from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
import time

from database import get_db
from models import User, QueryLog, ActivityLog
from auth import get_current_user
from embedder import embed_one
from vector_store import query_chunks
from bedrock_client import generate_response

router = APIRouter()
security = HTTPBearer()

class QueryRequest(BaseModel):
    question: str

class SourceDocument(BaseModel):
    filename: str
    page: int
    department: str
    similarity_score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    chunks_used: int

@router.post("/", response_model=QueryResponse)
async def query_documents(
    query: QueryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Query documents using RAG."""
    user = get_current_user(db, credentials.credentials)
    
    start_time = time.time()
    
    # Generate query embedding
    query_embedding = embed_one(query.question)
    
    # Search for relevant chunks
    chunks = query_chunks(
        db=db,
        company_id=str(user.company_id),
        department=user.department,
        role=user.role,
        query_embedding=query_embedding,
        n=5
    )
    
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant documents found"
        )
    
    # Build context from chunks
    context = "\n\n".join([chunk["text"] for chunk in chunks])
    
    # Generate response using Bedrock
    try:
        answer = generate_response(context, query.question)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating response: {str(e)}"
        )
    
    # Prepare sources
    sources = [
        SourceDocument(
            filename=chunk["meta"]["filename"],
            page=chunk["meta"]["page"] or 0,
            department=chunk["meta"]["dept"],
            similarity_score=chunk["score"]
        )
        for chunk in chunks
    ]
    
    # Log the query
    response_time_ms = int((time.time() - start_time) * 1000)
    query_log = QueryLog(
        company_id=user.company_id,
        user_id=user.id,
        department=user.department,
        question=query.question,
        chunks_used=len(chunks),
        response_time_ms=response_time_ms
    )
    db.add(query_log)
    
    # Log activity
    activity_log = ActivityLog(
        company_id=user.company_id,
        user_id=user.id,
        action="queried",
        department=user.department
    )
    db.add(activity_log)
    db.commit()
    
    return QueryResponse(
        answer=answer,
        sources=sources,
        chunks_used=len(chunks)
    )
