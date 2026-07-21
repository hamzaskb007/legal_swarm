# Connector Framework

## Architecture

The Connector Framework provides an extensible, registry-driven architecture for connecting to regulatory data sources. It consumes the Authority Registry to determine which connector to instantiate and how to configure it.

```
Authority Registry
      │
      ▼
 Authority
      │
      ├── parser      (ParserType)
      ├── capabilities (CapabilityType[])
      ├── endpoints    (Endpoint[])
      └── ...
      │
      ▼
 Connector Factory ──── Connector Registry
      │                       │
      ▼                       ▼
  Connector (abstract)    (registered classes)
      │
      ├── connect()
      ├── health()
      ├── fetch()
      ├── supports()
      └── close()
```

## Components

### 1. Connector (abstract base)

`src/connectors/base.py` — defines the contract every connector must implement:

| Method | Returns | Purpose |
|---|---|---|
| `connect()` | `ConnectionResult` | Establish connection to the data source |
| `health()` | `ConnectionHealth` | Return structured health information |
| `fetch(request)` | `FetchResult` | Retrieve data from the source |
| `supports(parser_type, capability)` | `bool` | Check whether a parser or capability is supported |
| `close()` | `None` | Tear down the connection |

**Class methods:**

| Method | Returns | Purpose |
|---|---|---|
| `metadata()` | `ConnectorMetadata` | Static metadata (name, version, parser types) |
| `capabilities()` | `ConnectorCapabilities` | Static capability declaration |

### 2. Models

`src/connectors/models.py` — all data transfer objects are immutable (`frozen=True`):

- **`ConnectorMetadata`** — name, version, description, parser_types, capabilities
- **`ConnectorCapabilities`** — parser type set, capability type set, supports_search, supports_streaming, max_concurrent_requests
- **`ConnectionResult`** — success, status, message, connected_at, metadata
- **`FetchRequest`** — url, parser_type, capabilities, parameters
- **`FetchResult`** — success, data, content_type, size_bytes, fetched_at, metadata
- **`ConnectionHealth`** — initialized, available, status, parser_supported, capabilities, version, last_health_check, details
- **`ConnectionStatus`** — INITIALIZED, CONNECTED, DISCONNECTED, ERROR
- **`Document`** (v1.1) — parsed document model with id (UUID), authority_id, source_url, canonical_url, title, summary, content, content_type, language, publication_date, last_modified, retrieved_at, document_type, metadata (dict), discovered_links (list[str])

### 3. Exception Hierarchy

`src/connectors/exceptions.py`:

```
ConnectorError (base)
├── ConnectorConfigurationError
├── UnsupportedConnectorError
├── ConnectorRegistrationError
├── ConnectorInitializationError
├── ConnectionError
└── CapabilityError
```

### 4. Connector Registry

`src/connectors/registry.py` — stores connector **classes** (not instances):

- `register(connector_class)` — register by `ConnectorMetadata.name`
- `unregister(name)` — remove a registration
- `lookup_by_parser(parser_type)` — find connectors supporting a parser
- `lookup_by_capability(capability)` — find connectors supporting a capability
- `list_registered()` — list all registered connector names
- `get(name)` — retrieve a connector class by name
- `validate_registrations()` — check for missing capabilities, invalid parser-to-capability mappings

**Validation rules:**
- Duplicate `name` registrations raise `ConnectorRegistrationError`
- `validate_registrations()` warns if a parser type (e.g. `PDF`) is declared but the corresponding capability is missing
- Manual parser type is exempt from capability validation

### 5. Connector Factory

`src/connectors/factory.py` — creates connector **instances** from `Authority` objects:

1. Resolves candidates by parser type and capability from the registry
2. Deduplicates candidates
3. If multiple candidates match, selects the best match using a scoring heuristic:
   - +10 for matching parser type
   - +5 per matching capability
   - +20 if `ConnectorCapabilities.compatible_with()` returns `True`
4. Instantiates the winning class with the `Authority` object
5. `create_all(authorities)` — batch creation with partial-failure reporting

**Open/Closed:** Adding a new connector requires only implementing the class and registering it. The factory requires zero modifications.

