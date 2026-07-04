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
│   └── agents/             # Specialised jurisdiction agents + orchestrator
│       ├── base_agent.py   #   Abstract base agent
│       ├── orchestrator.py #   Agent orchestrator
│       └── jurisdiction/   #   6 domain-specific agents
│
├── tests/
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
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
- `CitationRecord` — Individual source citation with authority, reliability, URL, authority_level (1–5), regulatory_relevance_tag, last_verified_timestamp
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
- `NotApplicableReason` — Enum of explicit N/A reasons (NO_TAX, NO_AML_KYC_REQUIRED, NO_PASSPORTING)

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

Checks whether a regulatory entry contains the required information. Returns a validation report showing Passed, Warning, or Failed.

### Validation Rules

| ID | Rule | Status |
|----|------|--------|
| VAL_001 | Primary regulator defined | FAILED |
| VAL_002 | At least one fund structure | WARNING |
| VAL_003 | Confidence score ≥ threshold | PASSED |
| VAL_004 | At least one source citation | FAILED |
| VAL_005 | Filing obligations present | WARNING |
| VAL_006 | Licensing requirements present | WARNING |
| VAL_007 | Substance requirements present | WARNING |
| VAL_008 | Regulatory timelines present | WARNING |
| VAL_009 | Regulatory costs present | WARNING |
| VAL_010 | Penalty exposure present | WARNING |
| VAL_011 | Wind-down procedure present | WARNING |
| VAL_012 | Fund manager requirements present | WARNING |
| VAL_013 | Beneficial ownership rules present | WARNING |
| VAL_014 | Record retention policies present | WARNING |
| VAL_015 | ≥2 primary citations (SRS §5.3) | FAILED |
| VAL_016 | Tax Framework citation if tax_summary populated | WARNING |
| VAL_017 | Capital Requirements citation if capital > 0 | WARNING |
| VAL_018 | Critical fields not silently None | WARNING |

---

## Confidence Scoring

**Location**

```
src/confidence/scorer.py
```

Calculates how trustworthy an entry is. The score is computed as:

```
final = clamp(
    base_authority_weight
    + citation_volume_bonus (max +0.2)
    - recency_penalty (−0.1 per stale citation >365d)
    - contradiction_penalty (−0.15 per unresolved)
    - authority_level_penalty (−0.02 per citation at level 4+)
    + completeness_bonus (up to +0.1, proportional to populated modules)
    - refresh_penalty (up to −0.1, proportional to days >180 since update),
  0.0, 1.0
)
```

Output includes numeric score, confidence level, and a list of contributing factors.

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

## Agent Architecture

**Location**

```
src/agents/
├── __init__.py              # create_default_orchestrator factory
├── base_agent.py            # BaseAgent ABC
├── orchestrator.py          # Orchestrator (runs agent chain)
└── jurisdiction/
    ├── regulatory_authority_agent.py
    ├── licensing_agent.py
    ├── capital_requirement_agent.py
    ├── fund_structure_agent.py
    ├── tax_framework_agent.py
    └── compliance_obligation_agent.py
```

Agents are a validation and enrichment layer that sits **above** the `JurisdictionBuilder`. Each agent has:

- `validate(entry) → bool` — domain-specific check
- `process(entry) → RegulatoryEntry` — enrichment / transformation

The **Orchestrator** runs agents sequentially. If any agent's `validate()` returns `False`, the orchestrator **blocks** (stops the chain) and logs a `BLOCKED` audit event. Otherwise it logs `ORCHESTRATION_COMPLETE`.

### Agents

| Agent | Validates |
|-------|-----------|
| RegulatoryAuthorityAgent | primary_regulator non-empty |
| LicensingAgent | licensing_requirements populated |
| CapitalRequirementAgent | min_capital on fund structures |
| FundStructureAgent | permitted_fund_structures non-empty |
| TaxFrameworkAgent | tax_summary and withholding_tax_rate present |
| ComplianceObligationAgent | filing_obligations non-empty and aml_kyc_framework present |

Create a default orchestrator with:

```python
from src.agents import create_default_orchestrator
orchestrator = create_default_orchestrator()
entry, report = orchestrator.run(regulatory_entry)
```

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
Confidence Scoring
     │
     ▼
Validation (18 rules)
     │
     ▼
Contradiction Detection
     │
     ▼
Agent Orchestration (6 agents, blocks on failure)
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
2. **Validation** — `ValidationEngine.validate()` runs all 18 rules
3. **Contradiction detection** — `CitationContradictionDetector.detect()` checks citation hierarchy
4. **Orchestration** — `Orchestrator.run()` runs 6 agents sequentially; blocks on failure
5. **Audit logging** — `AuditLogger.log()` writes an immutable record to `logs/audit.jsonl`

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
ConfidenceScorer.score(entry) → deterministic score
    (authority weight + volume bonus − recency − contradiction
     − authority_level penalty + completeness bonus − refresh penalty)
    ↓
