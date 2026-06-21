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
│   └── agents/             # Reserved for future AI agents
│
├── tests/
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

Examples include:

- RegulatoryEntry
- CitationRecord
- ConfidenceScore
- ValidationReport
- VersionRecord
- AuditLogEntry

This acts as the single source of truth for all project data.

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

# Future Improvements

Planned features include:

- Multi-agent orchestration
- Database integration
- Automatic data refresh
- User authentication
- Encryption
- More validation rules
- Expanded regulatory datasets

---

# Summary

The foundation layer provides the core building blocks of Legal Swarm. It ensures that regulatory information is stored consistently, validated correctly, scored for reliability, tracked over time, and logged for auditing.