"""
Hugging Face dataset recipes: canonical conversion from HF rows to leaderboard ground_truth.

TODO: Add more recipes (SQuAD document_qa, CoNLL-2003 NER).
TODO: Optional background jobs for large imports / long-running evals.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from datasets import load_dataset

GLUE_HF_ID = "nyu-mll/glue"
GLUE_SST2_CONFIG = "sst2"

SST2_ID_LABEL = {0: "negative", 1: "positive"}


def sst2_row_to_ground_truth_item(
    idx: int,
    split: str,
    sentence: str,
    label: int,
) -> Dict[str, Any]:
    """One leaderboard ground-truth dict for GLUE SST-2."""
    if label not in SST2_ID_LABEL:
        raise ValueError(
            f"GLUE SST-2 has no usable label for scoring at index {idx}: {label!r}. "
            "Use train or validation split; test labels are typically unset (-1)."
        )
    answer = SST2_ID_LABEL[label]
    ex_id = f"sst2_{split}_{idx}"
    return {
        "id": ex_id,
        "question": sentence,
        "sentence": sentence,
        "answer": answer,
        "metadata": {
            "source": "huggingface",
            "dataset_name": GLUE_HF_ID,
            "config": GLUE_SST2_CONFIG,
            "split": split,
            "hf_idx": idx,
        },
    }


def hf_rows_to_glue_sst2_ground_truth(
    rows: List[Dict[str, Any]],
    split: str,
) -> List[Dict[str, Any]]:
    """
    Convert HF-style row dicts (keys sentence, label) for unit tests without load_dataset.
    """
    ground_truth: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        sentence = row["sentence"]
        label = row["label"]
        ground_truth.append(sst2_row_to_ground_truth_item(idx, split, sentence, int(label)))
    return ground_truth


def load_glue_sst2_ground_truth(
    split: str,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load GLUE SST-2 from Hugging Face; only rows with labels 0/1 are kept for scoring.

    Raises:
        ValueError: unlabeled / invalid labels (e.g. test split with -1).
    """
    ds = load_dataset(GLUE_HF_ID, GLUE_SST2_CONFIG, split=split)
    n = len(ds)
    if limit is not None:
        n = min(n, limit)
    ground_truth: List[Dict[str, Any]] = []
    for idx in range(n):
        row = ds[idx]
        ground_truth.append(
            sst2_row_to_ground_truth_item(
                idx,
                split,
                str(row["sentence"]),
                int(row["label"]),
            )
        )
    return ground_truth


def build_glue_sst2_import_payload(
    split: str = "validation",
    limit: Optional[int] = None,
    leaderboard_dataset_id: Optional[str] = None,
    display_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full dataset dict for DB persistence (matches Dataset model fields, plus optional id).
    """
    ground_truth = load_glue_sst2_ground_truth(split=split, limit=limit)
    split_slug = split.replace("-", "_")
    lid = leaderboard_dataset_id or f"hf_glue_sst2_{split_slug}"
    name = display_name or (
        "GLUE SST-2 Validation"
        if split == "validation"
        else f"GLUE SST-2 ({split})"
    )
    return {
        "id": lid,
        "name": name,
        "description": (
            f"GLUE SST-2 ({GLUE_SST2_CONFIG}) from {GLUE_HF_ID}, split={split!r}, "
            f"{len(ground_truth)} examples. Labels: 0→negative, 1→positive."
        ),
        "url": f"https://huggingface.co/datasets/{GLUE_HF_ID}",
        "task_type": "text_classification",
        "test_set_public": False,
        "labels_public": False,
        "primary_metric": "accuracy",
        "additional_metrics": ["f1", "precision", "recall"],
        "ground_truth": ground_truth,
    }


# Recipe key: (hf_dataset_id lowercased, config lowercased)
RECIPE_IMPORTERS = {
    (GLUE_HF_ID.lower(), GLUE_SST2_CONFIG.lower()): build_glue_sst2_import_payload,
}


def try_recipe_import(
    dataset_name: str,
    config: str,
    split: str,
    limit: Optional[int],
    leaderboard_dataset_id: Optional[str],
    display_name: Optional[str],
) -> Optional[Dict[str, Any]]:
    """If a registered recipe matches, return import payload; else None."""
    key = (dataset_name.strip().lower(), config.strip().lower())
    builder = RECIPE_IMPORTERS.get(key)
    if not builder:
        return None
    return builder(
        split=split,
        limit=limit,
        leaderboard_dataset_id=leaderboard_dataset_id,
        display_name=display_name,
    )
