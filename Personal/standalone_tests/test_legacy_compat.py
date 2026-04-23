"""Legacy /public and /api/leaderboard routes (Company CRA contract)."""
import importlib
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Patch database *before* main imports for TestClient startup.
import database as dbmod
from models import Base

_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_test_session = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


def _init():
    Base.metadata.create_all(bind=_test_engine)


dbmod.engine = _test_engine
dbmod.SessionLocal = _test_session
dbmod.init_db = _init

if "main" in sys.modules:
    importlib.reload(sys.modules["main"])
from main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=_test_engine)
    _init()
    with TestClient(app) as c:
        yield c


def test_public_get_leaderboard_empty(client):
    r = client.get("/public/get_leaderboard")
    assert r.status_code == 200
    assert r.json() == {"success": True, "leaderboard": []}


def test_legacy_translation_submit_roundtrip(client):
    payload = {
        "name": "demo_mt",
        "task_type": "translation",
        "evaluation_metric": "bleu",
        "reference_data": {
            "source_texts": ["Hello", "Good morning"],
            "reference_translations": ["Hola", "Buenos días"],
        },
    }
    r = client.post("/public/add_dataset", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["success"] is True

    r = client.get("/public/get_source_sentences", params={"dataset_name": "demo_mt", "count": 2, "start_idx": 0})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["success"] and data["count"] == 2

    r = client.post(
        "/public/submit_model",
        json={
            "benchmarkDatasetName": "demo_mt",
            "modelName": "test-model",
            "modelResults": ["Hola", "Buenos días"],
            "sentence_ids": [0, 1],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert "score" in body
    assert body["score"] >= 0
