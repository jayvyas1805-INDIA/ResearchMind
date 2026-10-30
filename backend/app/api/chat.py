"""API route for RAG-based question answering about a paper."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.paper import Paper
from app.schemas.chat import ChatRequest, ChatResponse, ChatSourceOut, SentenceGroundingOut
from app.services import llm_service, rag_service

logger = logging.getLogger("papermind.chat")

router = APIRouter(prefix="/papers", tags=["Chat"])


@router.post("/{paper_id}/chat", response_model=ChatResponse)
def chat_with_paper(paper_id: str, body: ChatRequest, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        result = rag_service.answer_question(paper_id, body.question, db, top_k=body.top_k)
    except llm_service.LLMError as exc:
        logger.error("LLM error answering question for paper %s: %s", paper_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("RAG pipeline failed for paper %s", paper_id)
        raise HTTPException(status_code=500, detail="Failed to generate an answer.") from exc

    sentence_grounding_out = None
    is_grounded = None
    supported_ratio = None
    if result.groundedness is not None:
        is_grounded = result.groundedness.grounded
        supported_ratio = result.groundedness.supported_ratio
        sentence_grounding_out = [
            SentenceGroundingOut(
                sentence=s.sentence,
                support_score=s.support_score,
                chunk_id=result.sources[s.best_chunk_index].chunk_id
                if 0 <= s.best_chunk_index < len(result.sources)
                else None,
            )
            for s in result.groundedness.sentence_scores
        ]

    return ChatResponse(
        paper_id=paper_id,
        question=body.question,
        answer=result.answer,
        grounded=result.grounded,
        answer_mode=result.answer_mode,
        sources=[
            ChatSourceOut(
                chunk_id=s.chunk_id,
                page_number=s.page_number,
                section=s.section,
                text=s.chunk_text,
                similarity_score=s.similarity_score,
            )
            for s in result.sources
        ],
        is_grounded=is_grounded,
        supported_ratio=supported_ratio,
        sentence_grounding=sentence_grounding_out,
    )
