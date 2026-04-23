"""
Background evaluation service for processing submissions

This module handles the async evaluation of submissions in a queue.
For production, consider using Celery or similar for distributed task processing.

Prediction coverage:
- ``POST /api/submissions`` requires a prediction for every ground-truth example
  (see ``validate_complete_predictions``), with unique example ids.
- Legacy ``POST /public/submit_model`` may submit a subset of examples by design;
  evaluators score only examples that have predictions (see evaluators.py).
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional

from database import SessionLocal
from models import Submission, Dataset, SubmissionStatus
from evaluators import get_evaluator
from datetime import datetime
import traceback
from scipy import stats
import numpy as np


def validate_prediction_ids_unique(predictions: List[Dict[str, Any]]) -> None:
    """Raise ValueError if any prediction id is duplicated."""
    ids = [p["id"] for p in predictions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate prediction ids are not allowed")


def validate_complete_predictions(
    ground_truth: List[Dict[str, Any]], predictions: List[Dict[str, Any]]
) -> None:
    """
    Require exactly one prediction per ground-truth row (REST API contract).

    Raises:
        ValueError: missing ids, extra ids, duplicates, or empty predictions.
    """
    if not predictions:
        raise ValueError("predictions cannot be empty")
    validate_prediction_ids_unique(predictions)
    gt_ids = {item["id"] for item in ground_truth}
    pred_ids = {p["id"] for p in predictions}
    if pred_ids != gt_ids:
        missing = gt_ids - pred_ids
        extra = pred_ids - gt_ids
        parts = []
        if missing:
            sample = sorted(missing)
            suffix = "…" if len(sample) > 15 else ""
            parts.append(
                f"missing {len(missing)} example id(s), e.g. {sample[:15]}{suffix}"
            )
        if extra:
            sample = sorted(extra)
            suffix = "…" if len(sample) > 15 else ""
            parts.append(
                f"{len(extra)} unknown id(s) not in dataset, e.g. {sample[:15]}{suffix}"
            )
        raise ValueError(
            "Predictions must include exactly one entry per test example. "
            + "; ".join(parts)
        )


def bootstrap_primary_metric_ci(
    evaluator,
    ground_truth: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
    primary_metric: str,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Optional[str]:
    """
    Nonparametric bootstrap confidence interval for the primary metric by
    resampling test examples with replacement and re-running the evaluator.
    """
    n = len(ground_truth)
    if n < 2:
        return None
    pred_map = {p["id"]: p for p in predictions}
    rng = np.random.default_rng(seed)
    samples: List[float] = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        sub_gt = [ground_truth[i] for i in idx]
        sub_pred = [pred_map[ground_truth[i]["id"]] for i in idx if ground_truth[i]["id"] in pred_map]
        try:
            scores = evaluator.evaluate(sub_gt, sub_pred)
            m = scores.get(primary_metric)
            if m is not None:
                samples.append(float(m))
        except Exception:
            continue
    if len(samples) < max(30, n_bootstrap // 20):
        return None
    low_p = (1.0 - confidence) / 2.0
    hi_p = 1.0 - low_p
    lo, hi = np.percentile(samples, [100.0 * low_p, 100.0 * hi_p])
    return f"{float(lo):.4f} - {float(hi):.4f}"


def compute_confidence_interval(scores: list, confidence=0.95) -> str:
    """
    Compute confidence interval for scores using bootstrap or normal approximation
    
    Args:
        scores: List of individual scores
        confidence: Confidence level (default 0.95 for 95% CI)
        
    Returns:
        String representation of CI, e.g., "0.85 - 0.93"
    """
    if not scores or len(scores) < 2:
        return None
    
    mean = np.mean(scores)
    std_err = stats.sem(scores)
    
    # Use t-distribution for small samples
    ci = stats.t.interval(
        confidence,
        len(scores) - 1,
        loc=mean,
        scale=std_err
    )
    
    return f"{ci[0]:.2f} - {ci[1]:.2f}"


def evaluate_submission(submission_id: str):
    """
    Evaluate a submission against ground truth
    
    This function:
    1. Loads the submission and dataset
    2. Runs the appropriate evaluator
    3. Computes scores and confidence intervals
    4. Updates the submission with results
    """
    db = SessionLocal()
    
    try:
        # Get submission
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            print(f"Submission {submission_id} not found")
            return
        
        # Update status to processing
        submission.status = SubmissionStatus.PROCESSING
        db.commit()
        
        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == submission.dataset_id).first()
        if not dataset:
            raise Exception(f"Dataset {submission.dataset_id} not found")
        
        # Validate prediction ids (unique; must be known ground-truth ids)
        validate_prediction_ids_unique(submission.predictions)
        gt_ids = {item["id"] for item in dataset.ground_truth}
        pred_ids = {item["id"] for item in submission.predictions}

        if not pred_ids.issubset(gt_ids):
            unknown = pred_ids - gt_ids
            raise Exception(f"Invalid prediction IDs: {unknown}")
        
        # Get appropriate evaluator
        evaluator = get_evaluator(dataset.task_type.value)
        
        # Run evaluation
        scores = evaluator.evaluate(dataset.ground_truth, submission.predictions)
        
        # Get primary score
        primary_score = scores.get(dataset.primary_metric)
        if primary_score is None:
            raise Exception(f"Primary metric '{dataset.primary_metric}' not found in evaluation results")
        
        # Bootstrap CI over resampled examples (falls back to None if too few samples)
        ci = bootstrap_primary_metric_ci(
            evaluator,
            dataset.ground_truth,
            submission.predictions,
            dataset.primary_metric,
        )
        if ci is None:
            ci = f"{float(primary_score):.4f} - {float(primary_score):.4f}"
        
        # Update submission with results
        submission.primary_score = primary_score
        submission.detailed_scores = scores
        submission.confidence_interval = ci
        submission.status = SubmissionStatus.COMPLETED
        submission.evaluated_at = datetime.utcnow()
        
        db.commit()
        
        print(f"✓ Submission {submission_id} evaluated successfully")
        print(f"  Model: {submission.model_name}")
        print(f"  Score: {primary_score} ({dataset.primary_metric})")
        print(f"  All metrics: {scores}")
        
        # Log evaluation
        from logger import log_evaluation
        log_evaluation(
            submission_id=submission_id,
            dataset_id=dataset.id,
            model_name=submission.model_name,
            score=primary_score,
            metric=dataset.primary_metric
        )
        
        # Invalidate cache for this dataset's leaderboard
        from cache import invalidate_leaderboard_cache
        invalidate_leaderboard_cache(dataset.id)
        
    except Exception as e:
        # Mark submission as failed
        submission.status = SubmissionStatus.FAILED
        submission.error_message = str(e)
        db.commit()
        
        print(f"✗ Submission {submission_id} evaluation failed: {e}")
        traceback.print_exc()
        
    finally:
        db.close()


def recompute_leaderboard_rankings(dataset_id: str):
    """
    Recompute and cache leaderboard rankings for a dataset
    
    This can be called after new submissions to update the cached rankings.
    Currently, rankings are computed on-the-fly in the API.
    """
    # Future enhancement: Cache rankings in LeaderboardEntry table
    # for faster leaderboard queries
    pass

