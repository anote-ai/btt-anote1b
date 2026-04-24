"""
Legacy JSON API shapes expected by Company CRA (former Flask app).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Dataset, Submission, SubmissionStatus, TaskType
from evaluation_service import evaluate_submission
from cache import invalidate_leaderboard_cache
from rate_limiter import limiter, RATE_LIMITS

router = APIRouter(tags=["legacy-company"])
_curated_leaderboard: List[Dict[str, Any]] = []


def _json_err(status: int, msg: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"success": False, "error": msg})


def _task_type_from_flask(s: str) -> TaskType:
    if not s:
        raise ValueError("task_type required")
    key = s.strip().lower().replace("-", "_")
    mapping = {
        "translation": TaskType.TRANSLATION,
        "text_classification": TaskType.TEXT_CLASSIFICATION,
        "ner": TaskType.NER,
        "named_entity_recognition": TaskType.NER,
        "document_qa": TaskType.DOCUMENT_QA,
        "line_qa": TaskType.LINE_QA,
        "chatbot": TaskType.LINE_QA,
        "prompting": TaskType.LINE_QA,
        "retrieval": TaskType.RETRIEVAL,
    }
    if key not in mapping:
        raise ValueError(f"Unsupported task_type for legacy API: {s}")
    return mapping[key]


def _ground_truth_from_reference_data(task_type: TaskType, rd: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if task_type == TaskType.TRANSLATION:
        sources = rd.get("source_texts") or []
        refs = rd.get("reference_translations") or []
        for i, (src, ref) in enumerate(zip(sources, refs)):
            items.append({"id": str(i), "question": str(src), "answer": str(ref)})
        return items
    if task_type == TaskType.TEXT_CLASSIFICATION:
        sources = rd.get("source_texts") or rd.get("texts") or []
        labels = rd.get("labels") or []
        for i, (src, lbl) in enumerate(zip(sources, labels)):
            items.append({"id": str(i), "question": str(src), "answer": str(lbl)})
        return items
    if task_type == TaskType.NER:
        sources = rd.get("source_texts") or []
        entities = rd.get("entities") or []
        for i, (src, ent) in enumerate(zip(sources, entities)):
            ans = ent if isinstance(ent, list) else [ent]
            items.append({"id": str(i), "question": str(src), "answer": ans})
        return items
    if task_type in (TaskType.DOCUMENT_QA, TaskType.LINE_QA):
        contexts = rd.get("contexts") or []
        questions = rd.get("questions") or rd.get("source_texts") or []
        answers = rd.get("answers") or []
        if contexts and len(contexts) == len(answers):
            qs = questions if len(questions) == len(contexts) else [""] * len(contexts)
            for i, (ctx, q, a) in enumerate(zip(contexts, qs, answers)):
                items.append({"id": str(i), "context": ctx, "question": q, "answer": a})
        else:
            for i, (q, a) in enumerate(zip(questions, answers)):
                items.append({"id": str(i), "question": q, "answer": a})
        return items
    raise ValueError("Could not build ground_truth from reference_data")


@router.get("/public/get_leaderboard")
def legacy_get_leaderboard(limit: int = 100, db: Session = Depends(get_db)):
    rows = (
        db.query(Submission, Dataset)
        .join(Dataset, Submission.dataset_id == Dataset.id)
        .filter(Submission.status == SubmissionStatus.COMPLETED)
        .order_by(Submission.primary_score.desc())
        .limit(limit)
        .all()
    )
    leaderboard = []
    for rank, (sub, ds) in enumerate(rows, start=1):
        leaderboard.append({
            "rank": rank,
            "model_name": sub.model_name,
            "dataset_name": ds.name,
            "task_type": ds.task_type.value,
            "evaluation_metric": ds.primary_metric,
            "score": float(sub.primary_score) if sub.primary_score is not None else 0.0,
            "submitted_at": (
                sub.evaluated_at.isoformat() if sub.evaluated_at else sub.created_at.isoformat()
            ),
        })
    return {"success": True, "leaderboard": leaderboard}


@router.get("/public/datasets")
def legacy_list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).order_by(Dataset.name).all()
    items = []
    for d in datasets:
        row: Dict[str, Any] = {
            "name": d.name,
            "task_type": d.task_type.value,
            "evaluation_metric": d.primary_metric,
        }
        if d.url:
            row["url"] = d.url
        if d.description:
            row["description"] = d.description
        gt = d.ground_truth or []
        if isinstance(gt, list):
            row["size"] = len(gt)
        items.append(row)
    names = {x["name"] for x in items}
    for ds in _curated_leaderboard:
        n = ds.get("name")
        if n and n not in names:
            items.append({
                "name": n,
                "task_type": ds.get("task_type", ""),
                "evaluation_metric": ds.get("evaluation_metric", ""),
                "url": ds.get("url"),
                "description": ds.get("description"),
            })
    return {"success": True, "datasets": items}


@router.get("/public/get_source_sentences")
def legacy_get_source_sentences(
    dataset_name: str = "flores_spanish_translation",
    count: int = 3,
    start_idx: int = 0,
    db: Session = Depends(get_db),
):
    ds = db.query(Dataset).filter(Dataset.name == dataset_name).first()
    if not ds or not ds.ground_truth:
        return _json_err(404, "Dataset not found or has no examples")
    pool = []
    for item in ds.ground_truth:
        if isinstance(item, dict):
            text = item.get("source_text") or item.get("question") or item.get("text") or ""
            pool.append(str(text))
        else:
            pool.append(str(item))
    if start_idx < 0:
        start_idx = 0
    end = min(start_idx + count, len(pool))
    selected = pool[start_idx:end]
    sentence_ids = list(range(start_idx, end))
    return {
        "success": True,
        "dataset_name": dataset_name,
        "sentence_ids": sentence_ids,
        "source_sentences": selected,
        "count": len(selected),
    }


@router.post("/public/submit_model")
@limiter.limit(RATE_LIMITS["submission"])
def legacy_submit_model(
    request: Request,
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    benchmark_dataset_name = body.get("benchmarkDatasetName")
    model_name = body.get("modelName")
    model_results = body.get("modelResults")
    sentence_ids = body.get("sentence_ids")
    if not all([
        benchmark_dataset_name,
        model_name,
        isinstance(model_results, list),
        isinstance(sentence_ids, list),
    ]):
        return _json_err(
            400,
            "Missing required fields: benchmarkDatasetName, modelName, modelResults (list), sentence_ids (list)",
        )
    if len(model_results) != len(sentence_ids):
        return _json_err(400, "Length of sentence_ids must match length of modelResults")

    ds = db.query(Dataset).filter(Dataset.name == benchmark_dataset_name).first()
    if not ds:
        return _json_err(404, "Dataset not found")
    gt_list = ds.ground_truth or []
    predictions = []
    for pred_text, sid in zip(model_results, sentence_ids):
        if sid < 0 or sid >= len(gt_list):
            return _json_err(400, f"Invalid sentence_id {sid}")
        gid = gt_list[sid].get("id", str(sid))
        predictions.append({"id": gid, "prediction": pred_text})

    submission_id = str(uuid.uuid4())
    sub = Submission(
        id=submission_id,
        dataset_id=ds.id,
        model_name=model_name,
        predictions=predictions,
        status=SubmissionStatus.PENDING,
    )
    db.add(sub)
    db.commit()
    invalidate_leaderboard_cache(ds.id)

    evaluate_submission(submission_id)
    from database import SessionLocal

    sdb = SessionLocal()
    try:
        sub_final = sdb.query(Submission).filter(Submission.id == submission_id).first()
        if not sub_final:
            return _json_err(500, "Submission lost after evaluation")
        if sub_final.status != SubmissionStatus.COMPLETED:
            return _json_err(400, sub_final.error_message or "Evaluation failed")
        return {"success": True, "score": float(sub_final.primary_score)}
    finally:
        sdb.close()


@router.post("/public/add_dataset")
def legacy_add_dataset(body: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    name = body.get("name")
    task_type_raw = body.get("task_type")
    evaluation_metric = body.get("evaluation_metric")
    reference_data = body.get("reference_data") or {}
    if not all([name, task_type_raw, evaluation_metric]):
        return _json_err(400, "Missing required fields: name, task_type, evaluation_metric")
    if not isinstance(reference_data, dict):
        return _json_err(400, "reference_data must be a JSON object")

    try:
        tt = _task_type_from_flask(str(task_type_raw))
    except ValueError as e:
        return _json_err(400, str(e))

    if db.query(Dataset).filter(Dataset.name == name).first():
        return _json_err(400, "Dataset with this name already exists")

    try:
        ground_truth = _ground_truth_from_reference_data(tt, reference_data)
    except ValueError:
        ground_truth = []

    if not ground_truth:
        _curated_leaderboard.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "task_type": task_type_raw,
            "evaluation_metric": evaluation_metric,
            "description": reference_data.get("description"),
            "url": reference_data.get("url"),
            "models": [],
        })
        return {"success": True, "message": "Dataset registered (curated only; add examples via admin or full reference_data)"}

    ds = Dataset(
        id=str(uuid.uuid4()),
        name=name,
        description=reference_data.get("description"),
        url=reference_data.get("url"),
        task_type=tt,
        test_set_public=True,
        labels_public=False,
        primary_metric=str(evaluation_metric).lower(),
        additional_metrics=[],
        num_examples=len(ground_truth),
        ground_truth=ground_truth,
    )
    db.add(ds)
    db.commit()
    return {"success": True, "message": "Dataset added"}


@router.get("/public/dataset_details")
def legacy_dataset_details(name: Optional[str] = None, db: Session = Depends(get_db)):
    if not name:
        return _json_err(400, "Missing name")
    ds = db.query(Dataset).filter(Dataset.name == name).first()
    if ds:
        examples = []
        gt = ds.ground_truth or []
        count = len(gt) if isinstance(gt, list) else None
        if isinstance(gt, list):
            for item in gt[:5]:
                if isinstance(item, dict):
                    examples.append(item.get("source_text") or item.get("question") or item.get("text") or "")
                else:
                    examples.append(str(item))
        subs = (
            db.query(Submission)
            .filter(Submission.dataset_id == ds.id, Submission.status == SubmissionStatus.COMPLETED)
            .order_by(Submission.primary_score.desc())
            .limit(10)
            .all()
        )
        top_models = [{
            "model": s.model_name,
            "score": float(s.primary_score) if s.primary_score is not None else 0.0,
            "updated": (s.evaluated_at or s.created_at).isoformat(),
        } for s in subs]
        return {
            "success": True,
            "dataset": {
                "name": ds.name,
                "task_type": ds.task_type.value,
                "evaluation_metric": ds.primary_metric,
                "url": ds.url,
                "description": ds.description,
                "size": count,
                "examples": examples,
            },
            "top_models": top_models,
        }

    matched = next((d for d in _curated_leaderboard if d.get("name") == name), None)
    if matched:
        return {
            "success": True,
            "dataset": {
                "name": matched.get("name"),
                "task_type": matched.get("task_type", ""),
                "evaluation_metric": matched.get("evaluation_metric", ""),
                "url": matched.get("url"),
                "description": matched.get("description"),
                "size": None,
                "examples": [],
            },
            "top_models": matched.get("models") or [],
        }
    return _json_err(404, "Dataset not found")


@router.post("/api/leaderboard/add_dataset")
def curated_add_dataset(body: Dict[str, Any] = Body(...)):
    required = ["name", "task_type"]
    missing = [k for k in required if k not in body]
    if missing:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing required fields: " + ", ".join(missing)},
        )
    dataset_id = str(uuid.uuid4())
    new_ds = {
        "id": dataset_id,
        "name": body["name"],
        "url": body.get("url"),
        "task_type": body["task_type"],
        "description": body.get("description"),
        "models": body.get("models", []),
    }
    _curated_leaderboard.append(new_ds)
    return {"status": "success", "message": "Dataset added to leaderboard.", "dataset_id": dataset_id}


@router.post("/api/leaderboard/add_model")
def curated_add_model(body: Dict[str, Any] = Body(...)):
    required = ["dataset_name", "model", "rank", "score", "updated"]
    missing = [k for k in required if k not in body]
    if missing:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing required fields: " + ", ".join(missing)},
        )
    for ds in _curated_leaderboard:
        if ds.get("name") == body["dataset_name"]:
            ds.setdefault("models", []).append({
                "rank": body["rank"],
                "model": body["model"],
                "score": body["score"],
                "ci": body.get("ci"),
                "updated": body["updated"],
            })
            ds["models"].sort(key=lambda m: (m.get("rank") is None, m.get("rank")))
            return {"status": "success", "message": "Model added to dataset on leaderboard."}
    return JSONResponse(status_code=404, content={"status": "error", "message": "Dataset not found."})


@router.get("/api/leaderboard/list")
def curated_list():
    return {"status": "success", "datasets": _curated_leaderboard}


@router.get("/public/benchmark_csvs")
def legacy_benchmark_csvs():
    return {"success": True, "datasets": []}


@router.get("/public/benchmark_models")
def legacy_benchmark_models():
    return {"success": True, "models": []}


@router.post("/public/run_csv_benchmarks")
def legacy_run_csv_benchmarks():
    return _json_err(501, "CSV benchmarks are not enabled on the Personal API yet")
