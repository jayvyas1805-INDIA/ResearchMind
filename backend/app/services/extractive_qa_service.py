"""Local, extractive answers when a hosted language model is unavailable."""

import re
from dataclasses import dataclass
from math import log

from app.models.chunk import Chunk
from app.services import embedding_service

_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "did", "do", "does",
    "for", "from", "how", "i", "in", "into", "is", "it", "of", "on", "or", "that",
    "main", "paper", "numerical", "number", "the", "their", "this", "to", "was", "were", "what", "when",
    "where", "which", "who", "why", "with", "would", "used", "use",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_RESEARCH_QUESTION_RE = re.compile(
    r"\b(RQ\s*[1-9])\s*[:.]?\s*(.*?)(?=\bRQ\s*[1-9]\b|$)",
    re.IGNORECASE | re.DOTALL,
)
_INTENT_TERMS = {
    "dataset": {"data", "dataset", "datasets", "corpus", "benchmark", "benchmarks", "testset"},
    "method": {"method", "methods", "methodology", "approach", "framework", "proposed"},
    "model": {"model", "models", "algorithm", "algorithms", "system"},
    "result": {
        "result", "results", "finding", "findings", "achieved", "performance", "improved",
        "accuracy", "precision", "recall", "f1", "percentage",
    },
    "metric": {"metric", "metrics", "accuracy", "precision", "recall", "f1", "score"},
    "limitation": {"limitation", "limitations", "challenge", "challenges", "weakness"},
}
_PLURAL_FORMS = {
    "benchmarks": "benchmark",
    "datasets": "dataset",
    "findings": "finding",
    "limitations": "limitation",
    "metrics": "metric",
    "models": "model",
    "questions": "question",
    "results": "result",
}


@dataclass
class ExtractiveMatch:
    sentence: str
    chunk: Chunk
    score: float


def _tokens(text: str) -> set[str]:
    return {
        _PLURAL_FORMS.get(token, token) for token in _TOKEN_RE.findall(text.lower())
        if token not in _STOP_WORDS and len(token) > 1
    }


def _query_terms(query: str) -> set[str]:
    terms = _tokens(query)
    if "research" in terms and "question" in terms:
        terms.update({"rq1", "rq2", "rq3"})
    for intent, related_terms in _INTENT_TERMS.items():
        if intent in terms or intent + "s" in terms or (intent == "method" and "methodology" in terms):
            terms.update(related_terms)
    return terms


def rank_sentences(query: str, texts: list[str], limit: int = 3) -> list[str]:
    """Return the most query-relevant sentences, preserving their source wording."""
    query_terms = _query_terms(query)
    sentences = [
        sentence.strip()
        for text in texts
        for sentence in _SENTENCE_SPLIT_RE.split(text)
        if len(sentence.split()) >= 5
    ]
    if not query_terms or not sentences:
        return []

    tokenized = [_tokens(sentence) for sentence in sentences]
    document_frequency = {
        term: sum(term in sentence_tokens for sentence_tokens in tokenized)
        for term in query_terms
    }

    scored = []
    for index, sentence_tokens in enumerate(tokenized):
        score = sum(
            log(1 + (len(tokenized) - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
            if term in sentence_tokens
        )
        if score > 0:
            scored.append((score, index))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [sentences[index] for _, index in scored[:limit]]


def find_answers(query: str, chunks: list[Chunk], limit: int = 3) -> list[ExtractiveMatch]:
    """Rank paper sentences lexically and semantically, retaining source chunks."""
    query_terms = _query_terms(query)
    candidates = []
    for chunk in chunks:
        sentences = _SENTENCE_SPLIT_RE.split(chunk.text)
        if "research" in _tokens(query) and "question" in _tokens(query):
            sentences.extend(
                f"{match.group(1)}: {match.group(2).strip()[:700]}"
                for match in _RESEARCH_QUESTION_RE.finditer(chunk.text)
            )
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence.split()) < 5:
                continue
            matches = query_terms & _tokens(sentence)
            if matches:
                candidates.append((sentence, chunk, matches))

    if not candidates or not query_terms:
        return []

    document_frequency = {
        term: sum(term in candidate[2] for candidate in candidates)
        for term in query_terms
    }
    lexical_scores = []
    for index, (sentence, chunk, matches) in enumerate(candidates):
        score = sum(
            log(1 + (len(candidates) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5))
            for term in matches
        )
        lexical_scores.append(score)

    lexical_candidates = sorted(
        zip(candidates, lexical_scores),
        key=lambda item: item[1],
        reverse=True,
    )[:120]
    candidates = [candidate for candidate, _ in lexical_candidates]
    lexical_scores = [score for _, score in lexical_candidates]

    sentence_vectors = embedding_service.embed_texts([sentence for sentence, _, _ in candidates])
    semantic_query = " ".join(sorted(_tokens(query)))
    semantic_scores = sentence_vectors @ embedding_service.embed_query(semantic_query)
    max_lexical_score = max(lexical_scores, default=0.0)
    asks_research_questions = {"research", "question"} <= _tokens(query)

    ranked = []
    for (sentence, chunk, matches), lexical_score, semantic_score in zip(
        candidates, lexical_scores, semantic_scores
    ):
        is_explicit_research_question = (
            asks_research_questions
            and re.search(r"\bRQ\s*[1-9]\b", sentence, re.IGNORECASE) is not None
        )
        if semantic_score < 0.35 and not is_explicit_research_question:
            continue
        lexical_score = lexical_score / max_lexical_score if max_lexical_score else 0.0
        if is_explicit_research_question:
            semantic_score = max(semantic_score, 0.85)
        combined_score = 0.65 * float(semantic_score) + 0.35 * lexical_score
        if matches and semantic_score >= 0.35:
            ranked.append(ExtractiveMatch(sentence, chunk, combined_score))

    ranked.sort(key=lambda item: (-item.score, item.chunk.id))
    selected = []
    seen_sentences = set()
    seen_chunks = set()
    for match in ranked:
        normalized = " ".join(match.sentence.lower().split())
        if normalized in seen_sentences or match.chunk.id in seen_chunks:
            continue
        selected.append(match)
        seen_sentences.add(normalized)
        seen_chunks.add(match.chunk.id)
        if len(selected) >= limit:
            break
    return selected
