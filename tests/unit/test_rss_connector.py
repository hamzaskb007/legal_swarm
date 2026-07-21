"""Unit tests for the RSS Connector."""

from __future__ import annotations

from unittest.mock import MagicMock
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
from src.connectors.rss.connector import RSSConnector, _SUPPORTED_MIME_TYPES
from src.connectors.rss.exceptions import (
    EmptyFeedError,
    FeedTooLargeError,
    InvalidXmlError,
    RssError,
    RssParseError,
    UnsupportedContentTypeError,
    UnsupportedFeedFormatError,
)
from src.connectors.rss.parser import (
    RssConfig,
    RSSParser,
    _detect_feed_type,
    _parse_rss_date,
    _parse_atom_date,
    _parse_xml_safe,
    _sanitize_html,
)

# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def authority() -> Authority:
    return Authority(
        id="test_rss",
        jurisdiction="xx",
        level=AuthorityLevel.LEVEL_1,
        name="Test RSS Authority",
        authority_type="regulator",
    )


# ===================================================================
# Sample feed data
# ===================================================================

_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Regulatory Updates</title>
    <description>Latest regulatory updates from Test Authority</description>
    <link>https://regulator.gov/rss</link>
    <language>en-us</language>
    <copyright>Copyright 2024 Test Authority</copyright>
    <managingEditor>editor@regulator.gov</managingEditor>
    <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    <lastBuildDate>Mon, 15 Jan 2024 12:00:00 GMT</lastBuildDate>
    <generator>RegulatoryFeedGen 1.0</generator>
    <category>finance</category>
    <category>regulation</category>
    <item>
      <title>New Capital Requirements 2024</title>
      <link>https://regulator.gov/rules/2024/001</link>
      <description>Updated capital adequacy framework for 2024.</description>
      <content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/">
        &lt;p&gt;The new framework requires &lt;strong&gt;minimum 15%&lt;/strong&gt; capital ratio.&lt;/p&gt;
        &lt;script&gt;alert('xss')&lt;/script&gt;
      </content:encoded>
      <pubDate>Wed, 15 Dec 2023 10:30:00 GMT</pubDate>
      <guid isPermaLink="false">urn:uuid:abc-123-def-456</guid>
      <author>author@regulator.gov</author>
      <category>capital</category>
      <category>compliance</category>
    </item>
    <item>
      <title>Reporting Deadline Extension</title>
      <link>https://regulator.gov/notices/2024/002</link>
      <description>Annual reporting deadline extended to March 31, 2024.</description>
      <pubDate>Fri, 05 Jan 2024 09:00:00 GMT</pubDate>
      <guid>https://regulator.gov/notices/2024/002</guid>
      <category>reporting</category>
    </item>
    <item>
      <title>Fee Schedule Update</title>
      <link>https://regulator.gov/fees/2024/003</link>
      <description>Updated fee structure for licensed entities.</description>
      <author>fees@regulator.gov</author>
    </item>
  </channel>
</rss>"""

_SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Regulatory Feed</title>
  <subtitle>Atom feed of regulatory updates</subtitle>
  <link href="https://regulator.gov/atom" rel="self"/>
  <link href="https://regulator.gov" rel="alternate"/>
  <id>urn:uuid:feed-001</id>
  <updated>2024-01-15T12:00:00Z</updated>
  <rights>Copyright 2024</rights>
  <generator>AtomFeedGen 2.0</generator>
  <author>
    <name>Test Authority</name>
  </author>
  <category term="finance"/>
  <category term="regulation"/>
  <entry>
    <title>New Capital Requirements (Atom)</title>
    <link href="https://regulator.gov/rules/atom/001" rel="alternate"/>
    <id>urn:uuid:entry-001</id>
    <published>2023-12-15T10:30:00Z</published>
    <updated>2024-01-10T08:00:00Z</updated>
    <summary>Updated capital adequacy framework for 2024.</summary>
    <content type="html">&lt;p&gt;Minimum &lt;strong&gt;15%&lt;/strong&gt; capital ratio required.&lt;/p&gt;</content>
    <author>
      <name>John Regulator</name>
    </author>
    <category term="capital"/>
    <category term="compliance"/>
  </entry>
  <entry>
    <title>Reporting Deadline (Atom)</title>
    <link href="https://regulator.gov/notices/atom/002" rel="alternate"/>
    <id>urn:uuid:entry-002</id>
    <published>2024-01-05T09:00:00Z</published>
    <summary>Extended to March 31, 2024.</summary>
    <category term="reporting"/>
  </entry>
  <entry>
    <title>Fee Schedule (Atom)</title>
    <id>urn:uuid:entry-003</id>
  </entry>
</feed>"""

