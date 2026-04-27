import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app
from database import Base, get_db
from models import Company, User
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
def setup_test_data():
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
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        department="general",
        role="admin"
    )
    db.add(user)
    db.commit()
    db.close()
    
    yield
    
    # Clean up
    Base.metadata.drop_all(bind=engine)

def test_login_success(setup_test_data):
    """Test successful login."""
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword",
        "company_slug": "test-company"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"

def test_login_invalid_credentials(setup_test_data):
    """Test login with invalid credentials."""
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
        "company_slug": "test-company"
    })
    
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]

def test_login_invalid_company(setup_test_data):
    """Test login with invalid company slug."""
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword",
        "company_slug": "invalid-company"
    })
    
    assert response.status_code == 401
    assert "Invalid company slug" in response.json()["detail"]

def test_get_current_user(setup_test_data):
    """Test getting current user info."""
    # First login to get token
    login_response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword",
        "company_slug": "test-company"
    })
    token = login_response.json()["access_token"]
    
    # Get current user
    response = client.get("/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["company_name"] == "Test Company"

def test_invalid_token(setup_test_data):
    """Test using invalid token."""
    response = client.get("/auth/me", headers={
        "Authorization": "Bearer invalid-token"
    })
    
    assert response.status_code == 401
