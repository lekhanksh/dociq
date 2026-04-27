from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_config

config = get_config()

engine = create_engine(
    config["database_url"],
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,        # reconnects if DB connection dropped
    pool_recycle=3600,         # recycle connections every hour
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency — yields a DB session, closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
