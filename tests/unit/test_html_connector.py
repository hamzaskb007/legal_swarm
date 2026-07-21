from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.authority.models import (
    Authority,
    AuthorityLevel,
    CapabilityType,
    ParserType,
)
from src.connectors.html.connector import HTMLConnector, _SUPPORTED_MIME_TYPES
from src.connectors.html.exceptions import (
    EmptyContentError,
    ExtractionError,
    HtmlError,
    HtmlParseError,
    UnsupportedContentTypeError,
)
from src.connectors.html.parser import HtmlContentExtractor, HtmlMetadataExtractor, HtmlParser
from src.connectors.http.exceptions import ConnectionError as HttpConnectionError
from src.connectors.http.models import Response
from src.connectors.models import (
    ConnectionStatus,
    Document,
    FetchRequest,
)

# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def authority() -> Authority:
    return Authority(
        id="test_fi",
        jurisdiction="fi",
        level=AuthorityLevel.LEVEL_1,
        name="Test Financial Authority",
        authority_type="regulator",
    )


_SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>Test Regulation Page</title>
  <meta name="description" content="Official test regulation guidance">
  <meta name="keywords" content="regulation, test, compliance">
  <meta name="date" content="2024-06-15">
  <link rel="canonical" href="https://example.gov/regulation">
</head>
<body>
  <nav>
    <a href="/home">Home</a>
    <a href="/contact">Contact</a>
  </nav>
  <header>
    <h1>Site Header</h1>
  </header>
  <main>
    <article>
      <h1>Regulation Title</h1>
      <p>This is the main regulatory content paragraph.</p>
      <p>Second paragraph with more details.</p>
      <ul>
        <li>Requirement one: must comply</li>
        <li>Requirement two: file annually</li>
      </ul>
      <a href="/regulation-pdf">Download full regulation</a>
    </article>
  </main>
  <footer>
    <p>Copyright notice - should be excluded from content</p>
  </footer>
  <script>alert("noise")</script>
  <style>.hidden{display:none}</style>
</body>
</html>"""

_SAMPLE_HTML_WITH_OG = """<html>
<head>
  <title>OG Article</title>
  <meta property="article:published_time" content="2024-01-10T08:00:00Z">
