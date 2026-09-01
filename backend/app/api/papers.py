"""API routes for uploading and retrieving research papers."""

import json
import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.paper import Paper, ProcessingStatus
from app.schemas.paper import (
    PaperDetailOut,
    PaperEntitiesOut,
    PaperSummaryOut,
    PaperUploadResponse,
)
from app.services import indexing_service, nlp_service, pdf_service
from app.utils.exceptions import PDFEmptyError, PDFExtractionError, PDFValidationError

logger = logging.getLogger("papermind.papers")

router = APIRouter(prefix="/papers", tags=["Papers"])


def _paper_to_detail(paper: Paper) -> PaperDetailOut:
    """Build the API response, parsing the stored entities JSON."""
    entities = None
    if paper.entities_json:
        try:
            entities = PaperEntitiesOut(**json.loads(paper.entities_json))
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse entities_json for paper %s", paper.id)

    return PaperDetailOut(
        id=paper.id,
        filename=paper.filename,
        title=paper.title,
        page_count=paper.page_count,
        processing_status=paper.processing_status,
        upload_date=paper.upload_date,
        authors=paper.authors,
        file_size_bytes=paper.file_size_bytes,
        error_message=paper.error_message,
        abstract=paper.abstract,
        methodology=paper.methodology,
        results_section=paper.results_section,
        limitations=paper.limitations,
        conclusion=paper.conclusion,
        entities=entities,
    )


@router.post("/upload", response_model=PaperUploadResponse)
async def upload_paper(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw_bytes = await file.read()

    try:
        result = pdf_service.process_upload(
            raw_bytes=raw_bytes,
            original_filename=file.filename,
            content_type=file.content_type,
        )
    except PDFValidationError as exc:
        logger.warning("Upload validation failed for '%s': %s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PDFEmptyError as exc:
        logger.warning("Empty PDF uploaded '%s': %s", file.filename, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PDFExtractionError as exc:
        logger.error("Extraction failed for '%s': %s", file.filename, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # unexpected — don't leak internals to the client
        logger.exception("Unexpected error processing upload '%s'", file.filename)
        raise HTTPException(status_code=500, detail="Unexpected error processing the file.") from exc

    paper = Paper(
        filename=file.filename,
        stored_path=result.stored_path,
        page_count=result.page_count,
        file_size_bytes=result.file_size_bytes,
        extracted_text=result.full_text,
        processing_status=ProcessingStatus.PROCESSING,
    )

    # --- Phase 3: run the NLP pipeline on the extracted text ---
    # Extraction succeeding but NLP failing shouldn't lose the uploaded
    # paper — we keep the record with status=FAILED and an error message
    # instead of raising, so the text is still available for retry/inspection.
    try:
        nlp_result = nlp_service.run_nlp_pipeline(result.full_text)

        paper.title = nlp_result.title
        paper.authors = nlp_result.authors
        paper.abstract = nlp_result.sections.get("abstract")
        paper.methodology = nlp_result.sections.get("methodology")
        paper.results_section = nlp_result.sections.get("results") or nlp_result.sections.get("experiments")
        paper.limitations = nlp_result.sections.get("limitations")
        paper.conclusion = nlp_result.sections.get("conclusion")
        paper.sections_json = json.dumps(nlp_result.sections)
        paper.entities_json = json.dumps(asdict(nlp_result.entities))
        paper.pages_json = json.dumps(
            [{"page_number": p.page_number, "text": nlp_service.clean_text(p.text)} for p in result.pages]
        )
        paper.processing_status = ProcessingStatus.PROCESSED
    except Exception as exc:
        logger.exception("NLP processing failed for '%s'", file.filename)
        paper.processing_status = ProcessingStatus.FAILED
        paper.error_message = f"Text extracted, but NLP processing failed: {exc}"

    try:
        db.add(paper)
        db.commit()
        db.refresh(paper)
    except Exception as exc:
        db.rollback()
        logger.exception("Database error saving paper '%s'", file.filename)
        raise HTTPException(status_code=500, detail="Failed to save paper record.") from exc

    # --- Phase 4: chunk, embed, and index the paper for semantic search ---
    # Indexing failure doesn't downgrade an otherwise-successful NLP result —
    # the paper's text/sections/entities remain usable even if search isn't
    # available for it yet. We surface the problem via error_message instead.
    if paper.processing_status == ProcessingStatus.PROCESSED:
        try:
            chunk_count = indexing_service.index_paper(paper, db)
            logger.info("Indexed %d chunks for paper %s", chunk_count, paper.id)
        except Exception as exc:
            logger.exception("Indexing failed for paper %s", paper.id)
            paper.error_message = f"Indexed text, but semantic indexing failed: {exc}"
            db.commit()

    return PaperUploadResponse(
        paper_id=paper.id,
        filename=paper.filename,
        page_count=paper.page_count,
        status=paper.processing_status,
    )


@router.get("", response_model=list[PaperSummaryOut])
def list_papers(db: Session = Depends(get_db)):
    papers = db.query(Paper).order_by(Paper.upload_date.desc()).all()
    return papers


@router.get("/{paper_id}", response_model=PaperDetailOut)
def get_paper(paper_id: str, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return _paper_to_detail(paper)


@router.post("/{paper_id}/analyze", response_model=PaperDetailOut)
def analyze_paper(paper_id: str, db: Session = Depends(get_db)):
    """
    Re-run the NLP pipeline (and re-index for search) on a paper's
    already-extracted text. Useful for re-processing without re-uploading
    the PDF (e.g. after updating the entity keyword lists or chunking logic).
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    if not paper.extracted_text:
        raise HTTPException(status_code=422, detail="This paper has no extracted text to analyze.")

    try:
        nlp_result = nlp_service.run_nlp_pipeline(paper.extracted_text)
        paper.title = nlp_result.title
        paper.authors = nlp_result.authors
        paper.abstract = nlp_result.sections.get("abstract")
        paper.methodology = nlp_result.sections.get("methodology")
        paper.results_section = nlp_result.sections.get("results") or nlp_result.sections.get("experiments")
        paper.limitations = nlp_result.sections.get("limitations")
        paper.conclusion = nlp_result.sections.get("conclusion")
        paper.sections_json = json.dumps(nlp_result.sections)
        paper.entities_json = json.dumps(asdict(nlp_result.entities))
        paper.processing_status = ProcessingStatus.PROCESSED
        paper.error_message = None
    except Exception as exc:
        logger.exception("Re-analysis failed for paper %s", paper_id)
        paper.processing_status = ProcessingStatus.FAILED
        paper.error_message = f"NLP re-analysis failed: {exc}"

    db.commit()
    db.refresh(paper)

    if paper.processing_status == ProcessingStatus.PROCESSED and paper.pages_json:
        try:
            chunk_count = indexing_service.index_paper(paper, db)
            logger.info("Re-indexed %d chunks for paper %s", chunk_count, paper.id)
        except Exception as exc:
            logger.exception("Re-indexing failed for paper %s", paper_id)
            paper.error_message = f"Re-analyzed, but re-indexing failed: {exc}"
            db.commit()

    return _paper_to_detail(paper)
