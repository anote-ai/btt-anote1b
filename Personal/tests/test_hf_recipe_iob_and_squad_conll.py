"""Unit tests for IOB span parsing and recipe routing (no full HF downloads in CI)."""
import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from hf_dataset_recipes import (
    iob_tag_strings_to_spans,
    try_recipe_import,
    build_squad_import_payload,
    build_conll2003_import_payload,
)


def test_iob_tag_strings_to_spans_simple():
    tokens = ["John", "Smith", "lives", "in", "Paris"]
    tags = ["B-PER", "I-PER", "O", "O", "B-LOC"]
    spans = iob_tag_strings_to_spans(tokens, tags)
    assert spans == [("John Smith", "PER"), ("Paris", "LOC")]


def test_iob_single_token_entity():
    tokens = ["Obama", "spoke"]
    tags = ["B-PER", "O"]
    assert iob_tag_strings_to_spans(tokens, tags) == [("Obama", "PER")]


def test_try_recipe_import_squad(monkeypatch):
    def fake_squad(split, limit=None):
        return [
            {
                "id": "q1",
                "question": "Where?",
                "context": "Paris is here.",
                "answer": "Paris",
                "metadata": {},
            }
        ]

    monkeypatch.setattr("hf_dataset_recipes.load_squad_ground_truth", fake_squad)
    payload = try_recipe_import(
        "squad",
        "default",
        "validation",
        limit=1,
        leaderboard_dataset_id="hf_squad_test",
        display_name="Mini SQuAD",
    )
    assert payload is not None
    assert payload["id"] == "hf_squad_test"
    assert payload["task_type"] == "document_qa"
    assert payload["primary_metric"] == "exact_match"
    assert len(payload["ground_truth"]) == 1
    assert payload["ground_truth"][0]["question"] == "Where?"


def test_try_recipe_import_conll(monkeypatch):
    def fake_conll(split, limit=None):
        return [
            {
                "id": "n1",
                "text": "Apple Inc",
                "question": "Apple Inc",
                "tokens": ["Apple", "Inc"],
                "answer": [["Apple Inc", "ORG"]],
                "metadata": {},
            }
        ]

    monkeypatch.setattr("hf_dataset_recipes.load_conll2003_ground_truth", fake_conll)
    payload = try_recipe_import(
        "conll2003",
        "default",
        "validation",
        limit=1,
        leaderboard_dataset_id="hf_conll_test",
        display_name="Mini CoNLL",
    )
    assert payload is not None
    assert payload["task_type"] == "named_entity_recognition"
    assert payload["ground_truth"][0]["answer"] == [["Apple Inc", "ORG"]]


def test_build_squad_import_payload_applies_leaderboard_id(monkeypatch):
    monkeypatch.setattr(
        "hf_dataset_recipes.load_squad_ground_truth",
        lambda split, limit=None: [],
    )
    p = build_squad_import_payload(
        split="validation",
        leaderboard_dataset_id="custom_squad",
        display_name="X",
    )
    assert p["id"] == "custom_squad"
    assert p["name"] == "X"
