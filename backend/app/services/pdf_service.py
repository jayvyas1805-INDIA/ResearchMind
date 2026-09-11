"""
PDF ingestion service.

Responsible for:
- validating uploaded files
- saving them safely to disk
- extracting text page-by-page with PyMuPDF (fitz)

Kept independent of FastAPI so it can be reused/tested without spinning up
the API layer.
"""

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from typing import List

import fitz  # PyMuPDF

from app.core.config import get_settings
from app.utils.exceptions import PDFEmptyError, PDFExtractionError, PDFValidationError

settings = get_settings()

ALLOWED_CONTENT_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}


@dataclass
class PageText:
    page_number: int  # 1-indexed
    text: str


@dataclass
class ExtractionResult:
    stored_path: str
    stored_filename: str
    page_count: int
    full_text: str
    pages: List[PageText] = field(default_factory=list)
    file_size_bytes: int = 0
    content_hash: str = ""


def validate_upload(filename: str, content_type: str, file_size_bytes: int) -> None:
    """Raise PDFValidationError if the upload doesn't meet basic requirements."""
    if not filename:
        raise PDFValidationError("Uploaded file has no filename.")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise PDFValidationError(f"Unsupported file extension '{ext}'. Only .pdf is allowed.")

    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        # Some browsers/clients send generic content types — extension check
        # above is the primary guard, this is a secondary signal only.
        pass

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size_bytes <= 0:
        raise PDFValidationError("Uploaded file is empty.")
    if file_size_bytes > max_bytes:
        raise PDFValidationError(
            f"File is too large ({file_size_bytes / 1024 / 1024:.1f} MB). "
            f"Maximum allowed is {settings.MAX_UPLOAD_SIZE_MB} MB."
        )


def save_upload(raw_bytes: bytes, original_filename: str) -> tuple[str, str]:
    """
    Save the raw PDF bytes to disk under a UUID-prefixed name to avoid
    collisions/overwrites. Returns (stored_path, stored_filename).
    """
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(original_filename)[1].lower()
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_filename)

    with open(stored_path, "wb") as f:
        f.write(raw_bytes)

    return stored_path, stored_filename


def extract_text(stored_path: str) -> ExtractionResult:
    """
    Extract text page-by-page from a saved PDF file using PyMuPDF.

    Raises:
        PDFValidationError: if the file cannot be opened as a PDF (corrupt/invalid).
        PDFEmptyError: if the PDF opens but contains no extractable text at all.
        PDFExtractionError: for any other unexpected extraction failure.
    """
    try:
        doc = fitz.open(stored_path)
    except Exception as exc:  # PyMuPDF raises various errors for bad files
        raise PDFValidationError(f"File could not be opened as a valid PDF: {exc}") from exc

    try:
        pages: List[PageText] = []
        text_parts: List[str] = []

        for i, page in enumerate(doc, start=1):
            try:
                page_text = page.get_text("text") or ""
            except Exception as exc:
                raise PDFExtractionError(f"Failed extracting text on page {i}: {exc}") from exc

            pages.append(PageText(page_number=i, text=page_text.strip()))
            text_parts.append(page_text)

        page_count = doc.page_count
        full_text = "\n".join(text_parts).strip()

        if not full_text:
            raise PDFEmptyError(
                "No extractable text found in this PDF. It may be a scanned "
                "image-only document (OCR is not supported yet)."
            )

        file_size_bytes = os.path.getsize(stored_path)

        return ExtractionResult(
            stored_path=stored_path,
            stored_filename=os.path.basename(stored_path),
            page_count=page_count,
            full_text=full_text,
            pages=pages,
            file_size_bytes=file_size_bytes,
        )
    finally:
        doc.close()


def compute_content_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def process_upload(raw_bytes: bytes, original_filename: str, content_type: str) -> ExtractionResult:
    """
    Full ingestion pipeline: validate → save → extract.
    Single entry point used by the API route.
    """
    validate_upload(original_filename, content_type, len(raw_bytes))

    stored_path, _ = save_upload(raw_bytes, original_filename)

    try:
        result = extract_text(stored_path)
        result.content_hash = compute_content_hash(raw_bytes)
        return result
    except (PDFValidationError, PDFEmptyError, PDFExtractionError):
        # Clean up the saved file if extraction failed, so we don't
        # accumulate orphaned uploads.
        if os.path.exists(stored_path):
            os.remove(stored_path)
        raise
