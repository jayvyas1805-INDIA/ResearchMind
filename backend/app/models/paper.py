"""Database model for an uploaded research paper."""

import enum
import uuid

from sqlalchemy import Column, String, Integer, DateTime, Enum, Text
from sqlalchemy.sql import func

from app.core.database import Base


class ProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String, primary_key=True, default=generate_uuid)

    filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)

    # Metadata — populated in Phase 3 (NLP extraction). Nullable for now.
    title = Column(String, nullable=True)
    authors = Column(Text, nullable=True)  # comma-separated for now

    page_count = Column(Integer, nullable=False, default=0)
    file_size_bytes = Column(Integer, nullable=False, default=0)

    # Raw extracted text, stored so later phases (NLP, chunking) don't need
    # to re-parse the PDF from scratch.
    extracted_text = Column(Text, nullable=True)

    processing_status = Column(
        Enum(ProcessingStatus), nullable=False, default=ProcessingStatus.UPLOADED
    )
    error_message = Column(Text, nullable=True)

    upload_date = Column(DateTime(timezone=True), server_default=func.now())
