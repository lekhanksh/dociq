from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

# Try to import VECTOR, fallback to Float if not available
try:
    from pgvector.sqlalchemy import VECTOR
except ImportError:
    VECTOR = None

from database import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), default='starter')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    users = relationship("User", back_populates="company")
    documents = relationship("Document", back_populates="company")
    document_chunks = relationship("DocumentChunk", back_populates="company")
    query_logs = relationship("QueryLog", back_populates="company")
    activity_logs = relationship("ActivityLog", back_populates="company")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    department = Column(String(100), nullable=False)  # hr, finance, legal, general
    role = Column(String(50), nullable=False)          # viewer, uploader, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    company = relationship("Company", back_populates="users")
    uploaded_documents = relationship("Document", back_populates="uploaded_by_user")
    query_logs = relationship("QueryLog", back_populates="user")
    activity_logs = relationship("ActivityLog", back_populates="user")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    filename = Column(String(500), nullable=False)
    department = Column(String(100), nullable=False)
    s3_key = Column(String(1000), nullable=False)
    file_size_bytes = Column(Integer)
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default='processing')  # processing, active, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="uploaded_documents")
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    department = Column(String(100), nullable=False)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer)
    embedding = Column(VECTOR(384) if VECTOR else Text, nullable=True)  # all-MiniLM-L6-v2 = 384 dims
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    document = relationship("Document", back_populates="chunks")
    company = relationship("Company", back_populates="document_chunks")

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    department = Column(String(100))
    question = Column(Text, nullable=False)
    chunks_used = Column(Integer)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company", back_populates="query_logs")
    user = relationship("User", back_populates="query_logs")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)  # uploaded, queried, deleted
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    department = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    company = relationship("Company", back_populates="activity_logs")
    user = relationship("User", back_populates="activity_logs")
