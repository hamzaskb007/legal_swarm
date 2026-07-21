from __future__ import annotations

from src.connectors.exceptions import ConnectorError


class RssError(ConnectorError):
    """Base exception for all RSS connector errors."""


class RssParseError(RssError):
    """Raised when feed XML cannot be parsed."""


class UnsupportedFeedFormatError(RssError):
    """Raised when the feed format is not RSS 2.0 or Atom."""


class UnsupportedContentTypeError(RssError):
    """Raised when the response MIME type is not a supported feed type."""


class EmptyFeedError(RssError):
    """Raised when the retrieved feed contains no entries."""


class FeedTooLargeError(RssError):
    """Raised when the feed exceeds the configured maximum size."""


class InvalidXmlError(RssError):
    """Raised when the feed contains malformed XML."""
