# Test Report

## Test Suite Summary

| Metric               | Value     |
|----------------------|-----------|
| Total test count     | 376       |
| Unit tests           | 349       |
| Integration tests    | 27        |
| Passed               | 376       |
| Failed               | 0         |
| Test coverage        | TBD       |

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

## Running Tests

```bash
# Run all tests
python3 -m pytest

# Run with coverage
python3 -m pytest --cov=src --cov-report=term-missing

# Run specific test file
python3 -m pytest tests/unit/test_jurisdictions.py

# Run specific test class
python3 -m pytest tests/integration/test_registry.py
```

## CI Status

All 376 tests pass. CI configuration in `.github/workflows/ci.yml` runs the full suite on each push.
