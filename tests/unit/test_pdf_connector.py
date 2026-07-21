"""Unit tests for the PDF Connector."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from src.authority.models import (
    Authority,
    AuthorityLevel,
    CapabilityType,
    ParserType,
)
from src.connectors.exceptions import ConnectorError
from src.connectors.http.exceptions import ConnectionError as HttpConnectionError
from src.connectors.http.exceptions import TimeoutError as HttpTimeoutError
from src.connectors.http.models import Response
from src.connectors.models import (
    ConnectionStatus,
    Document,
    FetchRequest,
)
from src.connectors.pdf.connector import PDFConnector, _SUPPORTED_MIME_TYPES
from src.connectors.pdf.exceptions import (
    PdfCorruptedError,
    PdfEmptyError,
    PdfEncryptedError,
    PdfError,
    PdfParseError,
    PdfTooLargeError,
    PdfTooManyPagesError,
    UnsupportedContentTypeError,
)
from src.connectors.pdf.parser import (
    PdfConfig,
    PDFParser,
    _parse_pdf_date,
)

# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def authority() -> Authority:
    return Authority(
        id="test_pdf",
        jurisdiction="xx",
        level=AuthorityLevel.LEVEL_1,
        name="Test PDF Authority",
        authority_type="regulator",
    )


# ===================================================================
# Sample PDF generation helpers
# ===================================================================


def _create_sample_pdf(
    *,
    title: str = "Test PDF Document",
    author: str = "Test Author",
    subject: str = "Test Subject",
    creator: str = "Test Creator",
    producer: str = "Test Producer",
    text: str = "This is a sample paragraph for testing the PDF connector.",
    pages: int = 1,
) -> bytes:
    import fitz

    doc = fitz.Document()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1} Heading", fontsize=14)
        page.insert_text((72, 108), f"{text} (Page {i + 1})", fontsize=11)

    doc.set_metadata(
        {
            "title": title,
            "author": author,
            "subject": subject,
            "creator": creator,
            "producer": producer,
            "creationDate": "D:20240101120000+00'00'",
            "modDate": "D:20240115120000Z",
        }
    )

    buf = io.BytesIO()
    doc.save(buf)
    result = buf.getvalue()
    doc.close()
    return result


def _create_multi_page_pdf(pages: int = 3) -> bytes:
    return _create_sample_pdf(
        title="Multi-Page Document",
        text="Multi-page content for testing.",
        pages=pages,
    )


def _create_pdf_no_metadata() -> bytes:
    import fitz

    doc = fitz.Document()
    page = doc.new_page()
    page.insert_text((72, 72), "No metadata here", fontsize=11)

    buf = io.BytesIO()
    doc.save(buf)
    result = buf.getvalue()
    doc.close()
    return result


def _create_encrypted_pdf() -> bytes:
    import fitz

    doc = fitz.Document()
    page = doc.new_page()
    page.insert_text((72, 72), "Encrypted PDF content", fontsize=11)

    buf = io.BytesIO()
    doc.save(buf, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="password", owner_pw="owner")
    result = buf.getvalue()
    doc.close()
    return result


def _create_corrupted_pdf() -> bytes:
    return b"%PDF-1.4\n% This is corrupted\xff\xfe\x00\x01\x00\x02"


_SAMPLE_PDF = _create_sample_pdf()
_SAMPLE_PDF_NO_META = _create_pdf_no_metadata()
_SAMPLE_PDF_MULTI_PAGE = _create_multi_page_pdf()
_SAMPLE_PDF_ENCRYPTED = _create_encrypted_pdf()
_SAMPLE_PDF_CORRUPTED = _create_corrupted_pdf()


# ===================================================================
# PDF date parsing
# ===================================================================


class TestPdfDateParsing:
    def test_parse_date_valid_with_offset(self) -> None:
        dt = _parse_pdf_date("D:20240101120000+00'00'")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12

    def test_parse_date_valid_utc(self) -> None:
        dt = _parse_pdf_date("D:20240115120000Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1

    def test_parse_date_none(self) -> None:
        assert _parse_pdf_date(None) is None

    def test_parse_date_empty(self) -> None:
        assert _parse_pdf_date("") is None

    def test_parse_date_invalid(self) -> None:
        assert _parse_pdf_date("not a date") is None


# ===================================================================
# PDFParser
# ===================================================================


class TestPDFParser:
    def test_parse_valid_pdf(self) -> None:
        parser = PDFParser()
        doc = parser.parse(_SAMPLE_PDF, "https://regulator.gov/doc.pdf", "test_pdf")
        assert doc.authority_id == "test_pdf"
        assert doc.source_url == "https://regulator.gov/doc.pdf"
        assert doc.title == "Test PDF Document"
        assert doc.summary == "Test Subject"
        assert doc.content_type == "application/pdf"
        assert doc.document_type == "regulatory_document"
        assert "sample paragraph" in doc.content
        assert doc.publication_date is not None
        assert doc.last_modified is not None
        assert doc.metadata["author"] == "Test Author"
        assert doc.metadata["subject"] == "Test Subject"
        assert doc.metadata["creator"] == "Test Creator"
        assert doc.metadata["producer"] == "Test Producer"
        assert doc.metadata["page_count"] == 1

    def test_parse_no_metadata(self) -> None:
        parser = PDFParser()
        doc = parser.parse(_SAMPLE_PDF_NO_META, "https://regulator.gov/nom.pdf", "test_pdf")
        assert doc.title is None
        assert doc.summary is None
        assert doc.publication_date is None
        assert doc.last_modified is None
        assert doc.metadata.get("author") is None
        assert doc.metadata.get("creator") is None
        assert doc.metadata.get("page_count") == 1

    def test_multi_page_pdf(self) -> None:
        parser = PDFParser()
        doc = parser.parse(_SAMPLE_PDF_MULTI_PAGE, "https://regulator.gov/multi.pdf", "test_pdf")
        assert doc.metadata["page_count"] == 3
        assert "Page 1" in doc.content
        assert "Page 2" in doc.content
        assert "Page 3" in doc.content

    def test_encrypted_pdf_raises(self) -> None:
        parser = PDFParser()
        with pytest.raises(PdfEncryptedError):
            parser.parse(_SAMPLE_PDF_ENCRYPTED, "https://regulator.gov/enc.pdf", "test_pdf")

    def test_corrupted_pdf_raises(self) -> None:
        parser = PDFParser()
        with pytest.raises(PdfCorruptedError):
            parser.parse(_SAMPLE_PDF_CORRUPTED, "https://regulator.gov/corrupt.pdf", "test_pdf")

    def test_empty_pdf_raises(self) -> None:
        import fitz

        parser = PDFParser()
        mock_doc = MagicMock(spec=fitz.Document)
        mock_doc.is_encrypted = False
        mock_doc.needs_pass = False
        mock_doc.page_count = 0
        mock_doc.metadata = {}
        with patch("fitz.open", return_value=mock_doc):
            with pytest.raises(PdfEmptyError, match="no pages"):
                parser.parse(_SAMPLE_PDF, "https://regulator.gov/empty.pdf", "test_pdf")

    def test_empty_bytes_raises(self) -> None:
        parser = PDFParser()
        with pytest.raises(PdfEmptyError, match="Empty"):
            parser.parse(b"", "https://regulator.gov/empty.pdf", "test_pdf")

    def test_too_large_raises(self) -> None:
        config = PdfConfig(max_pdf_size=10)
        parser = PDFParser(config)
        with pytest.raises(PdfTooLargeError):
            parser.parse(_SAMPLE_PDF, "https://regulator.gov/large.pdf", "test_pdf")

    def test_too_many_pages_raises(self) -> None:
        config = PdfConfig(max_pages=1)
        parser = PDFParser(config)
        with pytest.raises(PdfTooManyPagesError):
            parser.parse(_SAMPLE_PDF_MULTI_PAGE, "https://regulator.gov/multipage.pdf", "test_pdf")

    def test_max_text_length_respected(self) -> None:
        config = PdfConfig(max_text_length=10)
        parser = PDFParser(config)
        doc = parser.parse(_SAMPLE_PDF, "https://regulator.gov/doc.pdf", "test_pdf")
        assert len(doc.content) <= 50

    def test_content_type_support(self) -> None:
        assert PDFParser.is_supported_content_type("application/pdf")
        assert PDFParser.is_supported_content_type("application/pdf; charset=utf-8")
        assert not PDFParser.is_supported_content_type("text/html")
        assert not PDFParser.is_supported_content_type("")
        assert not PDFParser.is_supported_content_type("application/rss+xml")


# ===================================================================
# Document conversion
# ===================================================================


class TestPdfDocumentConversion:
    def test_document_frozen(self) -> None:
        parser = PDFParser()
        doc = parser.parse(_SAMPLE_PDF, "https://regulator.gov/doc.pdf", "test_pdf")
        with pytest.raises(Exception):
            setattr(doc, "title", "Changed")

    def test_document_has_uuid(self) -> None:
        parser = PDFParser()
        doc = parser.parse(_SAMPLE_PDF, "https://regulator.gov/doc.pdf", "test_pdf")
        assert isinstance(doc.id, UUID)

    def test_serialization_roundtrip(self) -> None:
        parser = PDFParser()
        doc = parser.parse(_SAMPLE_PDF, "https://regulator.gov/doc.pdf", "test_pdf")
        json_data = doc.model_dump_json()
        restored = Document.model_validate_json(json_data)
        assert restored.title == doc.title
        assert restored.content == doc.content
        assert restored.authority_id == doc.authority_id


# ===================================================================
# PDFConnector — Base
# ===================================================================


class TestPDFConnectorBase:
    def test_metadata(self) -> None:
        meta = PDFConnector.metadata()
        assert meta.name == "PDFConnector"
        assert meta.version == "1.0.0"
        assert ParserType.PDF in meta.parser_types
        assert CapabilityType.PDF in meta.capabilities

    def test_capabilities(self) -> None:
        caps = PDFConnector.capabilities()
        assert ParserType.PDF in caps.parser_types
        assert CapabilityType.PDF in caps.capability_types
        assert caps.supports_search is False
        assert caps.supports_streaming is False

    def test_connect(self, authority: Authority) -> None:
        connector = PDFConnector(authority)
        result = connector.connect()
        assert result.success is True
        assert result.status == ConnectionStatus.CONNECTED
        assert connector._initialized is True

    def test_close(self, authority: Authority) -> None:
        connector = PDFConnector(authority)
        connector.connect()
        connector.close()
        assert connector._initialized is False

    def test_health_before_connect(self, authority: Authority) -> None:
        connector = PDFConnector(authority)
        health = connector.health()
        assert health.initialized is False
        assert health.status == ConnectionStatus.INITIALIZED

    def test_health_after_connect(self, authority: Authority) -> None:
        connector = PDFConnector(authority)
        connector.connect()
        health = connector.health()
        assert health.initialized is True
        assert health.status == ConnectionStatus.CONNECTED
        assert health.parser_supported is True
        assert CapabilityType.PDF in health.capabilities

    def test_health_no_http(self, authority: Authority) -> None:
        connector = PDFConnector(authority)
        health = connector.health()
        assert health.available is False
        assert health.details["http_configured"] is False


# ===================================================================
# PDFConnector — Fetch
# ===================================================================


class TestPDFConnectorFetch:
    def test_fetch_without_http_returns_error(self, authority: Authority) -> None:
        connector = PDFConnector(authority)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://regulator.gov/doc.pdf"))
        assert result.success is False
        assert "HTTP client not configured" in result.metadata.get("error", "")

    def test_fetch_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=_SAMPLE_PDF,
            content_type="application/pdf",
            encoding="utf-8",
            elapsed_ms=300,
            response_size=len(_SAMPLE_PDF),
        )

        connector = PDFConnector(authority, http_client=mock_http)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://regulator.gov/doc.pdf"))

        assert result.success is True
        assert result.content_type == "application/pdf"
        assert result.size_bytes == len(_SAMPLE_PDF)
        assert result.metadata["title"] == "Test PDF Document"
        assert result.metadata["page_count"] == 1
        assert result.metadata["elapsed_ms"] == 300

    def test_fetch_unsupported_mime_type(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=b"{}",
            content_type="application/json",
            encoding="utf-8",
        )

        connector = PDFConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(UnsupportedContentTypeError, match="application/json"):
            connector.fetch(FetchRequest(url="https://regulator.gov/data.json"))

    def test_fetch_empty_body(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=b"",
            content_type="application/pdf",
            encoding="utf-8",
        )

        connector = PDFConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(PdfParseError, match="Empty"):
            connector.fetch(FetchRequest(url="https://regulator.gov/empty.pdf"))

    def test_fetch_propagates_http_error(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpConnectionError("Connection refused")

        connector = PDFConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(HttpConnectionError, match="Connection refused"):
            connector.fetch(FetchRequest(url="https://regulator.gov/doc.pdf"))

    def test_fetch_propagates_timeout(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpTimeoutError("Request timed out")

        connector = PDFConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(HttpTimeoutError, match="timed out"):
            connector.fetch(FetchRequest(url="https://regulator.gov/doc.pdf"))


# ===================================================================
# PDFConnector — Fetch Document
# ===================================================================


class TestPDFConnectorFetchDocument:
    def test_fetch_document_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=_SAMPLE_PDF,
            content_type="application/pdf",
            encoding="utf-8",
            elapsed_ms=250,
            response_size=len(_SAMPLE_PDF),
        )

        connector = PDFConnector(authority, http_client=mock_http)
        connector.connect()
        doc = connector.fetch_document(FetchRequest(url="https://regulator.gov/doc.pdf"))

        assert isinstance(doc, Document)
        assert doc.title == "Test PDF Document"
        assert doc.content_type == "application/pdf"
        assert doc.source_url == "https://regulator.gov/doc.pdf"
        assert doc.authority_id == "test_pdf"
        assert "sample paragraph" in doc.content

    def test_fetch_document_failure_raises(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=_SAMPLE_PDF_ENCRYPTED,
            content_type="application/pdf",
            encoding="utf-8",
        )

        connector = PDFConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(PdfParseError):
            connector.fetch_document(FetchRequest(url="https://regulator.gov/enc.pdf"))


# ===================================================================
# MIME validation
# ===================================================================


class TestPDFConnectorMimeValidation:
    def test_supported_mime_types(self) -> None:
        assert "application/pdf" in _SUPPORTED_MIME_TYPES

    def test_validate_mime_type_pdf(self) -> None:
        PDFConnector._validate_mime_type("application/pdf")

    def test_validate_mime_type_with_charset(self) -> None:
        PDFConnector._validate_mime_type("application/pdf; charset=utf-8")

    def test_validate_mime_type_rejects_html(self) -> None:
        with pytest.raises(UnsupportedContentTypeError, match="text/html"):
            PDFConnector._validate_mime_type("text/html")

    def test_validate_mime_type_rejects_json(self) -> None:
        with pytest.raises(UnsupportedContentTypeError):
            PDFConnector._validate_mime_type("application/json")

    def test_validate_mime_type_empty_string_allowed(self) -> None:
        PDFConnector._validate_mime_type("")


# ===================================================================
# Exception hierarchy
# ===================================================================


class TestPdfExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(PdfParseError, PdfError)
        assert issubclass(PdfCorruptedError, PdfError)
        assert issubclass(PdfEncryptedError, PdfError)
        assert issubclass(PdfEmptyError, PdfError)
        assert issubclass(PdfTooLargeError, PdfError)
        assert issubclass(PdfTooManyPagesError, PdfError)
        assert issubclass(UnsupportedContentTypeError, PdfError)

    def test_pdf_error_is_connector_error(self) -> None:
        assert issubclass(PdfError, ConnectorError)

    def test_pdf_parse_error_message(self) -> None:
        err = PdfParseError("custom parse error")
        assert str(err) == "custom parse error"


# ===================================================================
# PdfConfig
# ===================================================================


class TestPdfConfig:
    def test_defaults(self) -> None:
        config = PdfConfig()
        assert config.max_pdf_size == 50 * 1024 * 1024
        assert config.max_pages == 500
        assert config.max_text_length == 500 * 1024

    def test_custom_values(self) -> None:
        config = PdfConfig(max_pdf_size=1000, max_pages=10, max_text_length=500)
        assert config.max_pdf_size == 1000
        assert config.max_pages == 10
        assert config.max_text_length == 500

    def test_frozen(self) -> None:
        config = PdfConfig()
        with pytest.raises(Exception):
            config.max_pages = 100  # type: ignore[misc]
