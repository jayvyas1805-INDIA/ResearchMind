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

    # Metadata — populated by the NLP pipeline (Phase 3). Nullable since it's
    # only available after processing.
    title = Column(String, nullable=True)
    authors = Column(Text, nullable=True)

    page_count = Column(Integer, nullable=False, default=0)
    file_size_bytes = Column(Integer, nullable=False, default=0)

    # Raw extracted text, stored so later phases (NLP, chunking) don't need
    # to re-parse the PDF from scratch.
    extracted_text = Column(Text, nullable=True)

    # --- Phase 3: NLP extraction results ---
    # Stored as JSON strings (SQLite has no native JSON type in this setup).
    abstract = Column(Text, nullable=True)
    methodology = Column(Text, nullable=True)
    results_section = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    conclusion = Column(Text, nullable=True)
    sections_json = Column(Text, nullable=True)   # full section_name -> text map
    entities_json = Column(Text, nullable=True)   # models/datasets/metrics/etc.

    processing_status = Column(
        Enum(ProcessingStatus), nullable=False, default=ProcessingStatus.UPLOADED
    )
    error_message = Column(Text, nullable=True)

    upload_date = Column(DateTime(timezone=True), server_default=func.now())
