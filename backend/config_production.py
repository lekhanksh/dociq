"""
Production Configuration Management
Centralized configuration with validation and environment-specific settings
"""
import os
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """Application settings with validation"""
    
    # Environment
    ENV: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # API
    API_VERSION: str = Field(default="v1", description="API version")
    API_TITLE: str = Field(default="DocIQ RAG API", description="API title")
    API_DESCRIPTION: str = Field(default="Private & Secure Company RAG Chatbot", description="API description")
    
    # Security
    JWT_SECRET: str = Field(..., min_length=32, description="JWT secret key (min 32 chars)")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="Access token expiration (24 hours)")
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(default=10080, description="Refresh token expiration (7 days)")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:8080", "http://localhost:3000"],
        description="Allowed CORS origins"
    )
    
    # Database
    DATABASE_URL: str = Field(..., description="Database connection URL")
    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout (seconds)")
    
    # Vector Store
    VECTOR_BACKEND: str = Field(default="memory", description="Vector backend: memory or pgvector")
    VECTOR_DIMENSION: int = Field(default=384, description="Vector embedding dimension")
    
    # AWS
    AWS_REGION: str = Field(default="us-east-1", description="AWS region")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS access key")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS secret key")
    
    # S3
    S3_BUCKET_NAME: str = Field(..., description="S3 bucket name")
    S3_MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024, description="Max file size (100MB)")
    S3_ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".docx", ".doc", ".txt", ".md"],
        description="Allowed file extensions"
    )
    
    # Bedrock
    BEDROCK_MODEL_ID: str = Field(default="amazon.nova-pro-v1:0", description="Bedrock model ID")
    BEDROCK_MAX_TOKENS: int = Field(default=2000, description="Max tokens for Bedrock response")
    BEDROCK_TEMPERATURE: float = Field(default=0.3, description="Bedrock temperature")
    BEDROCK_TIMEOUT: int = Field(default=60, description="Bedrock timeout (seconds)")
    BEDROCK_RETRY_ATTEMPTS: int = Field(default=3, description="Bedrock retry attempts")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, description="Rate limit window (seconds)")
    RATE_LIMIT_REQUESTS_PER_WINDOW: int = Field(default=100, description="Requests per window")
    
    # Caching
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL for caching")
    CACHE_TTL_SECONDS: int = Field(default=3600, description="Cache TTL (1 hour)")
    CACHE_QUERY_RESPONSES: bool = Field(default=True, description="Cache query responses")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    LOG_FORMAT: str = Field(default="json", description="Log format: json or text")
    AUDIT_LOG_PATH: str = Field(default="./logs/audit.log", description="Audit log path")
    
    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, description="Enable Prometheus metrics")
    METRICS_PORT: int = Field(default=9090, description="Metrics port")
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    # Features
    ENABLE_DOCUMENT_PREVIEW: bool = Field(default=True, description="Enable document preview")
    ENABLE_BULK_UPLOAD: bool = Field(default=True, description="Enable bulk upload")
    ENABLE_WEBHOOKS: bool = Field(default=False, description="Enable webhooks")
    
    # Subscription Limits (Free Tier)
    FREE_TIER_MAX_DOCUMENTS: int = Field(default=10, description="Max documents for free tier")
    FREE_TIER_MAX_QUERIES_PER_MONTH: int = Field(default=50, description="Max queries per month for free tier")
    FREE_TIER_MAX_STORAGE_MB: int = Field(default=100, description="Max storage MB for free tier")
    FREE_TIER_MAX_USERS: int = Field(default=1, description="Max users for free tier")
    
    # Subscription Limits (Starter Tier)
    STARTER_TIER_MAX_DOCUMENTS: int = Field(default=100, description="Max documents for starter tier")
    STARTER_TIER_MAX_QUERIES_PER_MONTH: int = Field(default=500, description="Max queries per month for starter tier")
    STARTER_TIER_MAX_STORAGE_MB: int = Field(default=1000, description="Max storage MB for starter tier")
    STARTER_TIER_MAX_USERS: int = Field(default=5, description="Max users for starter tier")
    
    # Subscription Limits (Pro Tier)
    PRO_TIER_MAX_DOCUMENTS: int = Field(default=-1, description="Max documents for pro tier (-1 = unlimited)")
    PRO_TIER_MAX_QUERIES_PER_MONTH: int = Field(default=2000, description="Max queries per month for pro tier")
    PRO_TIER_MAX_STORAGE_MB: int = Field(default=10000, description="Max storage MB for pro tier")
    PRO_TIER_MAX_USERS: int = Field(default=20, description="Max users for pro tier")
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @validator("S3_ALLOWED_EXTENSIONS", pre=True)
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",") if ext.strip()]
        return v
    
    @validator("ENV")
    def validate_env(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENV must be one of {allowed}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    """Get validated settings from environment"""
    return Settings(
        ENV=os.getenv("ENV", "development"),
        DEBUG=os.getenv("DEBUG", "false").lower() == "true",
        JWT_SECRET=os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production"),
        DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///./dociq.db"),
        S3_BUCKET_NAME=os.getenv("S3_BUCKET_NAME", "your-company-documents"),
        AWS_REGION=os.getenv("AWS_REGION", "us-east-1"),
        BEDROCK_MODEL_ID=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"),
        CORS_ORIGINS=os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:3000"),
        RATE_LIMIT_WINDOW_SECONDS=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
        RATE_LIMIT_REQUESTS_PER_WINDOW=int(os.getenv("RATE_LIMIT_REQUESTS_PER_WINDOW", "100")),
        REDIS_URL=os.getenv("REDIS_URL"),
        AUDIT_LOG_PATH=os.getenv("AUDIT_LOG_PATH", "./logs/audit.log"),
        SENTRY_DSN=os.getenv("SENTRY_DSN"),
    )


# Global settings instance
settings = get_settings()
