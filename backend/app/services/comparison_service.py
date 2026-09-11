"""
Comparison service — compares two papers.

Per-paper facts (methodology, dataset, models, metrics, results, limitations)
come directly from Phase 3's NLP extraction — no LLM needed for those.
The LLM is used only for the deeper semantic comparison narrative
(similarities, differences, per-aspect comparisons), grounded in that same
extracted data (not the full PDFs).
"""
import json

from app.models.paper import Paper
from app.services import llm_service

COMPARISON_FIELDS = [
    "similarities", "differences", "methodology_comparison",
    "dataset_comparison", "model_comparison", "result_comparison",
]
NOT_AVAILABLE = "Not available in the paper."

SYSTEM_PROMPT = (
    "You are a research assistant comparing two academic papers. "
    "Use ONLY the provided context about each paper. "
    f'If a comparison cannot be made from the context, respond with exactly: "{NOT_AVAILABLE}" for that field. '
    "Do not invent information. Respond ONLY with valid JSON, no markdown fences, no preamble."
)


def _entities(paper: Paper, key: str) -> list[str]:
    if not paper.entities_json:
        return []
    try:
        return json.loads(paper.entities_json).get(key, [])
    except (json.JSONDecodeError, TypeError):
        return []


def paper_brief(paper: Paper) -> dict:
    """Facts pulled directly from Phase 3 extraction — no LLM call."""
    return {
        "id": paper.id,
        "title": paper.title or paper.filename,
        "methodology": paper.methodology or NOT_AVAILABLE,
        "dataset": ", ".join(_entities(paper, "datasets")) or NOT_AVAILABLE,
        "models": ", ".join(_entities(paper, "models")) or NOT_AVAILABLE,
        "metrics": ", ".join(_entities(paper, "metrics")) or NOT_AVAILABLE,
        "results": paper.results_section or NOT_AVAILABLE,
        "limitations": paper.limitations or NOT_AVAILABLE,
    }


def _paper_context(paper: Paper, label: str) -> str:
    brief = paper_brief(paper)
    return (
        f"[{label}: {brief['title']}]\n"
        f"Abstract: {(paper.abstract or NOT_AVAILABLE)[:800]}\n"
        f"Methodology: {brief['methodology'][:800]}\n"
        f"Dataset(s): {brief['dataset']}\n"
        f"Model(s)/Algorithm(s): {brief['models']}\n"
        f"Metric(s): {brief['metrics']}\n"
        f"Results: {brief['results'][:800]}\n"
        f"Limitations: {brief['limitations'][:500]}"
    )


def compare_papers(paper1: Paper, paper2: Paper) -> dict:
    context = _paper_context(paper1, "Paper A") + "\n\n" + _paper_context(paper2, "Paper B")

    prompt = (
        f"{context}\n\n"
        f"Produce a JSON object with exactly these keys: {', '.join(COMPARISON_FIELDS)}.\n"
        "Each value should be a concise 2-4 sentence comparison string referring to Paper A and Paper B. "
        f'If a comparison cannot be made from the context, use exactly: "{NOT_AVAILABLE}"'
    )
    raw = llm_service.generate(prompt, system=SYSTEM_PROMPT)

    cleaned = raw.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}

    comparison = {field: data.get(field, NOT_AVAILABLE) for field in COMPARISON_FIELDS}

    return {
        "paper1": paper_brief(paper1),
        "paper2": paper_brief(paper2),
        **comparison,
    }
