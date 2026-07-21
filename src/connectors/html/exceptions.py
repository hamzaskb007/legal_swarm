from __future__ import annotations

from src.connectors.exceptions import ConnectorError


class HtmlError(ConnectorError):
    """Base exception for all HTML connector errors."""


class HtmlParseError(HtmlError):
    """Raised when HTML content cannot be parsed."""


class UnsupportedContentTypeError(HtmlError):
    """Raised when the response MIME type is not supported HTML."""


class EmptyContentError(HtmlError):
    """Raised when the retrieved page contains no content."""


class ExtractionError(HtmlError):
    """Raised when content extraction fails."""
