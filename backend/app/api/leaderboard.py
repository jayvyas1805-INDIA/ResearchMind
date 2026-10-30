"""
API routes for the cross-paper results leaderboard.

This is the feature that a plain "paste-into-ChatGPT" workflow can't
replicate: a persistent, structured, filterable table of numeric claims
extracted across your ENTIRE paper library, that grows as you upload more
papers — not a one-off answer regenerated from scratch each time.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.paper import Paper
from app.models.result_claim import ResultClaim
from app.schemas.leaderboard import LeaderboardEntryOut, LeaderboardFacetsOut, LeaderboardResponse

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("", response_model=LeaderboardResponse)
def get_leaderboard(
    dataset: str | None = Query(default=None, description="Filter by dataset name (case-insensitive substring)"),
    metric: str | None = Query(default=None, description="Filter by metric name (case-insensitive substring)"),
    model: str | None = Query(default=None, description="Filter by model name (case-insensitive substring)"),
    min_value: float | None = Query(default=None, description="Only claims with a parsed value >= this"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(ResultClaim, Paper.title, Paper.filename, Paper.upload_date).join(
        Paper, ResultClaim.paper_id == Paper.id
    )

    if dataset:
        query = query.filter(ResultClaim.dataset_name.ilike(f"%{dataset}%"))
    if metric:
        query = query.filter(ResultClaim.metric_name.ilike(f"%{metric}%"))
    if model:
        query = query.filter(ResultClaim.model_name.ilike(f"%{model}%"))
    if min_value is not None:
        query = query.filter(ResultClaim.value >= min_value)

    # Highest reported value first — nulls (unparseable values) sort last.
    query = query.order_by(ResultClaim.value.is_(None), ResultClaim.value.desc())

    rows = query.limit(limit).all()

    entries = [
        LeaderboardEntryOut(
            id=claim.id,
            paper_id=claim.paper_id,
            paper_title=title or filename,
            model_name=claim.model_name,
            dataset_name=claim.dataset_name,
            metric_name=claim.metric_name,
            value_text=claim.value_text,
            value=claim.value,
            sentence=claim.sentence,
            page_number=claim.page_number,
            upload_date=upload_date,
        )
        for claim, title, filename, upload_date in rows
    ]

    return LeaderboardResponse(result_count=len(entries), entries=entries)


@router.get("/facets", response_model=LeaderboardFacetsOut)
def get_leaderboard_facets(db: Session = Depends(get_db)):
    """Distinct values available to filter by — powers the UI's dropdowns."""
    models = sorted({row[0] for row in db.query(ResultClaim.model_name).filter(ResultClaim.model_name.isnot(None)).distinct()})
    datasets = sorted({row[0] for row in db.query(ResultClaim.dataset_name).filter(ResultClaim.dataset_name.isnot(None)).distinct()})
    metrics = sorted({row[0] for row in db.query(ResultClaim.metric_name).distinct()})
    return LeaderboardFacetsOut(models=models, datasets=datasets, metrics=metrics)
