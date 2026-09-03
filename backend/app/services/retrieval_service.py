"""
Retrieval service.

Provides search(query, paper_id=None, top_k=5): embeds the query, searches
the FAISS index, and resolves the resulting vector ids back to their Chunk
rows (text, page, section) via the database.

Exposed via the API in Phase 5 (see app/api/search.py).
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.chunk import Chunk
from app.services import embedding_service, vector_service

settings = get_settings()


@dataclass
class SearchResult:
    chunk_id: int
    paper_id: str
    chunk_text: str
    page_number: Optional[int]
    section: Optional[str]
    similarity_score: float


def search(
    query: str,
    db: Session,
    paper_id: Optional[str] = None,
    top_k: int = None,
    min_score: Optional[float] = None,
) -> list[SearchResult]:
    """
    Semantic search over indexed chunks.

    If paper_id is given, results are restricted to that paper by
    over-fetching from FAISS and filtering in Python — simple and fine at
    small/medium (single-user, student-project) scale. A dedicated
    per-paper index or metadata filtering would be the next step if this
    needs to scale further.

    min_score: results with similarity below this are dropped as not
    relevant. Defaults to settings.MIN_SIMILARITY_THRESHOLD.
    """
    if top_k is None:
        top_k = settings.DEFAULT_TOP_K
    if min_score is None:
        min_score = settings.MIN_SIMILARITY_THRESHOLD

    if not query or not query.strip():
        return []

    query_vector = embedding_service.embed_query(query)

    # Over-fetch when filtering by paper, since some top hits may belong to
    # other papers and get filtered out below.
    fetch_k = top_k * 5 if paper_id else top_k
    raw_results = vector_service.search(query_vector, top_k=fetch_k)
    if not raw_results:
        return []

    chunk_ids = [chunk_id for chunk_id, _ in raw_results]
    chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
    chunk_by_id = {c.id: c for c in chunks}

    results: list[SearchResult] = []
    for chunk_id, score in raw_results:
        if score < min_score:
            continue
        chunk = chunk_by_id.get(chunk_id)
        if chunk is None:
            continue  # stale vector (e.g. chunk deleted but index not yet updated)
        if paper_id and chunk.paper_id != paper_id:
            continue

        results.append(
            SearchResult(
                chunk_id=chunk.id,
                paper_id=chunk.paper_id,
                chunk_text=chunk.text,
                page_number=chunk.page_number,
                section=chunk.section,
                similarity_score=score,
            )
        )
        if len(results) >= top_k:
            break

    return results