### 6. Connector Manager

`src/connectors/manager.py` — lifecycle coordination:

- `get_connector(authority_id)` — returns a cached connector instance (creates + connects on first call)
- `shutdown(authority_id|None)` — close and remove one or all connectors
- `health(authority_id|None)` — return health for one or all connectors
- `list_authorities()` — return IDs of active connector instances
- `stats` — `ConnectorStats` object with counters for created, lookups, shutdowns, errors

**Dependency injection:** The manager accepts `ConnectorFactory`, `ConnectorRegistry`, `AuditLogger`, and `AuthorityResolver` in its constructor.

## Integration with Authority Registry

1. **Connector selection** is driven entirely by `Authority.parser` and `Authority.capabilities`
2. **`ConnectorCapabilities.compatible_with(authority)`** validates that a connector can handle a given authority
3. **`AuthorityResolver`** resolves authority IDs to `Authority` objects
4. The factory receives an `Authority` object and inspects its metadata — no agent-level connector selection logic

## HTTP Infrastructure

`src/connectors/http/` — shared HTTP layer consumed by all network-based connectors:

### Components

- **`HttpClient`** (abstract base) — `get(url, headers, params, timeout)`, `head()`, `request(Request)`, `health()`, `close()`
- **`UrllibHttpClient`** — stdlib implementation with no external dependencies (urllib.request)
- **`HttpConfig`** — frozen model: timeout (30s), connect_timeout (10s), read_timeout (20s), max_redirects (5), retry_count (3), retry_delay (1s), max_response_size (10MB), user_agent, verify_ssl, default_headers, follow_redirects
- **`Request`** / **`Response`** — immutable models with `response.text` property, `response.ok`, `response.is_redirect`
- **`RetryPolicy`** (abstract) — `max_retries`, `delay(attempt)`, `should_retry(attempt, response, exception)`
  - `ExponentialBackoffRetry` — exponential backoff up to 30s max delay
  - `NoRetry` — max_retries = 0, never retries
- **Exception hierarchy** — `HttpError` → `TimeoutError`, `RedirectError`, `ConnectionError`, `InvalidResponseError`, `UnsupportedMimeTypeError`, `ResponseTooLargeError`, `InvalidUrlError`, `HttpConfigurationError`

### Key design decisions:
- All connectors use `HttpClient` interface only — no direct urllib/requests usage
- `UrllibHttpClient` uses stdlib only (zero new dependencies)
- Retry policy is a replaceable strategy (ExponentialBackoffRetry or NoRetry)
- Response size is capped at `HttpConfig.max_response_size` (default 10MB)

## HTML Connector

`src/connectors/html/` — production-ready HTML scraper connector:

### Components

- **`HtmlParser`** — orchestrates metadata extraction + content extraction
- **`HtmlContentExtractor`** — SAX-style content extraction using stdlib `html.parser.HTMLParser`
  - Strips `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`, `<aside>`, `<noscript>`, `<iframe>`, `<form>` and more
  - Extracts text from `<p>`, `<h1>-<h6>`, `<li>`, `<blockquote>`, `<pre>`, `<code>`, `<td>`, `<th>`, `<article>`, `<main>`, `<section>`
  - Normalizes whitespace and collapses excessive newlines
- **`HtmlMetadataExtractor`** — regex-based metadata extraction
  - Title from `<title>`
  - Canonical URL from `<link rel="canonical">`
  - Language from `<html lang="...">`
  - Meta description, keywords, publication date
  - Open Graph article:published_time / article:modified_time
  - Link discovery from `<a href="...">` (skips `#fragment` and `javascript:` links)
- **`HTMLConnector`** — implements `Connector` interface using `HttpClient` + `HtmlParser`
  - `parser_types=[ParserType.HTML]`, `capabilities=[CapabilityType.HTML, CapabilityType.SEARCH]`
  - Validates MIME type before parsing (accepts `text/html`, `application/xhtml+xml`)
  - Raises `UnsupportedContentTypeError`, `EmptyContentError`, `HtmlParseError`
  - `fetch_document(request)` convenience method returns parsed `Document` directly

