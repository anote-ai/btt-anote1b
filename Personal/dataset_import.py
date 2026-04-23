"""Persist Hugging Face / imported dataset payloads into the leaderboard database."""
from __future__ import annotations

import uuid
from typing import Any, Dict

from sqlalchemy.orm import Session

from models import Dataset, TaskType


class DatasetImportError(Exception):
    """Raised when an import payload cannot be persisted (conflict or bad data)."""


def persist_imported_dataset(db: Session, payload: Dict[str, Any]) -> Dataset:
    """
    Insert a new Dataset from an importer payload (keys align with Dataset / DatasetCreate).

    Raises:
        DatasetImportError: duplicate id or name, or missing required fields.
    """
    name = payload.get("name")
    ground_truth = payload.get("ground_truth")
    if not name:
        raise DatasetImportError("payload must include 'name'")
    if not ground_truth:
        raise DatasetImportError("payload must include non-empty 'ground_truth'")

    dataset_id = payload.get("id") or str(uuid.uuid4())

    if db.query(Dataset).filter(Dataset.id == dataset_id).first():
        raise DatasetImportError(f"Dataset id already exists: {dataset_id}")
    if db.query(Dataset).filter(Dataset.name == name).first():
        raise DatasetImportError(f"Dataset name already exists: {name}")

    task_type = payload.get("task_type", "text_classification")
    try:
        tt = TaskType(task_type) if isinstance(task_type, str) else task_type
    except ValueError as e:
        raise DatasetImportError(str(e)) from e

    dataset = Dataset(
        id=dataset_id,
        name=name,
        description=payload.get("description"),
        url=payload.get("url"),
        task_type=tt,
        test_set_public=bool(payload.get("test_set_public", False)),
        labels_public=bool(payload.get("labels_public", False)),
        primary_metric=payload.get("primary_metric", "accuracy"),
        additional_metrics=payload.get("additional_metrics") or [],
        num_examples=len(ground_truth),
        ground_truth=ground_truth,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset
