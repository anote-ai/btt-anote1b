# Agent onboarding — Anote monorepo

This file orients coding agents and new contributors to the repository: what it is, where the real product lives, and how to run it locally.

## What this project is

**Anote Leaderboard** is a benchmarking platform for evaluating models on fixed datasets with transparent metrics, leaderboard rankings, and submission workflows. The **canonical implementation** is under [`Personal/`](Personal/):

- **Backend:** FastAPI (`main.py`), SQLAlchemy + `DATABASE_URL` (SQLite by default as `leaderboard.db`, Postgres in production), optional Redis for leaderboard caching, rate limits via `slowapi`.
- **Frontend:** Vite + React in [`Personal/frontend/`](Personal/frontend/) (`npm run dev`, not `npm start`).
- **Features:** Dataset CRUD, question export without leaking labels (when configured), prediction submissions, background evaluation (`evaluation_service.py` + task-specific `evaluators.py`), metrics catalog (`/api/metrics`), Hugging Face import (`/api/admin/import-huggingface`), admin seeding, **legacy `/public/*` routes** in [`Personal/legacy_compat.py`](Personal/legacy_compat.py) for older clients that expected the Flask JSON shape.

[`Company/`](Company/) is **legacy reference only** (Flask + Create React App marketing shell). Do **not** extend it for new product work unless you are porting a specific artifact into `Personal/`. See [`Company/CLAUDE.md`](Company/CLAUDE.md) and the root [`README.md`](README.md).

## Repository layout

| Path | Role |
|------|------|
| [`Personal/`](Personal/) | **Ship this:** API, Vite UI, tests, `railway.json`, seed scripts |
| [`Personal/my-leaderboard/`](Personal/my-leaderboard/) | Nested duplicate / variant (e.g. extra `auth.py`); prefer editing root `Personal/` unless you need that subtree |
| [`Company/`](Company/) | Archived Flask + CRA; optional compare / CSV demo assets |

## How to run everything (local)

### 1. API (Personal)

```bash
cd Personal
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
```

**First-time or empty DB:** create tables and load benchmarks (same idea as deploy):

```bash
python init_db.py
```

If the DB already has data and you want a full reset:

```bash
FORCE_RESEED=true python init_db.py
```

**Start the server:**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- **OpenAPI:** http://localhost:8000/docs  
- **Health:** http://localhost:8000/health  
- **Root `GET /`:** returns 404 by design (API only); use `/docs` or the Vite app.

**Lightweight seed without full `init_db.py`:** `POST http://localhost:8000/api/admin/seed-data` (sample datasets from `seed_data.py` only).

### 2. Frontend (Personal)

```bash
cd Personal/frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

Vite defaults to something like **http://localhost:5173**. Ensure `VITE_API_URL` matches your API origin (no trailing slash required).

### 3. Optional: Company UI (compare only)

```bash
cd Company/frontend
npm install
REACT_APP_API_ENDPOINT=http://localhost:8000 npm start
```

Uses CRA’s `npm start` on ~3000. Point the env at Personal’s API if you rely on `legacy_compat` routes, or at `http://localhost:5001` if you also run the old Flask app from `Company/backend`.

## Environment variables (Personal API)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL; default `sqlite:///./leaderboard.db` |
| Redis-related | Used by `cache.py` when configured for leaderboard caching |
| `FORCE_RESEED` | When `true`, `init_db.py` clears datasets/submissions then re-seeds |

## Tests and CI

- From `Personal/`, with deps installed:  
  `PYTHONPATH=. pytest -q standalone_tests/`  
  (Legacy API contract tests; CI runs this.)
- Broader suite under `Personal/tests/` may need consistent `PYTHONPATH` and DB fixtures; see `tests/conftest.py`.

## Key files for agents

- [`Personal/main.py`](Personal/main.py) — FastAPI routes
- [`Personal/legacy_compat.py`](Personal/legacy_compat.py) — Company-style `/public/*` and curated `/api/leaderboard/*`
- [`Personal/models.py`](Personal/models.py) — `Dataset`, `Submission`, `TaskType`, etc.
- [`Personal/init_db.py`](Personal/init_db.py) — Full DB seed orchestration (used in deploy before uvicorn)
- [`Personal/seed_data.py`](Personal/seed_data.py) — Core sample datasets + baselines
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — Personal backend + Vite build

## Git remote

This workspace commonly uses remote **`personal`** → `https://github.com/anote-ai/btt-anote1b.git` on branch **`main`**.
