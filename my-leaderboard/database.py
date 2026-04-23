"""
Database setup and session management
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base

# Load my-leaderboard/.env (does not override existing OS env vars)
_PKG_DIR = Path(__file__).resolve().parent
load_dotenv(_PKG_DIR / ".env")

# Stable SQLite path: always under this package, regardless of uvicorn cwd
_DEFAULT_SQLITE_PATH = (_PKG_DIR / "leaderboard.db").resolve()
_DEFAULT_SQLITE_URL = f"sqlite:///{_DEFAULT_SQLITE_PATH.as_posix()}"

DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_SQLITE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")


def get_db() -> Session:
    """
    Dependency for FastAPI to get database session
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
