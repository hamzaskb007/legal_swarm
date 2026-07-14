# Authority Registry

## Overview

The Authority Registry provides a centralized, configuration-driven system for managing regulatory authorities across all jurisdictions. Instead of hardcoding regulator URLs, names, and reliability scores in Python code, these values are defined in YAML files under `config/authorities/`. The registry auto-discovers all authority files on startup, validates them for consistency, and exposes them via the `AuthorityResolver` service.

## Architecture

```
config/authorities/*.yaml
        │
        ▼
 AuthorityRegistry    ← loads, validates, indexes
        │
        ▼
 AuthorityResolver    ← query methods for consumers
        │
        ▼
 Jurisdiction Builders ← use resolver for citation creation
```

## YAML Schema

Each authority file defines a single regulatory body:

```yaml
id: sec                       # Unique machine identifier
jurisdiction: US              # ISO jurisdiction code
name: U.S. Securities and Exchange Commission  # Full display name
level: 1                      # AuthorityLevel (1-5)
authority_type: regulator     # Category (regulator, legal_firm, etc.)
base_url: https://www.sec.gov # Primary website
search_url: https://www.sec.gov/search          # Optional search endpoint
legislation_url: https://www.sec.gov/rules      # Optional legislation page
parser: html                  # ParserType: html, pdf, api, rss, manual
refresh_interval: 24          # Refresh cadence in hours
reliability_score: 0.95       # Default reliability score (0.0-1.0)
enabled: true                 # Active flag
metadata:                     # Optional key-value pairs
  country: United States
  acronym: SEC
  region: North America
```

### Authority Levels

| Level | Label | SourceAuthority | Examples |
|-------|-------|----------------|----------|
| 1 | Official regulator | PRIMARY | SEC, MAS, CIMA, CSSF |
| 2 | Government legislation database | PRIMARY | Statutes, Acts, Regulations |
| 3 | Government gazette | PRIMARY | Official gazettes |
| 4 | Recognized legal firm | SECONDARY | Walkers, Ogier |
| 5 | Professional advisory | TERTIARY | Consulting firms |

### Parser Types

- `html` — HTML web pages
- `pdf` — PDF documents
- `api` — REST API endpoints
- `rss` — RSS/Atom feeds
- `manual` — Manually curated data

## AuthorityRegistry

**File:** `src/authority/registry.py`

Auto-discovers YAML files in `config/authorities/` on construction. Each `.yaml` file is parsed and validated:

- **Duplicate `id`** — raises `ValueError`
- **Duplicate `name`** (case-insensitive) — raises `ValueError`
- **Duplicate `base_url`** — raises `ValueError`
- **Missing directory** — raises `FileNotFoundError`

### Methods

| Method | Description |
|--------|-------------|
| `get_by_id(authority_id)` | Get a single authority by its `id` |
| `get_all()` | Return all loaded authorities |
| `get_by_jurisdiction(code)` | Filter by jurisdiction code |
| `get_by_level(level)` | Filter by authority level |
| `get_enabled()` | Return only enabled authorities |
| `get_by_name(name)` | Case-insensitive name lookup |

## AuthorityResolver

**File:** `src/authority/resolver.py`

Wraps the registry with domain-specific query methods:

| Method | Description |
|--------|-------------|
| `get_primary_authority(jurisdiction)` | Returns the first level-1 authority for a jurisdiction |
| `get_all_authorities(jurisdiction)` | All authorities for a jurisdiction |
| `get_by_name(name)` | Delegates to registry |
| `get_by_level(level)` | Delegates to registry (accepts `int` or `AuthorityLevel`) |
| `get_enabled()` | Delegates to registry |
| `get_by_id(authority_id)` | Delegates to registry |
| `resolve_for_citation(authority_id)` | Returns authority for citation context |
| `create_citation(authority_id, **overrides)` | Creates a `CitationRecord` pre-filled from authority defaults, with optional overrides |

## Citation Integration

The `CitationRecord` model now includes an optional `authority_id` field that references the authority in the registry.

When creating citations in jurisdiction builders, the resolver is used to populate fields:

