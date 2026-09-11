"""
Tests for the groundedness checker's aggregation logic. The NLI model
itself is mocked (via get_nli_model) so this runs without downloading
cross-encoder/nli-deberta-v3-small — these tests verify the score
aggregation and thresholding math is correct, not the model's judgment.
"""
from unittest.mock import MagicMock, patch

import numpy as np

from app.services import groundedness_service as gs


def _mock_model(three_class_scores):
    """three_class_scores: list of [contradiction, entailment, neutral] rows."""
    model = MagicMock()
    model.predict.return_value = np.array(three_class_scores)
    return model


def test_fully_supported_answer_is_grounded():
    # 1 sentence, 1 chunk, strongly entailed.
    with patch.object(gs, "get_nli_model", return_value=_mock_model([[0.0, 5.0, 0.0]])), \
         patch.object(gs, "_split_into_sentences", return_value=["The model achieved 90% accuracy."]):
        report = gs.check_groundedness("The model achieved 90% accuracy.", ["LSTM reached 90% accuracy on the test set."])

    assert report.grounded is True
    assert report.supported_ratio == 1.0
    assert report.sentence_scores[0].support_score > 0.9


def test_unsupported_sentence_lowers_ratio():
    # 2 sentences, 1 chunk: first entailed, second contradicted/neutral.
    with patch.object(gs, "get_nli_model", return_value=_mock_model([[0.0, 5.0, 0.0], [0.0, -5.0, 5.0]])), \
         patch.object(gs, "_split_into_sentences", return_value=["Sentence A.", "Sentence B."]):
        report = gs.check_groundedness("Sentence A. Sentence B.", ["Some context chunk."])

    assert report.supported_ratio == 0.5
    assert report.grounded is False  # below default 0.6 ratio threshold
    assert report.sentence_scores[0].support_score > report.sentence_scores[1].support_score


def test_picks_best_matching_chunk_among_several():
    # 1 sentence, 2 chunks: second chunk entails it much better.
    with patch.object(gs, "get_nli_model", return_value=_mock_model([[0.0, -5.0, 0.0], [0.0, 5.0, 0.0]])), \
         patch.object(gs, "_split_into_sentences", return_value=["The dataset had 10000 samples."]):
        report = gs.check_groundedness("The dataset had 10000 samples.", ["Irrelevant chunk.", "The dataset contains 10000 labeled samples."])

    assert report.sentence_scores[0].best_chunk_index == 1


def test_empty_answer_returns_ungrounded():
    report = gs.check_groundedness("", ["some context"])
    assert report.grounded is False
    assert report.sentence_scores == []


def test_empty_context_returns_ungrounded():
    report = gs.check_groundedness("An answer.", [])
    assert report.grounded is False
