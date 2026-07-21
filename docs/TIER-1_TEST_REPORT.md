# Test Report

## Test Suite Summary

| Metric               | Value     |
|----------------------|-----------|
| Total test count     | 967       |
| Unit tests           | 940       |
| Integration tests    | 27        |
| Passed               | 967       |
| Failed               | 0         |
| Ruff                 | clean     |
| Mypy                 | clean     |

## Test Categories

### Foundation Layer Tests (83 tests — unchanged)

- **Unit — Schema** (`tests/unit/test_schema.py`): CitationRecord, SourceGovernanceRecord, CapitalRequirement, ConfidenceScore, ValidationReport, AuditLogEntry, RegulatoryEntry
- **Unit — Validation** (`tests/unit/test_validators.py`): HasPrimaryRegulatorRule, HasAtLeastOneFundStructureRule, ConfidenceThresholdRule, HasSourceCitationsRule, FilingObligationsRule, ValidationEngine
- **Unit — Confidence** (`tests/unit/test_confidence.py`): LevelFromScore, ConfidenceScorer (determinism, penalties, clamping)
- **Unit — Contradiction** (`tests/unit/test_contradiction.py`): CitationContradictionDetector, CrossEntryContradictionDetector
- **Unit — Source Governance** (`tests/unit/test_governance.py`): SourceGovernanceManager (dedup, tier sorting, average reliability)
- **Unit — Audit** (`tests/unit/test_audit.py`): AuditLogger (file I/O, read all/by jurisdiction/by event type, immutability)
- **Unit — Versioning** (`tests/unit/test_versioning.py`): DeltaTracker, _bump_version
- **Integration — Pipeline** (`tests/integration/test_pipeline.py`): Full end-to-end pipeline (construction, validation, scoring, contradictions, audit logging, delta tracking, determinism)

### HTTP Infrastructure Tests (62 tests)

- **Unit — Models** (`tests/unit/test_http_client.py`): Request/Response defaults, frozen, text encoding, ok/is_redirect properties
- **Unit — Exception hierarchy**: All 9 error types inherit from `HttpError`, message preservation
- **Unit — RetryPolicy**: ExponentialBackoffRetry, NoRetry, retryable codes/exceptions, delay calculation, validation
- **Unit — Config**: defaults, frozen, custom values, user agent
- **Unit — UrllibHttpClient**: URL validation (scheme/host), convenience methods (get, head), retry integration, mocked requests (success, error, timeout, redirect, oversized response, retry exhaustion), edge cases (OSError, URL building, size checking)

### Connector Framework Tests (78 tests)

- **Unit — Models** (`tests/unit/test_connectors.py`): ConnectorMetadata, ConnectorCapabilities, ConnectionResult, FetchRequest, FetchResult, ConnectionHealth — defaults, frozen, parser/capability compatibility
- **Unit — Exception hierarchy**: ConnectorError, ConnectorConfigurationError, UnsupportedConnectorError, ConnectorRegistrationError, ConnectorInitializationError, ConnectionError, CapabilityError
- **Unit — Connector interface**: abstract instantiation guard, disabled authority rejection, lifecycle, `supports()` dispatch
- **Unit — Connector Registry**: register/list/unregister, duplicate detection, lookup by parser/capability, validation warnings
- **Unit — Connector Factory**: create from authority, batch creation, partial failure, best-match scoring, empty registry
- **Unit — Connector Manager**: get/reuse/shutdown, health collection, statistics, error recording
- **Unit — Scoring**: named constant correctness, deterministic ordering

### Tier 1 Jurisdiction Tests (293 tests — new)

**Unit — Jurisdiction Builders** (`tests/unit/test_jurisdictions.py`):

