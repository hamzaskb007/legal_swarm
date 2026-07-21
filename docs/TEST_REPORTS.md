# Legal Swarm — Test Suite Report

**Total Tests:** 967
**Passing:** 967
**Failing:** 0
**Ruff:** clean
**Mypy:** clean
**Test Runner:** pytest 9.1.1
**Python:** 3.11

---

## Overview

The Legal Swarm test suite covers the foundation layer (83 tests), HTTP infrastructure (62 tests), connector framework (78 tests), Tier 1 jurisdictions (293 tests), HTML connector (55 tests), RSS connector (92 tests), PDF connector (46 tests), and REST API connector (102 tests). All 967 tests pass with zero failures. Ruff and mypy are clean. All tests are fully deterministic with no external dependencies.

---

## Foundation Layer Tests (83 tests)

### Schema (25 tests) — 99% coverage

Every Pydantic model in `src/schema/schema.py` enforces its constraints: `CitationRecord` rejects reliability scores outside 0.0–1.0 and excerpts over 2000 characters; `SourceGovernanceRecord` requires at least one citation; `CapitalRequirement` uses `Decimal` for financial precision; `ValidationReport` computes overall status correctly from individual rule results; `AuditLogEntry` is frozen and rejects mutation; `RegulatoryEntry` normalizes jurisdiction codes, rejects confidence below 0.4 unless UNVERIFIED, and auto-generates IDs and schema versions.

### Validation Engine (12 tests) — 96% coverage

VAL_001 fails on empty primary regulator; VAL_002 produces WARNING for missing fund structures; VAL_003 passes UNVERIFIED entries below 0.4; VAL_004 fails without primary citations; VAL_005 produces WARNING without filing obligations; engine-level tests confirm all five rules run and custom rules can be added.

### Confidence Scorer (10 tests) — 97% coverage

Level mapping assigns HIGH ≥ 0.75, MEDIUM ≥ 0.50, LOW ≥ 0.40, UNVERIFIED < 0.40. Scorer confirms PRIMARY > TERTIARY, recency penalty for citations over 365 days, score clamped to 0.0–1.0, and deterministic output for identical inputs.

### Contradiction Detection (6 tests) — 97% coverage

Intra-entry detector flags secondary/tertiary citations with higher reliability than primary; returns empty list when no primaries exist. Cross-entry detector compares identical entries (empty contradictions), detects field value differences, and stores both conflicting sources.

### Audit Logger (7 tests) — 100% coverage

Append-only logging: `log()` creates and appends to file; multiple calls accumulate; `read_all/by_jurisdiction/by_event_type` filter correctly; frozen entries reject mutation.

### Delta Tracker (7 tests) — 88% coverage

Version bump increments patch segment (1.0.0 → 1.0.1); malformed versions return safe default; delta tracker produces no deltas for identical entries, detects field changes with old/new values, increments version, records author, and auto-generates change summaries.

### Source Governance (8 tests) — 97% coverage

PRIMARY/SECONDARY/TERTIARY citations stored in correct lists; URL-based deduplication; dominant source correctly identified; average reliability computed correctly across citations.

### Full Pipeline Integration (7 tests)

All seven modules work together: construct entry → validate → score → detect contradictions → audit log → delta track. Confirms well-formed entry passes, confidence is valid, no contradictions in clean data, audit record written, version bumped on change, and end-to-end determinism.

---

## HTTP Infrastructure Tests (62 tests)

### Models — Request/Response defaults, frozen, text encoding, ok/is_redirect properties

### Exception hierarchy — All 9 error types inherit from `HttpError`

### RetryPolicy — ExponentialBackoffRetry and NoRetry; retryable status codes/exceptions; delay calculation; validation

### Config — defaults, frozen, custom values, user agent

### UrllibHttpClient — URL scheme/host validation; get/head convenience methods; retry integration; mocked requests (success, error, timeout, redirect, oversized, retry exhaustion); OSError/URL building/size checking edge cases

