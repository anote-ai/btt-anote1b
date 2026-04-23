"""Evaluation policy: full-coverage REST submissions, bootstrap CI, seed merge helper."""

import pytest

from evaluators import TextClassificationEvaluator
from evaluation_service import (
    bootstrap_primary_metric_ci,
    validate_complete_predictions,
    validate_prediction_ids_unique,
)
from seed_data import SAMPLE_DATASETS, merged_ground_truth_for_sample_config


def test_merged_ground_truth_includes_extras_for_ag_news():
    cfg = next(d for d in SAMPLE_DATASETS if d["name"].startswith("AG News"))
    merged = merged_ground_truth_for_sample_config(cfg)
    assert len(merged) >= len(cfg["ground_truth"])


def test_validate_complete_predictions_ok():
    gt = [
        {"id": "1", "question": "a", "answer": "x"},
        {"id": "2", "question": "b", "answer": "y"},
    ]
    preds = [
        {"id": "1", "prediction": "x"},
        {"id": "2", "prediction": "y"},
    ]
    validate_complete_predictions(gt, preds)


def test_validate_complete_predictions_missing_id():
    gt = [{"id": "1", "answer": "a"}, {"id": "2", "answer": "b"}]
    preds = [{"id": "1", "prediction": "a"}]
    with pytest.raises(ValueError, match="exactly one entry"):
        validate_complete_predictions(gt, preds)


def test_validate_prediction_ids_unique_rejects_duplicates():
    preds = [
        {"id": "1", "prediction": "a"},
        {"id": "1", "prediction": "b"},
    ]
    with pytest.raises(ValueError, match="Duplicate"):
        validate_prediction_ids_unique(preds)


def test_bootstrap_ci_non_degenerate():
    ev = TextClassificationEvaluator()
    gt = [
        {"id": "1", "question": "a", "answer": "positive"},
        {"id": "2", "question": "b", "answer": "negative"},
        {"id": "3", "question": "c", "answer": "positive"},
        {"id": "4", "question": "d", "answer": "negative"},
    ]
    preds = [
        {"id": "1", "prediction": "positive"},
        {"id": "2", "prediction": "negative"},
        {"id": "3", "prediction": "negative"},
        {"id": "4", "prediction": "positive"},
    ]
    ci = bootstrap_primary_metric_ci(ev, gt, preds, "accuracy", n_bootstrap=400, seed=7)
    assert ci is not None
    lo_s, hi_s = ci.split(" - ")
    lo, hi = float(lo_s), float(hi_s)
    assert lo <= hi
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0
