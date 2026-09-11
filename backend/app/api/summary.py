"""API routes for generating a structured research summary."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.paper import Paper
from app.schemas.summary import SummaryOut
from app.services import llm_service, summary_service

logger = logging.getLogger("papermind.summary")

router = APIRouter(prefix="/papers", tags=["Summary"])


def _get_paper_or_404(paper_id: str, db: Session) -> Paper:
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return paper


def _generate_and_cache(paper: Paper, db: Session) -> SummaryOut:
    try:
        data = summary_service.generate_summary(paper, db)
    except llm_service.LLMError as exc:
        logger.error("LLM error generating summary for %s: %s", paper.id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Summary generation failed for %s", paper.id)
        raise HTTPException(status_code=500, detail="Summary generation failed.") from exc

    paper.summary_json = json.dumps(data)
    db.commit()
    return SummaryOut(**data)


@router.get("/{paper_id}/summary", response_model=SummaryOut)
def get_summary(paper_id: str, db: Session = Depends(get_db)):
    paper = _get_paper_or_404(paper_id, db)
    if paper.summary_json:
        return SummaryOut(**json.loads(paper.summary_json))
    return _generate_and_cache(paper, db)


@router.post("/{paper_id}/summary", response_model=SummaryOut)
def regenerate_summary(paper_id: str, db: Session = Depends(get_db)):
    paper = _get_paper_or_404(paper_id, db)
    return _generate_and_cache(paper, db)
