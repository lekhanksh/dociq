from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import User, Company
from auth import authenticate_user, create_access_token, get_current_user

router = APIRouter()
security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str
    password: str
    company_slug: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    department: str
    role: str
    company_name: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    # Find company by slug
    company = db.query(Company).filter(
        Company.slug == request.company_slug,
        Company.is_active == True
    ).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid company slug"
        )
    
    # Authenticate user
    user = authenticate_user(db, request.email, request.password, str(company.id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role,
            "company_name": company.name
        }
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user information."""
    user = get_current_user(db, credentials.credentials)
    company = db.query(Company).filter(Company.id == user.company_id).first()
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        role=user.role,
        company_name=company.name if company else ""
    )

@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Refresh JWT token."""
    user = get_current_user(db, credentials.credentials)
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
