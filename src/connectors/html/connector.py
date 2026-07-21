from __future__ import annotations

import logging
from datetime import datetime

from src.authority.models import Authority, CapabilityType, ParserType
from src.connectors.base import Connector
from src.connectors.html.exceptions import (
    EmptyContentError,
    HtmlError,
    HtmlParseError,
    UnsupportedContentTypeError,
)
from src.connectors.html.parser import HtmlParser
from src.connectors.http.client import HttpClient
from src.connectors.http.exceptions import HttpError
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
        "text/html",
        "application/xhtml+xml",
    }
)


class HTMLConnector(Connector):
    """Retrieves regulatory content from authority websites."""

    def __init__(
        self,
        authority: Authority,
        http_client: HttpClient | None = None,
    ) -> None:
        super().__init__(authority)
        self._http = http_client
        self._parser = HtmlParser()
        self._started_at: datetime | None = None

    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="HTMLConnector",
            version="1.0.0",
            description="Retrieves HTML content from authority websites",
            parser_types=[ParserType.HTML],
            capabilities=[CapabilityType.HTML, CapabilityType.SEARCH],
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            parser_types=frozenset({ParserType.HTML}),
            capability_types=frozenset({CapabilityType.HTML, CapabilityType.SEARCH}),
            supports_search=True,
        )

    def connect(self) -> ConnectionResult:
        self._initialized = True
        self._started_at = datetime.utcnow()
        log.debug("HTMLConnector initialized for authority: %s", self._authority.id)
        return ConnectionResult(
            success=True,
            status=ConnectionStatus.CONNECTED,
            message="HTML connector initialized",
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
            capabilities=[CapabilityType.HTML, CapabilityType.SEARCH],
            version="1.0.0",
            last_health_check=datetime.utcnow(),
            details={
                "http_configured": self._http is not None,
            },
        )

    def fetch(self, request: FetchRequest) -> FetchResult:
        if not self._http:
            return FetchResult(
                success=False,
                metadata={"error": "HTTP client not configured"},
            )

        log.debug("Fetching URL: %s", request.url)

        try:
            response = self._http.get(
                url=request.url,
                headers=request.parameters.get("headers")
                if isinstance(request.parameters.get("headers"), dict)
                else None,
                timeout=request.parameters.get("timeout")
                if isinstance(request.parameters.get("timeout"), (int, float))
                else None,
            )

            self._validate_mime_type(response.content_type)

            html = response.text

            if not html.strip():
                raise EmptyContentError(f"Empty page content from {request.url}")

            doc = self._parser.parse(html, request.url, response.content_type)

            log.debug(
                "Fetched %s (%d bytes, %dms, title=%s)",
                request.url,
                response.response_size or len(response.body),
                response.elapsed_ms,
                doc.title,
            )

            return FetchResult(
                success=True,
                data=doc.model_dump_json(),
                content_type=response.content_type,
                size_bytes=response.response_size or len(response.body),
                fetched_at=datetime.utcnow(),
                metadata={
                    "title": doc.title,
                    "canonical_url": doc.canonical_url,
                    "language": doc.language,
                    "links": doc.discovered_links,
                    "elapsed_ms": response.elapsed_ms,
                },
            )

        except UnsupportedContentTypeError:
            raise
        except EmptyContentError:
            raise
        except HtmlParseError:
            raise
        except HttpError:
            raise
        except Exception as e:
            raise HtmlParseError(f"Unexpected error fetching {request.url}: {e}") from e

    def close(self) -> None:
        self._initialized = False
        self._started_at = None
        log.debug("HTMLConnector closed for authority: %s", self._authority.id)

    def fetch_document(self, request: FetchRequest) -> Document:
        """High-level method returning a parsed Document directly."""
        try:
            result = self.fetch(request)
        except HtmlError as e:
            raise HtmlParseError(f"Failed to fetch document: {e}") from e
        if not result.success:
            raise HtmlParseError(
                f"Failed to fetch document: {result.metadata.get('error', 'unknown error')}"
            )
        doc = Document.model_validate_json(result.data)
        return doc

    @staticmethod
    def _validate_mime_type(content_type: str) -> None:
        base_type = content_type.split(";")[0].strip().lower()
        if base_type and base_type not in _SUPPORTED_MIME_TYPES:
            raise UnsupportedContentTypeError(
                f"Unsupported content type: {content_type} "
                f"(supported: {', '.join(sorted(_SUPPORTED_MIME_TYPES))})"
            )
