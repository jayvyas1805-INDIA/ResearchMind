"""Tests for pdf_service: validation and content hashing (pure logic, no I/O needed)."""
import pytest

from app.services import pdf_service
from app.utils.exceptions import PDFValidationError


def test_validate_upload_rejects_non_pdf_extension():
    with pytest.raises(PDFValidationError):
        pdf_service.validate_upload("notes.txt", "text/plain", 1000)


def test_validate_upload_rejects_empty_file():
    with pytest.raises(PDFValidationError):
        pdf_service.validate_upload("paper.pdf", "application/pdf", 0)


def test_validate_upload_rejects_oversized_file(monkeypatch):
    from app.core import config
    config.get_settings.cache_clear()
    with pytest.raises(PDFValidationError):
        too_big = (pdf_service.settings.MAX_UPLOAD_SIZE_MB + 1) * 1024 * 1024
        pdf_service.validate_upload("paper.pdf", "application/pdf", too_big)


def test_validate_upload_accepts_reasonable_pdf():
    pdf_service.validate_upload("paper.pdf", "application/pdf", 1024 * 500)


def test_compute_content_hash_is_deterministic():
    h1 = pdf_service.compute_content_hash(b"hello world")
    h2 = pdf_service.compute_content_hash(b"hello world")
    h3 = pdf_service.compute_content_hash(b"different content")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # sha256 hex digest length