### Exception hierarchy:
```
HtmlError (→ ConnectorError)
├── HtmlParseError
├── UnsupportedContentTypeError
├── EmptyContentError
└── ExtractionError
```

### Usage:
```python
from src.connectors.html import HTMLConnector
from src.connectors.http.client import UrllibHttpClient
from src.connectors.models import FetchRequest

http_client = UrllibHttpClient()
connector = HTMLConnector(authority, http_client=http_client)
connector.connect()

# Low-level
result = connector.fetch(FetchRequest(url="https://regulator.gov/page"))
doc = Document.model_validate_json(result.data)

# High-level
doc = connector.fetch_document(FetchRequest(url="https://regulator.gov/page"))
```

## Scoring Constants

`src/connectors/scoring.py` — all magic numbers used in connector selection:

| Constant | Value | Usage |
|---|---|---|
| `EXACT_PARSER_MATCH_SCORE` | 10 | Exact parser type match |
| `CAPABILITY_MATCH_SCORE` | 5 | Per-matching capability |
| `FULL_COMPATIBILITY_BONUS` | 20 | `compatible_with()` returns true |

These are the only tuning knobs for the factory's best-match algorithm.

## Extension Guide

To add a new connector (e.g., an RSS scraper):

```python
from src.connectors.base import Connector
from src.connectors.models import (
    ConnectorMetadata, ConnectorCapabilities,
    ConnectionResult, ConnectionHealth, FetchRequest, FetchResult,
)
from src.authority.models import Authority, ParserType, CapabilityType

class MyRSSConnector(Connector):
    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="MyRSSConnector",
            parser_types=[ParserType.RSS],
            capabilities=[CapabilityType.RSS],
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            parser_types=frozenset({ParserType.RSS}),
            capability_types=frozenset({CapabilityType.RSS}),
        )

    def connect(self) -> ConnectionResult: ...
    def health(self) -> ConnectionHealth: ...
    def fetch(self, request: FetchRequest) -> FetchResult: ...
    def close(self) -> None: ...

# Register it
from src.connectors.registry import ConnectorRegistry
registry = ConnectorRegistry()
registry.register(MyRSSConnector)
```

No changes needed to the factory, manager, or any agent code.

## Dependency Flow

```
                     ┌─────────────────┐
                     │ AuthorityRegistry│
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │AuthorityResolver │
                     └────────┬────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
      ┌──────────────────┐      ┌──────────────────┐
      │ ConnectorFactory  │      │ConnectorRegistry  │
      │ (create instance) │      │ (store classes)   │
      └────────┬─────────┘      └────────┬─────────┘
               │                         │
               └──────────┬──────────────┘
                          ▼
                 ┌────────────────┐
                 │ ConnectorManager│
                 │ (lifecycle)    │
                 └────────┬───────┘
                          │
                          ▼
                 ┌────────────────┐
                 │   Connector    │
                 │ (abstract)     │
                 └────────────────┘
```

## Design Patterns

| Pattern | Usage |
|---|---|
| **Strategy** | Each connector implements the same interface with different strategies for data retrieval |
| **Registry** | Connector classes are registered and looked up by parser type and capability |
| **Factory** | `ConnectorFactory` creates the correct connector based on authority metadata |
| **Dependency Injection** | Manager accepts factory, registry, logger, and resolver as constructor parameters |
| **Template Method** | `Connector` base class provides `supports()` with configurable behavior via abstract methods |
| **Open/Closed** | New connector types require no changes to factory, manager, or registry infrastructure |

## RSS Connector

`src/connectors/rss/` — production-ready RSS 2.0 and Atom feed connector:

### Architecture

```
RSSConnector
      │
      ├── HttpClient (shared HTTP infrastructure)
      │
      ▼
  RSSParser
      │
      ├── _detect_feed_type()  → RSS or Atom
      ├── _parse_rss_feed()    → RSS 2.0 item extraction
      ├── _parse_atom_feed()   → Atom entry extraction
      │
      ▼
  Document models
```

### Components

