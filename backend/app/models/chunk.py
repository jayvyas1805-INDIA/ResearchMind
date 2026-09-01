"""
Database model for a text chunk produced during Phase 4 (chunking).

Uses an integer autoincrement primary key rather than a UUID, deliberately —
this integer is reused directly as the FAISS vector id (FAISS's IndexIDMap
requires int64 ids), so there's a single source of truth for "which chunk
does this vector belong to" instead of a separate id-mapping table.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.core.database import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)  # == FAISS vector id

    paper_id = Column(String, ForeignKey("papers.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)  # order within the paper, 0-based

    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)  # canonical section name, or "unclassified"

    text = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
