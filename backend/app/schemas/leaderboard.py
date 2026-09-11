"""Pydantic schemas for the cross-paper results leaderboard."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LeaderboardEntryOut(BaseModel):
    id: int
    paper_id: str
    paper_title: str
    model_name: Optional[str] = None
    dataset_name: Optional[str] = None
    metric_name: str
    value_text: str
    value: Optional[float] = None
    sentence: str
    page_number: Optional[int] = None
    upload_date: Optional[datetime] = None


class LeaderboardResponse(BaseModel):
    result_count: int
    entries: list[LeaderboardEntryOut]


class LeaderboardFacetsOut(BaseModel):
    models: list[str]
    datasets: list[str]
    metrics: list[str]
