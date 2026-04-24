# Hugging Face models, splits, and evaluation

This document explains how to add **new splits**, **new models**, and **new dataset recipes** while keeping **inference separate from scoring**: the runner only produces prediction JSON; **`evaluate_submission`** computes all metrics from ground truth.

## Principles

1. **Import** creates a `Dataset` row (ground truth + task type + metrics config) in the DB.
2. **Run model** creates a `Submission` with `predictions: [{"id": "...", "prediction": "..."}, ...]` and calls **`evaluate_submission(submission_id)`**—never set `primary_score` by hand in scripts.
3. Use the **same** `DATABASE_URL` and run CLI scripts from **`Personal/`** so import and runner see the same `leaderboard.db` (or the same Postgres URL).

## Prerequisites

```bash
cd Personal
pip install -r requirements.txt
pip install -r requirements-hf-inference.txt   # transformers + torch (optional for API-only)
```

Optional: `HF_TOKEN` for higher Hub rate limits or private assets.

---

## Adding or changing splits (same benchmark, different HF split)

Use **`scripts/import_hf_dataset.py`**. For GLUE SST-2 the recipe lives in `hf_dataset_recipes.py`.

| Flag | Role |
|------|------|
| `--dataset` | HF dataset id (e.g. `nyu-mll/glue`) |
| `--config` | Subset (e.g. `sst2`) |
| `--split` | HF split name (`validation`, `train`, …) |
| `--dataset-id` | **Primary key** in the leaderboard DB; pick a stable string per split, e.g. `hf_glue_sst2_train` |
| `--limit` | Max rows; **`0`** = entire split (for registered recipes) |
| `--name` | Display name; use when the default name would **collide** (dataset `name` must be unique in DB) |

**Example — full validation split with a fixed leaderboard id:**

```bash
PYTHONPATH=. python scripts/import_hf_dataset.py \
  --dataset nyu-mll/glue --config sst2 --split validation \
  --dataset-id hf_glue_sst2_validation --limit 0
```

**Example — training split (use a distinct `--dataset-id` and usually `--name`):**

```bash
PYTHONPATH=. python scripts/import_hf_dataset.py \
  --dataset nyu-mll/glue --config sst2 --split train \
  --dataset-id hf_glue_sst2_train \
  --name "GLUE SST-2 Train" \
  --limit 0
```

**SST-2 test split:** GLUE SST-2 **test** labels are typically **unlabeled** (`-1`). The recipe rejects those rows for scoring. Prefer **`validation`** (or **train**) for leaderboard evaluation.

After import, run the model with **`--dataset-id`** set to the same id you passed to `--dataset-id` on import.

---

## Adding more models (same dataset, different HF checkpoint)

Use **`scripts/run_hf_model_on_dataset.py`**. Change **`--model-id`** to any Hub model that works with the **`sentiment-analysis`** (or compatible text-classification) pipeline for binary sentiment.

```bash
PYTHONPATH=. python scripts/run_hf_model_on_dataset.py \
  --dataset-id hf_glue_sst2_validation \
  --model-id <org>/<model-name> \
  --limit 200 \
  --batch-size 16
```

**Label normalization** is in `hf_runner_inference.normalize_hf_sentiment_label`: it maps common outputs (e.g. `POSITIVE` / `NEGATIVE`, `LABEL_0` / `LABEL_1`) to **`positive`** / **`negative`**. If a new model emits different strings, extend that function and add a unit test in `tests/test_hf_runner_inference.py`.

**Leaderboard `model_name`:** `submission_model_name_from_id` derives a short name from the Hub id (with a special case for DistilBERT SST-2). For new flagship models you may add explicit aliases there for readability.

**Task type:** `run_hf_model_on_dataset.py` requires **`text_classification`**. For other tasks, use the matching script below.

### Document QA (SQuAD-style)

**Import** (recipe key `squad` + config `default`):

```bash
PYTHONPATH=. python scripts/import_hf_dataset.py \
  --dataset squad --config default --split validation \
  --dataset-id hf_squad_validation --limit 200
```

**Run** extractive QA (`question` + `context` must be present on each ground-truth row):

```bash
PYTHONPATH=. python scripts/run_hf_qa_on_dataset.py \
  --dataset-id hf_squad_validation \
  --model-id distilbert-base-cased-distilled-squad \
  --limit 50
```

### Named entity recognition (CoNLL-2003)

**Import:**

```bash
PYTHONPATH=. python scripts/import_hf_dataset.py \
  --dataset conll2003 --config default --split validation \
  --dataset-id hf_conll2003_validation --limit 200
```

**Run** token-classification + aggregated entities:

```bash
PYTHONPATH=. python scripts/run_hf_ner_on_dataset.py \
  --dataset-id hf_conll2003_validation \
  --model-id dslim/bert-base-NER \
  --limit 50
```

