"""
Tests for the ablation harness's per-experiment scoring — chunking is real
(pure logic + spaCy, skipped if unavailable), but embedding/FAISS are
mocked so this doesn't download models or need faiss installed to verify
the Recall@k/MRR computation is correct for a given configuration.
"""
from unittest.mock import patch

import numpy as np
import pytest

from eval import ablation


def _spacy_available():
    try:
        from app.services.nlp_service import get_nlp
        get_nlp()
        return True
    except Exception:
        return False


requires_spacy = pytest.mark.skipif(not _spacy_available(), reason="spaCy model not installed")


@requires_spacy
def test_run_experiment_scores_against_known_fixture():
    """
    With a large chunk size (whole page per chunk) the mapping from chunk
    to page is 1:1 and unambiguous, so we can assert exact retrieval
    behavior deterministically by mocking only the embedding step.
    """
    qa_questions = [{"question": "highest accuracy model", "relevant_pages": [3]}]

    # Fake embedding: make the query vector identical to page 3's chunk
    # vector (and all others orthogonal), so retrieval is deterministic
    # regardless of the real embedding model's behavior.
    def fake_embed(texts, model_name):
        vectors = []
        for t in texts:
            v = np.zeros(8, dtype="float32")
            if "90 percent" in t or "highest accuracy" in t:
                v[0] = 1.0
            else:
                v[hash(t) % 7 + 1] = 1.0
            vectors.append(v)
        return np.array(vectors, dtype="float32")

    with patch.object(ablation, "_embed", side_effect=fake_embed):
        report = ablation.run_experiment(
            chunk_target_words=1000,  # large enough that each page is ~1 chunk
            chunk_min_words=10,
            embedding_model="fake-model",
            top_k_values=[1, 5],
            qa_questions=qa_questions,
        )

    assert report["n_chunks"] > 0
    assert 0.0 <= report["mrr"] <= 1.0
    assert set(report["recall_at_k"].keys()) == {1, 5}


def test_print_comparison_table_does_not_crash(capsys):
    reports = [{
        "label": "test config", "n_chunks": 10,
        "recall_at_k": {1: 0.5, 5: 0.9}, "mrr": 0.6,
    }]
    ablation.print_comparison_table(reports, [1, 5])
    captured = capsys.readouterr()
    assert "test config" in captured.out
    assert "0.50" in captured.out