- `TestJurisdictionBuilders` (parametrized across all 8 builders, 24 tests each = 192 tests):
  - Builder is valid subclass
  - Entry has correct tier (TIER_1)
  - Entry has jurisdiction code (uppercase, min length 2)
  - Entry has jurisdiction name
  - Entry has primary regulator (non-empty)
  - Entry has source governance (citations populated, dominant source set)
  - Entry has primary citations (at least 1)
  - Entry has fund structures (at least 1)
  - Entry has filing obligations (at least 1)
  - Entry has investor requirements
  - Entry has tax summary
  - Entry has AML/KYC framework
  - Entry has version record (1.0.0 with author)
  - Entry has placeholder confidence (UNVERIFIED, 0.0)
  - All citations have real HTTPS URLs with valid reliability scores
  - All citations have publication dates
  - No contradictions at build time
  - Has licensing requirements (list populated, first item has licence_type and issuing_authority)
  - Has substance requirements (local_office_required and local_directors_required set)
  - Has regulatory timelines (list populated, first item has minimum_days > 0)
  - Has regulatory costs (list populated, first item has amount > 0)
  - Has penalty exposure (list populated, first item has maximum_fine_usd > 0)
  - Has wind-down procedure (voluntary_liquidation_available set, typical_duration_days > 0)
  - Has fund manager requirements (local_manager_required and fit_and_proper_required set)
  - Has marketing restrictions (list populated, first item has target_investor_type)
  - Has beneficial ownership rules (register_required set, filing_authority populated)
  - Has record retention policies (list populated, first item has minimum_retention_years > 0)

- `TestJurisdictionPipeline` (parametrized, 5 tests each = 40 tests):
  - Pipeline confidence scored (score 0–1, valid level)
  - Pipeline validation passes (no FAILED status)
  - Pipeline contradiction detection (returns list)
  - Pipeline deterministic confidence (same input → same output)
  - Pipeline full run via builder (confidence updated, contradictions initialised)

- `TestSpecificJurisdictions` (17 tests):
  - Each jurisdiction has correct regulator
  - Luxembourg has UCITS Part I structure
  - Singapore has VCC structure
  - Delaware has 30% withholding tax
  - Cayman Islands has 0% withholding tax
  - Delaware has SEC primary authority citation
  - Luxembourg has authorisation timeline events
  - Cayman Islands beneficial ownership threshold is 25%
  - Singapore record retention minimum is 5+ years

- `TestJurisdictionBuilderBase` (1 test):
  - Placeholder confidence properties

**Integration — Registry** (`tests/integration/test_registry.py`):

- `TestJurisdictionRegistry` (19 tests):
  - Registry loads all 8 Tier 1 jurisdictions
  - Registry contains expected jurisdiction codes
  - `get_entry` returns entry for valid code
  - `get_entry` normalises case
  - `get_entry` raises KeyError for unknown codes
  - `get_all` returns all entries
  - `__len__` returns correct count
  - `__contains__` works (case-insensitive)
  - All entries are Tier 1
  - All entries pass validation (no FAILED)
  - All entries have confidence scores (not UNVERIFIED)
  - All entries have primary citations
  - All entries have fund structures
  - All entries have filing obligations
  - Cross-jurisdiction comparison works
  - Contradictions detected during comparison
  - Comparison between different jurisdictions produces summary
  - Registry access is audit logged
  - Registry is deterministic (same inputs → same outputs)

- `TestRegistryAudit` (2 tests):
  - All entries are audit logged on construction

### HTML Connector Tests (55 tests)

- **HtmlContentExtractor** (10): content extraction, excluded tag stripping, whitespace normalization, empty input, reset, nested excluded tags, heading/list extraction
- **HtmlMetadataExtractor** (14): title, canonical URL, meta description/keywords/language, publication date, OG properties, link discovery (skip anchor/javascript)
- **HtmlParser** (7): full document parsing, empty/whitespace error, invalid HTML grace, metadata propagation
- **HTMLConnector lifecycle** (7): metadata, capabilities, connect, close, health states, HTTP configuration
- **HTMLConnector fetch** (9): without HTTP, success, MIME rejection, empty content, HTTP errors, timeout, fetch_document
- **MIME validation** (7): supported types, charset, rejection of PDF/JSON, empty string
- **Exception hierarchy** (1): inheritance

### RSS Connector Tests (92 tests)

