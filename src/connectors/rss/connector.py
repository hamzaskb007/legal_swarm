from __future__ import annotations

import logging
from datetime import datetime

from pydantic import TypeAdapter

from src.authority.models import Authority, CapabilityType, ParserType
from src.connectors.base import Connector
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
from src.connectors.rss.exceptions import (
    EmptyFeedError,
    RssError,
    RssParseError,
    UnsupportedContentTypeError,
)
from src.connectors.rss.parser import RSSParser

_document_list_adapter = TypeAdapter(list[Document])

log = logging.getLogger(__name__)

_SUPPORTED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/rss+xml",
        "application/atom+xml",
        "application/xml",
        "text/xml",
    }
)


class RSSConnector(Connector):
    """Retrieves and parses RSS 2.0 and Atom feeds from authorities.

    Uses the shared HTTP infrastructure for all networking.
    Delegates all parsing to RSSParser (which is independently testable).
    """

    def __init__(
        self,
        authority: Authority,
        http_client: HttpClient | None = None,
        parser: RSSParser | None = None,
    ) -> None:
        super().__init__(authority)
        self._http = http_client
        self._parser = parser or RSSParser()
        self._started_at: datetime | None = None

    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="RSSConnector",
            version="1.0.0",
            description="Retrieves RSS 2.0 and Atom feeds from authorities",
            parser_types=[ParserType.RSS],
            capabilities=[CapabilityType.RSS],
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            parser_types=frozenset({ParserType.RSS}),
            capability_types=frozenset({CapabilityType.RSS}),
            supports_streaming=True,
        )

    def connect(self) -> ConnectionResult:
        self._initialized = True
        self._started_at = datetime.utcnow()
        log.debug("RSSConnector initialized for authority: %s", self._authority.id)
        return ConnectionResult(
            success=True,
            status=ConnectionStatus.CONNECTED,
            message="RSS connector initialized",
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
            capabilities=[CapabilityType.RSS],
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

        log.debug("Fetching feed: %s", request.url)

        try:
            response = self._http.get(
                url=request.url,
                headers=(
                    request.parameters.get("headers")
                    if isinstance(request.parameters.get("headers"), dict)
                    else None
                ),
                timeout=(
                    request.parameters.get("timeout")
                    if isinstance(request.parameters.get("timeout"), (int, float))
                    else None
                ),
            )

            self._validate_mime_type(response.content_type)

            xml = response.text
            documents = self._parser.parse(
                xml_content=xml,
                source_url=request.url,
                authority_id=self._authority.id,
            )

            log.debug(
                "Fetched feed %s (%d bytes, %dms, %d entries)",
                request.url,
                response.response_size or len(response.body),
                response.elapsed_ms,
                len(documents),
            )

            return FetchResult(
                success=True,
                data=_document_list_adapter.dump_json(documents).decode("utf-8"),
                content_type=response.content_type,
                size_bytes=response.response_size or len(response.body),
                fetched_at=datetime.utcnow(),
                metadata={
                    "entry_count": len(documents),
                    "elapsed_ms": response.elapsed_ms,
                    "feed_type": "rss",
                },
            )

        except UnsupportedContentTypeError:
            raise
        except RssError:
            raise
        except HttpError:
            raise
        except Exception as e:
            raise RssParseError(f"Unexpected error fetching feed {request.url}: {e}") from e

    def close(self) -> None:
        self._initialized = False
        self._started_at = None
        log.debug("RSSConnector closed for authority: %s", self._authority.id)

    def fetch_documents(self, request: FetchRequest) -> list[Document]:
        """High-level method returning parsed Documents directly."""
        try:
            result = self.fetch(request)
        except RssError as e:
            raise RssParseError(f"Failed to fetch feed: {e}") from e
        if not result.success:
            raise RssParseError(
                f"Failed to fetch feed: {result.metadata.get('error', 'unknown error')}"
            )
        data = result.data
        if not data:
            raise EmptyFeedError("No data returned from feed")
        docs = _document_list_adapter.validate_json(data)
        return docs

    @staticmethod
    def _validate_mime_type(content_type: str) -> None:
        base_type = content_type.split(";")[0].strip().lower()
        if base_type and base_type not in _SUPPORTED_MIME_TYPES:
            raise UnsupportedContentTypeError(
                f"Unsupported content type: {content_type} "
                f"(supported: {', '.join(sorted(_SUPPORTED_MIME_TYPES))})"
            )
