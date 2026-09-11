"""
Tests for the pure-logic pieces of the NER fine-tuning pipeline:
weak-span extraction and the precision/recall/F1 scoring math. Does not
train or load any model — those need spaCy's full training stack and
real data, run manually per training/README.md.
"""
from training.generate_weak_labels import _find_weak_spans
from training.evaluate_ner import prf, score_system


def test_find_weak_spans_matches_known_terms():
    text = "We fine-tuned BERT on the SQuAD dataset and measured F1 score."
    spans = _find_weak_spans(text)
    labels_found = {label for _, _, label in spans}
    assert "MODEL" in labels_found
    assert "DATASET" in labels_found
    assert "METRIC" in labels_found


def test_find_weak_spans_prefers_longer_match():
    text = "We used a Bidirectional GRU for this task."
    spans = _find_weak_spans(text)
    matched_texts = [text[s:e] for s, e, _ in spans]
    assert "Bidirectional GRU" in matched_texts
    assert "GRU" not in matched_texts  # shouldn't double-match the substring


def test_find_weak_spans_no_matches_on_unrelated_text():
    spans = _find_weak_spans("The weather was nice yesterday.")
    assert spans == []


def test_prf_perfect_score():
    assert prf(tp=10, fp=0, fn=0) == (1.0, 1.0, 1.0)


def test_prf_no_predictions():
    p, r, f1 = prf(tp=0, fp=0, fn=5)
    assert p == 0.0
    assert r == 0.0
    assert f1 == 0.0


def test_prf_partial_overlap():
    p, r, f1 = prf(tp=3, fp=1, fn=2)
    assert abs(p - 0.75) < 1e-9
    assert abs(r - 0.6) < 1e-9


def test_score_system_computes_correct_counts(capsys):
    gold = [{"text": "x", "entities": [[0, 4, "MODEL"], [5, 9, "DATASET"]]}]

    def predict_fn(text):
        return [(0, 4, "MODEL")]  # misses the DATASET entity

    result = score_system("test", predict_fn, gold, {"MODEL", "DATASET"})
    assert result["precision"] == 1.0  # the one prediction made was correct
    assert abs(result["recall"] - 0.5) < 1e-9  # only found 1 of 2 gold entities
