import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import get_config
from models import User

config = get_config()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=config["jwt_expiry_hours"])
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config["jwt_secret"], algorithm="HS256")
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, config["jwt_secret"], algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(db: Session, token: str) -> User:
    """Get current user from JWT token."""
    payload = verify_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def authenticate_user(db: Session, email: str, password: str, company_id: str) -> Optional[User]:
    """Authenticate user with email and password."""
    user = db.query(User).filter(
        User.email == email,
        User.company_id == company_id,
        User.is_active == True
    ).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user