```python
resolver = AuthorityResolver()
sec = resolver.get_by_id("sec")

manager.add_citation(CitationRecord(
    authority_id="sec",
    source_name=sec.name,
    source_url=sec.base_url,
    authority=SourceAuthority.PRIMARY,
    authority_level=sec.level.value,
    reliability_score=sec.reliability_score,
    section_reference="Section 3(c)(1)",
    ...
))
```

For legislation citations with specific document names, the `authority_id` still links to the regulator:

```python
manager.add_citation(CitationRecord(
    authority_id="sec",
    source_name="Investment Company Act of 1940",
    source_url=None,
    authority=SourceAuthority.PRIMARY,
    authority_level=2,
    reliability_score=0.98,
    section_reference="Sections 3(c)(1) and 3(c)(7)",
    ...
))
```

## Adding a New Regulator

To add a new regulatory authority:

1. Create a YAML file in `config/authorities/` (e.g., `fca.yaml`)
2. Populate the file with the authority metadata following the schema above
3. The registry automatically discovers the file — no code changes required

```bash
# Example: config/authorities/fca.yaml
echo "id: fca
jurisdiction: GB
name: Financial Conduct Authority
level: 1
authority_type: regulator
base_url: https://www.fca.org.uk
refresh_interval: 24
reliability_score: 0.92
enabled: true" > config/authorities/fca.yaml
```

Then reference it in any builder:

```python
fca = resolver.get_by_id("fca")
manager.add_citation(CitationRecord(
    authority_id="fca",
    source_name=fca.name,
    source_url=fca.base_url,
    ...
))
```

## Currently Registered Authorities

| ID | Name | Jurisdiction | Level | Reliability |
|----|------|-------------|-------|-------------|
| `cima` | Cayman Islands Monetary Authority | KY | 1 | 0.90 |
| `cssf` | Commission de Surveillance du Secteur Financier | LU | 1 | 0.90 |
| `central_bank_ireland` | Central Bank of Ireland | IE | 1 | 0.90 |
| `mas` | Monetary Authority of Singapore | SG | 1 | 0.90 |
| `acra` | Accounting and Corporate Regulatory Authority | SG | 1 | 0.85 |
| `bvi_fsc` | BVI Financial Services Commission | VG | 1 | 0.90 |
| `sca` | Securities and Commodities Authority | AE | 1 | 0.85 |
| `dfsa` | Dubai Financial Services Authority | AE | 1 | 0.85 |
| `adgm_fsra` | Abu Dhabi Global Market FSRA | AE | 1 | 0.85 |
| `jfsc` | Jersey Financial Services Commission | JE | 1 | 0.90 |
| `sec` | U.S. Securities and Exchange Commission | US | 1 | 0.95 |
| `cftc` | U.S. Commodity Futures Trading Commission | US | 1 | 0.93 |
| `walkers` | Walkers Global | KY | 4 | 0.80 |
| `ogier` | Ogier | JE | 4 | 0.80 |

## Reliability Scoring Model

Each authority defines a default `reliability_score` (0.0–1.0). When a citation references an authority, it inherits this score unless explicitly overridden:

- **Level 1 regulators**: 0.85–0.95 (SEC highest at 0.95)
- **Level 4 legal firms**: 0.80
- **Legislation citations** (level 2): can override with a higher score (e.g., 0.97) since the specific act carries more weight than the regulator's general website

The `ConfidenceScorer` uses the citation's final `reliability_score` in its formula, combined with:

- Authority weight (PRIMARY=1.0, SECONDARY=0.6, TERTIARY=0.3)
- Citation volume bonus (max +0.2)
- Recency penalty (−0.1 per stale citation)
- Contradiction penalty (−0.15 per unresolved)
- Authority level penalty (−0.02 per citation at level 4+)
- Completeness bonus (up to +0.1)
- Refresh recency penalty (up to −0.1)

## Validation

On startup, the registry validates that:

1. All YAML files are parseable and match the `Authority` schema
2. No two authorities share the same `id`
3. No two authorities share the same `name` (case-insensitive)
4. No two authorities share the same `base_url`

Invalid configuration causes immediate failure — fail-fast design.

## Running Tests

```bash
python3 -m pytest tests/unit/test_authority.py -v
```
