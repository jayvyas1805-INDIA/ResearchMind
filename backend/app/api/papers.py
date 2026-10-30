"""API routes for uploading and retrieving research papers."""

import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.paper import Paper, ProcessingStatus
from app.models.result_claim import ResultClaim
from app.schemas.paper import (
    PaperDetailOut,
    PaperEntitiesOut,
    PaperSummaryOut,
    PaperUploadResponse,
)
from app.services import indexing_service, nlp_service, pdf_service, results_extraction_service
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


def _extract_and_store_result_claims(paper: Paper, db: Session) -> None:
    """
    Runs results_extraction_service over the paper's Results section
    (falling back to full text if no section was detected) and stores the
    structured claims — this is what feeds the cross-paper leaderboard.
    Idempotent: clears any existing claims for this paper first, so
    re-analysis doesn't duplicate rows.
    """
    db.query(ResultClaim).filter(ResultClaim.paper_id == paper.id).delete()

    source_text = paper.results_section or paper.extracted_text
    if not source_text:
        db.commit()
        return

    claims = results_extraction_service.extract_result_claims(source_text)
    for c in claims:
        db.add(
            ResultClaim(
                paper_id=paper.id,
                model_name=c.model_name,
                dataset_name=c.dataset_name,
                metric_name=c.metric_name,
                value_text=c.value_text,
                value=c.value,
                sentence=c.sentence,
                section="results" if paper.results_section else None,
            )
        )
    db.commit()
    logger.info("Extracted %d result claims for paper %s", len(claims), paper.id)


def _run_nlp_and_index(paper: Paper, db: Session, pages_payload: list | None = None) -> None:
    """
    Shared pipeline: NLP -> (optionally store pages_json) -> commit -> index.
    Used by both /upload and /{id}/analyze so the logic lives in one place.
    Failures at either stage are recorded on the paper, not raised, so a
    partial success (e.g. text + NLP but no index) is still usable.
    """
    try:
        nlp_result = nlp_service.run_nlp_pipeline(paper.extracted_text)
        nlp_service.apply_nlp_result_to_paper(paper, nlp_result)
        if pages_payload is not None:
            paper.pages_json = json.dumps(pages_payload)
        paper.processing_status = ProcessingStatus.PROCESSED
        paper.error_message = None
    except Exception as exc:
        logger.exception("NLP processing failed for paper %s", paper.id)
        paper.processing_status = ProcessingStatus.FAILED
        paper.error_message = f"Text extracted, but NLP processing failed: {exc}"

    db.add(paper)
    db.commit()
    db.refresh(paper)

    if paper.processing_status == ProcessingStatus.PROCESSED:
        try:
            _extract_and_store_result_claims(paper, db)
        except Exception:
            logger.exception("Result-claim extraction failed for paper %s", paper.id)
            # Non-fatal — the leaderboard just won't have entries for this paper.

    if paper.processing_status == ProcessingStatus.PROCESSED and paper.pages_json:
        try:
            chunk_count = indexing_service.index_paper(paper, db)
            logger.info("Indexed %d chunks for paper %s", chunk_count, paper.id)
        except Exception as exc:
            logger.exception("Indexing failed for paper %s", paper.id)
            paper.error_message = f"Processed, but semantic indexing failed: {exc}"
            db.commit()


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

    # Duplicate detection: same file content already uploaded and processed.
    existing = (
        db.query(Paper)
        .filter(Paper.content_hash == result.content_hash, Paper.processing_status == ProcessingStatus.PROCESSED)
        .first()
    )
    if existing:
        import os
        if os.path.exists(result.stored_path):
            os.remove(result.stored_path)
        logger.info("Duplicate upload detected for '%s', matches paper %s", file.filename, existing.id)
        return PaperUploadResponse(
            paper_id=existing.id,
            filename=existing.filename,
            page_count=existing.page_count,
            status=existing.processing_status,
        )

    paper = Paper(
        filename=file.filename,
        stored_path=result.stored_path,
        content_hash=result.content_hash,
        page_count=result.page_count,
        file_size_bytes=result.file_size_bytes,
        extracted_text=result.full_text,
        processing_status=ProcessingStatus.PROCESSING,
    )

    pages_payload = [
        {"page_number": p.page_number, "text": nlp_service.clean_text(p.text)} for p in result.pages
    ]
    _run_nlp_and_index(paper, db, pages_payload=pages_payload)

    return PaperUploadResponse(
        paper_id=paper.id,
        filename=paper.filename,
        page_count=paper.page_count,
        status=paper.processing_status,
    )


@router.get("", response_model=list[PaperSummaryOut])
def list_papers(db: Session = Depends(get_db)):
    return db.query(Paper).order_by(Paper.upload_date.desc()).all()


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

    _run_nlp_and_index(paper, db)  # pages_json already set from the original upload
    return _paper_to_detail(paper)
