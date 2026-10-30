"""API route for comparing two papers."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.paper import Paper
from app.schemas.comparison import CompareRequest, ComparisonOut
from app.services import comparison_service, llm_service

logger = logging.getLogger("papermind.comparison")

router = APIRouter(prefix="/papers", tags=["Comparison"])


@router.post("/compare", response_model=ComparisonOut)
def compare_papers(body: CompareRequest, db: Session = Depends(get_db)):
    if body.paper_id_1 == body.paper_id_2:
        raise HTTPException(status_code=400, detail="Please select two different papers.")

    paper1 = db.query(Paper).filter(Paper.id == body.paper_id_1).first()
    paper2 = db.query(Paper).filter(Paper.id == body.paper_id_2).first()
    if not paper1 or not paper2:
        raise HTTPException(status_code=404, detail="One or both papers were not found.")

    try:
        result = comparison_service.compare_papers(paper1, paper2)
    except llm_service.LLMError as exc:
        logger.error("LLM error comparing papers: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Comparison failed for %s vs %s", body.paper_id_1, body.paper_id_2)
        raise HTTPException(status_code=500, detail="Comparison failed.") from exc

    return ComparisonOut(**result)