- **`RssConfig`** — frozen model: max_feed_size (10MB), max_entries (500), max_content_length (100KB)
- **`RSSParser`** — standalone feed parser with no network I/O; independently testable
  - `parse(xml_content, source_url, authority_id)` → `list[Document]`
  - `is_supported_content_type(content_type)` → `bool`
  - Automatically detects RSS 2.0 vs Atom via root element inspection
  - Uses stdlib `xml.etree.ElementTree` only (zero new dependencies)
  - DOCTYPE stripping for XXE protection
- **`RSSConnector`** — implements `Connector` interface using `HttpClient` + `RSSParser`
  - `parser_types=[ParserType.RSS]`, `capabilities=[CapabilityType.RSS]`
  - Accepts MIME types: `application/rss+xml`, `application/atom+xml`, `application/xml`, `text/xml`
  - `fetch_documents(request)` convenience method returns `list[Document]` directly

### Feed Parsing Strategy

| Feature | RSS 2.0 | Atom |
|---|---|---|
| Root element | `<rss version="2.0">` | `<feed xmlns=".../Atom">` |
| Feed metadata | `<channel>` children | `<feed>` children |
| Entry element | `<item>` | `<entry>` |
| Entry URL | `<link>` | `<link rel="alternate"> href` |
| Publication date | `<pubDate>` (RFC 2822) | `<published>` (ISO 8601) |
| Updated date | N/A | `<updated>` (ISO 8601) |
| Content | `<content:encoded>` preferred, fallback `<description>` | `<content>` preferred, fallback `<summary>` |
| GUID | `<guid>` | `<id>` |
| Categories | `<category>` text | `<category term="...">` |

### Feed Metadata Extraction

Extracted from feed-level XML elements and stored in log output (not persisted):

- **title** — feed title
- **description/subtitle** — feed description
- **language** — RSS `<language>` or Atom `html lang`
- **copyright/rights** — feed copyright
- **generator** — feed generator
- **categories** — feed-level category tags
- **last build date / updated** — feed update timestamp

### Content Handling

- `<content:encoded>` (RSS) or `<content>` (Atom) preferred over summary
- Scripts, styles, iframes, objects, embeds stripped via regex sanitization
- Long content truncated at `max_content_length`
- Preservation: paragraphs, lists, inline formatting
- All entry content stored as `text/html` content type

### Exception Hierarchy

```
RssError (→ ConnectorError)
├── RssParseError
├── UnsupportedContentTypeError
├── UnsupportedFeedFormatError
├── EmptyFeedError
├── FeedTooLargeError
└── InvalidXmlError
```

### Security

- XXE protection via DOCTYPE stripping before XML parsing
- No external entity resolution (stdlib default)
- No linked resource fetching
- No embedded content execution
- Feed size limits prevent oversized payloads
- Redirect limits inherited from HTTP infrastructure

### Performance

- Single-pass XML parsing via `xml.etree.ElementTree`
- Feed type detection before full parse
- Entry count limited at configurable `max_entries`
- Content length limited at configurable `max_content_length`
- Zero external dependencies for feed parsing

### Integration

1. **Connector Registry** — registers with `ParserType.RSS` and `CapabilityType.RSS`
2. **Connector Factory** — automatically selected when `authority.parser == "rss"`
3. **Connector Manager** — full lifecycle support (get, shutdown, health, stats)
4. **Authority Registry** — no authority-specific logic; driven entirely by `Authority.parser` and `Authority.capabilities`

### Usage

```python
from src.connectors.rss import RSSConnector, RSSParser, RssConfig
from src.connectors.http.client import UrllibHttpClient
from src.connectors.models import FetchRequest

http_client = UrllibHttpClient()
connector = RSSConnector(authority, http_client=http_client)
connector.connect()

# Low-level
result = connector.fetch(FetchRequest(url="https://regulator.gov/rss"))

# High-level
documents = connector.fetch_documents(FetchRequest(url="https://regulator.gov/rss"))
```

## REST API Connector

The REST API Connector retrieves regulatory documents from REST-based authority APIs and converts responses into the immutable Document model. It is generic and configurable — multiple authorities can use it without writing custom connector logic.

### Architecture

