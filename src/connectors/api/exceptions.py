from __future__ import annotations

from src.connectors.exceptions import ConnectorError


class ApiError(ConnectorError):
    """Base exception for all REST API connector errors."""


class ApiParseError(ApiError):
    """Raised when the API response cannot be parsed."""


class UnsupportedContentTypeError(ApiError):
    """Raised when the response MIME type is not a supported JSON type."""


class UnsupportedResponseFormatError(ApiError):
    """Raised when the response format is not supported (e.g. XML)."""


class EmptyResponseError(ApiError):
    """Raised when the API returns an empty response body."""


class ApiRateLimitedError(ApiError):
    """Raised when the API responds with a rate-limit status."""


class ApiServerError(ApiError):
    """Raised when the API returns a 5xx server error."""


class ApiAuthenticationError(ApiError):
    """Raised on 401/403 authentication failures."""
