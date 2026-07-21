from __future__ import annotations

import logging
from datetime import datetime

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
from src.connectors.pdf.exceptions import (
    PdfError,
    PdfParseError,
    UnsupportedContentTypeError,
)
from src.connectors.pdf.parser import PDFParser

log = logging.getLogger(__name__)

_SUPPORTED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
    }
)


class PDFConnector(Connector):
    """Retrieves text and metadata from PDF documents hosted by authorities.

    Uses the shared HTTP infrastructure for all networking.
    Delegates all parsing to PDFParser (which is independently testable).
    """

    def __init__(
        self,
        authority: Authority,
        http_client: HttpClient | None = None,
        parser: PDFParser | None = None,
    ) -> None:
        super().__init__(authority)
        self._http = http_client
        self._parser = parser or PDFParser()
        self._started_at: datetime | None = None

    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="PDFConnector",
            version="1.0.0",
            description="Retrieves text and metadata from PDF documents",
            parser_types=[ParserType.PDF],
            capabilities=[CapabilityType.PDF],
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            parser_types=frozenset({ParserType.PDF}),
            capability_types=frozenset({CapabilityType.PDF}),
            supports_search=False,
            supports_streaming=False,
        )

    def connect(self) -> ConnectionResult:
        self._initialized = True
        self._started_at = datetime.utcnow()
        log.debug("PDFConnector initialized for authority: %s", self._authority.id)
        return ConnectionResult(
            success=True,
            status=ConnectionStatus.CONNECTED,
            message="PDF connector initialized",
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
            capabilities=[CapabilityType.PDF],
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

        log.debug("Fetching PDF: %s", request.url)

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

            body = response.body
            if not body:
                raise PdfParseError("Empty response body")

            doc = self._parser.parse(
                pdf_content=body,
                source_url=request.url,
                authority_id=self._authority.id,
            )

            log.debug(
                "Fetched PDF %s (%d bytes, %dms, %d pages)",
                request.url,
                response.response_size or len(body),
                response.elapsed_ms,
                doc.metadata.get("page_count", "?"),
            )

            return FetchResult(
                success=True,
                data=doc.model_dump_json(),
                content_type=response.content_type,
                size_bytes=response.response_size or len(body),
                fetched_at=datetime.utcnow(),
                metadata={
                    "title": doc.title,
                    "page_count": doc.metadata.get("page_count"),
                    "elapsed_ms": response.elapsed_ms,
                },
            )

        except UnsupportedContentTypeError:
            raise
        except PdfError:
            raise
        except HttpError:
            raise
        except Exception as e:
            raise PdfParseError(f"Unexpected error fetching PDF {request.url}: {e}") from e

    def close(self) -> None:
        self._initialized = False
        self._started_at = None
        log.debug("PDFConnector closed for authority: %s", self._authority.id)

    def fetch_document(self, request: FetchRequest) -> Document:
        """High-level method returning a parsed Document directly."""
        try:
            result = self.fetch(request)
        except PdfError as e:
            raise PdfParseError(f"Failed to fetch PDF: {e}") from e
        if not result.success:
            raise PdfParseError(
                f"Failed to fetch PDF: {result.metadata.get('error', 'unknown error')}"
            )
        data = result.data
        if not data:
            raise PdfParseError("No data returned from PDF fetch")
        doc = Document.model_validate_json(data)
        return doc

    @staticmethod
    def _validate_mime_type(content_type: str) -> None:
        base_type = content_type.split(";")[0].strip().lower()
        if base_type and base_type not in _SUPPORTED_MIME_TYPES:
            raise UnsupportedContentTypeError(
                f"Unsupported content type: {content_type} "
                f"(supported: {', '.join(sorted(_SUPPORTED_MIME_TYPES))})"
            )
