# Legal Swarm - Foundation Layer

## Overview

Legal Swarm is a Python-based backend for managing regulatory information. It provides a structured way to store, validate, compare, and track legal and compliance data.

The foundation layer focuses on:

- Structured data models
- Validation
- Confidence scoring
- Contradiction detection
- Audit logging
- Version tracking

---

# Project Structure

```
legal-swarm/
│
├── src/
│   ├── schema/             # Data models
│   ├── validation/         # Validation rules
│   ├── confidence/         # Confidence score calculation
│   ├── contradiction/      # Contradiction detection
│   ├── governance/         # Citation management
│   ├── versioning/         # Version tracking
│   ├── audit/              # Audit logging
│   ├── jurisdictions/      # Jurisdiction builders & registry
│   │   ├── base.py         #   Abstract jurisdiction builder
│   │   ├── registry.py     #   Central jurisdiction registry
│   │   └── tier1/          #   8 Tier 1 regulatory entries
│   └── agents/             # Reserved for future AI agents
│
├── tests/
│   ├── unit/               # 349 unit tests
│   └── integration/         # 27 integration tests
├── docs/
├── deploy/
├── main.py
└── README.md
```

---

# Modules

## Schema

**Location**

```
src/schema/schema.py
```

Contains all Pydantic models used throughout the project.

### Core Models

- `RegulatoryEntry` — Master record for a jurisdiction (all fields below)
- `CitationRecord` — Individual source citation with authority, reliability, URL
- `SourceGovernanceRecord` — Collection of citations sorted by authority tier
- `ConfidenceScore` — Numeric score (0–1), level (UNVERIFIED / LOW / MEDIUM / HIGH), rationale
- `ValidationReport` / `ValidationRuleResult` — Per-rule and overall validation status
- `CapitalRequirement` — Minimum capital / NAV requirements per fund type
- `FilingObligation` — Periodic filing requirements (audited accounts, returns, etc.)
- `InvestorRequirement` — Qualified / professional / retail eligibility rules
- `TaxSummary` — Corporate tax, withholding tax, VAT/GST, treaty network
- `AmlKycFramework` — AML/KYC obligations, customer due diligence, reporting
- `FundStructure` — Permitted fund types (UCITS, VCC, SIF, etc.)
- `VersionRecord` — Semver tracking with author and change summary
- `ContradictionRecord` — Conflicting field between citations or entries
- `AuditLogEntry` — Immutable JSONL log entry

### Regulatory Data Models (added in Tier 1 expansion)

| Model | Key Fields | Purpose |
|-------|-----------|---------|
| `LicensingRequirement` | `licence_type`, `issuing_authority`, `applies_to`, `statutory_reference` | Types of licences needed to operate |
| `SubstanceRequirement` | `local_office_required`, `local_directors_required`, `minimum_local_directors`, `local_staff_required` | Economic substance obligations |
| `RegulatoryTimeline` | `process_name`, `minimum_days`, `maximum_days`, `typical_days` | Typical authorisation timelines |
| `RegulatoryCost` | `cost_type`, `amount`, `currency`, `amount_usd_equivalent`, `frequency` | Annual regulatory fees and costs |
| `PenaltyExposure` | `breach_type`, `maximum_fine_usd`, `criminal_liability`, `licence_revocation_possible` | Penalty framework per breach type |
| `WindDownProcedure` | `voluntary_liquidation_available`, `typical_duration_days`, `regulator_approval_required`, `creditor_protection_period_days` | Fund wind-down / liquidation process |
| `FundManagerRequirement` | `local_manager_required`, `minimum_aum_for_full_licence_usd`, `fit_and_proper_required`, `experience_years_required` | Manager licensing & substance rules |
| `MarketingRestriction` | `target_investor_type`, `permitted_jurisdictions`, `restricted_jurisdictions`, `pre_marketing_allowed` | Cross-border marketing limitations |
| `BeneficialOwnershipRule` | `register_required`, `register_public`, `threshold_percentage`, `filing_authority` | Beneficial ownership disclosure rules |
| `RecordRetentionPolicy` | `minimum_retention_years`, `applies_to`, `statutory_reference` | Document retention obligations |

These models are stored as optional fields on `RegulatoryEntry` (e.g. `licensing_requirements: list[LicensingRequirement] | None = None`) — fully backward compatible.

---

## Validation

**Location**

```
src/validation/validators.py
```

Checks whether a regulatory entry contains the required information.

Example checks:

- Primary regulator exists
- At least one citation
- Confidence score is valid
- Filing information is present

Returns a validation report showing Passed, Warning, or Failed.

---

## Confidence Scoring

**Location**

```
src/confidence/scorer.py
```

Calculates how trustworthy an entry is.

The score depends on:

- Source quality
- Number of citations
- Data freshness
- Existing contradictions

Output includes:

- Numeric score
- Confidence level
- Explanation

---

## Contradiction Detection

**Location**

```
src/contradiction/detector.py
```

Compares regulatory information and identifies conflicting values.

Examples:

- Different tax rates
- Different regulators
- Different investment requirements

Produces a list of detected contradictions.

---

## Source Governance

**Location**

```
src/governance/source_governance.py
```

Manages citations.

Responsibilities:

- Remove duplicate sources
- Classify sources as Primary, Secondary, or Tertiary
- Calculate overall source reliability

---

## Version Tracking

**Location**

```
src/versioning/delta_tracker.py
```

Tracks changes between two versions of a regulatory entry.

It records:

- Changed fields
- Old value
- New value
- Version number

---

## Audit Logging

**Location**

```
src/audit/logger.py
```

Records important events during execution.

Examples:

- Validation completed
- Confidence calculated
- Contradiction detected
- Version updated

Logs are stored in JSONL format.

---

# Workflow

```
Input Data
     │
     ▼
Source Governance
     │
     ▼
Create Regulatory Entry
     │
     ▼
Validation
     │
     ▼
Confidence Scoring
     │
     ▼
Contradiction Detection
     │
     ▼
Audit Logging
     │
     ▼
Store Result
```

---

# Technologies

- Python 3.11
- Pydantic v2
- JSONL
- Docker
- GitHub Actions
- Pytest

---

# Running the Project

Install dependencies

```bash
pip install -e ".[dev]"
```

Run the project

```bash
python main.py
```

Using Docker

```bash
docker-compose up --build
```

---

# Tier 1 Jurisdiction Population

**Location:** `src/jurisdictions/`

Implements the Tier 1 jurisdiction data layer — 8 fully populated regulatory entries that pass through the complete framework pipeline.

## Structure

```
src/jurisdictions/
├── __init__.py             # Package exports (JurisdictionRegistry, JurisdictionBuilder)
├── base.py                 # Abstract base class (JurisdictionBuilder)
├── registry.py             # Central registry (JurisdictionRegistry)
└── tier1/
    ├── __init__.py
    ├── cayman_islands.py   # KY – CIMA regulated
    ├── luxembourg.py       # LU – CSSF regulated
    ├── ireland.py          # IE – Central Bank of Ireland regulated
    ├── singapore.py        # SG – MAS regulated
    ├── bvi.py              # VG – FSC regulated
    ├── uae.py              # AE – SCA/DFSA/FSRA regulated
    ├── jersey.py           # JE – JFSC regulated
    └── delaware.py         # US-DE – SEC/CFTC regulated
```

## JurisdictionBuilder (base.py)

Abstract base class that all jurisdiction builders extend. Subclasses must implement `build_entry()` which returns a `RegulatoryEntry` with a placeholder confidence score (UNVERIFIED, 0.0). The `run_pipeline()` method then:

1. **Confidence scoring** — `ConfidenceScorer.score()` computes a deterministic score
2. **Validation** — `ValidationEngine.validate()` runs VAL_001–VAL_005
3. **Contradiction detection** — `CitationContradictionDetector.detect()` checks citation hierarchy
4. **Audit logging** — `AuditLogger.log()` writes an immutable record to `logs/audit.jsonl`

## JurisdictionRegistry (registry.py)

Central registry that loads all 8 Tier 1 entries on construction. Provides:

- `get_entry(code)` — retrieve entry by jurisdiction code (case-insensitive)
- `get_all()` — return all entries
- `compare(code_a, code_b)` — cross-jurisdiction comparison via `CrossEntryContradictionDetector`
- `validation_reports` — dict of validation reports keyed by code
- `__len__` / `__contains__` — standard container protocols

Every access is logged to the audit trail.

## Tier 1 Jurisdictions

| Code   | Jurisdiction               | Primary Regulator                  | Notable Structures                  |
|--------|----------------------------|------------------------------------|-------------------------------------|
| KY     | Cayman Islands             | Cayman Islands Monetary Authority  | Administered, Managed, Private, MF  |
| LU     | Luxembourg                 | CSSF                               | UCITS Part I, Part II, SIF, RAIF   |
| IE     | Ireland                    | Central Bank of Ireland            | UCITS, QIAIF, RIAIF, ICAV          |
| SG     | Singapore                  | MAS                                | VCC, Authorised CIS, Restricted CIS |
| VG     | British Virgin Islands     | BVI FSC                            | Incubator, Approved, Professional   |
| AE     | United Arab Emirates       | SCA / DFSA / ADGM FSRA             | Public, Private, DIFC, ADGM         |
| JE     | Jersey                     | JFSC                               | Expert, Listed, Unclassified, ICCR  |
| US-DE  | Delaware (United States)   | SEC / CFTC                         | LP, LLC, RIC, Private Fund          |

### Regulatory Data Per Jurisdiction

