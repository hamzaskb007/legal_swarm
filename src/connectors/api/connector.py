from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, cast

from src.authority.models import Authority, CapabilityType, ParserType
from src.connectors.api.exceptions import (
    ApiAuthenticationError,
    ApiError,
    ApiParseError,
    ApiRateLimitedError,
    ApiServerError,
    UnsupportedContentTypeError,
)
from src.connectors.api.parser import (
    ApiConfig,
    ApiPaginationCursor,
    ApiPaginationNextLink,
    ApiPaginationPageNumber,
    ApiPaginationStrategy,
    APIParser,
    _extract_items,
    _resolve_next_page,
)
from src.connectors.base import Connector
from src.connectors.http.client import HttpClient
from src.connectors.http.exceptions import HttpError
from src.connectors.http.models import HttpMethod
from src.connectors.models import (
    ConnectorCapabilities,
    ConnectorMetadata,
    ConnectionHealth,
    ConnectionResult,
    ConnectionStatus,
    Document,
    FetchRequest,
    FetchResult,
)

log = logging.getLogger(__name__)

_SUPPORTED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/json",
    }
)


class APIConnector(Connector):
    """Retrieves regulatory documents from REST-based authority APIs.

    Uses the shared HTTP infrastructure for all networking.
    Delegates all parsing to APIParser (which is independently testable).
    Supports configurable pagination, field mapping, and filters.
    """

    def __init__(
        self,
        authority: Authority,
        http_client: HttpClient | None = None,
        parser: APIParser | None = None,
        api_config: ApiConfig | None = None,
    ) -> None:
        super().__init__(authority)
        self._api_config = api_config or ApiConfig()
        self._http = http_client
        self._parser = parser or APIParser(self._api_config)
        self._started_at: datetime | None = None

    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="APIConnector",
            version="1.0.0",
            description="Retrieves regulatory documents from REST-based authority APIs",
            parser_types=[ParserType.API],
            capabilities=[CapabilityType.API, CapabilityType.JSON],
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            parser_types=frozenset({ParserType.API}),
            capability_types=frozenset({CapabilityType.API, CapabilityType.JSON}),
            supports_search=False,
            supports_streaming=True,
        )

    def connect(self) -> ConnectionResult:
        self._initialized = True
        self._started_at = datetime.utcnow()
        log.debug("APIConnector initialized for authority: %s", self._authority.id)
        return ConnectionResult(
            success=True,
            status=ConnectionStatus.CONNECTED,
            message="API connector initialized",
            connected_at=self._started_at,
        )

    def health(self) -> ConnectionHealth:
        return ConnectionHealth(
            initialized=self._initialized,
            available=self._http is not None,
            status=ConnectionStatus.CONNECTED
            if self._initialized
            else ConnectionStatus.INITIALIZED,
            parser_supported=True,
            capabilities=[CapabilityType.API, CapabilityType.JSON],
            version="1.0.0",
            last_health_check=datetime.utcnow(),
            details={
                "http_configured": self._http is not None,
                "endpoint_url": self._api_config.endpoint_url,
                "auth_type": self._api_config.auth_type,
                "response_format": self._api_config.response_format,
                "pagination_strategy": self._resolve_pagination_type(),
            },
        )

    def fetch(self, request: FetchRequest) -> FetchResult:
        if not self._http:
            return FetchResult(
                success=False,
                metadata={"error": "HTTP client not configured"},
            )

        url = request.url or self._api_config.endpoint_url
        override_params: dict[str, str] = {}
        if isinstance(request.parameters.get("params"), dict):
            override_params = request.parameters["params"]

        log.debug("Fetching API: %s", url)

        try:
            pagination = self._api_config.pagination
            all_items: list[dict[str, Any]] = []
            page_index = 0
            current_url = url
            next_url: str | None = url
            current_params = {**self._build_request_params(), **override_params}

            while next_url is not None:
                headers = self._build_headers(request)
                timeout = self._resolve_timeout(request)

                response = self._http.request(
                    self._build_http_request(
                        method=self._api_config.method,
                        url=next_url if next_url and next_url != current_url else current_url,
                        headers=headers,
                        params=current_params if not (next_url and next_url != current_url) else {},
                        timeout=timeout,
                    )
                )

                self._validate_mime_type(response.content_type)

                body = response.body
                if not body:
                    raise ApiParseError("Empty response body")

                self._check_status(response.status_code, url)

                data = self._decode_response(body)

                page_items = _extract_items(data, self._api_config.field_mapping.items_path)
                all_items.extend(page_items)

                if pagination:
                    next_url = self._resolve_next_page_url(data, pagination, page_index)
                    if next_url:
                        current_params = {}
                        page_index += 1
                    else:
                        next_url = None
                else:
                    next_url = None

            documents = [
                self._parser._item_to_doc(item, url, self._authority.id) for item in all_items
            ]

            log.debug(
                "Fetched API %s (%d bytes, %dms, %d documents, %d pages)",
                url,
                response.response_size or len(body),
                response.elapsed_ms,
                len(documents),
                page_index + 1,
            )

            return FetchResult(
                success=True,
                data=_document_list_json(documents),
                content_type=response.content_type,
                size_bytes=response.response_size or len(body),
                fetched_at=datetime.utcnow(),
                metadata={
                    "document_count": len(documents),
                    "page_count": page_index + 1,
                    "elapsed_ms": response.elapsed_ms,
                },
            )

        except UnsupportedContentTypeError:
            raise
        except ApiError:
            raise
        except HttpError:
            raise
        except Exception as e:
            raise ApiParseError(f"Unexpected error fetching API {url}: {e}") from e

    def close(self) -> None:
        self._initialized = False
        self._started_at = None
        log.debug("APIConnector closed for authority: %s", self._authority.id)

    def fetch_documents(self, request: FetchRequest) -> list[Document]:
        """High-level method returning parsed Documents directly."""
        try:
            result = self.fetch(request)
        except (ApiError, HttpError) as e:
            raise ApiParseError(f"Failed to fetch API: {e}") from e
        if not result.success:
            raise ApiParseError(
                f"Failed to fetch API: {result.metadata.get('error', 'unknown error')}"
            )
        data = result.data
        if not data:
            raise ApiParseError("No data returned from API fetch")
        return _document_list_parse(data)

    def _build_request_params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        for key, val in self._api_config.filter_params.items():
            if val:
                params[key] = val
        return params

    def _build_headers(self, request: FetchRequest) -> dict[str, str]:
        headers = dict(self._api_config.headers)
        if isinstance(request.parameters.get("headers"), dict):
            headers.update(request.parameters["headers"])
        return headers

    def _resolve_timeout(self, request: FetchRequest) -> float | None:
        if isinstance(request.parameters.get("timeout"), (int, float)):
            return cast(float, request.parameters["timeout"])
        return self._api_config.timeout

    def _check_status(self, status_code: int, url: str) -> None:
        if status_code == 401 or status_code == 403:
            raise ApiAuthenticationError(f"Authentication failed for {url} (HTTP {status_code})")
        if status_code == 429:
            raise ApiRateLimitedError(f"Rate limited by API at {url}")
        if 500 <= status_code < 600:
            raise ApiServerError(f"Server error from {url} (HTTP {status_code})")

    def _decode_response(self, body: bytes) -> Any:
        try:
            text = body.decode("utf-8", errors="replace").strip()
            return json.loads(text) if text else {}
        except json.JSONDecodeError as e:
            raise ApiParseError(f"Invalid JSON in response: {e}") from e

    def _resolve_next_page_url(
        self,
        data: Any,
        strategy: ApiPaginationStrategy,
        page_index: int,
    ) -> str | None:
        if isinstance(strategy, ApiPaginationPageNumber):
            if page_index == 0:
                return None
            return None
        if isinstance(strategy, ApiPaginationCursor):
            cursor = _resolve_next_page(data, strategy)
            if cursor is not None:
                base = self._api_config.endpoint_url
                param = strategy.cursor_param
                return f"{base}?{param}={cursor}"
            return None
        if isinstance(strategy, ApiPaginationNextLink):
            return _resolve_next_page(data, strategy)
        return None

    def _resolve_pagination_type(self) -> str | None:
        pagination = self._api_config.pagination
        if pagination is None:
            return None
        return pagination.type

    @staticmethod
    def _build_http_request(
        method: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, str],
        timeout: float | None,
    ) -> Any:
        from src.connectors.http.models import Request

        return Request(
            url=url,
            method=HttpMethod(method.upper()),
            headers=headers,
            params={k: v for k, v in params.items() if v is not None},
            timeout_override=timeout,
        )

    @staticmethod
    def _validate_mime_type(content_type: str) -> None:
        base_type = content_type.split(";")[0].strip().lower()
        if base_type and base_type not in _SUPPORTED_MIME_TYPES:
            raise UnsupportedContentTypeError(
                f"Unsupported content type: {content_type} "
                f"(supported: {', '.join(sorted(_SUPPORTED_MIME_TYPES))})"
            )


def _document_list_json(documents: list[Document]) -> str:
    from pydantic import TypeAdapter

    adapter = TypeAdapter(list[Document])
    return adapter.dump_json(documents).decode("utf-8")


def _document_list_parse(data: str) -> list[Document]:
    from pydantic import TypeAdapter

    adapter = TypeAdapter(list[Document])
    return adapter.validate_json(data)
