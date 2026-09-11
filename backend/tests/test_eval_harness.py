"""
Tests for the eval harness's scoring math (Recall@k / MRR) — retrieval
itself is mocked so this verifies the metric computation is correct,
independent of any live embedding model or FAISS index.
"""
from unittest.mock import patch

from eval.run_eval import evaluate
from app.services.retrieval_service import SearchResult


def _result(page):
    return SearchResult(chunk_id=page, paper_id="p1", chunk_text="x", page_number=page, section="s", similarity_score=0.5)


def test_recall_and_mrr_perfect_retrieval(db_session):
    qa_set = {"paper_id": "p1", "questions": [{"question": "q1", "relevant_pages": [2]}]}
    with patch("eval.run_eval.retrieval_service.search", return_value=[_result(2), _result(3)]):
        report = evaluate(qa_set, db_session, ks=[1, 5])

    assert report["recall_at_k"][1] == 1.0
    assert report["recall_at_k"][5] == 1.0
    assert report["mrr"] == 1.0


def test_recall_and_mrr_late_hit():
    qa_set = {"paper_id": "p1", "questions": [{"question": "q1", "relevant_pages": [5]}]}
    with patch("eval.run_eval.retrieval_service.search", return_value=[_result(1), _result(2), _result(5)]):
        report = evaluate(qa_set, db=None, ks=[1, 3])

    assert report["recall_at_k"][1] == 0.0   # correct page is rank 3, not top-1
    assert report["recall_at_k"][3] == 1.0
    assert abs(report["mrr"] - (1 / 3)) < 1e-9


def test_recall_and_mrr_complete_miss():
    qa_set = {"paper_id": "p1", "questions": [{"question": "q1", "relevant_pages": [99]}]}
    with patch("eval.run_eval.retrieval_service.search", return_value=[_result(1), _result(2)]):
        report = evaluate(qa_set, db=None, ks=[1, 5])

    assert report["recall_at_k"][1] == 0.0
    assert report["recall_at_k"][5] == 0.0
    assert report["mrr"] == 0.0


def test_averages_across_multiple_questions():
    qa_set = {
        "paper_id": "p1",
        "questions": [
            {"question": "hit", "relevant_pages": [1]},
            {"question": "miss", "relevant_pages": [99]},
        ],
    }
    side_effects = [[_result(1)], [_result(2)]]
    with patch("eval.run_eval.retrieval_service.search", side_effect=side_effects):
        report = evaluate(qa_set, db=None, ks=[1])

    assert report["recall_at_k"][1] == 0.5  # 1 of 2 questions hit
    assert report["mrr"] == 0.5              # (1.0 + 0.0) / 2
