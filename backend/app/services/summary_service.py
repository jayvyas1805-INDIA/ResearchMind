"""
Summary service — generates a structured, grounded research summary.

Reuses existing Phase 3 extracted sections/entities as the primary context
(no full-PDF resend to the LLM). Falls back to a retrieval query only if
section extraction produced nothing usable.
"""
import json
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.services import llm_service, retrieval_service

SUMMARY_FIELDS = [
    "research_problem", "objective", "methodology", "models_algorithms",
    "dataset", "evaluation_metrics", "key_results", "limitations", "future_work",
]

NOT_AVAILABLE = "Not available in the paper."

SYSTEM_PROMPT = (
    "You are a research assistant producing a structured summary of an academic paper. "
    "Use ONLY the provided context. If a field cannot be determined from the context, "
    f'respond with exactly: "{NOT_AVAILABLE}" for that field. '
    "Do not invent information. Respond ONLY with valid JSON, no markdown fences, no preamble."
)


def _build_context(paper: Paper, db: Session) -> str:
    parts = []
    for label, text in [
        ("Abstract", paper.abstract),
        ("Methodology", paper.methodology),
        ("Results", paper.results_section),
        ("Limitations", paper.limitations),
        ("Conclusion", paper.conclusion),
    ]:
        if text:
            parts.append(f"[{label}]\n{text[:1500]}")

    if paper.entities_json:
        try:
            entities = json.loads(paper.entities_json)
            ent_lines = [
                f"{key.capitalize()}: {', '.join(entities[key][:15])}"
                for key in ("models", "datasets", "metrics", "methods")
                if entities.get(key)
            ]
            if ent_lines:
                parts.append("[Extracted Entities]\n" + "\n".join(ent_lines))
        except (json.JSONDecodeError, TypeError):
            pass

    if not parts:
        results = retrieval_service.search(
            query="research problem, objective, methodology, results, limitations, future work",
            db=db, paper_id=paper.id, top_k=8,
        )
        parts = [f"[page {r.page_number}]\n{r.chunk_text}" for r in results]

    return "\n\n".join(parts)


def generate_summary(paper: Paper, db: Session) -> dict:
    context = _build_context(paper, db)
    if not context.strip():
        return {field: NOT_AVAILABLE for field in SUMMARY_FIELDS}

    prompt = (
        f"Paper context:\n\n{context}\n\n"
        f"Produce a JSON object with exactly these keys: {', '.join(SUMMARY_FIELDS)}.\n"
        "Each value should be a concise 1-3 sentence string. "
        f'If information for a key is not present in the context, use exactly: "{NOT_AVAILABLE}"'
    )
    raw = llm_service.generate(prompt, system=SYSTEM_PROMPT)

    cleaned = raw.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {**{f: NOT_AVAILABLE for f in SUMMARY_FIELDS}, "research_problem": cleaned[:800]}

    return {field: data.get(field, NOT_AVAILABLE) for field in SUMMARY_FIELDS}
