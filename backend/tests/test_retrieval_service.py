"""
Tests for retrieval_service.search — FAISS and the embedding model are
mocked out so this runs fast and without needing them installed/loaded.
"""
from unittest.mock import patch

import numpy as np

from app.models.chunk import Chunk
from app.services import retrieval_service


def _make_chunk(db, chunk_id, paper_id, text="some text", page=1, section="results"):
    c = Chunk(id=chunk_id, paper_id=paper_id, chunk_index=0, page_number=page, section=section, text=text)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_search_filters_by_paper_id(db_session):
    _make_chunk(db_session, 1, "paper-A", text="chunk from paper A")
    _make_chunk(db_session, 2, "paper-B", text="chunk from paper B")

    with patch("app.services.retrieval_service.embedding_service.embed_query", return_value=np.zeros(384)), \
         patch("app.services.retrieval_service.vector_service.search", return_value=[(1, 0.9), (2, 0.8)]):
        results = retrieval_service.search("some query", db_session, paper_id="paper-A", top_k=5)

    assert len(results) == 1
    assert results[0].paper_id == "paper-A"
    assert results[0].chunk_id == 1


def test_search_drops_results_below_min_score(db_session):
    _make_chunk(db_session, 1, "paper-A", text="weak match")

    with patch("app.services.retrieval_service.embedding_service.embed_query", return_value=np.zeros(384)), \
         patch("app.services.retrieval_service.vector_service.search", return_value=[(1, 0.05)]):
        results = retrieval_service.search("query", db_session, paper_id="paper-A", min_score=0.2)

    assert results == []


def test_search_returns_empty_list_for_blank_query(db_session):
    results = retrieval_service.search("   ", db_session)
    assert results == []


def test_search_handles_no_index_results(db_session):
    with patch("app.services.retrieval_service.embedding_service.embed_query", return_value=np.zeros(384)), \
         patch("app.services.retrieval_service.vector_service.search", return_value=[]):
        results = retrieval_service.search("query", db_session)
    assert results == []
