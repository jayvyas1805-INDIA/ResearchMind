"""Pydantic schemas for the papers API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.paper import ProcessingStatus


class PaperUploadResponse(BaseModel):
    paper_id: str
    filename: str
    page_count: int
    status: ProcessingStatus

    model_config = ConfigDict(from_attributes=True)


class PaperSummaryOut(BaseModel):
    """Lightweight representation used in list views (Dashboard, Phase 9)."""

    id: str
    filename: str
    title: Optional[str] = None
    page_count: int
    processing_status: ProcessingStatus
    upload_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaperEntitiesOut(BaseModel):
    persons: list[str] = []
    organizations: list[str] = []
    models: list[str] = []
    datasets: list[str] = []
    metrics: list[str] = []
    methods: list[str] = []
    technologies: list[str] = []


class PaperDetailOut(PaperSummaryOut):
    authors: Optional[str] = None
    file_size_bytes: int
    error_message: Optional[str] = None

    # Phase 3: NLP extraction results
    abstract: Optional[str] = None
    methodology: Optional[str] = None
    results_section: Optional[str] = None
    limitations: Optional[str] = None
    conclusion: Optional[str] = None
    entities: Optional[PaperEntitiesOut] = None

    model_config = ConfigDict(from_attributes=True)
