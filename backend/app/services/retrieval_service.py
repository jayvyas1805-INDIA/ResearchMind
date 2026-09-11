"""
Retrieval service.

Provides search(query, paper_id=None, top_k=5): embeds the query, searches
the FAISS index, and resolves the resulting vector ids back to their Chunk
rows (text, page, section) via the database.

Also provides hybrid_search(): fuses this vector ranking with a BM25
lexical ranking via Reciprocal Rank Fusion (RRF). Pure vector similarity
misses exact-term matches (model names, numbers, acronyms) that a keyword
search catches trivially — hybrid retrieval is standard practice in
production RAG systems for exactly this reason.

Exposed via the API in Phase 5 (see app/api/search.py).
"""

import re
from dataclasses import dataclass
from typing import Optional

from rank_bm25 import BM25Okapi
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
    Semantic (vector-only) search over indexed chunks.

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


# ---------------------------------------------------------------------------
# Hybrid retrieval: vector search + BM25 lexical search, fused via RRF
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _vector_ranking(query_vector, paper_id: str, db: Session, candidate_k: int) -> list[int]:
    """Chunk ids for one paper, ordered by vector similarity (best first)."""
    fetch_k = candidate_k * 5  # over-fetch, then filter to this paper
    raw = vector_service.search(query_vector, top_k=fetch_k)
    if not raw:
        return []
    paper_chunk_ids = {row[0] for row in db.query(Chunk.id).filter(Chunk.paper_id == paper_id).all()}
    ranking = [chunk_id for chunk_id, _ in raw if chunk_id in paper_chunk_ids]
    return ranking[:candidate_k]


def _bm25_ranking(query: str, paper_id: str, db: Session, candidate_k: int) -> list[int]:
    """Chunk ids for one paper, ordered by BM25 lexical score (best first)."""
    chunks = db.query(Chunk).filter(Chunk.paper_id == paper_id).all()
    if not chunks:
        return []

    corpus_tokens = [_tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(_tokenize(query))

    ranked = sorted(zip([c.id for c in chunks], scores), key=lambda pair: pair[1], reverse=True)
    # Drop zero-score chunks — BM25 gives 0 when there's no term overlap at
    # all, which isn't a meaningful "match" worth fusing in.
    return [chunk_id for chunk_id, score in ranked[:candidate_k] if score > 0]


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """
    Combine multiple rankings of the same item ids into one fused ranking.

    RRF score for an item = sum over rankers of 1/(k + rank_in_that_ranker).
    An item missing from a ranking simply contributes 0 from that ranker.
    k=60 is the commonly used default from the original RRF paper — it
    dampens the influence of any single ranker's exact rank position.
    """
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)


def hybrid_search(
    query: str,
    db: Session,
    paper_id: str,
    top_k: int = None,
    candidate_k: int = 20,
) -> list[SearchResult]:
    """
    Hybrid retrieval: fuses vector search and BM25 lexical search via RRF.

    Requires paper_id (BM25 needs a bounded corpus to score against) — for
    a global, cross-paper search, use search() instead.

    Note: similarity_score on the returned results is the fused RRF score,
    not a cosine similarity — it's for relative ranking within this result
    set, not comparable across calls or against search()'s scores.
    """
    if top_k is None:
        top_k = settings.DEFAULT_TOP_K
    if not query or not query.strip() or not paper_id:
        return []

    query_vector = embedding_service.embed_query(query)
    vector_ranking = _vector_ranking(query_vector, paper_id, db, candidate_k)
    bm25_ranking = _bm25_ranking(query, paper_id, db, candidate_k)

    fused = reciprocal_rank_fusion([vector_ranking, bm25_ranking])
    if not fused:
        return []

    top_ids = [chunk_id for chunk_id, _ in fused[:top_k]]
    fused_scores = dict(fused)

    chunks = db.query(Chunk).filter(Chunk.id.in_(top_ids)).all()
    chunk_by_id = {c.id: c for c in chunks}

    results: list[SearchResult] = []
    for chunk_id in top_ids:
        chunk = chunk_by_id.get(chunk_id)
        if chunk is None:
            continue
        results.append(
            SearchResult(
                chunk_id=chunk.id,
                paper_id=chunk.paper_id,
                chunk_text=chunk.text,
                page_number=chunk.page_number,
                section=chunk.section,
                similarity_score=fused_scores[chunk_id],
            )
        )
    return results