_SAMPLE_EMPTY_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
    <description>No entries</description>
    <link>https://regulator.gov</link>
  </channel>
</rss>"""

_SAMPLE_EMPTY_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Empty Atom Feed</title>
  <id>urn:uuid:empty</id>
  <updated>2024-01-01T00:00:00Z</updated>
</feed>"""

_SAMPLE_MALFORMED_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Broken
</channel>
</rss>"""

_SAMPLE_RSS_MINIMAL = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Minimal Feed</title>
    <description>Minimal</description>
    <link>https://regulator.gov</link>
    <item>
      <title>Minimal Item</title>
      <link>https://regulator.gov/item</link>
      <description>A minimal item without dates or metadata.</description>
    </item>
  </channel>
</rss>"""

_SAMPLE_ATOM_MINIMAL = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Minimal Atom</title>
  <id>urn:uuid:minimal</id>
  <updated>2024-01-01T00:00:00Z</updated>
  <entry>
    <title>Minimal Entry</title>
    <id>urn:uuid:entry-minimal</id>
    <updated>2024-01-01T00:00:00Z</updated>
  </entry>
</feed>"""

_SAMPLE_RSS_WITH_XSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>XSS Feed</title>
    <description>Feed with XSS attempts</description>
    <link>https://regulator.gov</link>
    <item>
      <title>XSS Item</title>
      <link>https://regulator.gov/xss</link>
      <description>&lt;script&gt;alert('xss')&lt;/script&gt;&lt;p&gt;Safe content&lt;/p&gt;</description>
    </item>
  </channel>
</rss>"""

_RSS_WITH_CONTENT_ENCODED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Content Feed</title>
    <description>Full content feed</description>
    <link>https://regulator.gov</link>
    <item>
      <title>Content Item</title>
      <link>https://regulator.gov/content</link>
      <description>Short description</description>
      <content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/">
        &lt;p&gt;Full &lt;strong&gt;article&lt;/strong&gt; content here.&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Point 1&lt;/li&gt;&lt;li&gt;Point 2&lt;/li&gt;&lt;/ul&gt;
      </content:encoded>
      <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
      <guid>content-guid</guid>
    </item>
  </channel>
