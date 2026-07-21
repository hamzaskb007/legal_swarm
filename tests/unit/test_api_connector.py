"""Unit tests for the REST API Connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from src.authority.models import (
    Authority,
    AuthorityLevel,
    CapabilityType,
    ParserType,
)
from src.connectors.api.connector import APIConnector
from src.connectors.api.exceptions import (
    ApiAuthenticationError,
    ApiError,
    ApiParseError,
    ApiRateLimitedError,
    ApiServerError,
    EmptyResponseError,
    UnsupportedContentTypeError,
    UnsupportedResponseFormatError,
)
from src.connectors.api.parser import (
    ApiConfig,
    ApiFieldMapping,
    ApiPaginationCursor,
    ApiPaginationNextLink,
    ApiPaginationOffset,
    ApiPaginationPageNumber,
    APIParser,
    _extract_items,
    _get_json_value,
    _parse_timestamp,
)
from src.connectors.exceptions import ConnectorError as ConnectorErrorBase
from src.connectors.http.exceptions import ConnectionError as HttpConnectionError
from src.connectors.http.exceptions import TimeoutError as HttpTimeoutError
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
        id="test_api",
        jurisdiction="xx",
        level=AuthorityLevel.LEVEL_1,
        name="Test API Authority",
        authority_type="regulator",
    )


# ===================================================================
# Sample response data
# ===================================================================

_SAMPLE_SINGLE = {
    "id": "doc-001",
    "title": "New Capital Requirements 2024",
    "content": "Updated capital adequacy framework for 2024.",
    "summary": "Capital requirements update",
    "published_at": "2024-01-15T12:00:00Z",
    "updated_at": "2024-01-20T08:00:00Z",
    "type": "regulation",
    "language": "en",
    "author": "Regulatory Body",
    "status": "active",
}

_SAMPLE_ARRAY = [
    {
        "id": "doc-001",
        "title": "New Capital Requirements 2024",
        "content": "Updated capital adequacy framework for 2024.",
        "published_at": "2024-01-15T12:00:00Z",
    },
    {
        "id": "doc-002",
        "title": "Reporting Deadline Extension",
        "content": "Annual reporting deadline extended to March 31, 2024.",
        "published_at": "2024-01-10T09:00:00Z",
    },
    {
        "id": "doc-003",
        "title": "Fee Schedule Update",
        "content": "Updated fee structure for licensed entities.",
    },
]

_SAMPLE_WRAPPED = {
    "status": "ok",
    "data": {
        "items": _SAMPLE_ARRAY,
        "total": 3,
    },
    "meta": {
        "page": 1,
        "total_pages": 1,
    },
}

_SAMPLE_PAGINATED_PAGE1 = {
    "data": {
        "items": [_SAMPLE_ARRAY[0]],
    },
    "meta": {
        "page": 1,
        "total_pages": 2,
    },
}

_SAMPLE_PAGINATED_PAGE2 = {
    "data": {
        "items": [_SAMPLE_ARRAY[1], _SAMPLE_ARRAY[2]],
    },
    "meta": {
        "page": 2,
        "total_pages": 2,
    },
}

_SAMPLE_CURSOR_PAGE1 = {
    "data": {
        "items": [_SAMPLE_ARRAY[0]],
    },
    "meta": {
        "next_cursor": "cursor-page-2",
    },
}

_SAMPLE_CURSOR_PAGE2 = {
    "data": {
        "items": [_SAMPLE_ARRAY[1], _SAMPLE_ARRAY[2]],
    },
    "meta": {},
}

_SAMPLE_NEXTLINK_PAGE1 = {
    "data": {
        "items": [_SAMPLE_ARRAY[0]],
    },
    "links": {
        "next": "https://api.regulator.gov/docs?page=2",
    },
}

_SAMPLE_NEXTLINK_PAGE2 = {
    "data": {
        "items": [_SAMPLE_ARRAY[1], _SAMPLE_ARRAY[2]],
    },
    "links": {},
}


# ===================================================================
# JSON path extraction utilities
# ===================================================================


class TestJsonPathExtraction:
    def test_simple_key(self) -> None:
        assert _get_json_value({"title": "Foo"}, "title") == "Foo"

    def test_nested_key(self) -> None:
        assert _get_json_value({"meta": {"count": 5}}, "meta.count") == 5

    def test_deeply_nested(self) -> None:
        val = _get_json_value({"a": {"b": {"c": "deep"}}}, "a.b.c")
        assert val == "deep"

    def test_missing_key_returns_none(self) -> None:
        assert _get_json_value({"title": "Foo"}, "nonexistent") is None

    def test_nested_missing_returns_none(self) -> None:
        assert _get_json_value({"meta": {"a": 1}}, "meta.b.c") is None

    def test_non_dict_intermediate(self) -> None:
        assert _get_json_value({"meta": "string"}, "meta.count") is None

    def test_empty_path_returns_none(self) -> None:
        assert _get_json_value({"a": 1}, "") is None

    def test_list_access_returns_none(self) -> None:
        assert _get_json_value([1, 2, 3], "0") is None


class TestExtractItems:
    def test_root_list(self) -> None:
        items = _extract_items([{"a": 1}, {"a": 2}], None)
        assert len(items) == 2

    def test_root_dict(self) -> None:
        items = _extract_items({"title": "Foo"}, None)
        assert len(items) == 1
        assert items[0]["title"] == "Foo"

    def test_nested_items_path(self) -> None:
        data = {"data": {"items": [{"a": 1}]}}
        items = _extract_items(data, "data.items")
        assert len(items) == 1

    def test_items_path_not_found(self) -> None:
        with pytest.raises(ApiParseError, match="not found"):
            _extract_items({"data": {}}, "data.items")

    def test_items_path_not_a_list(self) -> None:
        with pytest.raises(ApiParseError, match="Expected list"):
            _extract_items({"data": "not a list"}, "data")

    def test_scalar_raises(self) -> None:
        with pytest.raises(ApiParseError, match="Unexpected response type"):
            _extract_items("scalar", None)


class TestTimestampParsing:
    def test_utc_zulu(self) -> None:
        dt = _parse_timestamp("2024-01-15T12:00:00Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_with_offset(self) -> None:
        dt = _parse_timestamp("2024-01-15T12:00:00+00:00")
        assert dt is not None

    def test_with_milliseconds(self) -> None:
        dt = _parse_timestamp("2024-01-15T12:00:00.123Z")
        assert dt is not None

    def test_with_milliseconds_and_offset(self) -> None:
        dt = _parse_timestamp("2024-01-15T12:00:00.123+00:00")
        assert dt is not None

    def test_none(self) -> None:
        assert _parse_timestamp(None) is None

    def test_empty_string(self) -> None:
        assert _parse_timestamp("") is None

    def test_invalid(self) -> None:
        assert _parse_timestamp("not-a-date") is None

    def test_non_string(self) -> None:
        assert _parse_timestamp(12345) is None

    def test_non_utc_offset(self) -> None:
        dt = _parse_timestamp("2024-06-15T14:30:00+05:00")
        assert dt is not None
        assert dt.tzinfo is not None


# ===================================================================
# APIParser — Valid JSON parsing
# ===================================================================


class TestAPIParserValidJson:
    def test_parse_single_object(self) -> None:
        mapping = ApiFieldMapping(
            title="title",
            content="content",
            summary="summary",
            publication_date="published_at",
            last_modified="updated_at",
            document_type="type",
            language="language",
            metadata={"author": "author", "status": "status"},
        )
        parser = APIParser(ApiConfig(field_mapping=mapping))
        body = json.dumps(_SAMPLE_SINGLE)
        docs = parser.parse(body, "https://api.regulator.gov/doc", "test_api")
        assert len(docs) == 1
        doc = docs[0]
        assert doc.title == "New Capital Requirements 2024"
        assert doc.content == "Updated capital adequacy framework for 2024."
        assert doc.summary == "Capital requirements update"
        assert doc.publication_date is not None
        assert doc.publication_date.year == 2024
        assert doc.last_modified is not None
        assert doc.document_type == "regulation"
        assert doc.language == "en"
        assert doc.metadata.get("author") == "Regulatory Body"
        assert doc.metadata.get("status") == "active"

    def test_parse_array(self) -> None:
        mapping = ApiFieldMapping(
            title="title",
            content="content",
            publication_date="published_at",
        )
        parser = APIParser(ApiConfig(field_mapping=mapping))
        body = json.dumps(_SAMPLE_ARRAY)
        docs = parser.parse(body, "https://api.regulator.gov/docs", "test_api")
        assert len(docs) == 3

    def test_parse_wrapped_array(self) -> None:
        mapping = ApiFieldMapping(
            title="title",
            content="content",
            publication_date="published_at",
            items_path="data.items",
        )
        parser = APIParser(ApiConfig(field_mapping=mapping))
        body = json.dumps(_SAMPLE_WRAPPED)
        docs = parser.parse(body, "https://api.regulator.gov/docs", "test_api")
        assert len(docs) == 3

    def test_parse_without_mapping(self) -> None:
        parser = APIParser()
        body = json.dumps({"title": "Foo", "content": "Bar"})
        docs = parser.parse(body, "https://api.regulator.gov/doc", "test_api")
        assert len(docs) == 1
        assert docs[0].title is None
        assert docs[0].content == ""
        assert docs[0].source_url == "https://api.regulator.gov/doc"

    def test_bytes_input(self) -> None:
        mapping = ApiFieldMapping(title="title")
        parser = APIParser(ApiConfig(field_mapping=mapping))
        body = json.dumps({"title": "Bytes Title"}).encode("utf-8")
        docs = parser.parse(body, "https://api.regulator.gov/doc", "test_api")
        assert len(docs) == 1
        assert docs[0].title == "Bytes Title"

    def test_source_url_fallback(self) -> None:
        mapping = ApiFieldMapping(title="title", source_url="url")
        parser = APIParser(ApiConfig(field_mapping=mapping))
        body = json.dumps({"title": "Doc", "url": "https://regulator.gov/doc/1"})
        docs = parser.parse(body, "https://api.regulator.gov/docs", "test_api")
        assert docs[0].source_url == "https://regulator.gov/doc/1"

    def test_content_type_set_on_document(self) -> None:
        parser = APIParser()
        body = json.dumps({"title": "Foo"})
        docs = parser.parse(body, "https://api.regulator.gov/doc", "test_api")
        assert docs[0].content_type == "application/json"


# ===================================================================
# APIParser — Missing fields
# ===================================================================


class TestAPIParserMissingFields:
    def test_missing_optional_fields(self) -> None:
        mapping = ApiFieldMapping(
            title="title",
            content="content",
            publication_date="published_at",
            last_modified="updated_at",
        )
        parser = APIParser(ApiConfig(field_mapping=mapping))
        body = json.dumps({"title": "Only Title"})
        docs = parser.parse(body, "https://api.regulator.gov/doc", "test_api")
        assert len(docs) == 1
        assert docs[0].title == "Only Title"
        assert docs[0].content == ""
        assert docs[0].publication_date is None
        assert docs[0].last_modified is None

    def test_none_values_in_fields(self) -> None:
        mapping = ApiFieldMapping(
            title="title",
            content="content",
            publication_date="published_at",
        )
        parser = APIParser(ApiConfig(field_mapping=mapping))
        body = json.dumps({"title": None, "content": None, "published_at": None})
        docs = parser.parse(body, "https://api.regulator.gov/doc", "test_api")
        assert len(docs) == 1
        assert docs[0].title is None
        assert docs[0].content == ""
        assert docs[0].publication_date is None

    def test_empty_string_fields(self) -> None:
        mapping = ApiFieldMapping(title="title", content="content")
        parser = APIParser(ApiConfig(field_mapping=mapping))
        body = json.dumps({"title": "", "content": ""})
        docs = parser.parse(body, "https://api.regulator.gov/doc", "test_api")
        assert len(docs) == 1
        assert docs[0].title == ""
        assert docs[0].content == ""


# ===================================================================
# APIParser — Error handling
# ===================================================================


class TestAPIParserErrors:
    def test_malformed_json_raises(self) -> None:
        parser = APIParser()
        with pytest.raises(ApiParseError, match="Invalid JSON"):
            parser.parse(b"{broken", "https://api.regulator.gov", "test_api")

    def test_empty_body_raises(self) -> None:
        parser = APIParser()
        with pytest.raises(EmptyResponseError, match="Empty"):
            parser.parse(b"", "https://api.regulator.gov", "test_api")

    def test_whitespace_body_raises(self) -> None:
        parser = APIParser()
        with pytest.raises(EmptyResponseError, match="Empty"):
            parser.parse(b"   ", "https://api.regulator.gov", "test_api")

    def test_null_json_raises(self) -> None:
        parser = APIParser()
        with pytest.raises(EmptyResponseError, match="Null"):
            parser.parse(b"null", "https://api.regulator.gov", "test_api")

    def test_empty_array_returns_empty(self) -> None:
        parser = APIParser()
        docs = parser.parse(b"[]", "https://api.regulator.gov", "test_api")
        assert len(docs) == 0

    def test_unsupported_content_type_raises(self) -> None:
        parser = APIParser()
        with pytest.raises(UnsupportedContentTypeError, match="text/html"):
            parser.parse(b"{}", "https://api.regulator.gov", "test_api", content_type="text/html")

    def test_empty_content_type_accepted(self) -> None:
        parser = APIParser()
        docs = parser.parse(b"{}", "https://api.regulator.gov", "test_api", content_type="")
        assert len(docs) == 1


# ===================================================================
# APIParser — Single document parsing
# ===================================================================


class TestAPIParserSingle:
    def test_parse_single_success(self) -> None:
        mapping = ApiFieldMapping(title="title")
        parser = APIParser(ApiConfig(field_mapping=mapping))
        doc = parser.parse_single(
            json.dumps({"title": "Single Doc"}),
            "https://api.regulator.gov/doc",
            "test_api",
        )
        assert doc.title == "Single Doc"

    def test_parse_single_empty_raises(self) -> None:
        parser = APIParser()
        with pytest.raises(EmptyResponseError):
            parser.parse_single(b"[]", "https://api.regulator.gov", "test_api")

    def test_parse_single_with_content_type(self) -> None:
        mapping = ApiFieldMapping(title="title")
        parser = APIParser(ApiConfig(field_mapping=mapping))
        doc = parser.parse_single(
            json.dumps({"title": "Doc"}),
            "https://api.regulator.gov/doc",
            "test_api",
            content_type="application/json",
        )
        assert doc.title == "Doc"


# ===================================================================
# APIParser — Document conversion & validation
# ===================================================================


class TestApiDocumentConversion:
    def test_document_frozen(self) -> None:
        mapping = ApiFieldMapping(title="title")
        parser = APIParser(ApiConfig(field_mapping=mapping))
        docs = parser.parse(
            json.dumps({"title": "Test"}),
            "https://api.regulator.gov/doc",
            "test_api",
        )
        with pytest.raises(Exception):
            setattr(docs[0], "title", "Changed")

    def test_document_has_uuid(self) -> None:
        parser = APIParser()
        docs = parser.parse(b"{}", "https://api.regulator.gov/doc", "test_api")
        assert isinstance(docs[0].id, UUID)

    def test_document_authority_id(self) -> None:
        mapping = ApiFieldMapping(title="title")
        parser = APIParser(ApiConfig(field_mapping=mapping))
        docs = parser.parse(
            json.dumps({"title": "Doc"}),
            "https://api.regulator.gov/doc",
            "custom_auth",
        )
        assert docs[0].authority_id == "custom_auth"

    def test_document_retrieved_at_set(self) -> None:
        parser = APIParser()
        docs = parser.parse(b"{}", "https://api.regulator.gov/doc", "test_api")
        assert docs[0].retrieved_at is not None

    def test_serialization_roundtrip(self) -> None:
        from pydantic import TypeAdapter

        parser = APIParser()
        docs = parser.parse(b"{}", "https://api.regulator.gov/doc", "test_api")
        adapter = TypeAdapter(list[Document])
        json_data = adapter.dump_json(docs)
        restored = adapter.validate_json(json_data)
        assert len(restored) == len(docs)

    def test_document_type_default(self) -> None:
        parser = APIParser()
        docs = parser.parse(b"{}", "https://api.regulator.gov/doc", "test_api")
        assert docs[0].document_type == "api_response"


# ===================================================================
# APIParser — MIME type validation
# ===================================================================


class TestAPIParserMimeSupport:
    def test_supported_mime_types(self) -> None:
        assert APIParser.is_supported_content_type("application/json")

    def test_supported_with_charset(self) -> None:
        assert APIParser.is_supported_content_type("application/json; charset=utf-8")

    def test_unsupported_types(self) -> None:
        assert not APIParser.is_supported_content_type("text/html")
        assert not APIParser.is_supported_content_type("application/xml")
        assert not APIParser.is_supported_content_type("application/pdf")
        assert not APIParser.is_supported_content_type("")

    def test_case_insensitive(self) -> None:
        assert APIParser.is_supported_content_type("APPLICATION/JSON")


# ===================================================================
# APIParser — Config
# ===================================================================


class TestApiConfig:
    def test_defaults(self) -> None:
        config = ApiConfig()
        assert config.method == "GET"
        assert config.response_format == "json"
        assert config.auth_type == "none"
        assert config.headers.get("Accept") == "application/json"

    def test_custom_values(self) -> None:
        mapping = ApiFieldMapping(title="doc_title", items_path="results")
        config = ApiConfig(
            endpoint_url="https://api.example.gov",
            method="POST",
            headers={"X-API-Key": "test-key"},
            auth_type="api_key",
            field_mapping=mapping,
            filter_params={"status": "active"},
        )
        assert config.endpoint_url == "https://api.example.gov"
        assert config.method == "POST"
        assert config.headers["X-API-Key"] == "test-key"
        assert config.field_mapping.title == "doc_title"
        assert config.filter_params["status"] == "active"

    def test_frozen(self) -> None:
        config = ApiConfig()
        with pytest.raises(Exception):
            config.method = "POST"  # type: ignore[misc]


class TestApiFieldMapping:
    def test_has_mappings_true(self) -> None:
        mapping = ApiFieldMapping(title="title")
        assert mapping.has_mappings is True

    def test_has_mappings_false(self) -> None:
        mapping = ApiFieldMapping()
        assert mapping.has_mappings is False

    def test_has_mappings_metadata_only(self) -> None:
        mapping = ApiFieldMapping(metadata={"source": "source_field"})
        assert mapping.has_mappings is True


# ===================================================================
# Pagination strategies
# ===================================================================


class TestPaginationStrategies:
    def test_page_number_defaults(self) -> None:
        p = ApiPaginationPageNumber(total_pages_path=None)
        assert p.type == "page_number"
        assert p.page_param == "page"
        assert p.page_size == 50
        assert p.first_page == 1

    def test_offset_defaults(self) -> None:
        p = ApiPaginationOffset()
        assert p.type == "offset"
        assert p.offset_param == "offset"
        assert p.max_offset == 10000

    def test_cursor_defaults(self) -> None:
        p = ApiPaginationCursor()
        assert p.type == "cursor"
        assert p.cursor_param == "cursor"
        assert p.cursor_path == "meta.next_cursor"
        assert p.max_pages == 100

    def test_next_link_defaults(self) -> None:
        p = ApiPaginationNextLink()
        assert p.type == "next_link"
        assert p.link_path == "links.next"
        assert p.max_pages == 100

    def test_page_number_params(self) -> None:
        p = ApiPaginationPageNumber(page_size=20, first_page=1)
        params = APIParser.get_page_params(p, 0)
        assert params["page"] == "1"
        assert params["page_size"] == "20"

        params = APIParser.get_page_params(p, 2)
        assert params["page"] == "3"
        assert params["page_size"] == "20"

    def test_offset_params(self) -> None:
        p = ApiPaginationOffset(page_size=25)
        params = APIParser.get_page_params(p, 0)
        assert params["offset"] == "0"
        assert params["limit"] == "25"

        params = APIParser.get_page_params(p, 3)
        assert params["offset"] == "75"
        assert params["limit"] == "25"

    def test_cursor_params(self) -> None:
        p = ApiPaginationCursor(page_size=30)
        params = APIParser.get_page_params(p, 0)
        assert params.get("limit") == "30"

    def test_next_link_params_returns_empty(self) -> None:
        p = ApiPaginationNextLink()
        params = APIParser.get_page_params(p, 0)
        assert params == {}


# ===================================================================
# APIConnector — Base
# ===================================================================


class TestAPIConnectorBase:
    def test_metadata(self) -> None:
        meta = APIConnector.metadata()
        assert meta.name == "APIConnector"
        assert meta.version == "1.0.0"
        assert ParserType.API in meta.parser_types
        assert CapabilityType.API in meta.capabilities

    def test_capabilities(self) -> None:
        caps = APIConnector.capabilities()
        assert ParserType.API in caps.parser_types
        assert CapabilityType.API in caps.capability_types
        assert CapabilityType.JSON in caps.capability_types
        assert caps.supports_streaming is True

    def test_connect(self, authority: Authority) -> None:
        connector = APIConnector(authority)
        result = connector.connect()
        assert result.success is True
        assert result.status == ConnectionStatus.CONNECTED
        assert connector._initialized is True

    def test_close(self, authority: Authority) -> None:
        connector = APIConnector(authority)
        connector.connect()
        connector.close()
        assert connector._initialized is False

    def test_health_before_connect(self, authority: Authority) -> None:
        connector = APIConnector(authority)
        health = connector.health()
        assert health.initialized is False
        assert health.status == ConnectionStatus.INITIALIZED

    def test_health_after_connect(self, authority: Authority) -> None:
        connector = APIConnector(authority)
        connector.connect()
        health = connector.health()
        assert health.initialized is True
        assert health.status == ConnectionStatus.CONNECTED
        assert health.parser_supported is True
        assert CapabilityType.API in health.capabilities

    def test_health_no_http(self, authority: Authority) -> None:
        connector = APIConnector(authority)
        health = connector.health()
        assert health.available is False
        assert health.details["http_configured"] is False


# ===================================================================
# APIConnector — Fetch
# ===================================================================


class TestAPIConnectorFetch:
    def test_fetch_without_http_returns_error(self, authority: Authority) -> None:
        connector = APIConnector(authority)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://api.regulator.gov"))
        assert result.success is False
        assert "HTTP client not configured" in result.metadata.get("error", "")

    def test_fetch_json_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=200,
            body=json.dumps(_SAMPLE_SINGLE).encode("utf-8"),
            content_type="application/json",
            encoding="utf-8",
            elapsed_ms=200,
            response_size=len(json.dumps(_SAMPLE_SINGLE)),
        )

        mapping = ApiFieldMapping(title="title", content="content")
        config = ApiConfig(field_mapping=mapping)
        connector = APIConnector(authority, http_client=mock_http, api_config=config)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://api.regulator.gov"))

        assert result.success is True
        assert result.content_type == "application/json"
        assert result.metadata["document_count"] == 1
        assert result.metadata["elapsed_ms"] == 200

    def test_fetch_array_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=200,
            body=json.dumps(_SAMPLE_ARRAY).encode("utf-8"),
            content_type="application/json",
            encoding="utf-8",
            elapsed_ms=150,
            response_size=len(json.dumps(_SAMPLE_ARRAY)),
        )

        mapping = ApiFieldMapping(title="title", content="content")
        config = ApiConfig(field_mapping=mapping)
        connector = APIConnector(authority, http_client=mock_http, api_config=config)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://api.regulator.gov"))

        assert result.success is True
        assert result.metadata["document_count"] == 3

    def test_fetch_unsupported_mime_type(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=200,
            body=json.dumps(_SAMPLE_SINGLE).encode("utf-8"),
            content_type="text/html",
            encoding="utf-8",
        )

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(UnsupportedContentTypeError, match="text/html"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))

    def test_fetch_empty_body(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=200,
            body=b"",
            content_type="application/json",
            encoding="utf-8",
        )

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(ApiParseError, match="Empty"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))

    def test_fetch_propagates_http_error(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.side_effect = HttpConnectionError("Connection refused")

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(HttpConnectionError, match="Connection refused"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))

    def test_fetch_propagates_timeout(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.side_effect = HttpTimeoutError("Request timed out")

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(HttpTimeoutError, match="timed out"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))

    def test_fetch_unauthorized_raises(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=401,
            body=b'{"error":"unauthorized"}',
            content_type="application/json",
        )

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(ApiAuthenticationError, match="Authentication"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))

    def test_fetch_forbidden_raises(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=403,
            body=b'{"error":"forbidden"}',
            content_type="application/json",
        )

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(ApiAuthenticationError, match="Authentication"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))

    def test_fetch_rate_limited_raises(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=429,
            body=b'{"error":"too many requests"}',
            content_type="application/json",
        )

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(ApiRateLimitedError, match="Rate limited"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))

    def test_fetch_server_error_raises(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=500,
            body=b'{"error":"server error"}',
            content_type="application/json",
        )

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(ApiServerError, match="Server error"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))

    def test_fetch_with_override_params(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=200,
            body=json.dumps(_SAMPLE_ARRAY).encode("utf-8"),
            content_type="application/json",
        )

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        result = connector.fetch(
            FetchRequest(
                url="https://api.regulator.gov",
                parameters={"params": {"status": "active"}},
            )
        )
        assert result.success is True
        call_kwargs = mock_http.request.call_args
        request_obj = call_kwargs[0][0]
        assert request_obj.params.get("status") == "active"

    def test_fetch_with_custom_headers(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=200,
            body=json.dumps(_SAMPLE_SINGLE).encode("utf-8"),
            content_type="application/json",
        )

        config = ApiConfig(headers={"Authorization": "Bearer test-token"})
        connector = APIConnector(authority, http_client=mock_http, api_config=config)
        connector.connect()
        connector.fetch(FetchRequest(url="https://api.regulator.gov"))

        call_kwargs = mock_http.request.call_args
        request_obj = call_kwargs[0][0]
        assert request_obj.headers.get("Authorization") == "Bearer test-token"

    def test_fetch_invalid_json_raises(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=200,
            body=b"not json at all",
            content_type="application/json",
        )

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(ApiParseError, match="Invalid JSON"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))

    def test_fetch_empty_response_body(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=200,
            body=b"",
            content_type="application/json",
        )

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(ApiParseError, match="Empty"):
            connector.fetch(FetchRequest(url="https://api.regulator.gov"))


# ===================================================================
# APIConnector — Paginated fetch
# ===================================================================


class TestAPIConnectorPaginatedFetch:
    def test_page_number_pagination(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.side_effect = [
            Response(
                status_code=200,
                body=json.dumps(_SAMPLE_PAGINATED_PAGE1).encode("utf-8"),
                content_type="application/json",
                elapsed_ms=100,
                response_size=100,
            ),
            Response(
                status_code=200,
                body=json.dumps(_SAMPLE_PAGINATED_PAGE2).encode("utf-8"),
                content_type="application/json",
                elapsed_ms=100,
                response_size=100,
            ),
        ]

        mapping = ApiFieldMapping(title="title", content="content", items_path="data.items")
        config = ApiConfig(
            field_mapping=mapping,
            pagination=ApiPaginationPageNumber(page_size=1, first_page=1),
        )
        connector = APIConnector(authority, http_client=mock_http, api_config=config)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://api.regulator.gov"))

        assert result.success is True
        assert result.metadata["document_count"] >= 1

    def test_next_link_pagination(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.side_effect = [
            Response(
                status_code=200,
                body=json.dumps(_SAMPLE_NEXTLINK_PAGE1).encode("utf-8"),
                content_type="application/json",
                elapsed_ms=100,
                response_size=100,
            ),
            Response(
                status_code=200,
                body=json.dumps(_SAMPLE_NEXTLINK_PAGE2).encode("utf-8"),
                content_type="application/json",
                elapsed_ms=100,
                response_size=100,
            ),
        ]

        mapping = ApiFieldMapping(title="title", content="content", items_path="data.items")
        config = ApiConfig(
            endpoint_url="https://api.regulator.gov/docs",
            field_mapping=mapping,
            pagination=ApiPaginationNextLink(max_pages=5),
        )
        connector = APIConnector(authority, http_client=mock_http, api_config=config)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://api.regulator.gov/docs"))

        assert result.success is True
        assert result.metadata["document_count"] >= 1

    def test_cursor_pagination(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.side_effect = [
            Response(
                status_code=200,
                body=json.dumps(_SAMPLE_CURSOR_PAGE1).encode("utf-8"),
                content_type="application/json",
                elapsed_ms=100,
                response_size=100,
            ),
            Response(
                status_code=200,
                body=json.dumps(_SAMPLE_CURSOR_PAGE2).encode("utf-8"),
                content_type="application/json",
                elapsed_ms=100,
                response_size=100,
            ),
        ]

        mapping = ApiFieldMapping(title="title", content="content", items_path="data.items")
        config = ApiConfig(
            endpoint_url="https://api.regulator.gov/docs",
            field_mapping=mapping,
            pagination=ApiPaginationCursor(max_pages=5),
        )
        connector = APIConnector(authority, http_client=mock_http, api_config=config)
        connector.connect()
        result = connector.fetch(FetchRequest(url="https://api.regulator.gov/docs"))

        assert result.success is True
        assert result.metadata["document_count"] >= 1


# ===================================================================
# APIConnector — Fetch Documents
# ===================================================================


class TestAPIConnectorFetchDocuments:
    def test_fetch_documents_success(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.return_value = Response(
            status_code=200,
            body=json.dumps(_SAMPLE_ARRAY).encode("utf-8"),
            content_type="application/json",
        )

        mapping = ApiFieldMapping(title="title", content="content")
        config = ApiConfig(field_mapping=mapping)
        connector = APIConnector(authority, http_client=mock_http, api_config=config)
        connector.connect()
        docs = connector.fetch_documents(FetchRequest(url="https://api.regulator.gov"))

        assert len(docs) == 3
        assert docs[0].title == "New Capital Requirements 2024"

    def test_fetch_documents_failure_raises(self, authority: Authority) -> None:
        mock_http = MagicMock()
        mock_http.request.side_effect = HttpConnectionError("Connection failed")

        connector = APIConnector(authority, http_client=mock_http)
        connector.connect()
        with pytest.raises(ApiParseError, match="Failed to fetch"):
            connector.fetch_documents(FetchRequest(url="https://api.regulator.gov"))


# ===================================================================
# APIConnector — MIME Validation
# ===================================================================


class TestAPIConnectorMimeValidation:
    def test_supported_mime_types(self) -> None:
        APIConnector._validate_mime_type("application/json")
        APIConnector._validate_mime_type("application/json; charset=utf-8")

    def test_rejects_html(self) -> None:
        with pytest.raises(UnsupportedContentTypeError, match="text/html"):
            APIConnector._validate_mime_type("text/html")

    def test_rejects_xml(self) -> None:
        with pytest.raises(UnsupportedContentTypeError, match="application/xml"):
            APIConnector._validate_mime_type("application/xml")

    def test_rejects_pdf(self) -> None:
        with pytest.raises(UnsupportedContentTypeError, match="application/pdf"):
            APIConnector._validate_mime_type("application/pdf")

    def test_empty_string_allowed(self) -> None:
        APIConnector._validate_mime_type("")


# ===================================================================
# Exception hierarchy
# ===================================================================


class TestApiExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(ApiError, ConnectorErrorBase)
        assert issubclass(ApiParseError, ApiError)
        assert issubclass(EmptyResponseError, ApiError)
        assert issubclass(UnsupportedContentTypeError, ApiError)
        assert issubclass(UnsupportedResponseFormatError, ApiError)
        assert issubclass(ApiRateLimitedError, ApiError)
        assert issubclass(ApiServerError, ApiError)
        assert issubclass(ApiAuthenticationError, ApiError)

    def test_api_error_message(self) -> None:
        err = ApiError("Test error")
        assert "Test error" in str(err)

    def test_api_parse_error_message(self) -> None:
        err = ApiParseError("Parse failed")
        assert "Parse failed" in str(err)
