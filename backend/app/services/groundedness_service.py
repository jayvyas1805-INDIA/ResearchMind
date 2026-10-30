"""
Groundedness / hallucination checker.

Even with a prompt that says "answer only from context", an LLM can still
add plausible-sounding details that aren't actually in the retrieved text.
This module catches that by checking, sentence-by-sentence, whether the
answer is actually *entailed* by the retrieved context — not just whether
it was generated with that context in the prompt.

Uses a cross-encoder NLI (Natural Language Inference) model: for each
answer sentence, we test it against every retrieved chunk and take the
strongest entailment score. A sentence with no chunk entailing it above
the threshold is flagged as unsupported.
"""
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from sentence_transformers import CrossEncoder

from app.core.config import get_settings
from app.services.nlp_service import get_nlp

settings = get_settings()

# NOTE: cross-encoder/nli-deberta-v3-* models are trained on SNLI/MultiNLI
# with label order [contradiction, entailment, neutral] per the model's
# Hugging Face card. If you swap in a different NLI model, verify its label
# order before trusting _ENTAILMENT_INDEX.
_ENTAILMENT_INDEX = 1


@lru_cache
def get_nli_model() -> CrossEncoder:
    return CrossEncoder(settings.NLI_MODEL)


def _split_into_sentences(text: str) -> list[str]:
    nlp = get_nlp()
    doc = nlp(text)
    return [s.text.strip() for s in doc.sents if s.text.strip()]


def _softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - np.max(logits))
    return exp / exp.sum()


@dataclass
class SentenceGrounding:
    sentence: str
    support_score: float   # entailment probability against the best-matching chunk
    best_chunk_index: int  # index into the context_chunks list passed to check_groundedness


@dataclass
class GroundednessReport:
    grounded: bool
    supported_ratio: float
    sentence_scores: list[SentenceGrounding] = field(default_factory=list)


def check_groundedness(answer: str, context_chunks: list[str]) -> GroundednessReport:
    """
    For each sentence in `answer`, find the context chunk that best entails
    it, and report whether enough of the answer is supported.

    context_chunks order matters — the caller should pass them in the same
    order used to build the LLM's context, so best_chunk_index can be
    mapped back to a specific source for citation purposes.
    """
    if not answer or not answer.strip() or not context_chunks:
        return GroundednessReport(grounded=False, supported_ratio=0.0, sentence_scores=[])

    sentences = _split_into_sentences(answer)
    if not sentences:
        return GroundednessReport(grounded=False, supported_ratio=0.0, sentence_scores=[])

    model = get_nli_model()

    # premise=chunk, hypothesis=sentence: "does this chunk entail this sentence?"
    pairs = [(chunk, sentence) for sentence in sentences for chunk in context_chunks]
    raw_scores = np.asarray(model.predict(pairs))

    if raw_scores.ndim == 1:
        # A binary entailment-only cross-encoder — treat the raw score
        # directly as an entailment probability.
        entailment_probs = raw_scores
    else:
        entailment_probs = np.array([_softmax(row)[_ENTAILMENT_INDEX] for row in raw_scores])

    n_chunks = len(context_chunks)
    sentence_scores: list[SentenceGrounding] = []
    supported_count = 0

    for i, sentence in enumerate(sentences):
        start = i * n_chunks
        scores_for_sentence = entailment_probs[start:start + n_chunks]
        best_idx = int(np.argmax(scores_for_sentence))
        best_score = float(scores_for_sentence[best_idx])

        sentence_scores.append(
            SentenceGrounding(sentence=sentence, support_score=best_score, best_chunk_index=best_idx)
        )
        if best_score >= settings.GROUNDEDNESS_SUPPORT_THRESHOLD:
            supported_count += 1

    supported_ratio = supported_count / len(sentences)
    grounded = supported_ratio >= settings.GROUNDEDNESS_SENTENCE_RATIO_THRESHOLD

    return GroundednessReport(grounded=grounded, supported_ratio=supported_ratio, sentence_scores=sentence_scores)