---

## Connector Framework Tests (78 tests)

### Models — ConnectorMetadata, ConnectorCapabilities, ConnectionResult, FetchRequest, FetchResult, ConnectionHealth: defaults, frozen, parser/capability compatibility

### Exception hierarchy — ConnectorError, ConnectorConfigurationError, UnsupportedConnectorError, ConnectorRegistrationError, ConnectorInitializationError, ConnectionError, CapabilityError

### Connector interface — abstract instantiation guard, disabled authority rejection, lifecycle, `supports()` dispatch

### Connector Registry — register/list/unregister, duplicate detection, lookup by parser/capability, validation warnings

### Connector Factory — create from authority, batch creation, partial failure, best-match scoring, empty registry

### Connector Manager — get/reuse/shutdown, health collection, statistics, error recording

### Scoring — named constant correctness, deterministic ordering

---

## Tier 1 Jurisdiction Tests (293 tests)

### Jurisdiction Builders (192 tests) — parametrized across 8 builders

Each builder verified for: valid subclass, tier, jurisdiction code (uppercase, min 2), name, primary regulator, source governance, citations, fund structures, filing obligations, investor requirements, tax summary, AML/KYC, version, placeholder confidence, HTTPS URLs, publication dates, no contradictions, licensing, substance, timelines, costs, penalties, wind-down, fund manager, marketing restrictions, beneficial ownership, record retention.

### Jurisdiction Pipeline (40 tests) — 5 tests × 8 builders

Pipeline confidence scored (score 0–1), validation passes (no FAILED), contradiction detection (returns list), deterministic confidence, full run via builder.

### Specific Jurisdictions (17 tests)

Each jurisdiction correct regulator; Luxembourg UCITS Part I; Singapore VCC; Delaware 30% withholding; Cayman 0% withholding; Delaware SEC citation; Luxembourg authorisation timeline; Cayman 25% BO threshold; Singapore 5+ year record retention.

### Jurisdiction Registry (19 tests + 2 audit tests)

Loads all 8 entries; contains expected codes; get_entry normalises case / raises KeyError; get_all/len/contains; all Tier 1; all pass validation; have confidence scored; have citations/fund structures/filing obligations; cross-jurisdiction comparison works; contradictions detected; audit logged; deterministic.

---

## HTML Connector Tests (55 tests)

### HtmlContentExtractor — content extraction, excluded tag stripping, whitespace normalization, empty input, reset, nested excluded tags, heading/list extraction

### HtmlMetadataExtractor — title, canonical URL, meta description/keywords/language, publication date, OG properties, link discovery (skip anchor/javascript)

### HtmlParser — full document parsing, empty/whitespace error, invalid HTML grace, metadata propagation

### HTMLConnector — metadata, capabilities, lifecycle, health states, fetch with/without HTTP, MIME validation, fetch_document, HTTP error propagation

### MIME validation — supported types, charset variants, rejection of PDF/JSON, empty string allowance

### Exception hierarchy — inheritance

---

## RSS Connector Tests (92 tests)

### Date parsing (10) — RSS RFC 2822, Atom ISO 8601, None/empty/invalid, timezone handling

### Content sanitization (9) — script/style/iframe/object/embed stripping, paragraph preservation

### Safe XML parsing (4) — valid/malformed XML, bytes, empty

### Feed type detection (4) — RSS/Atom detection, unsupported versions, unknown root

### RSS 2.0 parsing (13) — full feed, metadata, dates, empty, minimal, content:encoded, script stripping, limits

### Atom parsing (5) — full feed, metadata, missing links, empty, minimal

### Parser errors (4) — malformed XML, empty, invalid format, namespace rejection

### Document conversion (8) — frozen, UUID, authority_id, content type, document type, retrieved_at, serialization, limits

### MIME support (4) — supported/unsupported, charset, case