```
Authority YAML Config (parser: api)
         │
         ▼
   APIConnector ───── HttpClient (shared HTTP infra)
         │
         ▼
    APIParser
         │
         ▼
   list[Document]
```

The connector separates networking (APIConnector) from response transformation (APIParser).

### Components

#### `ApiConfig` (`src/connectors/api/parser.py`)

Configuration model for API endpoints. Supports:
- `endpoint_url` — base URL for the API
- `method` — HTTP method (GET, POST)
- `headers` — default headers (e.g., Authorization, Accept)
- `auth_type` — authentication type (`none`, placeholder for future)
- `response_format` — `json` or `json_array`
- `field_mapping` — maps JSON response fields to Document fields
- `pagination` — optional pagination strategy
- `filter_params` — default query/filter parameters
- `max_response_size` — response size limit

#### `ApiFieldMapping` (`src/connectors/api/parser.py`)

Maps JSON response fields to Document fields:

| Document Field | Config Path | Description |
|---|---|---|
| `title` | `field_mapping.title` | JSON path to title field |
| `content` | `field_mapping.content` | JSON path to content field |
| `summary` | `field_mapping.summary` | JSON path to summary |
| `publication_date` | `field_mapping.publication_date` | JSON path to ISO 8601 date |
| `last_modified` | `field_mapping.last_modified` | JSON path to update date |
| `source_url` | `field_mapping.source_url` | JSON path to source URL |
| `document_type` | `field_mapping.document_type` | JSON path to document type |
| `language` | `field_mapping.language` | JSON path to language code |
| `metadata` | `field_mapping.metadata` | Dict of `{meta_key: json_path}` |

The `items_path` field specifies where the array of items lives within a wrapped response (e.g., `data.items`). If not set, the parser assumes either a JSON array at root or a single JSON object.

No authority-specific mapping logic exists inside the connector — all behavior is driven by configuration.

#### Pagination Strategies

Four configurable pagination strategies:

| Strategy | Type | Parameters | Behavior |
|---|---|---|---|
| **Page Number** | `page_number` | `page_param`, `size_param`, `first_page`, `total_pages_path` | Sequential page-based requests with configurable page size |
| **Offset** | `offset` | `offset_param`, `limit_param`, `max_offset` | Offset/limit pagination with configurable max offset |
| **Cursor** | `cursor` | `cursor_param`, `cursor_path`, `max_pages` | Cursor-based pagination; reads next cursor from response |
| **Next Link** | `next_link` | `link_path`, `max_pages` | Follows `links.next` URLs from response body |

Pagination is optional — when no strategy is configured, the connector returns a single page of results.

### Supported Response Formats

- **JSON** — single object treated as one document
- **JSON arrays** — each element treated as a separate document
- Wrapped responses supported via `items_path`

Unsupported formats (XML, GraphQL, etc.) raise `UnsupportedResponseFormatError`.

### MIME Validation

Accepts: `application/json`
Rejects: `text/html`, `application/xml`, `application/pdf`, etc.

### Error Handling

| Scenario | Exception |
|---|---|
| Invalid JSON | `ApiParseError` |
| Empty response | `EmptyResponseError` |
| Unsupported MIME type | `UnsupportedContentTypeError` |
| Unsupported response format | `UnsupportedResponseFormatError` |
| HTTP timeout | `HttpTimeoutError` (propagated from HTTP layer) |
| Connection failure | `HttpConnectionError` (propagated) |
| 401/403 Authentication | `ApiAuthenticationError` |
| 429 Rate limit | `ApiRateLimitedError` |
| 5xx Server error | `ApiServerError` |
| Generic HTTP error | `HttpError` (propagated) |

Raw HTTP exceptions are never exposed — all connector-specific exceptions inherit from `ApiError` (which inherits from `ConnectorError`).

### Exception Hierarchy

```
ConnectorError
  └── ApiError
        ├── ApiParseError
        ├── UnsupportedContentTypeError
        ├── UnsupportedResponseFormatError
        ├── EmptyResponseError
        ├── ApiRateLimitedError
        ├── ApiServerError
        └── ApiAuthenticationError
```

### Security