Each Tier 1 builder populates 10 new regulatory data fields with jurisdiction-specific real-world data:

| Field | Example (Cayman Islands) | Example (Luxembourg) | Example (Singapore) |
|-------|-------------------------|---------------------|--------------------|
| Licensing | Mutual Fund Licence (CIMA), SIBL | UCITS Part I, SIF, RAIF approvals | CMS Licence (MAS), VCC registration |
| Substance | Physical office, 2 directors, AML officer | Local AIFM, depositary, admin agent | Local director, MAS rep office |
| Timelines | 30–180 days for licence | 90–180 days UCITS, 60–120 SIF | 90–210 days CMS, 14–60 VCC |
| Costs | $6,000–$39,000 annual CIMA fees | €3,500–€12,000 CSSF annual | $1,000–$100,000 MAS annual |
| Penalties | Up to $100,000 + 5 yrs imprisonment | Up to €5M + administrative fines | Up to SGD $2M + imprisonment |
| Wind-down | Voluntary liquidation, 180–365 days | Voluntary + regulatory approval, 180–365 days | Voluntary + MAS approval, 90–180 days |
| Manager | Local manager required, fit & proper test | Local AIFM required for UCITS, 5 yrs experience | CMS holder, residency requirement |
| Marketing | No restrictions on institutional | EU passport for UCITS, National placement for AIF/SIF | Restricted CIS only to accredited |
| BO Register | BOSS register, 25% threshold, non-public | RBE register, 25% threshold, public | ACRA register, 25% threshold, non-public |
| Record Retention | 5 years (AML), 6 years (CIMA) | 5 years (CSSF), 10 years (AML) | 5 years (MAS), 5 years (ACRA) |

## Data Pipeline for Each Entry

```
SourceGovernanceManager.add_citation() × N
    → Deduplicates by URL
    → Sorts into PRIMARY / SECONDARY / TERTIARY
    → .build() → SourceGovernanceRecord
    ↓
RegulatoryEntry constructed (placeholder confidence: UNVERIFIED, 0.0)
    ↓
ConfidenceScorer.score(entry) → deterministic score based on:
    - Base authority weight (PRIMARY=1.0, SECONDARY=0.6, TERTIARY=0.3)
    - Citation volume bonus (max +0.2)
    - Recency penalty (−0.1 per stale citation over 365 days)
    - Contradiction penalty (−0.15 per unresolved contradiction)
    ↓
ValidationEngine.validate(entry) → ValidationReport (5 rules)
    ↓
CitationContradictionDetector.detect(entry) → ContradictionRecord[]
    ↓
AuditLogger.log(event_type=VALIDATION, ...) → immutable audit log
    ↓
Entry registered in JurisdictionRegistry
```

---

# Test Suite

**376 total tests — 349 unit, 27 integration — all passing; mypy strict on 28 source files, zero errors.**

| File | Count | Scope |
|------|-------|-------|
| `tests/unit/test_schema.py` | ~10 | Schema model construction and defaults |
| `tests/unit/test_validators.py` | ~13 | ValidationEngine with all 5 rules |
| `tests/unit/test_confidence.py` | ~8 | ConfidenceScorer determinism, penalties, clamping |
| `tests/unit/test_contradiction.py` | ~6 | CitationContradictionDetector, CrossEntryContradictionDetector |
| `tests/unit/test_governance.py` | ~8 | SourceGovernanceManager (dedup, sorting, reliability) |
| `tests/unit/test_audit.py` | ~19 | AuditLogger file I/O, filtering, immutability |
| `tests/unit/test_versioning.py` | ~19 | DeltaTracker field comparison, version bumps |
| `tests/unit/test_jurisdictions.py` | 273 | 24 parametrized tests × 8 builders + 17 spot-checks + pipeline |
| `tests/integration/test_pipeline.py` | ~13 | End-to-end pipeline flow |
| `tests/integration/test_registry.py` | ~14 | Registry loading, access, comparison, audit logging |

---

# Future Improvements

Planned features include:

- Multi-agent orchestration
- Database integration
- Automatic data refresh
- User authentication
- Encryption
- More validation rules
- Expanded regulatory datasets (Tier 2, Tier 3 jurisdictions)

---

# Summary

The foundation layer provides the core building blocks of Legal Swarm. It ensures that regulatory information is stored consistently, validated correctly, scored for reliability, tracked over time, and logged for auditing. The Tier 1 jurisdiction layer extends this foundation with 8 fully populated regulatory entries, each backed by official citations and validated through the complete deterministic pipeline. Each entry includes 10 expanded regulatory data categories (licensing, substance, timelines, costs, penalties, wind-down, manager requirements, marketing restrictions, beneficial ownership, and record retention) populated with real-world jurisdiction-specific values. The full suite of 376 tests ensures correctness across all components.