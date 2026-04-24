"""
Convert Hugging Face Inference API / datasets-shaped JSON into leaderboard predictions.

Pure helpers (no torch); keep inference adapters separate from evaluators.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableSequence, Union

Json = Dict[str, Any]


def normalize_classification_label(raw: Union[str, Json]) -> str:
    """
    Map HF sentiment / text-classification labels to lowercase evaluator labels.

    Accepts a string or a dict with 'label' (pipeline or Inference API row).
    """
    if isinstance(raw, dict):
        raw = raw.get("label", "")
    if not isinstance(raw, str):
        raw = str(raw)
    u = raw.strip().upper()
    if u in ("POSITIVE", "LABEL_1", "POS", "1"):
        return "positive"
    if u in ("NEGATIVE", "LABEL_0", "NEG", "0"):
        return "negative"
    return raw.strip().lower()


def inference_api_classification_to_prediction(
    row: Json,
    *,
    example_id: str,
    label_key: str = "label",
) -> Json:
    """
    One HF Inference API classification payload -> {"id", "prediction"}.

    Supports:
      - {"label": "POSITIVE", "score": 0.99}
      - [{"label": "NEGATIVE", "score": 0.8}]  (list wrapper)
    """
    if isinstance(row, list) and row:
        row = row[0]
    if not isinstance(row, dict):
        raise TypeError(f"Expected dict or single-element list, got {type(row)}")
    label = row.get(label_key)
    if label is None:
        raise ValueError(f"Missing {label_key!r} in inference payload: {row!r}")
    return {"id": example_id, "prediction": normalize_classification_label(label)}


def rows_to_predictions(
    rows: MutableSequence[Mapping[str, Any]],
    *,
    id_field: str,
    prediction_field: str,
    label_normalization: str = "none",
) -> List[Json]:
    """
    Map tabular JSON / HF dataset export rows to leaderboard predictions.

    label_normalization:
      - "none": use value as-is (strings coerced)
      - "classification": use normalize_classification_label (POSITIVE/NEGATIVE etc.)
    """
    out: List[Json] = []
    for i, row in enumerate(rows):
        if id_field not in row:
            raise ValueError(f"Row {i} missing id field {id_field!r}")
        if prediction_field not in row:
            raise ValueError(f"Row {i} missing prediction field {prediction_field!r}")
        ex_id = str(row[id_field])
        raw_pred = row[prediction_field]
        if label_normalization == "classification":
            pred: Any = normalize_classification_label(raw_pred)
        else:
            pred = raw_pred
        out.append({"id": ex_id, "prediction": pred})
    return out