- **HTTPS validation** — delegated to shared HTTP infrastructure
- **Malformed URLs** — rejected by HTTP client validation
- **Oversized payloads** — checked via `max_response_size` config
- **Invalid JSON** — caught and wrapped as `ApiParseError`
- **Redirect limits** — enforced by shared HTTP client (max 5 redirects)
- No script execution, no automatic link following

### Performance

- Parser instances are reused across fetch calls
- No intermediate object copies during mapping
- Streaming-ready: connector uses urllib's streaming response
- Prepared for async: all networking goes through `HttpClient` interface

### Integration

- **Parser type**: `ParserType.API`
- **Capabilities**: `CapabilityType.API`, `CapabilityType.JSON`
- Registered automatically via `ConnectorRegistry` when `APIConnector.metadata()` declares `parser_types=[ParserType.API]`
- Instantiates via `ConnectorFactory` when an authority has `parser: api`
- No framework modifications required

### Usage

```python
from src.connectors.api import APIConnector, APIParser, ApiConfig, ApiFieldMapping
from src.connectors.http import UrllibHttpClient

config = ApiConfig(
    endpoint_url="https://api.regulator.gov/v1/documents",
    field_mapping=ApiFieldMapping(
        title="title",
        content="body",
        summary="description",
        publication_date="published_at",
        document_type="doc_type",
        items_path="data.items",
    ),
    pagination=ApiPaginationPageNumber(page_size=50, first_page=1),
    filter_params={"status": "active"},
)

http_client = UrllibHttpClient()
parser = APIParser(config)
connector = APIConnector(authority, http_client=http_client, api_config=config)
connector.connect()

# Low-level
result = connector.fetch(FetchRequest(url=config.endpoint_url))

# High-level
documents = connector.fetch_documents(FetchRequest(url=config.endpoint_url))
```

### Extension Guidelines

To connect to a new regulatory API:

1. Define an authority in YAML with `parser: api` and `capabilities: [api, json]`
2. Create an `ApiConfig` with the appropriate field mappings and pagination strategy
3. Pass the config to `APIConnector` via the `api_config` parameter
4. No code changes needed — the connector is fully configuration-driven

## Test Coverage

**967 total tests** (865 existing + 102 new API connector tests)

### Connector Framework (78 tests)
- **Models** (4 classes): defaults, frozen immutability, parser/capability compatibility
- **Exception hierarchy** (1 class): inheritance, raising, message preservation
- **Connector interface** (1 class): abstract instantiation guard, disabled authority rejection, lifecycle methods, `supports()` dispatch
- **Connector Registry** (1 class): register/list/unregister, duplicate detection, lookup by parser/capability, validation warnings
- **Connector Factory** (1 class): create from authority, batch creation, partial failure, best-match resolution, empty registry
- **Connector Manager** (1 class): get/reuse/shutdown, health collection, statistics, error cases
- **Scoring** (4 tests): named constant correctness, deterministic ordering, known values

### HTTP Infrastructure (62 tests)
- **Models** (2 classes): defaults, frozen, text encoding, ok/is_redirect properties
- **Exception hierarchy** (1 class): all 9 exception types inherit from `HttpError`, message preservation
- **RetryPolicy** (2 classes): exponential backoff, no retry, retryable status codes/exceptions, delay calculation, validation
- **Config** (1 class): defaults, frozen, custom values, user agent
- **UrllibHttpClient** (1 class): validation (scheme/host), convenience methods, retry integration, mocked requests (success, error, timeout, redirect, oversized responses, retry exhaustion), edge cases (OSError, URL building, size checking)

### HTML Connector (55 tests)
- **HtmlContentExtractor** (10 tests): content extraction, excluded tag stripping, whitespace normalization, empty input, reset, nested excluded tags, heading/list extraction
- **HtmlMetadataExtractor** (14 tests): title, canonical URL, meta description, keywords, language, publication date (meta + OG), link discovery (skip anchor/javascript)
- **HtmlParser** (7 tests): full document parsing, empty/whitespace error, invalid HTML grace, metadata propagation
- **HTMLConnector** (16 tests): metadata, capabilities, connect/close lifecycle, health states, fetch with/without HTTP, MIME validation, fetch_document, HTTP error propagation, exception hierarchy
- **MIME Validation** (7 tests): supported types, charset variants, rejection of PDF/JSON, empty string allowance

