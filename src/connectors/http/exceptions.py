from __future__ import annotations

from src.connectors.exceptions import ConnectorError


class HttpError(ConnectorError):
    """Base exception for all HTTP-layer errors."""


class TimeoutError(HttpError):
    """Raised when an HTTP request times out."""


class RedirectError(HttpError):
    """Raised when redirect handling fails (cycle, limit exceeded)."""


class ConnectionError(HttpError):
    """Raised when the HTTP client cannot connect to the remote host."""


class InvalidResponseError(HttpError):
    """Raised when the server response is malformed or unreadable."""


class UnsupportedMimeTypeError(HttpError):
    """Raised when the response MIME type is not supported."""


class ResponseTooLargeError(HttpError):
    """Raised when the response body exceeds the configured maximum."""


class InvalidUrlError(HttpError):
    """Raised when the provided URL is malformed or uses an unsupported scheme."""


class HttpConfigurationError(HttpError):
    """Raised when the HTTP client is misconfigured."""
