"""Pydantic schemas for the semantic search API."""

from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Body for POST /papers/{paper_id}/search."""

    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(default=None, ge=1, le=50)


class SearchResultOut(BaseModel):
    chunk_id: int
    paper_id: str
    text: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    similarity_score: float


class SearchResponse(BaseModel):
    query: str
    paper_id: str
    result_count: int
    results: list[SearchResultOut]
