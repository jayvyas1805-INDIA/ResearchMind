"""
Tests that the RAG pipeline returns a well-formed, schema-valid response
and correctly refuses to call the LLM when there's no relevant context —
LLM and retrieval are mocked so this doesn't need Ollama running.
"""
from unittest.mock import patch

import numpy as np

from app.schemas.chat import ChatResponse
from app.services import rag_service
from app.services.retrieval_service import SearchResult


def _fake_result():
    return SearchResult(
        chunk_id=1, paper_id="paper-A", chunk_text="The model achieved 90% accuracy.",
        page_number=5, section="results", similarity_score=0.85,
    )


def test_answer_question_returns_grounded_answer_with_sources(db_session):
    with patch("app.services.rag_service.retrieval_service.hybrid_search", return_value=[_fake_result()]), \
         patch("app.services.rag_service.llm_service.generate", return_value="The model achieved 90% accuracy."), \
         patch("app.services.rag_service.groundedness_service.check_groundedness", return_value=None):
        result = rag_service.answer_question("paper-A", "What was the accuracy?", db_session)

    assert result.grounded is True
    assert "90%" in result.answer
    assert len(result.sources) == 1
    assert result.sources[0].chunk_id == 1

    # Confirm the API response schema accepts this shape end-to-end.
    response = ChatResponse(
        paper_id="paper-A", question="What was the accuracy?", answer=result.answer,
        grounded=result.grounded,
        sources=[{
            "chunk_id": s.chunk_id, "page_number": s.page_number,
            "section": s.section, "text": s.chunk_text, "similarity_score": s.similarity_score,
        } for s in result.sources],
    )
    assert response.sources[0].chunk_id == 1


def test_answer_question_skips_llm_when_no_context_found(db_session):
    with patch("app.services.rag_service.retrieval_service.hybrid_search", return_value=[]) as mock_search, \
         patch("app.services.rag_service.llm_service.generate") as mock_generate:
        result = rag_service.answer_question("paper-A", "irrelevant question", db_session)

    assert result.grounded is False
    assert result.sources == []
    assert "couldn't find" in result.answer.lower()
    mock_generate.assert_not_called()  # never call the LLM with empty context


def test_answer_question_attaches_groundedness_report(db_session):
    from app.services import groundedness_service

    fake_report = groundedness_service.GroundednessReport(grounded=True, supported_ratio=1.0, sentence_scores=[])
    with patch("app.services.rag_service.retrieval_service.hybrid_search", return_value=[_fake_result()]), \
         patch("app.services.rag_service.llm_service.generate", return_value="Answer text."), \
         patch("app.services.rag_service.groundedness_service.check_groundedness", return_value=fake_report):
        result = rag_service.answer_question("paper-A", "question", db_session)

    assert result.groundedness is fake_report


def test_answer_question_survives_groundedness_check_failure(db_session):
    with patch("app.services.rag_service.retrieval_service.hybrid_search", return_value=[_fake_result()]), \
         patch("app.services.rag_service.llm_service.generate", return_value="Answer text."), \
         patch("app.services.rag_service.groundedness_service.check_groundedness", side_effect=RuntimeError("model not downloaded")):
        result = rag_service.answer_question("paper-A", "question", db_session)

    assert result.answer == "Answer text."  # chat still works even if groundedness check crashes
    assert result.groundedness is None


def test_answer_question_falls_back_to_relevant_extracted_passages(db_session):
    from app.models.chunk import Chunk
    from app.services.llm_service import LLMError

    db_session.add(
        Chunk(
            id=10,
            paper_id="paper-A",
            chunk_index=0,
            page_number=3,
            section="results",
            text="We evaluated the approach on the HumanEval benchmark dataset.",
        )
    )
    db_session.commit()

    with patch("app.services.rag_service.retrieval_service.hybrid_search", return_value=[_fake_result()]), \
         patch("app.services.rag_service.llm_service.generate", side_effect=LLMError("Mistral quota exceeded")), \
         patch("app.services.rag_service.extractive_qa_service.embedding_service.embed_texts", return_value=np.array([[1.0, 0.0]])), \
         patch("app.services.rag_service.extractive_qa_service.embedding_service.embed_query", return_value=np.array([1.0, 0.0])):
        result = rag_service.answer_question("paper-A", "Which dataset was used?", db_session)

    assert result.answer_mode == "extractive"
    assert "HumanEval" in result.answer
    assert result.sources[0].chunk_id == 10
