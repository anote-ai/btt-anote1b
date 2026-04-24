import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

from hf_prediction_adapters import (
    inference_api_classification_to_prediction,
    normalize_classification_label,
    rows_to_predictions,
)


def test_normalize_classification_label():
    assert normalize_classification_label("POSITIVE") == "positive"
    assert normalize_classification_label({"label": "NEGATIVE"}) == "negative"
    assert normalize_classification_label({"label": "LABEL_1"}) == "positive"


def test_inference_api_classification_to_prediction():
    assert inference_api_classification_to_prediction(
        {"label": "POSITIVE", "score": 0.9},
        example_id="sst2_validation_0",
    ) == {"id": "sst2_validation_0", "prediction": "positive"}
    assert inference_api_classification_to_prediction(
        [{"label": "NEGATIVE", "score": 0.7}],
        example_id="x",
    ) == {"id": "x", "prediction": "negative"}


def test_rows_to_predictions():
    rows = [
        {"my_id": "a", "pred": "hello"},
        {"my_id": "b", "pred": "world"},
    ]
    assert rows_to_predictions(
        rows, id_field="my_id", prediction_field="pred"
    ) == [
        {"id": "a", "prediction": "hello"},
        {"id": "b", "prediction": "world"},
    ]


def test_rows_to_predictions_classification_normalization():
    rows = [{"id": "1", "lab": {"label": "POSITIVE"}}]
    assert rows_to_predictions(
        rows, id_field="id", prediction_field="lab", label_normalization="classification"
    ) == [{"id": "1", "prediction": "positive"}]