### RSS Connector (92 tests)
- **Date parsing** (10 tests): RSS RFC 2822, Atom ISO 8601, None/empty/invalid inputs, timezone handling
- **Content sanitization** (9 tests): script/style/iframe/noscript/object/embed stripping, None/empty/truncation, paragraph preservation
- **Safe XML parsing** (4 tests): valid XML, malformed XML, bytes input, empty input
- **Feed type detection** (4 tests): RSS detection, Atom detection, unsupported RSS versions, unknown root tag
- **RSS 2.0 parsing** (13 tests): full feed, per-item metadata, missing dates, empty feed, minimal items, content:encoded preference, script stripping, max entries, max content length, feed size limit
- **Atom parsing** (5 tests): full feed, per-entry metadata, missing links, empty feed, minimal entries
- **Parser error handling** (4 tests): malformed XML, empty content, invalid format, namespace rejection
- **Document conversion** (8 tests): frozen immutability, UUID generation, authority_id mapping, content type, document type, retrieved_at, serialization roundtrip, entry count limit
- **MIME support** (4 tests): supported/unsupported types, charset variants, case insensitivity
- **Connector lifecycle** (7 tests): metadata, capabilities, connect, close, health states, HTTP configuration
- **Connector fetch** (8 tests): without HTTP, RSS success, Atom success, MIME rejection, empty content, HTTP errors, timeout, oversized feed
- **Fetch documents** (2 tests): success path, failure path
- **MIME validation** (8 tests): all 4 supported types, charset, rejection of HTML/JSON, empty string
- **Exception hierarchy** (5 tests): all subclasses inherit from RssError, RssError inherits from ConnectorError, message preservation
- **Config** (3 tests): defaults, custom values, frozen

### API Connector (102 tests)
- **JSON path extraction** (8 tests): simple/nested/deeply nested keys, missing/null/non-dict intermediates, empty path, list access
- **Item extraction** (6 tests): root list, root dict, nested items path, missing path, non-list path, scalar rejection
- **Timestamp parsing** (9 tests): UTC Zulu, offset, milliseconds, None/empty/invalid, non-string, non-UTC offset
- **Valid JSON parsing** (7 tests): single object, array, wrapped array, unmapped fields, bytes input, source URL fallback, content type
- **Missing field handling** (3 tests): optional fields, None values, empty strings
- **Parser error handling** (7 tests): malformed JSON, empty body, whitespace, null JSON, empty array, unsupported content type, empty content type
- **Single document parsing** (3 tests): success, empty array, with content type
- **Document conversion** (6 tests): frozen immutability, UUID, authority_id, retrieved_at, serialization, default document type
- **MIME support** (4 tests): supported/unsupported types, charset, case insensitivity
- **Config** (7 tests): ApiConfig defaults/custom/frozen, ApiFieldMapping has_mappings
- **Pagination strategies** (8 tests): all 4 strategies defaults, page number params, offset params, cursor params, next-link params
- **Connector lifecycle** (7 tests): metadata, capabilities, connect, close, health states, HTTP configuration
- **Connector fetch** (13 tests): without HTTP, JSON success, array success, MIME rejection, empty body, HTTP error propagation, timeout, 401/403/429/5xx status codes, override params, custom headers, invalid JSON
- **Paginated fetch** (3 tests): page number, next-link, cursor
- **Fetch documents** (2 tests): success path, failure path
- **MIME validation** (5 tests): JSON, charset variant, rejection of HTML/XML/PDF, empty string
- **Exception hierarchy** (3 tests): all subclasses inherit from ApiError, message preservation

## Extension Points

- **New response formats** — extend `APIParser` to support XML, CSV, or other formats
- **Authentication** — add auth providers to `api_config.auth_type` (currently supports `none` only)
- **Rate limiting layer** — wrapper connector or middleware
- **Caching layer** — wrapper connector that delegates to a base connector
