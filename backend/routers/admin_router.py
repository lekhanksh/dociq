from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from passlib.context import CryptContext

from database import get_db
from models import User, Company
from auth import get_current_user, get_password_hash

router = APIRouter()
security = HTTPBearer()

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str]
    department: str
    role: str  # viewer, uploader, admin

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    department: str
    role: str
    is_active: bool
    created_at: str

class CompanyCreate(BaseModel):
    name: str
    slug: str
    plan: str = "starter"

class CompanyResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    is_active: bool
    created_at: str

def require_admin(user: User):
    """Require user to be admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)."""
    current_user = get_current_user(db, credentials.credentials)
    require_admin(current_user)
    
    # Check if email already exists for this company
    existing_user = db.query(User).filter(
        User.email == user_data.email,
        User.company_id == current_user.company_id
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists for this company"
        )
    
    # Create user
    user = User(
        company_id=current_user.company_id,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        department=user_data.department,
        role=user_data.role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """List all users in the company (admin only)."""
    current_user = get_current_user(db, credentials.credentials)
    require_admin(current_user)
    
    users = db.query(User).filter(
        User.company_id == current_user.company_id
    ).all()
    
    return [
        UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            department=user.department,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]

@router.post("/companies", response_model=CompanyResponse)
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db)
):
    """Create a new company (super admin only - for initial setup)."""
    # Check if slug already exists
    existing_company = db.query(Company).filter(
        Company.slug == company_data.slug
    ).first()
    
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company slug already exists"
        )
    
    # Create company
    company = Company(
        name=company_data.name,
        slug=company_data.slug,
        plan=company_data.plan
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    
    return CompanyResponse(
        id=str(company.id),
        name=company.name,
        slug=company.slug,
        plan=company.plan,
        is_active=company.is_active,
        created_at=company.created_at.isoformat()
    )
