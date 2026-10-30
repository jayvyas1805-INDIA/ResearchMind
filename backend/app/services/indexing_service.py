"""
Indexing service.

Orchestrates the full Phase 4 pipeline for one paper:
  pages + sections -> chunks -> embeddings -> Chunk rows in DB -> FAISS index

Idempotent: re-indexing a paper first removes its existing chunks/vectors,
so it can be safely re-run (e.g. after re-analysis in Phase 3, or if
chunking logic changes).
"""

import json
import logging

from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.paper import Paper
from app.services import chunking_service, embedding_service, vector_service
from app.services.chunking_service import PageInput

logger = logging.getLogger("papermind.indexing")


def _repair_chunk_sections(db: Session) -> None:
    """Reclassify older chunks now that section matching normalizes PDF whitespace."""
    papers = db.query(Paper).filter(Paper.sections_json.isnot(None)).all()
    updated = 0
    for paper in papers:
        try:
            sections = json.loads(paper.sections_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse sections_json for paper %s", paper.id)
            continue
        chunks = db.query(Chunk).filter(Chunk.paper_id == paper.id).all()
        for chunk in chunks:
            section = chunking_service._best_matching_section(chunk.text, sections)
            if section != "unclassified" and chunk.section != section:
                chunk.section = section
                updated += 1
    if updated:
        db.commit()
        logger.info("Reclassified %d stored chunks using detected paper sections.", updated)


def _remove_existing_chunks(paper_id: str, db: Session) -> None:
    existing = db.query(Chunk).filter(Chunk.paper_id == paper_id).all()
    if not existing:
        return
    ids = [c.id for c in existing]
    vector_service.remove_ids(ids)
    db.query(Chunk).filter(Chunk.paper_id == paper_id).delete()
    db.commit()


def reconcile_index(db: Session) -> bool:
    """Rebuild FAISS from stored chunks when its ids do not match the database."""
    _repair_chunk_sections(db)
    chunks = db.query(Chunk).order_by(Chunk.id).all()
    chunk_ids = [chunk.id for chunk in chunks]
    if sorted(vector_service.get_vector_ids()) == chunk_ids:
        return False

    logger.warning(
        "FAISS index is out of sync with the database; rebuilding %d vectors.",
        len(chunks),
    )
    vectors = embedding_service.embed_texts([chunk.text for chunk in chunks])
    vector_service.replace_vectors(chunk_ids, vectors)
    logger.info("Rebuilt FAISS index with %d vectors.", len(chunk_ids))
    return True


def index_paper(paper: Paper, db: Session) -> int:
    """
    Chunk, embed, and index a paper's already-extracted, already-NLP-processed
    text. Requires paper.pages_json and paper.sections_json to be populated
    (Phases 2 and 3), and paper.id to already exist in the DB (i.e. call this
    after the paper has been committed at least once).

    Returns the number of chunks indexed.
    """
    if not paper.pages_json:
        raise ValueError("Paper has no page-level text to chunk (pages_json is empty).")

    pages_raw = json.loads(paper.pages_json)
    pages = [PageInput(page_number=p["page_number"], text=p["text"]) for p in pages_raw]

    sections = json.loads(paper.sections_json) if paper.sections_json else {}

    # Re-indexing safety: clear out any previous chunks/vectors for this paper first.
    _remove_existing_chunks(paper.id, db)

    chunks_data = chunking_service.chunk_paper(pages, sections)
    if not chunks_data:
        logger.warning("No chunks produced for paper %s — nothing to index.", paper.id)
        return 0

    texts = [c.text for c in chunks_data]
    vectors = embedding_service.embed_texts(texts)

    # Insert chunk rows first so each gets its autoincrement id, which we
    # then reuse directly as the FAISS vector id.
    chunk_rows = [
        Chunk(
            paper_id=paper.id,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            section=c.section,
            text=c.text,
        )
        for c in chunks_data
    ]
    db.add_all(chunk_rows)
    db.commit()
    for row in chunk_rows:
        db.refresh(row)

    ids = [row.id for row in chunk_rows]
    vector_service.add_vectors(ids, vectors)

    logger.info("Indexed %d chunks for paper %s", len(chunk_rows), paper.id)
    return len(chunk_rows)