ValidationEngine.validate(entry) → ValidationReport (18 rules)
    ↓
CitationContradictionDetector.detect(entry) → ContradictionRecord[]
    ↓
Orchestrator.run(entry) → 6 agents validate; blocks on failure
    ↓
AuditLogger.log(event_type=VALIDATION, ...) → immutable audit log
    ↓
Entry registered in JurisdictionRegistry
```

---

# Test Suite

**All tests passing; mypy strict on source files, zero errors.**

| File | Count | Scope |
|------|-------|-------|
| File | Tests | Scope |
|------|-------|-------|
| `tests/unit/test_schema.py` | 38 | Schema model construction, defaults, new CitationRecord fields |
| `tests/unit/test_validators.py` | 47 | ValidationEngine with all 18 rules |
| `tests/unit/test_confidence.py` | 14 | ConfidenceScorer determinism, penalties, clamping, completeness, refresh |
| `tests/unit/test_contradiction.py` | 6 | CitationContradictionDetector, CrossEntryContradictionDetector |
| `tests/unit/test_governance.py` | 8 | SourceGovernanceManager (dedup, sorting, reliability) |
| `tests/unit/test_audit.py` | 7 | AuditLogger file I/O, filtering, immutability |
| `tests/unit/test_versioning.py` | 7 | DeltaTracker field comparison, version bumps |
| `tests/unit/test_jurisdictions.py` | 273 | 24 parametrized tests × 8 builders + 17 spot-checks + pipeline |
| `tests/unit/test_agents.py` | 25 | Agent validate/process, orchestrator chain, blocking, audit |
| `tests/integration/test_pipeline.py` | 7 | End-to-end pipeline flow |
| `tests/integration/test_registry.py` | 21 | Registry loading, access, comparison, audit logging |

---

## SRS Compliance Matrix

| SRS Requirement | Coverage | How |
|-----------------|----------|-----|
| §5.1.1 Regulator identification | VAL_001 | `HasPrimaryRegulatorRule` |
| §5.1.2 Multi-source validation | VAL_004, VAL_015 | ≥1 citations, ≥2 primary citations |
| §5.1.3 Authority tier grading | SourceGovernanceRecord | PRIMARY/SECONDARY/TERTIARY + 1–5 authority_level |
| §5.1.4 Cross-source contradiction | ContradictionDetector | Citation + cross-entry detection |
| §5.1.6 Boolean field zero-false rule | Model design | Default `False` / `None` for optional booleans |
| §5.1.7 Silent null prohibition | VAL_018 | tax_summary, aml_kyc_framework, passporting_notes not None |
| §5.2.1 Citation-authority alignment | VAL_016, VAL_017 | Tag-based: Tax Framework / Capital Requirements |
| §5.2.2 Citation density | VAL_015 | ≥2 primary citations per entry |
| §5.3.1 Confidence formula | ConfidenceScorer | Weighted, bonus, penalty, clamped 0–1 |
| §5.3.2 Authority level contribution | authority_level_penalty | −0.02 per citation at level 4+ |
| §5.3.3 Module completeness bonus | completeness_bonus | Up to +0.1 for 11 module fields |
| §5.3.4 Refresh recency penalty | refresh_penalty | Up to −0.1 for >180 days stale |
| §6.1 Agent decomposition | 6 agents | RegAuth, Licensing, Capital, Fund, Tax, Compliance |
| §6.2 Sequential orchestration | Orchestrator | Blocking chain, BLOCKED audit events |

---

# Future Improvements

Planned features include:

- Database integration
- Automatic data refresh
- User authentication
- Encryption
- Expanded regulatory datasets (Tier 2, Tier 3 jurisdictions)

---

# Summary

The foundation layer provides the core building blocks of Legal Swarm. It ensures that regulatory information is stored consistently, validated correctly, scored for reliability, tracked over time, and logged for auditing. The Tier 1 jurisdiction layer extends this foundation with 8 fully populated regulatory entries, each backed by official citations and validated through the complete deterministic pipeline. Each entry includes 10 expanded regulatory data categories (licensing, substance, timelines, costs, penalties, wind-down, manager requirements, marketing restrictions, beneficial ownership, and record retention) populated with real-world jurisdiction-specific values. The agent layer adds 6 domain-specific agents and an orchestrator for sequential validation with blocking on failure. The full suite of tests ensures correctness across all components.