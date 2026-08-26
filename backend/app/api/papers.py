"""API routes for uploading and retrieving research papers."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.paper import Paper, ProcessingStatus
from app.schemas.paper import PaperDetailOut, PaperSummaryOut, PaperUploadResponse
from app.services import pdf_service
from app.utils.exceptions import PDFEmptyError, PDFExtractionError, PDFValidationError

logger = logging.getLogger("papermind.papers")

router = APIRouter(prefix="/papers", tags=["Papers"])


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
        processing_status=ProcessingStatus.PROCESSED,
    )

    try:
        db.add(paper)
        db.commit()
        db.refresh(paper)
    except Exception as exc:
        db.rollback()
        logger.exception("Database error saving paper '%s'", file.filename)
        raise HTTPException(status_code=500, detail="Failed to save paper record.") from exc

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
    return paper
