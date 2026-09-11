"""API route for semantic search within a paper."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.paper import Paper
from app.schemas.search import SearchRequest, SearchResponse, SearchResultOut
from app.services import retrieval_service

logger = logging.getLogger("papermind.search")

router = APIRouter(prefix="/papers", tags=["Search"])


def _run_search(paper_id: str, query: str, top_k: int | None, use_hybrid: bool, db: Session) -> SearchResponse:
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    try:
        if use_hybrid:
            results = retrieval_service.hybrid_search(query=query, db=db, paper_id=paper_id, top_k=top_k)
        else:
            results = retrieval_service.search(query=query, db=db, paper_id=paper_id, top_k=top_k)
    except Exception as exc:
        logger.exception("Search failed for paper %s", paper_id)
        raise HTTPException(status_code=500, detail="Search failed. Please try again.") from exc

    return SearchResponse(
        query=query,
        paper_id=paper_id,
        result_count=len(results),
        method="hybrid" if use_hybrid else "vector",
        results=[
            SearchResultOut(
                chunk_id=r.chunk_id,
                paper_id=r.paper_id,
                text=r.chunk_text,
                page_number=r.page_number,
                section=r.section,
                similarity_score=r.similarity_score,
            )
            for r in results
        ],
    )


@router.get("/{paper_id}/search", response_model=SearchResponse)
def search_paper_get(
    paper_id: str,
    q: str = Query(..., min_length=1, description="Natural-language search query"),
    top_k: int | None = Query(default=None, ge=1, le=50),
    hybrid: bool = Query(default=False, description="Fuse BM25 + vector search via RRF"),
    db: Session = Depends(get_db),
):
    return _run_search(paper_id, q, top_k, hybrid, db)


@router.post("/{paper_id}/search", response_model=SearchResponse)
def search_paper_post(paper_id: str, body: SearchRequest, db: Session = Depends(get_db)):
    return _run_search(paper_id, body.query, body.top_k, body.use_hybrid, db)
