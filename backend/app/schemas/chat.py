"""Pydantic schemas for the RAG chat/Q&A API."""
from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(default=None, ge=1, le=50)


class ChatSourceOut(BaseModel):
    chunk_id: int
    page_number: Optional[int] = None
    section: Optional[str] = None
    text: str
    similarity_score: float


class SentenceGroundingOut(BaseModel):
    sentence: str
    support_score: float
    chunk_id: Optional[int] = None  # the source chunk that best supports this sentence


class ChatResponse(BaseModel):
    paper_id: str
    question: str
    answer: str
    grounded: bool  # False only if no context was retrieved at all
    sources: list[ChatSourceOut]

    # NLI-based groundedness check (None if disabled or the check itself failed)
    is_grounded: Optional[bool] = None
    supported_ratio: Optional[float] = None
    sentence_grounding: Optional[list[SentenceGroundingOut]] = None
