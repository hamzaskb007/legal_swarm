from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, cast

from pydantic import BaseModel, Field

from src.connectors.api.exceptions import (
    ApiParseError,
    EmptyResponseError,
    UnsupportedResponseFormatError,
)
from src.connectors.models import Document

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUPPORTED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/json",
    }
)

DEFAULT_PAGE_SIZE = 50
DEFAULT_MAX_PAGES = 100
DEFAULT_MAX_RESPONSE_SIZE = 10 * 1024 * 1024

_RFC3339_PATTERNS: list[str] = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S.%f%z",
]


# ---------------------------------------------------------------------------
# Field mapping configuration
# ---------------------------------------------------------------------------


class ApiFieldMapping(BaseModel, frozen=True):
    """Maps JSON response fields to Document fields."""

    title: str | None = None
    content: str | None = None
    summary: str | None = None
    publication_date: str | None = None
    last_modified: str | None = None
    source_url: str | None = None
    document_type: str | None = None
    language: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    items_path: str | None = None

    @property
    def has_mappings(self) -> bool:
        return any(
            v is not None
            for v in (
                self.title,
                self.content,
                self.summary,
                self.publication_date,
                self.last_modified,
                self.source_url,
                self.document_type,
                self.language,
            )
        ) or bool(self.metadata)


# ---------------------------------------------------------------------------
# Pagination strategies
# ---------------------------------------------------------------------------


class ApiPaginationPageNumber(BaseModel, frozen=True):
    type: str = "page_number"
    page_param: str = "page"
    size_param: str = "page_size"
    page_size: int = DEFAULT_PAGE_SIZE
    first_page: int = 1
    total_pages_path: str | None = None


class ApiPaginationOffset(BaseModel, frozen=True):
    type: str = "offset"
    offset_param: str = "offset"
    limit_param: str = "limit"
    page_size: int = DEFAULT_PAGE_SIZE
    max_offset: int = 10000


class ApiPaginationCursor(BaseModel, frozen=True):
    type: str = "cursor"
    cursor_param: str = "cursor"
    cursor_path: str = "meta.next_cursor"
    page_size_param: str = "limit"
    page_size: int = DEFAULT_PAGE_SIZE
    max_pages: int = DEFAULT_MAX_PAGES


class ApiPaginationNextLink(BaseModel, frozen=True):
    type: str = "next_link"
    link_path: str = "links.next"
    max_pages: int = DEFAULT_MAX_PAGES


ApiPaginationStrategy = (
    ApiPaginationPageNumber | ApiPaginationOffset | ApiPaginationCursor | ApiPaginationNextLink
)


# ---------------------------------------------------------------------------
# Main API config
# ---------------------------------------------------------------------------


class ApiConfig(BaseModel, frozen=True):
    """Configuration for an API endpoint.

    Supports configurable API definitions rather than hardcoding
    authority-specific behavior.
    """

    endpoint_url: str = ""
    method: str = "GET"
    headers: dict[str, str] = Field(default_factory=lambda: {"Accept": "application/json"})
    auth_type: str = "none"
    auth_credentials: dict[str, str] = Field(default_factory=dict)
    response_format: str = "json"
    field_mapping: ApiFieldMapping = Field(default_factory=ApiFieldMapping)
    pagination: ApiPaginationStrategy | None = None
    filter_params: dict[str, str] = Field(default_factory=dict)
    date_from_param: str | None = None
    date_to_param: str | None = None
    max_response_size: int = DEFAULT_MAX_RESPONSE_SIZE
    timeout: float | None = None


# ---------------------------------------------------------------------------
# JSON value extraction utilities
# ---------------------------------------------------------------------------


