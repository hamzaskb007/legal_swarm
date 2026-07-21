from __future__ import annotations

from src.connectors.exceptions import ConnectorError


class PdfError(ConnectorError):
    """Base exception for all PDF connector errors."""


class PdfParseError(PdfError):
    """Raised when PDF content cannot be parsed."""


class UnsupportedContentTypeError(PdfError):
    """Raised when the response MIME type is not application/pdf."""


class PdfEncryptedError(PdfError):
    """Raised when the PDF is encrypted or password-protected."""


class PdfCorruptedError(PdfError):
    """Raised when the PDF is malformed or corrupted."""


class PdfTooLargeError(PdfError):
    """Raised when the PDF exceeds the configured maximum size."""


class PdfTooManyPagesError(PdfError):
    """Raised when the PDF exceeds the configured maximum page count."""


class PdfEmptyError(PdfError):
    """Raised when the PDF contains no pages or content."""
