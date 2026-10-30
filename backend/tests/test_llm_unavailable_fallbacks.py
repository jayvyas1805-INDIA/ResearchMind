from unittest.mock import patch

from app.models.paper import Paper
from app.services import comparison_service, summary_service
from app.services.llm_service import LLMError


def _paper(paper_id, title, abstract, dataset):
    return Paper(
        id=paper_id,
        filename=f"{paper_id}.pdf",
        stored_path=f"{paper_id}.pdf",
        title=title,
        page_count=1,
        abstract=abstract,
        methodology="We use a retrieval-augmented generation approach.",
        entities_json=f'{{"datasets": ["{dataset}"], "models": [], "metrics": [], "methods": []}}',
    )


def test_summary_generates_local_extractive_fields_if_llm_quota_is_unavailable(db_session):
    paper = _paper(
        "paper-A",
        "Paper A",
        "We evaluate the proposed system on the HumanEval benchmark dataset. "
        "The system improves exact match accuracy.",
        "HumanEval",
    )
    db_session.add(paper)
    db_session.commit()

    with patch("app.services.summary_service.llm_service.generate", side_effect=LLMError("quota exceeded")):
        summary = summary_service.generate_summary(paper, db_session)

    assert summary["generation_mode"] == "extractive"
    assert "HumanEval" in summary["dataset"]
    assert "approach" in summary["methodology"]


def test_compare_returns_extracted_comparison_if_llm_quota_is_unavailable():
    paper_a = _paper("paper-A", "Paper A", "Paper A abstract.", "HumanEval")
    paper_b = _paper("paper-B", "Paper B", "Paper B abstract.", "SWE-bench")

    with patch("app.services.comparison_service.llm_service.generate", side_effect=LLMError("quota exceeded")):
        comparison = comparison_service.compare_papers(paper_a, paper_b)

    assert comparison["generation_mode"] == "extractive"
    assert "HumanEval" in comparison["dataset_comparison"]
    assert "SWE-bench" in comparison["dataset_comparison"]
    assert comparison["methodology_comparison"] != comparison_service.NOT_AVAILABLE
