import numpy as np

from app.models.chunk import Chunk
from app.models.paper import Paper, ProcessingStatus
from app.services import extractive_qa_service, retrieval_service


def test_search_response_includes_a_query_focused_excerpt(db_session, monkeypatch):
    paper = Paper(
        id="paper-A",
        filename="paper.pdf",
        stored_path="paper.pdf",
        page_count=1,
        processing_status=ProcessingStatus.PROCESSED,
    )
    chunk = Chunk(
        id=1,
        paper_id="paper-A",
        chunk_index=0,
        page_number=2,
        section="results",
        text=(
            "The proposed system uses several retrieval stages. "
            "We evaluated the approach on the HumanEval benchmark dataset."
        ),
    )
    db_session.add_all([paper, chunk])
    db_session.commit()
    monkeypatch.setattr(
        retrieval_service,
        "hybrid_search",
        lambda **_kwargs: [
            retrieval_service.SearchResult(
                chunk_id=1,
                paper_id="paper-A",
                chunk_text=chunk.text,
                page_number=2,
                section="results",
                similarity_score=0.01,
            )
        ],
    )
    monkeypatch.setattr(
        extractive_qa_service.embedding_service,
        "embed_texts",
        lambda texts: np.array(
            [[1.0, 0.0] if "HumanEval" in text else [0.0, 1.0] for text in texts]
        ),
    )
    monkeypatch.setattr(
        extractive_qa_service.embedding_service,
        "embed_query",
        lambda _query: np.array([1.0, 0.0]),
    )

    from app.api.search import _run_search

    response = _run_search("paper-A", "Which dataset was used?", 5, True, db_session)

    assert response.result_count == 1
    assert "HumanEval" in response.results[0].excerpt
    assert response.results[0].text == chunk.text