</head>
<body><article><p>Content</p></article></body>
</html>"""


# ===================================================================
# HtmlContentExtractor
# ===================================================================


class TestHtmlContentExtractor:
    def test_extract_basic_content(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed(_SAMPLE_HTML)
        text = extractor.get_text()
        assert "This is the main regulatory content paragraph." in text
        assert "Second paragraph with more details." in text
        assert "Regulation Title" in text

    def test_strips_excluded_tags(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed(_SAMPLE_HTML)
        text = extractor.get_text()
        assert "alert" not in text
        assert "noise" not in text
        assert ".hidden" not in text
        assert "Copyright notice" not in text

    def test_strips_nav_header_footer(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed(_SAMPLE_HTML)
        text = extractor.get_text()
        assert "Home" not in text
        assert "Contact" not in text
        assert "Site Header" not in text

    def test_empty_html(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed("")
        assert extractor.get_text() == ""

    def test_whitespace_normalization(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed("<p>Hello    World</p>")
        assert "Hello World" in extractor.get_text()

    def test_multiple_newlines_collapsed(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed("<p>A</p><p>B</p><p>C</p>")
        text = extractor.get_text()
        assert "\n\n" not in text

    def test_reset(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed("<p>First</p>")
        assert "First" in extractor.get_text()
        extractor.reset()
        assert extractor.get_text() == ""

    def test_nested_excluded(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed("<div><script>if (a < b) {}</script></div><p>visible</p>")
        text = extractor.get_text()
        assert "visible" in text

    def test_heading_extraction(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed("<h1>Title</h1><h2>Subtitle</h2>")
        text = extractor.get_text()
        assert "Title" in text
        assert "Subtitle" in text

    def test_list_item_extraction(self) -> None:
        extractor = HtmlContentExtractor()
        extractor.feed("<ul><li>Item A</li><li>Item B</li></ul>")
        text = extractor.get_text()
        assert "Item A" in text
        assert "Item B" in text


# ===================================================================
# HtmlMetadataExtractor
# ===================================================================


class TestHtmlMetadataExtractor:
    def test_extract_title(self) -> None:
        assert HtmlMetadataExtractor.extract_title(_SAMPLE_HTML) == "Test Regulation Page"

    def test_extract_title_no_title(self) -> None:
        assert HtmlMetadataExtractor.extract_title("<html></html>") is None

    def test_extract_canonical_url(self) -> None:
        assert (
            HtmlMetadataExtractor.extract_canonical_url(_SAMPLE_HTML)
            == "https://example.gov/regulation"
        )

    def test_extract_canonical_url_none(self) -> None:
        assert HtmlMetadataExtractor.extract_canonical_url("<html></html>") is None

    def test_extract_meta_description(self) -> None:
        assert (
            HtmlMetadataExtractor.extract_description(_SAMPLE_HTML)
            == "Official test regulation guidance"
        )

    def test_extract_meta_keywords(self) -> None:
        assert (
            HtmlMetadataExtractor.extract_keywords(_SAMPLE_HTML) == "regulation, test, compliance"
        )

    def test_extract_language(self) -> None:
        assert HtmlMetadataExtractor.extract_language(_SAMPLE_HTML) == "en"

    def test_extract_language_none(self) -> None:
        assert HtmlMetadataExtractor.extract_language("<html></html>") is None

    def test_extract_publication_date_meta(self) -> None:
        assert HtmlMetadataExtractor.extract_publication_date(_SAMPLE_HTML) == "2024-06-15"

    def test_extract_publication_date_og(self) -> None:
        assert (
            HtmlMetadataExtractor.extract_publication_date(_SAMPLE_HTML_WITH_OG)
            == "2024-01-10T08:00:00Z"
        )

    def test_extract_publication_date_none(self) -> None:
        assert HtmlMetadataExtractor.extract_publication_date("<html></html>") is None

    def test_extract_links(self) -> None:
        links = HtmlMetadataExtractor.extract_links(_SAMPLE_HTML, "https://example.gov")
        assert "/home" in links
        assert "/contact" in links
        assert "/regulation-pdf" in links
        assert len(links) == 3

    def test_extract_links_skips_anchor_and_javascript(self) -> None:
        html = '<a href="#section">Jump</a><a href="javascript:void(0)">Noop</a><a href="/real">Real</a>'
        links = HtmlMetadataExtractor.extract_links(html, "https://example.gov")
        assert "/real" in links
        assert len(links) == 1

    def test_extract_links_empty(self) -> None:
        assert HtmlMetadataExtractor.extract_links("<html></html>", "https://example.gov") == []

    def test_extract_all(self) -> None:
        meta = HtmlMetadataExtractor.extract_all(_SAMPLE_HTML, "https://example.gov")
        assert meta["title"] == "Test Regulation Page"
        assert meta["canonical_url"] == "https://example.gov/regulation"
        assert meta["language"] == "en"
        assert meta["description"] == "Official test regulation guidance"


# ===================================================================
# HtmlParser
# ===================================================================


class TestHtmlParser:
    def test_parse_full_document(self) -> None:
        parser = HtmlParser()
        doc = parser.parse(_SAMPLE_HTML, "https://example.gov/regulation", "text/html")
        assert doc.title == "Test Regulation Page"
        assert doc.canonical_url == "https://example.gov/regulation"
        assert doc.language == "en"
        assert doc.summary == "Official test regulation guidance"
        assert doc.content_type == "text/html"
        assert doc.source_url == "https://example.gov/regulation"
        assert len(doc.discovered_links) == 3
        assert "Regulation Title" in doc.content
        assert "This is the main regulatory content paragraph." in doc.content

    def test_parse_empty_html_raises(self) -> None:
        parser = HtmlParser()
        with pytest.raises(HtmlParseError, match="Empty"):
            parser.parse("", "https://example.gov")

    def test_parse_whitespace_only_raises(self) -> None:
        parser = HtmlParser()
        with pytest.raises(HtmlParseError, match="Empty"):
            parser.parse("   \n\n   ", "https://example.gov")

    def test_parse_invalid_html_graceful(self) -> None:
        parser = HtmlParser()
        doc = parser.parse("<p>Hello", "https://example.gov")
        assert "Hello" in doc.content

    def test_parse_metadata_in_extra(self) -> None:
        parser = HtmlParser()
        doc = parser.parse(_SAMPLE_HTML, "https://example.gov")
        assert doc.metadata.get("description") == "Official test regulation guidance"
        assert doc.metadata.get("keywords") == "regulation, test, compliance"
        assert doc.metadata.get("publication_date_str") == "2024-06-15"

    def test_parse_no_extra_meta_when_absent(self) -> None:
        parser = HtmlParser()
        doc = parser.parse("<html><body><p>No meta</p></body></html>", "https://example.gov")
        assert doc.metadata == {}

    def test_document_frozen(self) -> None:
        parser = HtmlParser()
        doc = parser.parse(_SAMPLE_HTML, "https://example.gov")
        with pytest.raises(Exception):
            setattr(doc, "title", "Changed")


# ===================================================================
# HTMLConnector
# ===================================================================


class TestHTMLConnectorBase:
    def test_metadata(self) -> None:
        meta = HTMLConnector.metadata()
        assert meta.name == "HTMLConnector"
        assert meta.version == "1.0.0"
        assert ParserType.HTML in meta.parser_types
        assert CapabilityType.HTML in meta.capabilities

    def test_capabilities(self) -> None:
        caps = HTMLConnector.capabilities()
        assert ParserType.HTML in caps.parser_types
        assert CapabilityType.HTML in caps.capability_types
        assert CapabilityType.SEARCH in caps.capability_types
        assert caps.supports_search is True

    def test_connect(self, authority: Authority) -> None:
        connector = HTMLConnector(authority)
        result = connector.connect()
        assert result.success is True
        assert result.status == ConnectionStatus.CONNECTED
        assert connector._initialized is True

    def test_close(self, authority: Authority) -> None:
        connector = HTMLConnector(authority)
        connector.connect()
        connector.close()
        assert connector._initialized is False

    def test_health_before_connect(self, authority: Authority) -> None:
        connector = HTMLConnector(authority)
        health = connector.health()
        assert health.initialized is False
        assert health.status == ConnectionStatus.INITIALIZED

    def test_health_after_connect(self, authority: Authority) -> None:
        connector = HTMLConnector(authority)
        connector.connect()
        health = connector.health()
        assert health.initialized is True
        assert health.status == ConnectionStatus.CONNECTED
        assert health.parser_supported is True
        assert CapabilityType.HTML in health.capabilities

    def test_health_no_http(self, authority: Authority) -> None:
        connector = HTMLConnector(authority)
        health = connector.health()
        assert health.available is False
        assert health.details["http_configured"] is False


class TestHTMLConnectorFetch:
    def test_fetch_without_http_returns_error(self, authority: Authority) -> None:
        connector = HTMLConnector(authority)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://example.gov"))
        assert result.success is False
        assert "HTTP client not configured" in result.metadata.get("error", "")

    def test_fetch_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=_SAMPLE_HTML.encode("utf-8"),
            content_type="text/html",
            encoding="utf-8",
            elapsed_ms=150,
            response_size=len(_SAMPLE_HTML),
        )

        connector = HTMLConnector(authority, http_client=mock_http)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://example.gov/regulation"))

        assert result.success is True
        assert result.content_type == "text/html"
        assert result.size_bytes == len(_SAMPLE_HTML)
        assert result.metadata["title"] == "Test Regulation Page"
        assert result.metadata["canonical_url"] == "https://example.gov/regulation"
        assert result.metadata["language"] == "en"
        assert len(result.metadata["links"]) == 3
        assert result.metadata["elapsed_ms"] == 150

    def test_fetch_unsupported_mime_type(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=b"{}",
            content_type="application/json",
            encoding="utf-8",
        )

        connector = HTMLConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(UnsupportedContentTypeError, match="application/json"):
            connector.fetch(FetchRequest(url="https://example.gov/data.json"))

    def test_fetch_empty_content(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=b"   \n\n   ",
            content_type="text/html",
            encoding="utf-8",
        )

        connector = HTMLConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(EmptyContentError, match="Empty page"):
            connector.fetch(FetchRequest(url="https://example.gov/empty"))

    def test_fetch_propagates_http_error(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpConnectionError("Connection refused")

        connector = HTMLConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(HttpConnectionError, match="Connection refused"):
            connector.fetch(FetchRequest(url="https://example.gov"))


class TestHTMLConnectorFetchDocument:
    def test_fetch_document_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=_SAMPLE_HTML.encode("utf-8"),
            content_type="text/html",
            encoding="utf-8",
            elapsed_ms=120,
            response_size=len(_SAMPLE_HTML),
        )

        connector = HTMLConnector(authority, http_client=mock_http)
        connector.connect()
        doc = connector.fetch_document(FetchRequest(url="https://example.gov/regulation"))

        assert isinstance(doc, Document)
        assert doc.title == "Test Regulation Page"
        assert doc.content_type == "text/html"
        assert doc.source_url == "https://example.gov/regulation"

    def test_fetch_document_failure_raises(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=b"   ",
            content_type="text/html",
            encoding="utf-8",
        )

        connector = HTMLConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(HtmlParseError):
            connector.fetch_document(FetchRequest(url="https://example.gov/empty"))


class TestHTMLConnectorMimeValidation:
    def test_supported_mime_types(self) -> None:
        assert "text/html" in _SUPPORTED_MIME_TYPES
        assert "application/xhtml+xml" in _SUPPORTED_MIME_TYPES

    def test_validate_mime_type_html(self) -> None:
        HTMLConnector._validate_mime_type("text/html")

    def test_validate_mime_type_xhtml(self) -> None:
        HTMLConnector._validate_mime_type("application/xhtml+xml")

    def test_validate_mime_type_with_charset(self) -> None:
        HTMLConnector._validate_mime_type("text/html; charset=utf-8")

    def test_validate_mime_type_rejects_pdf(self) -> None:
        with pytest.raises(UnsupportedContentTypeError, match="application/pdf"):
            HTMLConnector._validate_mime_type("application/pdf")

    def test_validate_mime_type_rejects_json(self) -> None:
        with pytest.raises(UnsupportedContentTypeError):
            HTMLConnector._validate_mime_type("application/json")

    def test_validate_mime_type_empty_string_allowed(self) -> None:
        HTMLConnector._validate_mime_type("")


# ===================================================================
# Exception hierarchy
# ===================================================================


class TestHtmlExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(HtmlParseError, HtmlError)
        assert issubclass(UnsupportedContentTypeError, HtmlError)
        assert issubclass(EmptyContentError, HtmlError)
        assert issubclass(ExtractionError, HtmlError)

    def test_html_error_is_connector_error(self) -> None:
        from src.connectors.exceptions import ConnectorError

        assert issubclass(HtmlError, ConnectorError)
