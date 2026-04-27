from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
import boto3
import uuid
import tempfile
import os
from typing import List

from database import get_db
from models import User, Document, ActivityLog
from auth import get_current_user
from parser import parse_file
from embedder import embed_batch
from vector_store import upsert_chunks
from config import get_config

router = APIRouter()
security = HTTPBearer()

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_processed: int
    status: str

def get_s3_client():
    """Get S3 client."""
    config = get_config()
    return boto3.client("s3", region_name=config["aws_region"])

def validate_file(file: UploadFile) -> None:
    """Validate file type and size."""
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
    allowed_extensions = [".pdf", ".docx", ".txt"]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed types: PDF, DOCX, TXT"
        )
    
    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit"
        )

@router.post("/", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Upload and process a document."""
    user = get_current_user(db, credentials.credentials)
    
    # Validate file
    validate_file(file)
    
    # Get file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    file_type = file_extension[1:]  # Remove the dot
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # Parse document
        chunks = parse_file(temp_file_path, file_type)
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content found in document"
            )
        
        # Generate embeddings
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = embed_batch(chunk_texts)
        
        # Create document record
        document = Document(
            company_id=user.company_id,
            uploaded_by=user.id,
            filename=file.filename,
            department=user.department,
            s3_key="",  # Will be set after S3 upload
            file_size_bytes=file.size,
            chunk_count=len(chunks),
            status="processing"
        )
        db.add(document)
        db.flush()  # Get the document ID
        
        # Upload to S3
        s3_client = get_s3_client()
        config = get_config()
        s3_key = f"{user.company_id}/{document.id}/{file.filename}"
        
        with open(temp_file_path, "rb") as f:
            s3_client.upload_fileobj(f, config["s3_bucket"], s3_key)
        
        # Update document with S3 key
        document.s3_key = s3_key
        document.status = "active"
        
        # Store chunks with embeddings
        upsert_chunks(
            db=db,
            company_id=str(user.company_id),
            document_id=str(document.id),
            department=user.department,
            chunks=chunks,
            embeddings=embeddings
        )
        
        # Log activity
        activity_log = ActivityLog(
            company_id=user.company_id,
            user_id=user.id,
            action="uploaded",
            document_id=document.id,
            department=user.department
        )
        db.add(activity_log)
        db.commit()
        
        return UploadResponse(
            document_id=str(document.id),
            filename=file.filename,
            chunks_processed=len(chunks),
            status="active"
        )
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Delete a document."""
    user = get_current_user(db, credentials.credentials)
    
    # Find document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == user.company_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check permissions (admin or uploader)
    if user.role != "admin" and document.uploaded_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document"
        )
    
    # Delete from S3
    try:
        s3_client = get_s3_client()
        config = get_config()
        s3_client.delete_object(Bucket=config["s3_bucket"], Key=document.s3_key)
    except Exception as e:
        # Log error but continue with database deletion
        print(f"Error deleting from S3: {e}")
    
    # Delete chunks (will cascade)
    from vector_store import delete_document_chunks
    delete_document_chunks(db, document_id)
    
    # Delete document
    db.delete(document)
    
    # Log activity
    activity_log = ActivityLog(
        company_id=user.company_id,
        user_id=user.id,
        action="deleted",
        document_id=document.id,
        department=document.department
    )
    db.add(activity_log)
    db.commit()
    
    return {"message": "Document deleted successfully"}
