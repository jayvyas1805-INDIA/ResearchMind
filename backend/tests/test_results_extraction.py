"""
Tests for results_extraction_service's pattern-based numeric claim
extraction — pure regex/string logic plus spaCy sentence splitting.
"""
import pytest

from app.services import results_extraction_service as res


def _spacy_available():
    try:
        from app.services.nlp_service import get_nlp
        get_nlp()
        return True
    except Exception:
        return False


requires_spacy = pytest.mark.skipif(not _spacy_available(), reason="spaCy model not installed")


def test_parse_percentage_value():
    claims = res._extract_from_sentence("Our LSTM achieved 90% accuracy on the SQuAD dataset.")
    assert len(claims) >= 1
    claim = claims[0]
    assert claim.metric_name.lower() == "accuracy"
    assert claim.value == 90.0
    assert claim.model_name == "LSTM"
    assert claim.dataset_name == "SQuAD"


def test_parse_decimal_value_normalized_to_percentage_scale():
    claims = res._extract_from_sentence("The model obtained an F1 score of 0.88 on the test set.")
    assert len(claims) >= 1
    assert abs(claims[0].value - 88.0) < 1e-9


def test_no_claim_without_metric_term():
    claims = res._extract_from_sentence("The dataset contains 90 samples collected in 2020.")
    assert claims == []


def test_no_claim_without_nearby_number():
    claims = res._extract_from_sentence("Accuracy is an important metric for classification tasks in general.")
    assert claims == []


def test_multiple_models_and_datasets_produce_cross_product():
    claims = res._extract_from_sentence("Both LSTM and GRU achieved 90% accuracy on SQuAD and GLUE.")
    pairs = {(c.model_name, c.dataset_name) for c in claims}
    assert ("LSTM", "SQuAD") in pairs
    assert ("GRU", "GLUE") in pairs


def test_number_far_from_metric_is_not_matched():
    # "accuracy" and "42" are far apart (> proximity window) and unrelated.
    long_filler = "x" * 100
    sentence = f"We discuss accuracy briefly. {long_filler} The year was 42."
    claims = res._extract_from_sentence(sentence)
    assert claims == []


@requires_spacy
def test_extract_result_claims_processes_multiple_sentences():
    text = (
        "We evaluate several models. Our LSTM achieved 90% accuracy on SQuAD. "
        "The weather was nice. GRU reached an F1 of 0.85 on GLUE."
    )
    claims = res.extract_result_claims(text)
    metrics_found = {c.metric_name.lower() for c in claims}
    assert "accuracy" in metrics_found or "f1" in metrics_found or "f1 score" in metrics_found
    assert len(claims) >= 2


def test_extract_result_claims_handles_empty_text():
    assert res.extract_result_claims("") == []
    assert res.extract_result_claims(None) == []
