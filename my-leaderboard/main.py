"""
Main FastAPI application for the Leaderboard API
"""
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Any
import math
import os
import uuid
from datetime import datetime

from auth import (
    AuthUser,
    auth_mode,
    log_auth_config,
    require_write_user,
    resolve_user,
)
import database as database_module
from database import get_db, init_db
from models import Dataset, Submission, LeaderboardEntry, TaskType, SubmissionStatus
from schemas import (
    DatasetCreate, DatasetResponse, DatasetPublic,
    SubmissionCreate, SubmissionResponse,
    LeaderboardResponse, LeaderboardEntryResponse,
    SuccessResponse, ErrorResponse, MeResponse,
)
from evaluators import get_evaluator
from evaluation_service import evaluate_submission
from cache import cached_leaderboard, invalidate_leaderboard_cache, get_cache_stats
from rate_limiter import setup_rate_limiting, RATE_LIMITS
from logger import logger, log_api_request, log_evaluation, log_error


def _is_finite_score(value: Any) -> bool:
    """Reject None, NaN, and inf so Pydantic/JSON encoding cannot 500."""
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _sanitize_detailed_scores(obj: Any) -> Any:
    """Make nested structures JSON-safe (numpy scalars, NaN, weird keys)."""
    if obj is None:
        return None
    if hasattr(obj, "item") and callable(getattr(obj, "item", None)):
        try:
            return _sanitize_detailed_scores(obj.item())
        except Exception:
            return None
    if isinstance(obj, float):
        if not math.isfinite(obj):
            return None
        return obj
    if isinstance(obj, (int, str, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _sanitize_detailed_scores(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_detailed_scores(v) for v in obj]
    try:
        return float(obj)
    except (TypeError, ValueError):
        return str(obj)


# OpenAPI tags (used by /docs and /openapi.json)
openapi_tags = [
    {"name": "health", "description": "Liveness checks."},
    {"name": "datasets", "description": "Datasets and test questions (without answers)."},
    {"name": "submissions", "description": "Submit predictions, then poll for status and scores."},
    {"name": "leaderboards", "description": "Leaderboards across datasets and per dataset."},
    {"name": "metrics", "description": "Metric discovery and definitions."},
    {"name": "admin", "description": "Seeding, imports, and cache operations."},
    {"name": "auth", "description": "Identity probe for SPAs and CLIs."},
]

# Initialize FastAPI app
app = FastAPI(
    title="Anote Leaderboard API",
    description=(
        "API for benchmark datasets and Kaggle-style prediction submissions.\n\n"
        "## Quickstart\n"
        "- List datasets: `GET /api/datasets`\n"
        "- Get test questions (IDs + inputs): `GET /api/datasets/{dataset_id}/questions`\n"
        "- Describe submission shape: `GET /api/datasets/{dataset_id}/submission-format`\n"
        "- Submit predictions: `POST /api/submissions`\n"
        "- Poll status/results: `GET /api/submissions/{submission_id}`\n"
        "- View leaderboard: `GET /api/leaderboard` or `GET /api/leaderboard/{dataset_id}`\n\n"
        "## Authentication\n"
        "If auth is enabled server-side, send a Bearer token:\n\n"
        "```\n"
        "Authorization: Bearer <token>\n"
        "```\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=openapi_tags,
    servers=[
        {"url": "http://localhost:8001", "description": "Local development server (alt port)"},
        {"url": "http://localhost:8000", "description": "Local development server"},
        {"url": "/", "description": "Current server"},
    ]
)

# CORS: for cross-subdomain cookies + credentials, set LEADERBOARD_CORS_ORIGINS (comma-separated).
_cors_origins = (os.getenv("LEADERBOARD_CORS_ORIGINS") or "").strip()
if _cors_origins:
    _cors_list = [o.strip() for o in _cors_origins.split(",") if o.strip()]
    if not any(
        "localhost" in o or "127.0.0.1" in o for o in _cors_list
    ):
        logger.warning(
            "LEADERBOARD_CORS_ORIGINS has no localhost — add http://localhost:3000 for Vite dev or the "
            "browser will block API calls."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Setup rate limiting
limiter = setup_rate_limiting(app)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    logger.info("Database URL: %s", database_module.DATABASE_URL)
    log_auth_config()
    logger.info("Leaderboard API started successfully")
    print("Leaderboard API started successfully")


# ==================== Dataset Endpoints ====================

@app.post("/api/datasets", response_model=SuccessResponse, status_code=201, tags=["datasets"])
async def create_dataset(
    request: Request,
    dataset: DatasetCreate,
    db: Session = Depends(get_db),
    _auth_user: Optional[AuthUser] = Depends(require_write_user),
):
    """
    Create a new benchmark dataset
    
    This endpoint allows you to add a new dataset to the leaderboard.
    You can control visibility (public/private test sets) to prevent metric gaming.
    """
    # Check if dataset name already exists
    existing = db.query(Dataset).filter(Dataset.name == dataset.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Dataset '{dataset.name}' already exists")
    
    # Create new dataset
    dataset_id = str(uuid.uuid4())
    db_dataset = Dataset(
        id=dataset_id,
        name=dataset.name,
        description=dataset.description,
        url=dataset.url,
        task_type=TaskType(dataset.task_type),
        test_set_public=dataset.test_set_public,
        labels_public=dataset.labels_public,
        primary_metric=dataset.primary_metric,
        additional_metrics=dataset.additional_metrics,
        num_examples=dataset.num_examples or len(dataset.ground_truth),
        ground_truth=dataset.ground_truth
    )
    
    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)
    
    return SuccessResponse(
        message="Dataset created successfully",
        data={"dataset_id": dataset_id, "name": dataset.name}
    )


@app.get("/api/datasets", response_model=List[DatasetPublic], tags=["datasets"])
async def list_datasets(
    task_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all available datasets (public info only)
    
    Optionally filter by task_type.
    Ground truth labels are never exposed through this endpoint.
    """
    query = db.query(Dataset)
    
    if task_type:
        try:
            query = query.filter(Dataset.task_type == TaskType(task_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid task_type: {task_type}")
    
    datasets = query.all()
    
    # Prepare public response
    result = []
    for ds in datasets:
        questions = None
        if ds.test_set_public:
            # Provide questions without answers
            questions = [
                {k: v for k, v in item.items() if k != 'answer'}
                for item in ds.ground_truth
            ]
        
        result.append(DatasetPublic(
            id=ds.id,
            name=ds.name,
            description=ds.description,
            url=ds.url,
            task_type=ds.task_type.value,
            test_set_public=ds.test_set_public,
            primary_metric=ds.primary_metric,
            num_examples=ds.num_examples,
            questions=questions
        ))
    
    return result


@app.get("/api/datasets/{dataset_id}", response_model=DatasetPublic, tags=["datasets"])
async def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db)
):
    """Get details of a specific dataset"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    questions = None
    if dataset.test_set_public:
        questions = [
            {k: v for k, v in item.items() if k != 'answer'}
            for item in dataset.ground_truth
        ]
    
    return DatasetPublic(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        url=dataset.url,
        task_type=dataset.task_type.value,
        test_set_public=dataset.test_set_public,
        primary_metric=dataset.primary_metric,
        num_examples=dataset.num_examples,
        questions=questions
    )


@app.get("/api/datasets/{dataset_id}/questions", tags=["datasets"])
async def get_dataset_questions(
    dataset_id: str,
    db: Session = Depends(get_db)
):
    """
    Get test questions for a dataset (without answers)
    
    This endpoint provides the questions and their IDs so users can prepare predictions.
    Ground truth answers are never exposed.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Return questions without answers
    questions = [
        {k: v for k, v in item.items() if k != 'answer'}
        for item in dataset.ground_truth
    ]
    
    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "task_type": dataset.task_type.value,
        "num_questions": len(questions),
        "questions": questions
    }


@app.get("/api/datasets/{dataset_id}/submission-format", tags=["datasets"])
async def get_submission_format(dataset_id: str, db: Session = Depends(get_db)):
    """
    Describe the expected submission format for a dataset.

    Intended for CLIs and external integrations to dynamically discover how to
    structure `predictions` for `POST /api/submissions`.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    task = dataset.task_type.value
    if task == "text_classification":
        prediction_shape = {"id": "string", "prediction": "string (label)"}
        example_prediction = [{"id": "1", "prediction": "positive"}]
    elif task == "named_entity_recognition":
        prediction_shape = {"id": "string", "prediction": "list of [entity_text, entity_type] pairs"}
        example_prediction = [{"id": "1", "prediction": [["Barack Obama", "PERSON"], ["Hawaii", "LOC"]]}]
    elif task in {"document_qa", "line_qa"}:
        prediction_shape = {"id": "string", "prediction": "string (answer text)"}
        example_prediction = [{"id": "q1", "prediction": "Paris"}]
    elif task == "retrieval":
        prediction_shape = {"id": "string", "prediction": "list of doc ids (ranked best→worst)"}
        example_prediction = [{"id": "q1", "prediction": ["doc7", "doc2", "doc9"]}]
    else:
        prediction_shape = {"id": "string", "prediction": "task-specific (see dataset.task_type)"}
        example_prediction = [{"id": "1", "prediction": "…"}]

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "task_type": task,
        "primary_metric": dataset.primary_metric,
        "additional_metrics": dataset.additional_metrics or [],
        "prediction_item_shape": prediction_shape,
        "example": {
            "dataset_id": dataset.id,
            "model_name": "my-awesome-model",
            "predictions": example_prediction,
        },
        "notes": [
            "IDs must match those returned by GET /api/datasets/{dataset_id}/questions.",
            "Do not include ground-truth answers in submissions; they are stored server-side.",
        ],
    }


# ==================== Submission Endpoints ====================

@app.post("/api/submissions", response_model=SuccessResponse, status_code=202, tags=["submissions"])
@limiter.limit(RATE_LIMITS["submission"])
async def submit_predictions(
    request: Request,
    submission: SubmissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth_user: Optional[AuthUser] = Depends(require_write_user),
):
    """
    Submit model predictions for evaluation
    
    Predictions are queued for evaluation. You'll receive a submission_id
    to check the status and results later.
    """
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == submission.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Create submission
    submission_id = str(uuid.uuid4())
    merged_meta = dict(submission.submission_metadata or {})
    if auth_user and (auth_user.sub or auth_user.email):
        merged_meta.setdefault(
            "anote_user",
            {"sub": auth_user.sub, "email": auth_user.email},
        )
    db_submission = Submission(
        id=submission_id,
        dataset_id=submission.dataset_id,
        model_name=submission.model_name,
        model_version=submission.model_version,
        organization=submission.organization,
        predictions=submission.predictions,
        is_internal=submission.is_internal,
        submission_metadata=merged_meta or None,
        status=SubmissionStatus.PENDING
    )
    
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    
    # Log submission
    log_api_request(
        endpoint="/api/submissions",
        method="POST",
        submission_id=submission_id,
        dataset_id=submission.dataset_id,
        model_name=submission.model_name
    )
    
    # Queue evaluation as background task
    background_tasks.add_task(evaluate_submission, submission_id)
    
    # Invalidate cache for this dataset
    invalidate_leaderboard_cache(submission.dataset_id)
    
    return SuccessResponse(
        message="Submission received and queued for evaluation",
        data={
            "submission_id": submission_id,
            "status": "pending",
            "check_status_url": f"/api/submissions/{submission_id}"
        }
    )


@app.get("/api/submissions/{submission_id}", response_model=SubmissionResponse, tags=["submissions"])
async def get_submission_status(
    submission_id: str,
    db: Session = Depends(get_db)
):
    """
    Check the status and results of a submission
    
    Returns evaluation results if completed, or status if still processing.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return SubmissionResponse(
        id=submission.id,
        dataset_id=submission.dataset_id,
        model_name=submission.model_name,
        model_version=submission.model_version,
        organization=submission.organization,
        status=submission.status.value,
        primary_score=submission.primary_score,
        detailed_scores=submission.detailed_scores,
        confidence_interval=submission.confidence_interval,
        is_internal=submission.is_internal,
        created_at=submission.created_at,
        evaluated_at=submission.evaluated_at,
        error_message=submission.error_message
    )


@app.get("/api/submissions", response_model=List[SubmissionResponse], tags=["submissions"])
async def list_submissions(
    dataset_id: Optional[str] = None,
    model_name: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all submissions with optional filters"""
    query = db.query(Submission)
    
    if dataset_id:
        query = query.filter(Submission.dataset_id == dataset_id)
    if model_name:
        query = query.filter(Submission.model_name == model_name)
    if status:
        try:
            query = query.filter(Submission.status == SubmissionStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    submissions = query.order_by(Submission.created_at.desc()).all()
    
    return [
        SubmissionResponse(
            id=sub.id,
            dataset_id=sub.dataset_id,
            model_name=sub.model_name,
            model_version=sub.model_version,
            organization=sub.organization,
            status=sub.status.value,
            primary_score=sub.primary_score,
            detailed_scores=sub.detailed_scores,
            confidence_interval=sub.confidence_interval,
            is_internal=sub.is_internal,
            created_at=sub.created_at,
            evaluated_at=sub.evaluated_at,
            error_message=sub.error_message
        )
        for sub in submissions
    ]


# ==================== Leaderboard Endpoints ====================

@app.get("/api/leaderboard", response_model=List[LeaderboardResponse], tags=["leaderboards"])
@limiter.limit(RATE_LIMITS["leaderboard"])
@cached_leaderboard
async def get_all_leaderboards(
    request: Request,
    task_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get leaderboard for all datasets
    
    Returns ranked model submissions for each dataset.
    Optionally filter by task_type.
    """
    query = db.query(Dataset)
    
    if task_type:
        try:
            query = query.filter(Dataset.task_type == TaskType(task_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid task_type: {task_type}")
    
    datasets = query.all()
    leaderboards: List[LeaderboardResponse] = []
    
    for dataset in datasets:
        # Get completed submissions sorted by score
        submissions = (
            db.query(Submission)
            .filter(
                Submission.dataset_id == dataset.id,
                Submission.status == SubmissionStatus.COMPLETED,
                Submission.primary_score.isnot(None),
            )
            .order_by(Submission.primary_score.desc())
            .all()
        )
        submissions = [s for s in submissions if _is_finite_score(s.primary_score)]

        entries = []
        for rank, sub in enumerate(submissions, start=1):
            # Format date
            updated_month = sub.evaluated_at.strftime("%b %Y") if sub.evaluated_at else "N/A"

            # Create entry dict with detailed scores
            entry_data = {
                "rank": rank,
                "model_name": sub.model_name,
                "score": float(sub.primary_score),
                "confidence_interval": sub.confidence_interval,
                "updated_at": updated_month,
                "is_internal": sub.is_internal,
                "submission_id": sub.id,
                "detailed_scores": _sanitize_detailed_scores(sub.detailed_scores),
            }
            entries.append(entry_data)
        
        # Always include the dataset, even if there are no submissions yet.
        # This ensures that newly imported benchmarks (e.g., from HuggingFace)
        # are visible in the frontend and can show "0 models" instead of
        # being entirely hidden.
        try:
            tt = dataset.task_type.value
        except Exception:
            tt = str(dataset.task_type)
        leaderboards.append(LeaderboardResponse(
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            task_type=tt,
            url=dataset.url,
            primary_metric=dataset.primary_metric,
            entries=entries,
        ))
    
    return leaderboards


@app.get("/api/leaderboard/{dataset_id}", response_model=LeaderboardResponse, tags=["leaderboards"])
@limiter.limit(RATE_LIMITS["leaderboard"])
@cached_leaderboard
async def get_dataset_leaderboard(
    request: Request,
    dataset_id: str,
    include_internal: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get leaderboard for a specific dataset
    
    Optionally filter out internal submissions with include_internal=false
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    query = db.query(Submission).filter(
        Submission.dataset_id == dataset_id,
        Submission.status == SubmissionStatus.COMPLETED,
        Submission.primary_score.isnot(None),
    )
    
    if not include_internal:
        query = query.filter(Submission.is_internal == False)
    
    submissions = query.order_by(Submission.primary_score.desc()).all()
    submissions = [s for s in submissions if _is_finite_score(s.primary_score)]

    entries = []
    for rank, sub in enumerate(submissions, start=1):
        updated_month = sub.evaluated_at.strftime("%b %Y") if sub.evaluated_at else "N/A"

        entries.append({
            "rank": rank,
            "model_name": sub.model_name,
            "score": float(sub.primary_score),
            "confidence_interval": sub.confidence_interval,
            "updated_at": updated_month,
            "is_internal": sub.is_internal,
            "submission_id": sub.id,
            "detailed_scores": _sanitize_detailed_scores(sub.detailed_scores),
        })
    
    try:
        tt = dataset.task_type.value
    except Exception:
        tt = str(dataset.task_type)
    return LeaderboardResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        task_type=tt,
        url=dataset.url,
        primary_metric=dataset.primary_metric,
        entries=entries
    )


# ==================== Data Management ====================

@app.post("/api/admin/seed-data", response_model=SuccessResponse, tags=["admin"])
@limiter.limit(RATE_LIMITS["admin"])
async def seed_sample_data(
    request: Request,
    db: Session = Depends(get_db),
    _auth_user: Optional[AuthUser] = Depends(require_write_user),
):
    """
    Load sample datasets and baseline models
    
    This populates the leaderboard with popular benchmarks.
    """
    try:
        from seed_data import SAMPLE_DATASETS, create_baseline_predictions
        from datetime import datetime as dt
        
        datasets_added = 0
        submissions_added = 0
        
        for dataset_config in SAMPLE_DATASETS:
            # Check if dataset already exists
            existing = db.query(Dataset).filter(Dataset.name == dataset_config["name"]).first()
            if existing:
                continue
            
            # Create dataset
            dataset_id = str(uuid.uuid4())
            dataset = Dataset(
                id=dataset_id,
                name=dataset_config["name"],
                description=dataset_config["description"],
                url=dataset_config["url"],
                task_type=TaskType(dataset_config["task_type"]),
                test_set_public=dataset_config["test_set_public"],
                labels_public=dataset_config["labels_public"],
                primary_metric=dataset_config["primary_metric"],
                additional_metrics=dataset_config["additional_metrics"],
                num_examples=len(dataset_config["ground_truth"]),
                ground_truth=dataset_config["ground_truth"]
            )
            db.add(dataset)
            db.flush()
            datasets_added += 1
            
            # Create baseline submissions
            for baseline in dataset_config.get("baseline_models", []):
                submission_id = str(uuid.uuid4())
                predictions = create_baseline_predictions(
                    dataset_config["ground_truth"],
                    baseline["score"]
                )
                
                submission = Submission(
                    id=submission_id,
                    dataset_id=dataset_id,
                    model_name=baseline["model"],
                    model_version=baseline.get("version"),
                    organization=baseline.get("organization"),
                    predictions=predictions,
                    status=SubmissionStatus.COMPLETED,
                    primary_score=baseline["score"],
                    detailed_scores={dataset_config["primary_metric"]: baseline["score"]},
                    confidence_interval=f"{baseline['score']-0.02:.2f} - {baseline['score']+0.02:.2f}",
                    is_internal=True,
                    created_at=dt.now(),
                    evaluated_at=dt.now()
                )
                db.add(submission)
                submissions_added += 1
            
            db.commit()
        
        return SuccessResponse(
            message="Sample data loaded successfully",
            data={
                "datasets_added": datasets_added,
                "submissions_added": submissions_added
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/import-huggingface", response_model=SuccessResponse, tags=["admin"])
@limiter.limit(RATE_LIMITS["admin"])
async def import_from_huggingface(
    request: Request,
    dataset_name: str,
    config: str = "default",
    split: str = "test",
    num_samples: int = 100,
    db: Session = Depends(get_db),
    _auth_user: Optional[AuthUser] = Depends(require_write_user),
):
    """
    Import a dataset from HuggingFace Hub
    
    Args:
        dataset_name: HuggingFace dataset identifier (e.g., "ag_news")
        config: Dataset configuration/subset
        split: Dataset split (train/validation/test)
        num_samples: Number of samples to import
    """
    try:
        from hf_importer import HuggingFaceImporter
        
        # Import from HuggingFace
        importer = HuggingFaceImporter()
        dataset_data = importer.import_dataset(dataset_name, config, split, num_samples)
        
        if not dataset_data:
            raise HTTPException(status_code=400, detail="Failed to import dataset from HuggingFace")
        
        # Check if dataset already exists
        existing = db.query(Dataset).filter(Dataset.name == dataset_data["name"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Dataset already exists")
        
        # Create dataset
        dataset_id = str(uuid.uuid4())
        # Avoid passing task_type/name/num_examples twice (from **dataset_data and explicit args)
        filtered_data = {
            k: v
            for k, v in dataset_data.items()
            if k not in {"name", "task_type", "num_examples"}
        }
        dataset = Dataset(
            id=dataset_id,
            **filtered_data,
            name=dataset_data["name"],
            task_type=TaskType(dataset_data["task_type"]),
            num_examples=len(dataset_data["ground_truth"])
        )
        
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        return SuccessResponse(
            message=f"Successfully imported {dataset_name} from HuggingFace",
            data={
                "dataset_id": dataset_id,
                "name": dataset_data["name"],
                "num_examples": len(dataset_data["ground_truth"])
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Metrics Information ====================

@app.get("/api/metrics", tags=["metrics"])
async def get_all_metrics():
    """Get information about all available metrics"""
    from metrics_info import METRICS_CATALOG
    return METRICS_CATALOG


@app.get("/api/metrics/{metric_name}", tags=["metrics"])
async def get_metric_info(metric_name: str):
    """Get detailed information about a specific metric"""
    from metrics_info import get_metric_info as get_info
    info = get_info(metric_name)
    if not info.get("description"):
        raise HTTPException(status_code=404, detail="Metric not found")
    return info


@app.get("/api/metrics/task/{task_type}", tags=["metrics"])
async def get_task_metrics(task_type: str):
    """Get all relevant metrics for a specific task type"""
    from metrics_info import get_metrics_for_task, get_metric_info as get_info
    
    metric_names = get_metrics_for_task(task_type)
    metrics = {name: get_info(name) for name in metric_names}
    return metrics


# ==================== Health Check & Monitoring ====================

@app.get("/api/me", response_model=MeResponse, tags=["auth"])
async def api_me(request: Request):
    """Who is calling (Anote JWT, Google ID token, introspect, or cookies)."""
    mode = auth_mode()
    user = resolve_user(request)
    if user and (user.sub or user.email):
        return MeResponse(
            authenticated=True,
            auth_mode=mode,
            sub=user.sub,
            email=user.email,
        )
    return MeResponse(authenticated=False, auth_mode=mode)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "leaderboard-api"}


@app.get("/api/admin/cache-stats", tags=["admin"])
@limiter.limit(RATE_LIMITS["admin"])
async def get_cache_statistics(
    request: Request,
    _auth_user: Optional[AuthUser] = Depends(require_write_user),
):
    """Get cache statistics for monitoring"""
    return get_cache_stats()


@app.post("/api/admin/clear-cache", tags=["admin"])
@limiter.limit(RATE_LIMITS["admin"])
async def clear_cache(
    request: Request,
    dataset_id: Optional[str] = None,
    _auth_user: Optional[AuthUser] = Depends(require_write_user),
):
    """Clear cache (all or for specific dataset)"""
    invalidate_leaderboard_cache(dataset_id)
    return SuccessResponse(
        message="Cache cleared successfully",
        data={"dataset_id": dataset_id or "all"}
    )