- **Date parsing** (10): RSS RFC 2822, Atom ISO 8601, None/empty/invalid, timezone
- **Content sanitization** (9): script/style/iframe stripping, paragraph preservation
- **Safe XML parsing** (4): valid/malformed XML, bytes, empty
- **Feed type detection** (4): RSS/Atom detection, unsupported versions, unknown root
- **RSS 2.0 parsing** (13): full feed, metadata, dates, empty, minimal, content:encoded, script stripping, limits
- **Atom parsing** (5): full feed, metadata, missing links, empty, minimal
- **Parser errors** (4): malformed XML, empty, invalid format, namespace rejection
- **Document conversion** (8): frozen, UUID, authority_id, content type, document type, retrieved_at, serialization, limits
- **MIME support** (4): supported/unsupported types, charset, case
- **Connector lifecycle** (7): metadata, capabilities, connect, close, health states
- **Connector fetch** (8): without HTTP, RSS/Atom success, MIME rejection, empty, HTTP errors, timeout, oversized
- **Fetch documents** (2): success, failure
- **MIME validation** (8): all 4 supported types, charset, rejection of HTML/JSON, empty
- **Exception hierarchy** (5): inheritance, message preservation
- **Config** (3): defaults, custom, frozen

### PDF Connector Tests (46 tests)

- **Date parsing** (5): PDF date format, UTC, offset, None/empty/invalid
- **Valid PDF parsing** (4): full document, metadata, multi-page, content extraction
- **PDF errors** (5): encrypted, corrupted, empty, empty bytes, oversized, too many pages, text limit
- **Document conversion** (5): frozen, UUID, serialization roundtrip
- **Connector lifecycle** (7): metadata, capabilities, connect, close, health states
- **Connector fetch** (7): without HTTP, success, MIME rejection, empty body, HTTP errors, timeout
- **Fetch document** (2): success, failure
- **MIME validation** (5): supported, charset, rejection of HTML/JSON/RSS, empty
- **Exception hierarchy** (3): inheritance, message preservation
- **Config** (3): defaults, custom, frozen

### REST API Connector Tests (102 tests — new)

- **JSON path extraction** (8): simple/nested/deeply nested, missing/null, non-dict, empty path, list access
- **Item extraction** (6): root list, root dict, nested items path, missing path, non-list, scalar
- **Timestamp parsing** (9): UTC Zulu, offset, milliseconds, None/empty/invalid, non-string, non-UTC offset
- **Valid JSON parsing** (7): single object, array, wrapped array, unmapped, bytes, source URL fallback
- **Missing field handling** (3): optional fields, None values, empty strings
- **Parser errors** (7): malformed JSON, empty/whitespace body, null JSON, empty array, unsupported content type
- **Single document** (3): success, empty array, with content type
- **Document conversion** (6): frozen, UUID, authority_id, retrieved_at, serialization, default type
- **MIME support** (4): supported/unsupported, charset, case
- **Config** (7): ApiConfig defaults/custom/frozen, ApiFieldMapping has_mappings
- **Pagination strategies** (8): all 4 strategy defaults, params for page/offset/cursor/next-link
- **Connector lifecycle** (7): metadata, capabilities, connect, close, health states
- **Connector fetch** (13): without HTTP, JSON/array success, MIME rejection, empty body, HTTP error/timeout, 401/403/429/5xx, params, headers, invalid JSON
- **Paginated fetch** (3): page number, next-link, cursor
- **Fetch documents** (2): success, failure
- **MIME validation** (5): JSON, charset, rejection of HTML/XML/PDF, empty
- **Exception hierarchy** (3): inheritance, message preservation

## Running Tests

```bash
# Run all tests
python3 -m pytest

# Run with coverage
python3 -m pytest --cov=src --cov-report=term-missing

# Run specific test file
python3 -m pytest tests/unit/test_jurisdictions.py
python3 -m pytest tests/unit/test_api_connector.py
python3 -m pytest tests/unit/test_rss_connector.py
python3 -m pytest tests/unit/test_pdf_connector.py
python3 -m pytest tests/unit/test_connectors.py
python3 -m pytest tests/unit/test_http_client.py

# Run specific test class
python3 -m pytest tests/integration/test_registry.py
```

## CI Status

All **967 tests pass**. Ruff and mypy are clean. CI configuration in `.github/workflows/ci.yml` runs the full suite on each push.
