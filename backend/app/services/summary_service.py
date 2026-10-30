"""
Summary service — generates a structured, grounded research summary.

Reuses existing Phase 3 extracted sections/entities as the primary context
(no full-PDF resend to the LLM). Falls back to a retrieval query only if
section extraction produced nothing usable.
"""
import json
import logging
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.paper import Paper
from app.services import extractive_qa_service, llm_service, retrieval_service

logger = logging.getLogger("papermind.summary")

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
        return {**{field: NOT_AVAILABLE for field in SUMMARY_FIELDS}, "generation_mode": "extractive"}

    prompt = (
        f"Paper context:\n\n{context}\n\n"
        f"Produce a JSON object with exactly these keys: {', '.join(SUMMARY_FIELDS)}.\n"
        "Each value should be a concise 1-3 sentence string. "
        f'If information for a key is not present in the context, use exactly: "{NOT_AVAILABLE}"'
    )
    try:
        raw = llm_service.generate(prompt, system=SYSTEM_PROMPT)
    except llm_service.LLMError as exc:
        logger.warning(
            "LLM unavailable for paper %s; building an extractive summary: %s",
            paper.id,
            exc,
        )
        return _generate_extractive_summary(paper, db)

    cleaned = raw.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {**{f: NOT_AVAILABLE for f in SUMMARY_FIELDS}, "research_problem": cleaned[:800]}

    return {**{field: data.get(field, NOT_AVAILABLE) for field in SUMMARY_FIELDS}, "generation_mode": "llm"}


def _generate_extractive_summary(paper: Paper, db: Session) -> dict:
    chunks = (
        db.query(Chunk)
        .filter(Chunk.paper_id == paper.id, Chunk.section != "references")
        .order_by(Chunk.id)
        .all()
    )
    section_text = {
        "abstract": paper.abstract or "",
        "introduction": "",
        "methodology": paper.methodology or "",
        "results": paper.results_section or "",
        "limitations": paper.limitations or "",
        "conclusion": paper.conclusion or "",
    }
    if paper.sections_json:
        try:
            sections = json.loads(paper.sections_json)
            for name in ("introduction", "conclusion", "limitations"):
                section_text[name] = section_text[name] or sections.get(name, "")
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse sections_json for paper %s", paper.id)

    entities = {}
    if paper.entities_json:
        try:
            entities = json.loads(paper.entities_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse entities_json for paper %s", paper.id)

    field_sources = {
        "research_problem": [section_text["abstract"], section_text["introduction"]],
        "objective": [section_text["abstract"], section_text["introduction"]],
        "methodology": [section_text["methodology"]],
        "models_algorithms": [],
        "dataset": [],
        "evaluation_metrics": [],
        "key_results": [section_text["results"], section_text["abstract"]],
        "limitations": [section_text["limitations"]],
        "future_work": [section_text["conclusion"]],
    }
    field_queries = {
        "research_problem": "research problem challenge addressed motivation",
        "objective": "objective aim purpose research question",
        "methodology": "method methodology approach framework procedure",
        "models_algorithms": "model algorithm system architecture",
        "dataset": "dataset data corpus benchmark evaluation set",
        "evaluation_metrics": "evaluation metric accuracy precision recall score",
        "key_results": "results findings achieved performance improved",
        "limitations": "limitations weakness challenge threat",
        "future_work": "future work further research next steps",
    }

    entity_values = {
        "models_algorithms": entities.get("models", []) + entities.get("methods", []),
        "dataset": entities.get("datasets", []),
        "evaluation_metrics": entities.get("metrics", []),
    }
    summary = {}
    for field in SUMMARY_FIELDS:
        values = entity_values.get(field, [])
        if values:
            summary[field] = ", ".join(values[:12])
            continue

        source_texts = [text for text in field_sources[field] if text]
        if not source_texts:
            source_texts = [chunk.text for chunk in chunks]
        sentences = extractive_qa_service.rank_sentences(field_queries[field], source_texts, limit=2)
        summary[field] = " ".join(sentences) if sentences else NOT_AVAILABLE

    summary["generation_mode"] = "extractive"
    return summary
