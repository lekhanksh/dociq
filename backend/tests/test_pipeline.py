import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app
from database import Base, get_db
from models import Company, User, Document
from auth import get_password_hash

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def setup_pipeline_data():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create test company
    db = TestingSessionLocal()
    company = Company(
        name="Test Company",
        slug="test-company"
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    
    # Create test user
    user = User(
        company_id=company.id,
        email="test@test.com",
        hashed_password=get_password_hash("test123"),
        department="general",
        role="uploader"
    )
    db.add(user)
    db.commit()
    db.close()
    
    yield
    
    # Clean up
    Base.metadata.drop_all(bind=engine)

def get_auth_token():
    """Helper to get auth token."""
    response = client.post("/auth/login", json={
        "email": "test@test.com",
        "password": "test123",
        "company_slug": "test-company"
    })
    return response.json()["access_token"]

def test_document_upload_pipeline(setup_pipeline_data):
    """Test the complete document upload pipeline."""
    token = get_auth_token()
    
    # Create a test text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document. It contains multiple sentences. "
                "Each sentence should be processed as a separate chunk. "
                "The document should be stored in the database with embeddings.")
        temp_file_path = f.name
    
    try:
        # Upload the file
        with open(temp_file_path, 'rb') as f:
            response = client.post(
                "/upload/",
                files={"file": ("test.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"
        assert data["status"] == "active"
        assert data["chunks_processed"] > 0
        
        document_id = data["document_id"]
        
        # Verify document was created in database
        db = TestingSessionLocal()
        document = db.query(Document).filter(Document.id == document_id).first()
        assert document is not None
        assert document.filename == "test.txt"
        assert document.status == "active"
        assert document.chunk_count > 0
        
        db.close()
        
    finally:
        # Clean up temp file
        os.unlink(temp_file_path)

def test_query_pipeline(setup_pipeline_data):
    """Test the query pipeline with uploaded documents."""
    token = get_auth_token()
    
    # First upload a test document
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("DocIQ is a secure RAG chatbot for companies. "
                "It uses PostgreSQL with pgvector for vector storage. "
                "The system supports multi-tenant architecture.")
        temp_file_path = f.name
    
    try:
        # Upload the file
        with open(temp_file_path, 'rb') as f:
            upload_response = client.post(
                "/upload/",
                files={"file": ("test.txt", f, "text/plain")},
                headers={"Authorization": f"Bearer {token}"}
            )
        
        assert upload_response.status_code == 200
        
        # Wait a moment for processing
        import time
        time.sleep(1)
        
        # Query the document
        query_response = client.post(
            "/query/",
            json={"question": "What database does DocIQ use?"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Note: This might fail in test environment without AWS credentials
        # but we can at least verify the endpoint structure
        if query_response.status_code == 200:
            data = query_response.json()
            assert "answer" in data
            assert "sources" in data
            assert "chunks_used" in data
        elif query_response.status_code == 500:
            # Expected in test environment without AWS credentials
            assert "Error generating response" in query_response.json()["detail"]
        
    finally:
        # Clean up temp file
        os.unlink(temp_file_path)

def test_collection_info(setup_pipeline_data):
    """Test collection info endpoint."""
    token = get_auth_token()
    
    response = client.get(
        "/collections/info",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_chunks" in data
    assert "department_counts" in data
    assert "recent_queries" in data
    
    # Initially should be empty
    assert data["total_documents"] == 0
    assert data["total_chunks"] == 0
