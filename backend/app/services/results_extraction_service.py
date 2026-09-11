"""
Results extraction service.

Lightweight, explainable relation extraction: for each sentence in a
paper's text, find (metric, numeric value) pairs where a metric term
(Accuracy, F1, BLEU, ...) sits near a number, then attach any model/
dataset names that co-occur in the SAME sentence. This turns prose like
"our LSTM achieved 90% accuracy on the emotion dataset" into a structured
(model=LSTM, dataset=emotion dataset, metric=Accuracy, value=90.0) claim —
the raw material a cross-paper leaderboard is built from.

Deliberately pattern-based rather than another LLM call: it's cheap,
deterministic, auditable (every claim keeps its source sentence + page for
verification), and doesn't require sending paper text to an external API
just to pull out numbers next to words.
"""
import re
from dataclasses import dataclass
from typing import Optional

from app.services.nlp_service import get_nlp
from app.utils.research_terms import DATASETS, METRICS, MODELS

# Matches a percentage ("90%", "90.5 %") or a bare decimal in [0, 1]
# ("0.90") commonly used for accuracy/F1/etc.
_NUMBER_RE = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s?%|\b(0\.\d+|1\.0+)\b")

# How close (in characters) a metric term and a number must be within the
# same sentence to be considered related — keeps false positives down
# without needing full dependency parsing.
_PROXIMITY_WINDOW = 40

_MAX_MODEL_MATCHES_PER_SENTENCE = 3
_MAX_DATASET_MATCHES_PER_SENTENCE = 3


@dataclass
class ResultClaimData:
    model_name: Optional[str]
    dataset_name: Optional[str]
    metric_name: str
    value_text: str
    value: Optional[float]
    sentence: str


def _find_term_spans(text: str, terms: list[str]) -> list[tuple[int, int, str]]:
    spans = []
    occupied = [False] * len(text)
    for term in sorted(terms, key=len, reverse=True):
        for m in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text, re.IGNORECASE):
            start, end = m.start(), m.end()
            if any(occupied[start:end]):
                continue
            spans.append((start, end, term))
            for i in range(start, end):
                occupied[i] = True
    return spans


def _parse_numeric_value(match: re.Match) -> tuple[str, Optional[float]]:
    """Returns (raw matched text, normalized value on a 0-100 scale)."""
    raw = match.group(0).strip()
    if match.group(1) is not None:  # percentage form, e.g. "90" from "90%"
        try:
            return raw, float(match.group(1))
        except ValueError:
            return raw, None
    if match.group(2) is not None:  # decimal form, e.g. "0.90" -> 90.0
        try:
            return raw, float(match.group(2)) * 100
        except ValueError:
            return raw, None
    return raw, None


def _extract_from_sentence(sentence: str) -> list[ResultClaimData]:
    metric_spans = _find_term_spans(sentence, METRICS)
    if not metric_spans:
        return []

    number_matches = list(_NUMBER_RE.finditer(sentence))
    if not number_matches:
        return []

    model_spans = _find_term_spans(sentence, MODELS)[:_MAX_MODEL_MATCHES_PER_SENTENCE]
    dataset_spans = _find_term_spans(sentence, DATASETS)[:_MAX_DATASET_MATCHES_PER_SENTENCE]
    model_names = [span[2] for span in model_spans] or [None]
    dataset_names = [span[2] for span in dataset_spans] or [None]

    claims = []
    seen_metric_number_pairs = set()

    for metric_start, metric_end, metric_term in metric_spans:
        # Find the closest number to this specific metric mention.
        closest_number = None
        closest_distance = None
        for num_match in number_matches:
            distance = min(
                abs(num_match.start() - metric_end),
                abs(metric_start - num_match.end()),
            )
            if distance <= _PROXIMITY_WINDOW and (closest_distance is None or distance < closest_distance):
                closest_number = num_match
                closest_distance = distance

        if closest_number is None:
            continue

        pair_key = (metric_term, closest_number.start())
        if pair_key in seen_metric_number_pairs:
            continue
        seen_metric_number_pairs.add(pair_key)

        value_text, value = _parse_numeric_value(closest_number)

        # One claim row per (model, dataset) combination mentioned in the
        # sentence, capped by the limits above to avoid a combinatorial blowup.
        for model_name in model_names:
            for dataset_name in dataset_names:
                claims.append(
                    ResultClaimData(
                        model_name=model_name,
                        dataset_name=dataset_name,
                        metric_name=metric_term,
                        value_text=value_text,
                        value=value,
                        sentence=sentence.strip(),
                    )
                )

    return claims


def extract_result_claims(text: str, max_chars: int = 50_000) -> list[ResultClaimData]:
    """
    Scans `text` sentence-by-sentence for numeric result claims. Intended
    to be called on a paper's Results/Experiments section text (smaller,
    higher-precision), falling back to the full text if no such section
    was detected.
    """
    if not text or not text.strip():
        return []

    nlp = get_nlp()
    doc = nlp(text[:max_chars])

    all_claims: list[ResultClaimData] = []
    for sent in doc.sents:
        sentence_text = sent.text.strip()
        if not sentence_text:
            continue
        all_claims.extend(_extract_from_sentence(sentence_text))

    return all_claims
