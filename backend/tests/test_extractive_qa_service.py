import numpy as np

from app.models.chunk import Chunk
from app.services import extractive_qa_service


def _chunk(chunk_id, text, section="methodology"):
    return Chunk(
        id=chunk_id,
        paper_id="paper-A",
        chunk_index=chunk_id,
        page_number=chunk_id,
        section=section,
        text=text,
    )


def test_rank_sentences_prefers_sentences_about_the_requested_dataset():
    sentences = [
        "The proposed method combines retrieval with code generation.",
        "We evaluated the approach on the HumanEval benchmark dataset.",
        "The paper concludes with several directions for future work.",
    ]

    matches = extractive_qa_service.rank_sentences("Which dataset was used?", sentences, limit=1)

    assert matches == ["We evaluated the approach on the HumanEval benchmark dataset."]


def test_find_answers_returns_source_chunk_for_matching_passage(monkeypatch):
    chunks = [
        _chunk(1, "The proposed architecture has three retrieval stages."),
        _chunk(2, "We evaluated the model on the HumanEval benchmark dataset."),
    ]
    monkeypatch.setattr(
        extractive_qa_service.embedding_service,
        "embed_texts",
        lambda texts: np.array([[1.0, 0.0] if "HumanEval" in text else [0.0, 1.0] for text in texts]),
    )
    monkeypatch.setattr(
        extractive_qa_service.embedding_service,
        "embed_query",
        lambda _query: np.array([1.0, 0.0]),
    )

    matches = extractive_qa_service.find_answers("Which dataset was used?", chunks)

    assert matches
    assert matches[0].chunk.id == 2
    assert "HumanEval" in matches[0].sentence


def test_find_answers_returns_empty_when_no_question_terms_match(monkeypatch):
    chunks = [_chunk(1, "The proposed architecture has three retrieval stages.")]
    monkeypatch.setattr(
        extractive_qa_service.embedding_service,
        "embed_texts",
        lambda texts: np.zeros((len(texts), 2)),
    )
    monkeypatch.setattr(
        extractive_qa_service.embedding_service,
        "embed_query",
        lambda _query: np.ones(2),
    )

    assert extractive_qa_service.find_answers("What is the author affiliation?", chunks) == []


def test_find_answers_preserves_explicit_research_questions(monkeypatch):
    chunks = [
        _chunk(
            1,
            "RQ1: How does the system retrieve code? This question examines retrieval methods. "
            "RQ2: Which benchmarks are used?",
        )
    ]
    monkeypatch.setattr(
        extractive_qa_service.embedding_service,
        "embed_texts",
        lambda texts: np.zeros((len(texts), 2)),
    )
    monkeypatch.setattr(
        extractive_qa_service.embedding_service,
        "embed_query",
        lambda _query: np.zeros(2),
    )

    matches = extractive_qa_service.find_answers("What are the research questions?", chunks)

    assert matches
    assert any("RQ1" in match.sentence for match in matches)
