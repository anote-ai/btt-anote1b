#!/usr/bin/env python3
"""
Load predictions JSON from a file, validate coverage against a dataset in the DB,
create a Submission, and run evaluate_submission (same path as the API).

File format: JSON array of {"id": "...", "prediction": ...}

Example:
  cd Personal && PYTHONPATH=. python scripts/submit_predictions_from_file.py \\
    --dataset-id hf_glue_sst2_validation \\
    --predictions-file ./preds.json \\
    --model-name my_run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit predictions from JSON file + evaluate")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--predictions-file", required=True, help="JSON array of {id, prediction}")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-version", default="", help="Optional version string")
    parser.add_argument(
        "--metadata-file",
        default=None,
        help="Optional JSON object merged into submission_metadata",
    )
    args = parser.parse_args()

    os.chdir(ROOT)

    from database import SessionLocal, init_db
    from models import Dataset, Submission, SubmissionStatus
    from evaluation_service import evaluate_submission, validate_complete_predictions

    init_db()

    with open(args.predictions_file, encoding="utf-8") as f:
        predictions = json.load(f)
    if not isinstance(predictions, list):
        print("predictions file must be a JSON array", file=sys.stderr)
        sys.exit(1)

    meta = None
    if args.metadata_file:
        with open(args.metadata_file, encoding="utf-8") as f:
            meta = json.load(f)
        if not isinstance(meta, dict):
            print("metadata file must be a JSON object", file=sys.stderr)
            sys.exit(1)

    db = SessionLocal()
    try:
        ds = db.query(Dataset).filter(Dataset.id == args.dataset_id).first()
        if not ds:
            print(f"Dataset not found: {args.dataset_id!r}", file=sys.stderr)
            sys.exit(1)
        try:
            validate_complete_predictions(ds.ground_truth, predictions)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

        submission_id = str(uuid.uuid4())
        sub = Submission(
            id=submission_id,
            dataset_id=ds.id,
            model_name=args.model_name,
            model_version=(args.model_version or None),
            predictions=predictions,
            status=SubmissionStatus.PENDING,
            submission_metadata=meta,
            is_internal=False,
        )
        db.add(sub)
        db.commit()

        evaluate_submission(submission_id)
        db.refresh(sub)

        if sub.status != SubmissionStatus.COMPLETED:
            print(sub.error_message or "Evaluation failed", file=sys.stderr)
            sys.exit(1)

        print(f"submission_id={submission_id}")
        print(f"primary_score={sub.primary_score}")
        print(f"primary_metric={ds.primary_metric}")
        print("detailed_scores:")
        for k, v in sorted((sub.detailed_scores or {}).items()):
            print(f"  {k}: {v}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