CoNLL loading may require `trust_remote_code=True` in newer `datasets` versions; upgrade `datasets` or allow remote code per Hugging Face docs if import fails.

---

## Discover submission shape (API)

`GET /api/datasets/{dataset_id}/submission-format` returns `prediction_item_shape`, an **`example`** payload for `POST /api/submissions`, and notes. Use it from CLIs or notebooks before building `predictions`.

---

## User predictions from JSON, HF Inference API, or dataset exports

### Submit from a JSON file

`scripts/submit_predictions_from_file.py` loads a JSON **array** of `{ "id", "prediction" }`, checks **exact id coverage** against the dataset in the DB, creates a `Submission`, and calls **`evaluate_submission`** (same scoring path as the API).

```bash
PYTHONPATH=. python scripts/submit_predictions_from_file.py \
  --dataset-id hf_glue_sst2_validation \
  --predictions-file ./my_preds.json \
  --model-name notebook_baseline
```

Optional `--metadata-file` (JSON object) is stored in `submission_metadata`.

### Adapters (`hf_prediction_adapters.py`)

Pure helpers (no model download):

- **`inference_api_classification_to_prediction`** — one HF Inference API row such as `{"label": "POSITIVE", "score": 0.99}` → leaderboard `prediction` string (aligned with SST-2-style normalization).
- **`rows_to_predictions`** — tabular JSON / exported rows with `--id-field` / `--prediction-field`; optional `label_normalization="classification"`.

Use these in notebooks to turn Hub responses into the canonical list, then **`POST /api/submissions`** or **`submit_predictions_from_file.py`**.

---

## How evaluation works (adding metrics vs. adding predictions)

- **Metrics** are determined by the dataset’s `primary_metric` / `additional_metrics` and by **`evaluators.py`** for the task type (e.g. classification accuracy, F1).
- **Submissions** must include a prediction for **every** ground-truth example id after `--limit` slicing; the runner checks set equality before creating the submission.
- **`evaluation_service.evaluate_submission`** loads the dataset, runs the evaluator, sets **`primary_score`** and **`detailed_scores`**, updates submission status, and invalidates leaderboard cache when applicable.

To change **what** is measured (e.g. extra metrics), adjust the evaluator and/or dataset metadata—not the HF runner.

---

## Adding a new Hugging Face *dataset* (new recipe)

Today, first-class HF imports beyond generic sampling are driven by **recipes** in **`hf_dataset_recipes.py`**:

1. Implement a builder that returns a payload dict with keys aligned to **`persist_imported_dataset`** (`id`, `name`, `task_type`, `primary_metric`, `additional_metrics`, `ground_truth`, …).
2. Register it in **`RECIPE_IMPORTERS`** keyed by `(hf_dataset_id.lower(), config.lower())`.
3. Ensure each ground-truth item has stable **`id`** and task-specific input fields (e.g. **`sentence`** for SST-2 classification; **`question`** + **`context`** for SQuAD; **`text`** for CoNLL NER).
4. Import via **`import_hf_dataset.py`**; if the recipe sets a default `id`, you can still override with **`--dataset-id`**.

Registered recipes today: **GLUE SST-2** (`nyu-mll/glue` / `sst2`), **SQuAD** (`squad` / `default`), **CoNLL-2003** (`conll2003` / `default`). Add more by extending **`RECIPE_IMPORTERS`** in **`hf_dataset_recipes.py`**.

---

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| `Dataset not found` | Empty DB, wrong `DATABASE_URL`, or typo in `--dataset-id`. The runner prints `DATABASE_URL` and existing dataset ids when lookup fails. |
| Import `Dataset name already exists` | Reuse **`--name`** for a new split or pick a unique display name. |
| `Unexpected sentiment label` | Model output not covered by **`normalize_hf_sentiment_label`**; extend mappings. |
| Import vs. API different data | **`DATABASE_URL`** or working directory differs between processes. |

---

## Related files

| File | Purpose |
|------|---------|
| `scripts/import_hf_dataset.py` | CLI import |
| `scripts/run_hf_model_on_dataset.py` | Text classification (sentiment) runner |
| `scripts/run_hf_qa_on_dataset.py` | Document QA runner |
| `scripts/run_hf_ner_on_dataset.py` | NER runner |
| `scripts/submit_predictions_from_file.py` | Load predictions JSON → submission → evaluate |
| `hf_dataset_recipes.py` | Recipe payloads (SST-2, SQuAD, CoNLL-2003, …) |
| `hf_prediction_adapters.py` | HF API / tabular row → prediction dict helpers |
| `hf_importer.py` | Routes to recipe or generic HF sampling |
| `hf_runner_inference.py` | Deps check, batching, label normalization |
| `dataset_import.py` | `persist_imported_dataset` |
| `evaluation_service.py` | `evaluate_submission` orchestration |
| `evaluators.py` | Task-specific metrics |
| `requirements-hf-inference.txt` | Optional torch/transformers stack |
