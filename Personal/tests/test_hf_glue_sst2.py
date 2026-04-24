"""
GLUE SST-2 (nyu-mll/glue, sst2) import recipe and evaluator integration.
"""
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database
from database import init_db
from seed_data import clear_database
from models import Submission, SubmissionStatus
from evaluators import get_evaluator
from evaluation_service import evaluate_submission
from dataset_import import persist_imported_dataset, DatasetImportError
from hf_dataset_recipes import (
    hf_rows_to_glue_sst2_ground_truth,
    sst2_row_to_ground_truth_item,
    build_glue_sst2_import_payload,
    try_recipe_import,
)
from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    clear_database()
    try:
        yield
    finally:
        clear_database()


def test_sst2_label_mapping_and_stable_ids():
    rows = [
        {"sentence": "great", "label": 1},
        {"sentence": "awful", "label": 0},
    ]
    gt = hf_rows_to_glue_sst2_ground_truth(rows, "validation")
    assert gt[0]["id"] == "sst2_validation_0"
    assert gt[0]["answer"] == "positive"
    assert gt[0]["sentence"] == "great"
    assert gt[0]["metadata"]["source"] == "huggingface"
    assert gt[0]["metadata"]["dataset_name"] == "nyu-mll/glue"
    assert gt[0]["metadata"]["config"] == "sst2"
    assert gt[1]["answer"] == "negative"


def test_sst2_rejects_unlabeled_label():
    with pytest.raises(ValueError, match="no usable label"):
        sst2_row_to_ground_truth_item(0, "test", "x", -1)


def test_try_recipe_import_returns_payload(monkeypatch):
    def fake_load(split: str, limit=None):
        rows = [
            {"sentence": "a", "label": 1},
            {"sentence": "b", "label": 0},
        ]
        if limit is not None:
            rows = rows[:limit]
        return hf_rows_to_glue_sst2_ground_truth(rows, split)

    monkeypatch.setattr("hf_dataset_recipes.load_glue_sst2_ground_truth", fake_load)
    payload = try_recipe_import(
        "nyu-mll/glue",
        "sst2",
        "validation",
        limit=2,
        leaderboard_dataset_id="hf_test_only",
        display_name="Mini SST-2",
    )
    assert payload is not None
    assert payload["id"] == "hf_test_only"
    assert payload["name"] == "Mini SST-2"
    assert payload["task_type"] == "text_classification"
    assert payload["primary_metric"] == "accuracy"
    assert len(payload["ground_truth"]) == 2


def test_persist_duplicate_id_errors():
    rows = [{"sentence": "a", "label": 1}, {"sentence": "b", "label": 0}]
    gt = hf_rows_to_glue_sst2_ground_truth(rows, "validation")
    payload = {
        "id": "dup_test",
        "name": "Dup Test",
        "description": "d",
        "url": "https://huggingface.co/datasets/nyu-mll/glue",
        "task_type": "text_classification",
        "test_set_public": False,
        "labels_public": False,
        "primary_metric": "accuracy",
        "additional_metrics": ["f1"],
        "ground_truth": gt,
    }
    db = database.SessionLocal()
    try:
        persist_imported_dataset(db, payload)
        with pytest.raises(DatasetImportError, match="already exists"):
            persist_imported_dataset(db, payload)
    finally:
        db.close()


def test_submission_scores_match_evaluator_not_hand_authored():
    """Scores must come from evaluate_submission / evaluator only."""
    rows = [
        {"sentence": "good", "label": 1},
        {"sentence": "bad", "label": 0},
        {"sentence": "fine", "label": 1},
    ]
    gt = hf_rows_to_glue_sst2_ground_truth(rows, "validation")
    payload = {
        "id": "hf_sst2_unit",
        "name": "SST-2 Unit",
        "description": "unit",
        "url": "https://huggingface.co/datasets/nyu-mll/glue",
        "task_type": "text_classification",
        "test_set_public": False,
        "labels_public": False,
        "primary_metric": "accuracy",
        "additional_metrics": ["f1", "precision", "recall"],
        "ground_truth": gt,
    }
    db = database.SessionLocal()
    try:
        ds = persist_imported_dataset(db, payload)
        predictions = [
            {"id": "sst2_validation_0", "prediction": "positive"},
            {"id": "sst2_validation_1", "prediction": "negative"},
            {"id": "sst2_validation_2", "prediction": "positive"},
        ]
        ev = get_evaluator("text_classification")
        expected = ev.evaluate(ds.ground_truth, predictions)

        submission_id = str(uuid.uuid4())
        sub = Submission(
            id=submission_id,
            dataset_id=ds.id,
            model_name="oracle_unit",
            predictions=predictions,
            status=SubmissionStatus.PENDING,
            is_internal=False,
        )
        db.add(sub)
        db.commit()

        evaluate_submission(submission_id)
        db.refresh(sub)

        assert sub.status == SubmissionStatus.COMPLETED
        assert sub.primary_score is not None
        assert sub.primary_score == pytest.approx(expected["accuracy"])
        assert sub.detailed_scores["accuracy"] == pytest.approx(expected["accuracy"])
    finally:
        db.close()