def _get_json_value(obj: Any, path: str) -> Any:
    """Get a value from a nested dict using dot notation.

    Examples:
        _get_json_value({"meta": {"count": 5}}, "meta.count") -> 5
        _get_json_value({"title": "Foo"}, "title") -> "Foo"
    """
    if not path:
        return None
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _extract_items(data: Any, items_path: str | None) -> list[dict[str, Any]]:
    """Extract the items list from a response using an optional path."""
    if items_path:
        items = _get_json_value(data, items_path)
        if items is None:
            raise ApiParseError(f"Items path '{items_path}' not found in response")
    elif isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = [data]
    else:
        raise ApiParseError(f"Unexpected response type: {type(data).__name__}")

    if not isinstance(items, list):
        raise ApiParseError(
            f"Expected list at items path '{items_path or 'root'}', got {type(items).__name__}"
        )

    return items


def _resolve_next_page(data: Any, strategy: ApiPaginationStrategy) -> str | None:
    """Resolve the next page URL/identifier from a pagination strategy."""
    if isinstance(strategy, ApiPaginationNextLink):
        return cast(str | None, _get_json_value(data, strategy.link_path))
    if isinstance(strategy, ApiPaginationCursor):
        return cast(str | None, _get_json_value(data, strategy.cursor_path))
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse an RFC 3339 / ISO 8601 timestamp string."""
    if value is None or not isinstance(value, str):
        return None
    cleaned = value.strip().replace("Z", "+00:00")
    for fmt in _RFC3339_PATTERNS:
        try:
            dt = datetime.strptime(cleaned, fmt)
            if dt.tzinfo is not None:
                return dt
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        log.debug("Could not parse timestamp: %s", value)
        return None


# ---------------------------------------------------------------------------
# APIParser
# ---------------------------------------------------------------------------


class APIParser:
    """Parses JSON API responses into Document models.

    Separates networking from response transformation — independently
    testable without any HTTP infrastructure.
    """

    def __init__(self, config: ApiConfig | None = None) -> None:
        self._config = config or ApiConfig()

    @property
    def config(self) -> ApiConfig:
        return self._config

    def parse(
        self,
        body: bytes | str,
        source_url: str,
        authority_id: str,
        content_type: str = "",
    ) -> list[Document]:
        """Parse a JSON API response body into Document instances."""
        self._validate_content_type(content_type)
        self._validate_response_format()

        data = self._decode_json(body)

        items = _extract_items(data, self._config.field_mapping.items_path)

        documents = [self._item_to_doc(item, source_url, authority_id) for item in items]

        log.debug(
            "Parsed %d documents from %s",
            len(documents),
            source_url,
        )

        return documents

    def parse_single(
        self,
        body: bytes | str,
        source_url: str,
        authority_id: str,
        content_type: str = "",
    ) -> Document:
        """Parse a single JSON object response into a single Document."""
        docs = self.parse(body, source_url, authority_id, content_type)
        if not docs:
            raise EmptyResponseError("No documents parsed from response")
        if len(docs) > 1:
            log.warning(
                "parse_single got %d documents from %s, returning first",
                len(docs),
                source_url,
            )
        return docs[0]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _decode_json(self, body: bytes | str) -> Any:
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        body = body.strip()
        if not body:
            raise EmptyResponseError("Empty response body")

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ApiParseError(f"Invalid JSON in response: {e}") from e

        if data is None:
            raise EmptyResponseError("Null/empty JSON response")
        if isinstance(data, list) and not data:
            log.debug("Empty JSON array response from %s")
            return []

        return data

    def _item_to_doc(
        self,
        item: dict[str, Any],
        source_url: str,
        authority_id: str,
    ) -> Document:
        mapping = self._config.field_mapping

        title = self._map_str(item, mapping.title) if mapping.title else None
        content = (self._map_str(item, mapping.content) or "") if mapping.content else ""
        summary = self._map_str(item, mapping.summary) if mapping.summary else None
        pub_date = (
            self._map_date(item, mapping.publication_date) if mapping.publication_date else None
        )
        last_mod = self._map_date(item, mapping.last_modified) if mapping.last_modified else None
        doc_url = self._map_str(item, mapping.source_url) if mapping.source_url else None
        doc_type = self._map_str(item, mapping.document_type) if mapping.document_type else None
        language = self._map_str(item, mapping.language) if mapping.language else None

        extra_meta: dict[str, Any] = {}
        for meta_key, json_path in mapping.metadata.items():
            value = self._map_str(item, json_path)
            if value is not None:
                extra_meta[meta_key] = value

        return Document(
            authority_id=authority_id,
            source_url=doc_url or source_url,
            title=title,
            summary=summary,
            content=content,
            content_type="application/json",
            language=language,
            publication_date=pub_date,
            last_modified=last_mod,
            document_type=doc_type or "api_response",
            metadata=extra_meta,
        )

    @staticmethod
    def _map_str(item: dict[str, Any], path: str) -> str | None:
        value = _get_json_value(item, path)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        return None

    @staticmethod
    def _map_date(item: dict[str, Any], path: str) -> datetime | None:
        value = _get_json_value(item, path)
        return _parse_timestamp(value)

    @staticmethod
    def _validate_content_type(content_type: str) -> None:
        if not content_type:
            return
        base_type = content_type.split(";")[0].strip().lower()
        if not base_type:
            return
        if base_type not in _SUPPORTED_CONTENT_TYPES:
            from src.connectors.api.exceptions import UnsupportedContentTypeError

            raise UnsupportedContentTypeError(
                f"Unsupported content type: {content_type} "
                f"(supported: {', '.join(sorted(_SUPPORTED_CONTENT_TYPES))})"
            )

    def _validate_response_format(self) -> None:
        fmt = self._config.response_format.lower()
        if fmt not in ("json", "json_array"):
            raise UnsupportedResponseFormatError(
                f"Unsupported response format: {fmt} (supported: json, json_array)"
            )

    @staticmethod
    def is_supported_content_type(content_type: str) -> bool:
        base_type = content_type.split(";")[0].strip().lower()
        return base_type in _SUPPORTED_CONTENT_TYPES if base_type else False

    @staticmethod
    def get_page_params(
        strategy: ApiPaginationStrategy,
        page_index: int,
    ) -> dict[str, str]:
        """Build query parameters for a specific page of results."""
        params: dict[str, str] = {}

        if isinstance(strategy, ApiPaginationPageNumber):
            params[strategy.page_param] = str(strategy.first_page + page_index)
            params[strategy.size_param] = str(strategy.page_size)

        elif isinstance(strategy, ApiPaginationOffset):
            offset = page_index * strategy.page_size
            params[strategy.offset_param] = str(offset)
            params[strategy.limit_param] = str(strategy.page_size)

        elif isinstance(strategy, ApiPaginationCursor):
            if page_index > 0:
                log.debug("Cursor pagination requires cursor from previous response")
            params[strategy.page_size_param] = str(strategy.page_size)

        elif isinstance(strategy, ApiPaginationNextLink):
            pass

        return params

    def should_fetch_more(
        self,
        strategy: ApiPaginationStrategy,
        data: Any,
        page_index: int,
        total_fetched: int,
    ) -> bool:
        """Determine whether to fetch the next page."""
        if isinstance(strategy, ApiPaginationPageNumber):
            max_page = strategy.first_page + DEFAULT_MAX_PAGES
            if page_index >= max_page:
                return False
            if strategy.total_pages_path:
                total = _get_json_value(data, strategy.total_pages_path)
                if isinstance(total, (int, float)) and page_index >= int(total):
                    return False
            return True

        if isinstance(strategy, ApiPaginationOffset):
            max_offset = strategy.max_offset
            next_offset = (page_index + 1) * strategy.page_size
            return next_offset < max_offset

        if isinstance(strategy, ApiPaginationCursor):
            if page_index >= strategy.max_pages:
                return False
            cursor = _resolve_next_page(data, strategy)
            return cursor is not None

        if isinstance(strategy, ApiPaginationNextLink):
            if page_index >= strategy.max_pages:
                return False
            next_link = _resolve_next_page(data, strategy)
            return next_link is not None

        return False
