"""Custom exceptions used across services for clear, specific error handling."""


class PDFValidationError(Exception):
    """Raised when an uploaded file fails validation (type, size, corruption)."""


class PDFEmptyError(Exception):
    """Raised when a PDF is valid but contains no extractable text."""


class PDFExtractionError(Exception):
    """Raised when text extraction fails for a reason other than the above."""