def test_majority_baseline_matches_evaluator(monkeypatch):
    """Sanity baseline: all majority class — score equals evaluator on same preds."""
    rows = [
        {"sentence": "a", "label": 1},
        {"sentence": "b", "label": 1},
        {"sentence": "c", "label": 0},
    ]
    gt = hf_rows_to_glue_sst2_ground_truth(rows, "validation")
    payload = {
        "id": "hf_sst2_maj",
        "name": "SST-2 Maj",
        "description": "unit",
        "url": "https://huggingface.co/datasets/nyu-mll/glue",
        "task_type": "text_classification",
        "test_set_public": False,
        "labels_public": False,
        "primary_metric": "accuracy",
        "additional_metrics": ["f1", "precision", "recall"],
        "ground_truth": gt,
    }
    db = database.SessionLocal()
    try:
        ds = persist_imported_dataset(db, payload)
        maj = "positive"
        predictions = [{"id": item["id"], "prediction": maj} for item in gt]
        ev = get_evaluator("text_classification")
        expected = ev.evaluate(ds.ground_truth, predictions)

        submission_id = str(uuid.uuid4())
        sub = Submission(
            id=submission_id,
            dataset_id=ds.id,
            model_name="majority_baseline",
            predictions=predictions,
            status=SubmissionStatus.PENDING,
            is_internal=True,
        )
        db.add(sub)
        db.commit()
        evaluate_submission(submission_id)
        db.refresh(sub)

        assert sub.status == SubmissionStatus.COMPLETED
        assert sub.primary_score == pytest.approx(expected["accuracy"])
    finally:
        db.close()


def test_leaderboard_entry_matches_evaluator(client):
    """Leaderboard API exposes primary_score from evaluator, not hand-written."""
    rows = [{"sentence": "ok", "label": 1}]
    gt = hf_rows_to_glue_sst2_ground_truth(rows, "validation")
    payload = {
        "id": "hf_sst2_lb",
        "name": "SST-2 LB",
        "description": "unit",
        "url": "https://huggingface.co/datasets/nyu-mll/glue",
        "task_type": "text_classification",
        "test_set_public": False,
        "labels_public": False,
        "primary_metric": "accuracy",
        "additional_metrics": ["f1", "precision", "recall"],
        "ground_truth": gt,
    }
    db = database.SessionLocal()
    ds_id = None
    try:
        ds = persist_imported_dataset(db, payload)
        ds_id = ds.id
        predictions = [{"id": "sst2_validation_0", "prediction": "positive"}]
        ev = get_evaluator("text_classification")
        expected_acc = ev.evaluate(ds.ground_truth, predictions)["accuracy"]

        submission_id = str(uuid.uuid4())
        sub = Submission(
            id=submission_id,
            dataset_id=ds.id,
            model_name="lb_check",
            predictions=predictions,
            status=SubmissionStatus.PENDING,
            is_internal=False,
        )
        db.add(sub)
        db.commit()
        evaluate_submission(submission_id)
    finally:
        db.close()

    r = client.get(f"/api/leaderboard/{ds_id}")
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["score"] == pytest.approx(expected_acc)
    assert entries[0]["model_name"] == "lb_check"


def test_build_payload_monkeypatched_no_network(monkeypatch):
    """build_glue_sst2_import_payload without hitting Hugging Face."""

    def fake_load(split: str, limit=None):
        raw = [
            {"sentence": "x", "label": 0},
            {"sentence": "y", "label": 1},
        ]
        if limit is not None:
            raw = raw[:limit]
        return hf_rows_to_glue_sst2_ground_truth(raw, split)

    monkeypatch.setattr(
        "hf_dataset_recipes.load_glue_sst2_ground_truth",
        fake_load,
    )
    out = build_glue_sst2_import_payload(
        split="validation",
        limit=2,
        leaderboard_dataset_id="x",
        display_name="Y",
    )
    assert len(out["ground_truth"]) == 2
    assert out["ground_truth"][0]["answer"] == "negative"
