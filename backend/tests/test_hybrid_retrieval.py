"""
Tests for Reciprocal Rank Fusion (pure function, no dependencies) and
hybrid_search's fusion logic (vector/BM25 rankings mocked so this doesn't
need a live embedding model, FAISS index, or rank_bm25 installed).
"""
from unittest.mock import patch

import numpy as np

from app.services.retrieval_service import reciprocal_rank_fusion


def test_rrf_agrees_when_both_rankers_agree():
    # Both rankers put item 1 first, item 2 second — fused order should match.
    fused = reciprocal_rank_fusion([[1, 2, 3], [1, 2, 3]])
    fused_ids = [item_id for item_id, _ in fused]
    assert fused_ids == [1, 2, 3]


def test_rrf_boosts_items_ranked_well_by_multiple_rankers():
    # Item 2 is #1 in ranker A but missing from ranker B.
    # Item 3 is #2 in both rankers — appearing in both should let it win
    # even though it's never ranked #1 anywhere.
    fused = reciprocal_rank_fusion([[2, 3, 4], [3, 5, 6]])
    fused_ids = [item_id for item_id, _ in fused]
    assert fused_ids[0] == 3  # appears near the top in both rankings


def test_rrf_handles_disjoint_rankings():
    fused = reciprocal_rank_fusion([[1, 2], [3, 4]])
    fused_ids = {item_id for item_id, _ in fused}
    assert fused_ids == {1, 2, 3, 4}


def test_rrf_handles_empty_rankings():
    assert reciprocal_rank_fusion([[], []]) == []


def test_hybrid_search_fuses_vector_and_bm25_rankings(db_session):
    from app.models.chunk import Chunk
    from app.services import retrieval_service

    for i in [1, 2, 3]:
        db_session.add(Chunk(id=i, paper_id="paper-A", chunk_index=0, page_number=i, section="s", text=f"chunk {i} text"))
    db_session.commit()

    with patch("app.services.retrieval_service.embedding_service.embed_query", return_value=np.zeros(384)), \
         patch("app.services.retrieval_service._vector_ranking", return_value=[1, 2, 3]), \
         patch("app.services.retrieval_service._bm25_ranking", return_value=[2, 1, 3]):
        results = retrieval_service.hybrid_search("query", db_session, paper_id="paper-A", top_k=3)

    assert len(results) == 3
    # Items 1 and 2 both rank highly in both lists, so should outrank item 3
    # (which is last in both).
    result_ids = [r.chunk_id for r in results]
    assert result_ids[-1] == 3


def test_hybrid_search_requires_paper_id(db_session):
    from app.services import retrieval_service
    assert retrieval_service.hybrid_search("query", db_session, paper_id="") == []


def test_search_tokenizer_ignores_question_stop_words():
    from app.services.retrieval_service import _tokenize

    assert _tokenize("Which dataset was used to evaluate the model?") == [
        "dataset", "evaluate", "model"
    ]


def test_bm25_search_ignores_reference_chunks(db_session):
    from app.models.chunk import Chunk
    from app.services.retrieval_service import _bm25_ranking

    db_session.add_all([
        Chunk(
            id=1, paper_id="paper-A", chunk_index=0, section="methodology",
            text="We evaluate the approach on the HumanEval benchmark dataset.",
        ),
        Chunk(
            id=2, paper_id="paper-A", chunk_index=1, section="references",
            text="HumanEval dataset paper and benchmark study reference.",
        ),
    ])
    db_session.commit()

    assert _bm25_ranking("Which dataset was used?", "paper-A", db_session, 10) == [1]


def test_vector_ranking_searches_past_global_top_k_before_paper_filter(db_session):
    from app.models.chunk import Chunk
    from app.services import retrieval_service

    db_session.add_all([
        Chunk(id=1, paper_id="other-paper", chunk_index=0, text="unrelated global result"),
        Chunk(id=2, paper_id="target-paper", chunk_index=0, text="target paper result"),
    ])
    db_session.commit()

    with patch(
        "app.services.retrieval_service.vector_service.get_vector_count",
        return_value=200,
    ), patch(
        "app.services.retrieval_service.vector_service.search",
        return_value=[(1, 0.9), (2, 0.8)],
    ) as mock_search:
        results = retrieval_service._vector_ranking(
            np.zeros(384), "target-paper", db_session, candidate_k=20
        )

    assert results == [2]
    assert mock_search.call_count == 1
    assert mock_search.call_args.kwargs["top_k"] == 200


def test_hybrid_search_does_not_return_reference_chunks(db_session):
    from app.models.chunk import Chunk
    from app.services import retrieval_service

    db_session.add_all([
        Chunk(id=1, paper_id="paper-A", chunk_index=0, section="results", text="paper result passage"),
        Chunk(id=2, paper_id="paper-A", chunk_index=1, section="references", text="reference passage"),
    ])
    db_session.commit()

    with patch("app.services.retrieval_service.embedding_service.embed_query", return_value=np.zeros(384)), \
         patch("app.services.retrieval_service._vector_ranking", return_value=[2, 1]), \
         patch("app.services.retrieval_service._bm25_ranking", return_value=[2, 1]):
        results = retrieval_service.hybrid_search("paper result", db_session, "paper-A", top_k=2)

    assert [result.chunk_id for result in results] == [1]
