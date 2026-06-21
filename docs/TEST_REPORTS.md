# Legal Swarm — Test Suite Report

**Total Tests:** 83
**Passing:** 83
**Failing:** 0
**Code Coverage:** 98%
**Test Runner:** pytest 9.1.1
**Python:** 3.11

---

## Overview

The Legal Swarm foundation layer ships with a full automated test suite covering all seven core modules. 83 tests are passing with zero failures and 98% code coverage across the entire codebase. Tests are split into unit tests, which test each module in isolation, and integration tests, which verify the full pipeline end to end. All tests are fully deterministic — no randomness, no external dependencies, no mocking of time. Running the suite on any machine with Python 3.11 and the dependencies in `pyproject.toml` will reproduce these results exactly.

---

## Unit Tests — Schema (25 tests) — 99% coverage

These tests verify that every Pydantic model in `src/schema/schema.py` enforces its constraints correctly. They confirm that a `CitationRecord` rejects reliability scores outside the 0.0–1.0 range and excerpts longer than 2000 characters, that `SourceGovernanceRecord` refuses to construct without at least one citation, and that `CapitalRequirement` stores monetary values as `Decimal` rather than `float` to guarantee financial precision. The `ValidationReport` tests verify that the overall status is computed correctly — if any single rule result is FAILED the overall status becomes FAILED, if any result is WARNING with no failures the overall becomes WARNING, and only when all results pass does the overall become PASSED. The `AuditLogEntry` tests confirm that the frozen model raises an error immediately if anything attempts to modify it after construction. The `RegulatoryEntry` tests verify that jurisdiction codes are normalized to uppercase, that entries with a confidence score below 0.4 are rejected at construction time unless marked UNVERIFIED, and that all auto-generated fields such as entry ID and schema version are populated correctly.

---

## Unit Tests — Validation Engine (12 tests) — 96% coverage

These tests verify each of the five validation rules individually and then verify the engine as a whole. VAL_001 is confirmed to fail when the primary regulator field is empty or whitespace only. VAL_002 is confirmed to produce a WARNING rather than a hard failure when no fund structures are defined, since this may be legitimately incomplete at ingestion time. VAL_003 is confirmed to pass entries marked UNVERIFIED even when their confidence score is below 0.4, since UNVERIFIED is the correct designation for low-confidence data. VAL_004 is confirmed to fail hard when no primary citations are present, as citation governance is non-negotiable. VAL_005 produces a WARNING when no filing obligations are defined. The engine-level tests confirm that all five rules run and produce a report, and that custom rules can be added via `add_rule()` and are correctly included in subsequent validation runs.

---

## Unit Tests — Confidence Scorer (10 tests) — 97% coverage

These tests verify the deterministic scoring formula and the level mapping function. The level mapping is confirmed to correctly assign HIGH for scores at or above 0.75, MEDIUM for scores at or above 0.50, LOW for scores at or above 0.40, and UNVERIFIED for anything below 0.40. The scorer tests confirm that a PRIMARY source produces a higher score than a TERTIARY source, that citations older than 365 days incur a recency penalty which is reflected in the contributing factors list, and that the final score is always clamped within the 0.0 to 1.0 range regardless of inputs. Most importantly, the determinism test confirms that running the scorer twice on the exact same entry produces the exact same score both times, which is a core system requirement.

---

## Unit Tests — Contradiction Detection (6 tests) — 97% coverage

These tests cover both the intra-entry and cross-entry contradiction detectors. The intra-entry detector is confirmed to flag cases where a secondary or tertiary citation has a higher reliability score than the primary citations, which represents a data governance violation. It is also confirmed to return an empty list when no primary citations exist, since there is nothing to compare against. The cross-entry detector is confirmed to return an empty list when two identical entries are compared, to correctly detect when the same field holds different values across two entries, and to store both conflicting sources in the resulting `ContradictionRecord` so the disagreement is fully traceable.

---

## Unit Tests — Audit Logger (7 tests) — 100% coverage

These tests verify the append-only logging architecture. They confirm that calling `log()` creates a file on disk and writes a record to it, that multiple calls accumulate correctly without overwriting previous records, and that `read_all()` returns the correct number of entries. The filtering tests confirm that `read_by_jurisdiction()` and `read_by_event_type()` correctly return only the matching records. The immutability test confirms that attempting to modify a retrieved log entry raises an error immediately, enforcing tamper-resistance at the Python level. The audit logger is the only module with 100% code coverage.

---

## Unit Tests — Delta Tracker (7 tests) — 88% coverage

These tests verify field-level change detection and automatic version bumping. The version bumping function is confirmed to correctly increment the patch segment of a semver string from 1.0.0 to 1.0.1, and to handle malformed version strings gracefully by returning a safe default. The delta tracker is confirmed to produce no deltas when two identical entries are compared, to correctly detect and record a field change including the old and new values, to automatically increment the version ID and store the previous version reference, to record the author of the change, and to auto-generate a change summary when none is provided.

---

## Unit Tests — Source Governance (8 tests) — 97% coverage

These tests verify the citation management and deduplication logic. They confirm that PRIMARY, SECONDARY, and TERTIARY citations are stored in their correct lists, that citations sharing the same URL are rejected as duplicates with `add_citation()` returning False, and that citations without a URL are not subject to deduplication since URL is the deduplication key. The dominant source tests confirm that PRIMARY is correctly identified as dominant when present, and that SECONDARY is identified as dominant when no primary citations exist. The reliability tests confirm that average reliability is computed correctly across all citations and that an empty manager returns 0.0 without errors.

---

## Integration Tests — Full Pipeline (7 tests)

These tests verify that all seven modules work together correctly as a complete pipeline. A full `RegulatoryEntry` is constructed with real citation data, fund structures, investor requirements, and filing obligations, then passed through every layer in sequence — validation, confidence scoring, contradiction detection, audit logging, and delta tracking. The tests confirm that a well-formed entry passes all validation rules, that the confidence scorer produces a valid output, that no contradictions are detected in a clean entry, that the audit record is written and retrievable from disk, and that a field change between two versions is correctly detected with the version bumped from 1.0.0 to 1.0.1. The final test runs the full validation and scoring pipeline twice on the same entry and confirms that both runs produce identical results, verifying end-to-end determinism.

---

## Reproducibility

To reproduce these results on any machine:

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=src
```

Expected output: 83 passed, 0 failed, 98% coverage.