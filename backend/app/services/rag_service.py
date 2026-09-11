"""
RAG service — retrieves relevant chunks, builds a grounded context, and asks
the configured LLM to answer using ONLY that context, with citations.

Also runs an NLI-based groundedness check on the generated answer (see
groundedness_service) — the system prompt asking the LLM not to hallucinate
is not a guarantee, so we verify it independently.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services import groundedness_service, llm_service, retrieval_service

logger = logging.getLogger("papermind.rag")
settings = get_settings()

SYSTEM_PROMPT = (
    "You are a research assistant answering questions about a specific academic paper. "
    "Answer ONLY using the provided context excerpts from the paper. "
    "If the answer is not present in the context, clearly say the information was not found in the paper. "
    "Do not invent facts, numbers, or citations that are not in the context."
)


@dataclass
class RAGAnswer:
    answer: str
    sources: list  # list of retrieval_service.SearchResult
    grounded: bool  # False if no relevant context was found at all (i.e. LLM was never even called)
    groundedness: Optional[groundedness_service.GroundednessReport] = None  # NLI-based check on the answer itself


def _build_context(results) -> str:
    parts = []
    for i, r in enumerate(results, start=1):
        loc = f"page {r.page_number}" if r.page_number else "unknown page"
        parts.append(f"[Excerpt {i} - {loc}, section: {r.section}]\n{r.chunk_text}")
    return "\n\n".join(parts)


def answer_question(paper_id: str, question: str, db: Session, top_k: Optional[int] = None) -> RAGAnswer:
    results = retrieval_service.search(query=question, db=db, paper_id=paper_id, top_k=top_k)

    if not results:
        return RAGAnswer(
            answer="The information was not found in this paper.",
            sources=[],
            grounded=False,
        )

    context = _build_context(results)
    prompt = (
        f"Context excerpts from the paper:\n\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above. If the answer isn't there, say so explicitly."
    )
    answer_text = llm_service.generate(prompt, system=SYSTEM_PROMPT)

    groundedness_report = None
    if settings.GROUNDEDNESS_CHECK_ENABLED:
        try:
            # Pass chunk texts in the SAME order used to build the context,
            # so best_chunk_index maps directly back to `results`.
            groundedness_report = groundedness_service.check_groundedness(
                answer_text, [r.chunk_text for r in results]
            )
        except Exception:
            # Groundedness checking is a safety net, not a hard dependency —
            # a failure here (e.g. NLI model not downloaded yet) shouldn't
            # break the chat feature itself.
            logger.exception("Groundedness check failed for paper %s", paper_id)

    return RAGAnswer(answer=answer_text, sources=results, grounded=True, groundedness=groundedness_report)