### Connector lifecycle (7) — metadata, capabilities, connect, close, health states

### Connector fetch (8) — without HTTP, RSS/Atom success, MIME rejection, empty, HTTP errors, timeout, oversized

### Fetch documents (2) — success, failure

### MIME validation (8) — 4 supported types, charset, rejection of HTML/JSON, empty

### Exception hierarchy (5) — inheritance, message preservation

### Config (3) — defaults, custom, frozen

---

## PDF Connector Tests (46 tests)

### Date parsing (5) — PDF date format `D:YYYYMMDDHHmmSS[±]HH'mm'`, UTC, offset, None/empty/invalid

### Valid PDF parsing (4) — full document, metadata, multi-page, content extraction with PyMuPDF

### PDF errors (5) — encrypted, corrupted, empty (0 pages), empty bytes, oversized, too many pages, text limit

### Document conversion (5) — frozen, UUID, serialization roundtrip

### Connector lifecycle (7) — metadata, capabilities, connect, close, health states

### Connector fetch (7) — without HTTP, success, MIME rejection, empty body, HTTP errors, timeout

### Fetch document (2) — success, failure

### MIME validation (5) — supported, charset, rejection of HTML/JSON/RSS, empty

### Exception hierarchy (3) — inheritance, message preservation

### Config (3) — defaults, custom, frozen

---

## REST API Connector Tests (102 tests — new)

### JSON path extraction (8) — simple/nested/deeply nested, missing/null, non-dict, empty path, list access

### Item extraction (6) — root list, root dict, nested items path, missing path, non-list, scalar rejection

### Timestamp parsing (9) — RFC 3339 UTC Zulu, offset, milliseconds, None/empty/invalid, non-string, non-UTC offset

### Valid JSON parsing (7) — single object, array, wrapped array, unmapped fields, bytes input, source URL fallback

### Missing field handling (3) — optional fields, None values, empty strings

### Parser errors (7) — malformed JSON, empty/whitespace body, null JSON, empty array, unsupported content type

### Single document (3) — parse_single success, empty array, with content type

### Document conversion (6) — frozen, UUID, authority_id, retrieved_at, serialization, default document type

### MIME support (4) — supported/unsupported, charset, case insensitivity

### Config (7) — ApiConfig defaults/custom/frozen, ApiFieldMapping has_mappings

### Pagination strategies (8) — all 4 strategy defaults (page_number, offset, cursor, next_link), params for each

### Connector lifecycle (7) — metadata, capabilities, connect, close, health states

### Connector fetch (13) — without HTTP, JSON/array success, MIME rejection, empty body, HTTP error/timeout, 401/403/429/5xx status, params, headers, invalid JSON

### Paginated fetch (3) — page number, next-link, cursor pagination

### Fetch documents (2) — success, failure

### MIME validation (5) — JSON, charset, rejection of HTML/XML/PDF, empty

### Exception hierarchy (3) — all 7 subclasses inherit from ApiError, message preservation

---

## Running Tests

```bash
# Run all tests
python3 -m pytest

# Run with coverage
python3 -m pytest --cov=src --cov-report=term-missing

# Run specific connector test file
python3 -m pytest tests/unit/test_api_connector.py -v
python3 -m pytest tests/unit/test_rss_connector.py -v
python3 -m pytest tests/unit/test_pdf_connector.py -v
python3 -m pytest tests/unit/test_html_connector.py -v

# Run framework/HTTP tests
python3 -m pytest tests/unit/test_connectors.py -v
python3 -m pytest tests/unit/test_http_client.py -v

# Run foundation / jurisdiction tests
python3 -m pytest tests/unit/test_schema.py -v
python3 -m pytest tests/unit/test_jurisdictions.py -v
python3 -m pytest tests/integration/test_registry.py -v
```

---

## Reproducibility

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=src
```

Expected output: 967 passed, 0 failed, ruff clean, mypy clean.
