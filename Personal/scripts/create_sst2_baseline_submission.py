#!/usr/bin/env python3
"""
Create a sanity-check submission for a GLUE SST-2-style dataset (evaluator-scored only).

Majority-label strategy uses ground-truth labels to predict the same class for every
example (leaky sanity check for infra, not a real model).

Run from repo root:
  cd Personal && PYTHONPATH=. python scripts/create_sst2_baseline_submission.py \\
    --dataset-id hf_glue_sst2_validation --strategy majority_label

By default runs evaluation in-process (no HTTP). Use --api-url to POST to a running server.
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _majority_label(ground_truth: list) -> str:
    labels = [str(item["answer"]) for item in ground_truth]
    return Counter(labels).most_common(1)[0][0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-id", required=True, help="Dataset.id (e.g. hf_glue_sst2_validation)")
    parser.add_argument(
        "--strategy",
        choices=["majority_label"],
        default="majority_label",
        help="majority_label: predict the majority gold label for every example",
    )
    parser.add_argument("--model-name", default="baseline_majority_label")
    parser.add_argument(
        "--api-url",
        default=None,
        help="If set, POST /api/submissions here (e.g. http://127.0.0.1:8000)",
    )
    args = parser.parse_args()

    os.chdir(ROOT)

    from database import SessionLocal
    from models import Dataset, Submission, SubmissionStatus
    from evaluation_service import evaluate_submission

    db = SessionLocal()
    try:
        ds = db.query(Dataset).filter(Dataset.id == args.dataset_id).first()
        if not ds:
            print(f"Dataset not found: {args.dataset_id}", file=sys.stderr)
            sys.exit(1)
        if ds.task_type.value != "text_classification":
            print("This script expects text_classification.", file=sys.stderr)
            sys.exit(1)

        gt = ds.ground_truth or []
        if args.strategy == "majority_label":
            pred_label = _majority_label(gt)
            predictions = [{"id": item["id"], "prediction": pred_label} for item in gt]
        else:
            raise SystemExit("unknown strategy")

        if args.api_url:
            import json
            import urllib.error
            import urllib.request

            base = args.api_url.rstrip("/")
            body = json.dumps(
                {
                    "dataset_id": args.dataset_id,
                    "model_name": args.model_name,
                    "predictions": predictions,
                    "is_internal": True,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                f"{base}/api/submissions",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=600) as resp:
                    print(resp.read().decode())
            except urllib.error.HTTPError as e:
                print(e.read().decode(), file=sys.stderr)
                sys.exit(1)
            return

        submission_id = str(uuid.uuid4())
        sub = Submission(
            id=submission_id,
            dataset_id=ds.id,
            model_name=args.model_name,
            predictions=predictions,
            status=SubmissionStatus.PENDING,
            is_internal=True,
        )
        db.add(sub)
        db.commit()
        evaluate_submission(submission_id)
        db.refresh(sub)
        if sub.status != SubmissionStatus.COMPLETED:
            print(sub.error_message or "evaluation failed", file=sys.stderr)
            sys.exit(1)
        print(
            f"OK submission_id={submission_id} primary_score={sub.primary_score} "
            f"metric={ds.primary_metric}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