</rss>"""


# ===================================================================
# Date parsing
# ===================================================================


class TestDateParsing:
    def test_parse_rss_date_valid(self) -> None:
        dt = _parse_rss_date("Mon, 01 Jan 2024 12:00:00 GMT")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1

    def test_parse_rss_date_none(self) -> None:
        assert _parse_rss_date(None) is None

    def test_parse_rss_date_empty(self) -> None:
        assert _parse_rss_date("") is None

    def test_parse_rss_date_invalid(self) -> None:
        assert _parse_rss_date("not a date") is None

    def test_parse_rss_date_various_formats(self) -> None:
        dt = _parse_rss_date("01 Jan 2024 12:00:00 +0000")
        assert dt is not None
        assert dt.year == 2024

    def test_parse_atom_date_valid(self) -> None:
        dt = _parse_atom_date("2024-01-15T12:00:00Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1

    def test_parse_atom_date_none(self) -> None:
        assert _parse_atom_date(None) is None

    def test_parse_atom_date_empty(self) -> None:
        assert _parse_atom_date("") is None

    def test_parse_atom_date_invalid(self) -> None:
        assert _parse_atom_date("not a date") is None

    def test_parse_atom_date_no_tz(self) -> None:
        dt = _parse_atom_date("2024-01-15T12:00:00")
        assert dt is not None
        assert dt.tzinfo is not None


# ===================================================================
# Content sanitization
# ===================================================================


class TestContentSanitization:
    def test_scripts_removed(self) -> None:
        result = _sanitize_html("<p>Safe</p><script>alert('xss')</script><p>Also safe</p>")
        assert "alert" not in result
        assert "Safe" in result
        assert "Also safe" in result

    def test_style_removed(self) -> None:
        result = _sanitize_html("<p>Text</p><style>.hidden{}</style>")
        assert ".hidden" not in result
        assert "Text" in result

    def test_iframe_removed(self) -> None:
        result = _sanitize_html("<p>Text</p><iframe src='evil'></iframe>")
        assert "iframe" not in result
        assert "Text" in result

    def test_noscript_removed(self) -> None:
        result = _sanitize_html("<p>Text</p><noscript>No JS</noscript>")
        assert "No JS" not in result

    def test_object_embed_removed(self) -> None:
        result = _sanitize_html("<p>Text</p><object>flash</object><embed>plugin</embed>")
        assert "flash" not in result
        assert "plugin" not in result

    def test_none_input(self) -> None:
        assert _sanitize_html(None) == ""

    def test_empty_input(self) -> None:
        assert _sanitize_html("") == ""

    def test_truncation(self) -> None:
        long = "a" * 2000
        result = _sanitize_html(long, max_length=100)
        assert len(result) <= 100

    def test_paragraphs_preserved(self) -> None:
        result = _sanitize_html("<p>First</p><p>Second</p>")
        assert "<p>First</p>" in result


# ===================================================================
# Safe XML parsing
# ===================================================================


class TestSafeXmlParsing:
    def test_valid_xml(self) -> None:
        root = _parse_xml_safe("<root><item>data</item></root>")
        assert root.tag == "root"

    def test_malformed_xml_raises(self) -> None:
        with pytest.raises(InvalidXmlError, match="Malformed XML"):
            _parse_xml_safe("<root><broken>")

    def test_bytes_input(self) -> None:
        root = _parse_xml_safe(b"<root><item>data</item></root>")
        assert root.tag == "root"

    def test_empty_input_raises(self) -> None:
        with pytest.raises(InvalidXmlError):
            _parse_xml_safe("")


# ===================================================================
# Feed type detection
# ===================================================================


class TestFeedTypeDetection:
    def test_detect_rss(self) -> None:
        root = _parse_xml_safe('<rss version="2.0"><channel><title>T</title></channel></rss>')
        assert _detect_feed_type(root).value == "rss"

    def test_detect_atom(self) -> None:
        root = _parse_xml_safe('<feed xmlns="http://www.w3.org/2005/Atom"><title>T</title></feed>')
        assert _detect_feed_type(root).value == "atom"

    def test_unsupported_rss_version(self) -> None:
        root = _parse_xml_safe('<rss version="0.91"><channel><title>T</title></channel></rss>')
        with pytest.raises(UnsupportedFeedFormatError, match="0.91"):
            _detect_feed_type(root)

    def test_unknown_root_tag(self) -> None:
        root = _parse_xml_safe("<html><body></body></html>")
        with pytest.raises(UnsupportedFeedFormatError, match="html"):
            _detect_feed_type(root)


# ===================================================================
# RSSParser — RSS 2.0
# ===================================================================


class TestRSSParserRss:
    def test_parse_full_rss_feed(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        assert len(docs) == 3

        doc1 = docs[0]
        assert doc1.title == "New Capital Requirements 2024"
        assert doc1.authority_id == "test_rss"
        assert doc1.source_url == "https://regulator.gov/rules/2024/001"
        assert doc1.canonical_url == "https://regulator.gov/rules/2024/001"
        assert doc1.content_type == "text/html"
        assert doc1.document_type == "regulatory_update"
        assert "minimum 15%" in doc1.content
        assert doc1.publication_date is not None
        assert doc1.publication_date.year == 2023
        assert doc1.metadata.get("guid") == "urn:uuid:abc-123-def-456"
        assert doc1.metadata.get("author") == "author@regulator.gov"
        assert "capital" in doc1.metadata.get("categories", [])
        assert "compliance" in doc1.metadata.get("categories", [])

    def test_second_item(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        doc2 = docs[1]
        assert doc2.title == "Reporting Deadline Extension"
        assert doc2.source_url == "https://regulator.gov/notices/2024/002"
        assert doc2.summary == "Annual reporting deadline extended to March 31, 2024."
        assert doc2.metadata.get("author") is None

    def test_item_without_date(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        doc3 = docs[2]
        assert doc3.title == "Fee Schedule Update"
        assert doc3.publication_date is None
        assert doc3.metadata.get("author") == "fees@regulator.gov"

    def test_empty_rss_feed_raises(self) -> None:
        parser = RSSParser()
        with pytest.raises(RssParseError, match="No entries"):
            parser.parse(_SAMPLE_EMPTY_RSS, "https://regulator.gov", "test_rss")

    def test_minimal_rss_item(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS_MINIMAL, "https://regulator.gov", "test_rss")
        assert len(docs) == 1
        assert docs[0].title == "Minimal Item"
        assert docs[0].publication_date is None
        assert docs[0].metadata == {}

    def test_rss_content_encoded_preferred(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_RSS_WITH_CONTENT_ENCODED, "https://regulator.gov", "test_rss")
        doc = docs[0]
        assert "Full" in doc.content
        assert "article" in doc.content
        assert "Short description" not in doc.content
        assert doc.summary == "Short description"

    def test_rss_scripts_stripped(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS_WITH_XSS, "https://regulator.gov", "test_rss")
        doc = docs[0]
        assert "alert" not in doc.content
        assert "Safe content" in doc.content

    def test_max_entries_respected(self) -> None:
        config = RssConfig(max_entries=1)
        parser = RSSParser(config)
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        assert len(docs) == 1

    def test_max_content_length_respected(self) -> None:
        config = RssConfig(max_content_length=10)
        parser = RSSParser(config)
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        assert len(docs[0].content) <= 10

    def test_feed_too_large_raises(self) -> None:
        config = RssConfig(max_feed_size=10)
        parser = RSSParser(config)
        with pytest.raises(FeedTooLargeError):
            parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")


# ===================================================================
# RSSParser — Atom
# ===================================================================


class TestRSSParserAtom:
    def test_parse_full_atom_feed(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_ATOM, "https://regulator.gov/atom", "test_rss")
        assert len(docs) == 3

        doc1 = docs[0]
        assert doc1.title == "New Capital Requirements (Atom)"
        assert doc1.authority_id == "test_rss"
        assert doc1.source_url == "https://regulator.gov/rules/atom/001"
        assert doc1.summary == "Updated capital adequacy framework for 2024."
        assert "15%" in doc1.content
        assert doc1.publication_date is not None
        assert doc1.last_modified is not None
        assert doc1.metadata.get("guid") == "urn:uuid:entry-001"
        assert doc1.metadata.get("author") == "John Regulator"
        assert "capital" in doc1.metadata.get("categories", [])
        assert "compliance" in doc1.metadata.get("categories", [])

    def test_second_atom_entry(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_ATOM, "https://regulator.gov/atom", "test_rss")
        doc2 = docs[1]
        assert doc2.title == "Reporting Deadline (Atom)"
        assert doc2.source_url == "https://regulator.gov/notices/atom/002"
        assert doc2.metadata.get("author") is None

    def test_entry_without_link(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_ATOM, "https://regulator.gov/atom", "test_rss")
        doc3 = docs[2]
        assert doc3.title == "Fee Schedule (Atom)"
        assert doc3.source_url == "https://regulator.gov/atom"
        assert doc3.canonical_url is None

    def test_empty_atom_feed_raises(self) -> None:
        parser = RSSParser()
        with pytest.raises(RssParseError, match="No entries"):
            parser.parse(_SAMPLE_EMPTY_ATOM, "https://regulator.gov/atom", "test_rss")

    def test_minimal_atom_entry(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_ATOM_MINIMAL, "https://regulator.gov/atom", "test_rss")
        assert len(docs) == 1
        assert docs[0].title == "Minimal Entry"
        assert docs[0].publication_date is not None
        assert docs[0].metadata.get("guid") == "urn:uuid:entry-minimal"


# ===================================================================
# RSSParser — Error handling
# ===================================================================


class TestRSSParserErrors:
    def test_malformed_xml_raises_invalid_xml(self) -> None:
        parser = RSSParser()
        with pytest.raises(InvalidXmlError):
            parser.parse("<rss><channel>", "https://regulator.gov", "test_rss")

    def test_empty_content_raises(self) -> None:
        parser = RSSParser()
        with pytest.raises(RssParseError, match="Empty"):
            parser.parse("", "https://regulator.gov", "test_rss")

    def test_invalid_feed_format(self) -> None:
        parser = RSSParser()
        with pytest.raises(UnsupportedFeedFormatError):
            parser.parse(
                "<html><body>Not a feed</body></html>",
                "https://regulator.gov",
                "test_rss",
            )

    def test_atom_ns_rejection(self) -> None:
        """Verify feeds with a different namespace are not recognized as Atom."""
        parser = RSSParser()
        with pytest.raises(UnsupportedFeedFormatError):
            parser.parse(
                '<feed xmlns="http://some-other-ns"><entry><title>T</title></entry></feed>',
                "https://regulator.gov",
                "test_rss",
            )


# ===================================================================
# RSSParser — Document conversion
# ===================================================================


class TestDocumentConversion:
    def test_document_frozen(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        with pytest.raises(Exception):
            setattr(docs[0], "title", "Changed")

    def test_document_has_uuid(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        assert isinstance(docs[0].id, UUID)

    def test_document_authority_id(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "custom_auth")
        assert docs[0].authority_id == "custom_auth"

    def test_document_content_type(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        assert docs[0].content_type == "text/html"

    def test_document_document_type(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        assert docs[0].document_type == "regulatory_update"

    def test_document_retrieved_at_set(self) -> None:
        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        assert docs[0].retrieved_at is not None

    def test_serialization_roundtrip(self) -> None:
        from pydantic import TypeAdapter

        parser = RSSParser()
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        adapter = TypeAdapter(list[Document])
        json_data = adapter.dump_json(docs)
        restored = adapter.validate_json(json_data)
        assert len(restored) == len(docs)
        assert restored[0].title == docs[0].title

    def test_entry_count_limit(self) -> None:
        config = RssConfig(max_entries=2)
        parser = RSSParser(config)
        docs = parser.parse(_SAMPLE_RSS, "https://regulator.gov/rss", "test_rss")
        assert len(docs) == 2


# ===================================================================
# RSSParser — MIME type support
# ===================================================================


class TestRSSParserMimeSupport:
    def test_supported_mime_types(self) -> None:
        assert RSSParser.is_supported_content_type("application/rss+xml")
        assert RSSParser.is_supported_content_type("application/atom+xml")
        assert RSSParser.is_supported_content_type("application/xml")
        assert RSSParser.is_supported_content_type("text/xml")

    def test_supported_with_charset(self) -> None:
        assert RSSParser.is_supported_content_type("application/rss+xml; charset=utf-8")
        assert RSSParser.is_supported_content_type("text/xml; charset=iso-8859-1")

    def test_unsupported_types(self) -> None:
        assert not RSSParser.is_supported_content_type("text/html")
        assert not RSSParser.is_supported_content_type("application/json")
        assert not RSSParser.is_supported_content_type("application/pdf")
        assert not RSSParser.is_supported_content_type("")

    def test_case_insensitive(self) -> None:
        assert RSSParser.is_supported_content_type("APPLICATION/RSS+XML")


# ===================================================================
# RSSConnector — Base
# ===================================================================


class TestRSSConnectorBase:
    def test_metadata(self) -> None:
        meta = RSSConnector.metadata()
        assert meta.name == "RSSConnector"
        assert meta.version == "1.0.0"
        assert ParserType.RSS in meta.parser_types
        assert CapabilityType.RSS in meta.capabilities

    def test_capabilities(self) -> None:
        caps = RSSConnector.capabilities()
        assert ParserType.RSS in caps.parser_types
        assert CapabilityType.RSS in caps.capability_types
        assert caps.supports_streaming is True

    def test_connect(self, authority: Authority) -> None:
        connector = RSSConnector(authority)
        result = connector.connect()
        assert result.success is True
        assert result.status == ConnectionStatus.CONNECTED
        assert connector._initialized is True

    def test_close(self, authority: Authority) -> None:
        connector = RSSConnector(authority)
        connector.connect()
        connector.close()
        assert connector._initialized is False

    def test_health_before_connect(self, authority: Authority) -> None:
        connector = RSSConnector(authority)
        health = connector.health()
        assert health.initialized is False
        assert health.status == ConnectionStatus.INITIALIZED

    def test_health_after_connect(self, authority: Authority) -> None:
        connector = RSSConnector(authority)
        connector.connect()
        health = connector.health()
        assert health.initialized is True
        assert health.status == ConnectionStatus.CONNECTED
        assert health.parser_supported is True
        assert CapabilityType.RSS in health.capabilities

    def test_health_no_http(self, authority: Authority) -> None:
        connector = RSSConnector(authority)
        health = connector.health()
        assert health.available is False
        assert health.details["http_configured"] is False


# ===================================================================
# RSSConnector — Fetch
# ===================================================================


class TestRSSConnectorFetch:
    def test_fetch_without_http_returns_error(self, authority: Authority) -> None:
        connector = RSSConnector(authority)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://regulator.gov/rss"))
        assert result.success is False
        assert "HTTP client not configured" in result.metadata.get("error", "")

    def test_fetch_rss_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=_SAMPLE_RSS.encode("utf-8"),
            content_type="application/rss+xml",
            encoding="utf-8",
            elapsed_ms=200,
            response_size=len(_SAMPLE_RSS),
        )

        connector = RSSConnector(authority, http_client=mock_http)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://regulator.gov/rss"))

        assert result.success is True
        assert result.content_type == "application/rss+xml"
        assert result.size_bytes == len(_SAMPLE_RSS)
        assert result.metadata["entry_count"] == 3
        assert result.metadata["elapsed_ms"] == 200

    def test_fetch_atom_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=_SAMPLE_ATOM.encode("utf-8"),
            content_type="application/atom+xml",
            encoding="utf-8",
            elapsed_ms=150,
            response_size=len(_SAMPLE_ATOM),
        )

        connector = RSSConnector(authority, http_client=mock_http)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://regulator.gov/atom"))

        assert result.success is True
        assert result.metadata["entry_count"] == 3

    def test_fetch_unsupported_mime_type(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=_SAMPLE_RSS.encode("utf-8"),
            content_type="text/html",
            encoding="utf-8",
        )

        connector = RSSConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(UnsupportedContentTypeError, match="text/html"):
            connector.fetch(FetchRequest(url="https://regulator.gov/rss"))

    def test_fetch_empty_content(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=b"   \n\n   ",
            content_type="application/rss+xml",
            encoding="utf-8",
        )

        connector = RSSConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(RssParseError, match="Empty"):
            connector.fetch(FetchRequest(url="https://regulator.gov/rss"))

    def test_fetch_propagates_http_error(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpConnectionError("Connection refused")

        connector = RSSConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(HttpConnectionError, match="Connection refused"):
            connector.fetch(FetchRequest(url="https://regulator.gov/rss"))

    def test_fetch_propagates_timeout(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpTimeoutError("Request timed out")

        connector = RSSConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(HttpTimeoutError, match="timed out"):
            connector.fetch(FetchRequest(url="https://regulator.gov/rss"))

    def test_fetch_oversized_feed(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=("x" * 2000).encode("utf-8"),
            content_type="application/rss+xml",
            encoding="utf-8",
        )

        connector = RSSConnector(
            authority,
            http_client=mock_http,
            parser=RSSParser(RssConfig(max_feed_size=100)),
        )
        connector.connect()
        with pytest.raises(FeedTooLargeError):
            connector.fetch(FetchRequest(url="https://regulator.gov/rss"))


# ===================================================================
# RSSConnector — Fetch Documents
# ===================================================================


class TestRSSConnectorFetchDocuments:
    def test_fetch_documents_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=_SAMPLE_RSS.encode("utf-8"),
            content_type="application/rss+xml",
            encoding="utf-8",
            elapsed_ms=120,
            response_size=len(_SAMPLE_RSS),
        )

        connector = RSSConnector(authority, http_client=mock_http)
        connector.connect()
        docs = connector.fetch_documents(FetchRequest(url="https://regulator.gov/rss"))

        assert isinstance(docs, list)
        assert len(docs) == 3
        assert isinstance(docs[0], Document)
        assert docs[0].title == "New Capital Requirements 2024"

    def test_fetch_documents_failure_raises(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.get.return_value = Response(
            status_code=200,
            body=b"   ",
            content_type="application/rss+xml",
            encoding="utf-8",
        )

        connector = RSSConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(RssParseError):
            connector.fetch_documents(FetchRequest(url="https://regulator.gov/rss"))


# ===================================================================
# RSSConnector — MIME validation
# ===================================================================


class TestRSSConnectorMimeValidation:
    def test_supported_mime_types(self) -> None:
        assert "application/rss+xml" in _SUPPORTED_MIME_TYPES
        assert "application/atom+xml" in _SUPPORTED_MIME_TYPES
        assert "application/xml" in _SUPPORTED_MIME_TYPES
        assert "text/xml" in _SUPPORTED_MIME_TYPES

    def test_validate_mime_type_rss(self) -> None:
        RSSConnector._validate_mime_type("application/rss+xml")

    def test_validate_mime_type_atom(self) -> None:
        RSSConnector._validate_mime_type("application/atom+xml")

    def test_validate_mime_type_xml(self) -> None:
        RSSConnector._validate_mime_type("application/xml")

    def test_validate_mime_type_text_xml(self) -> None:
        RSSConnector._validate_mime_type("text/xml")

    def test_validate_mime_type_with_charset(self) -> None:
        RSSConnector._validate_mime_type("application/rss+xml; charset=utf-8")

    def test_validate_mime_type_rejects_html(self) -> None:
        with pytest.raises(UnsupportedContentTypeError, match="text/html"):
            RSSConnector._validate_mime_type("text/html")

    def test_validate_mime_type_rejects_json(self) -> None:
        with pytest.raises(UnsupportedContentTypeError):
            RSSConnector._validate_mime_type("application/json")

    def test_validate_mime_type_empty_string_allowed(self) -> None:
        RSSConnector._validate_mime_type("")


# ===================================================================
# Exception hierarchy
# ===================================================================


class TestRssExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(RssParseError, RssError)
        assert issubclass(UnsupportedContentTypeError, RssError)
        assert issubclass(UnsupportedFeedFormatError, RssError)
        assert issubclass(EmptyFeedError, RssError)
        assert issubclass(FeedTooLargeError, RssError)
        assert issubclass(InvalidXmlError, RssError)

    def test_rss_error_is_connector_error(self) -> None:
        assert issubclass(RssError, ConnectorError)

    def test_rss_parse_error_message(self) -> None:
        err = RssParseError("custom parse error")
        assert str(err) == "custom parse error"

    def test_unsupported_content_type_message(self) -> None:
        err = UnsupportedContentTypeError("bad type")
        assert str(err) == "bad type"

    def test_unsupported_feed_format_message(self) -> None:
        err = UnsupportedFeedFormatError("unknown format")
        assert str(err) == "unknown format"


# ===================================================================
# RssConfig
# ===================================================================


class TestRssConfig:
    def test_defaults(self) -> None:
        config = RssConfig()
        assert config.max_feed_size == 10 * 1024 * 1024
        assert config.max_entries == 500
        assert config.max_content_length == 100 * 1024

    def test_custom_values(self) -> None:
        config = RssConfig(max_feed_size=1000, max_entries=10, max_content_length=500)
        assert config.max_feed_size == 1000
        assert config.max_entries == 10
        assert config.max_content_length == 500

    def test_frozen(self) -> None:
        config = RssConfig()
        with pytest.raises(Exception):
            config.max_entries = 100
