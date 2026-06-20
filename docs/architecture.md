# Legal Swarm — Architecture Documentation

## Overview

Legal Swarm is a multi-agent regulatory intelligence system designed to ingest,
validate, compare, and serve regulatory data across jurisdictions. This document
records all architectural decisions, assumptions, trade-offs, and design rationale
made during the foundation layer implementation.

---

## Stack

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python 3.11 | Best ecosystem for AI/ML and agentic workflows |
| Schema / Validation | Pydantic v2 | Fast, strict, type-safe; native JSON serialization |
| Build system | Hatchling via pyproject.toml | PEP 517/518 compliant, no legacy setup.py |
| Containerization | Docker + Compose | Reproducible deployment across environments |
| CI | GitHub Actions | Native to GitHub, zero additional tooling |

---

## Architectural Decisions

### AD-001 — Single Master Canonical Schema

**Decision:** All regulatory data is represented by one top-level model: `RegulatoryEntry`.  
**Rationale:** A single authoritative schema prevents drift across agents. Every agent reads and writes the same type, making cross-agent validation trivial.  
**Trade-off:** Schema changes require all agents to update simultaneously. Mitigated by semantic versioning (`schema_version` field on every entry).

---

### AD-002 — Pydantic v2 with Frozen Audit Records

**Decision:** `AuditLogEntry` uses `model_config = {"frozen": True}`.  
**Rationale:** Audit records must be immutable. Pydantic v2's frozen config raises an error on any attempted mutation at the Python level.  
**Trade-off:** Frozen models cannot be updated in-place. This is intentional — audit records are append-only by design.

---

### AD-003 — Deterministic Confidence Scoring

**Decision:** Confidence scores are computed deterministically from source authority, citation volume, recency, and contradiction count — not via LLM inference.  
**Rationale:** LLM-based scoring is non-deterministic and difficult to audit. Deterministic scoring produces reproducible results and a clear audit trail.  
**Trade-off:** Deterministic scoring cannot capture nuanced semantic quality of citations. Mitigated by the `rationale` and `contributing_factors` fields which expose all scoring inputs.

---

### AD-004 — Append-Only JSONL Audit Log

**Decision:** Audit logs are written to a `.jsonl` file (one JSON object per line), append-only.  
**Rationale:** JSONL is human-readable, grep-friendly, and trivially parseable. Append-only writes ensure no historical record is ever overwritten.  
**Trade-off:** Not suitable for high-throughput production (use a database-backed log in that case). Acceptable for the current phase; the interface (`AuditLogger`) abstracts the storage backend for easy future swap.

---

### AD-005 — Field-Path-Aware Contradiction Detection

**Decision:** `ContradictionRecord` stores a `field_path` using dot-notation (e.g. `investor_requirements.min_investment_usd`).  
**Rationale:** Field-level granularity allows precise contradiction resolution without invalidating an entire entry. Agents can resolve individual fields independently.  
**Trade-off:** Requires consistent field-path conventions across all agents. Enforced by using the same `COMPARABLE_FIELDS` constant in `CrossEntryContradictionDetector`.

---

### AD-006 — Semantic Versioning for Entries

**Decision:** Each `RegulatoryEntry` carries a `VersionRecord` with a semver string.  
**Rationale:** Regulatory data changes over time. Semver makes it unambiguous whether a change is a patch (data correction), minor (new field added), or major (structural change).  
**Trade-off:** Manual version bumping is error-prone. `DeltaTracker.compute_delta()` auto-increments the patch segment; major/minor bumps are reserved for deliberate schema changes.

---

### AD-007 — Source Authority Hierarchy

**Decision:** Citations are classified as PRIMARY / SECONDARY / TERTIARY and stored in separate lists within `SourceGovernanceRecord`.  
**Rationale:** Source authority directly affects confidence scoring. Keeping them in separate lists makes authority-weighted operations efficient without filtering.  
**Trade-off:** A citation's authority classification is set at ingestion time and not re-evaluated. Agents must classify correctly on input.

---

## Assumptions

1. Jurisdiction codes follow ISO 3166-1 alpha-2 (or a documented custom extension for multi-region codes).
2. All monetary values are normalized to USD equivalent at ingestion time.
3. The foundation layer does not connect to any external data source — data ingestion agents are a higher layer.
4. Python 3.11+ is available in all deployment environments.

---

## Future Considerations

- Replace JSONL audit log with a time-series database (InfluxDB / TimescaleDB) for high-volume deployments.
- Add a migration framework (Alembic-style) for schema version upgrades.
- Introduce async I/O (`asyncio`) at the agent orchestration layer.
- Add OpenTelemetry instrumentation for distributed tracing across agents.
