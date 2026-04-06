"""
Shared pytest fixtures for all tests
"""
import os
from pathlib import Path

# Before importing database: isolated test DB + auth default
os.environ.setdefault("LEADERBOARD_AUTH_MODE", "off")
_test_db = Path(__file__).resolve().parent / "test_leaderboard.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.as_posix()}"

import pytest
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from models import Base, Dataset, Submission


@pytest.fixture(scope="function", autouse=True)
def clean_db():
    """Clean database before each test (same engine as the FastAPI app)."""
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        db.query(Submission).delete()
        db.query(Dataset).delete()
        db.commit()
    finally:
        db.close()

    yield

    db = SessionLocal()
    try:
        db.query(Submission).delete()
        db.query(Dataset).delete()
        db.commit()
    finally:
        db.close()
