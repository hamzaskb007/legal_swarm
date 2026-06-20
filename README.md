# Legal Swarm — Regulatory Intelligence System

Multi-agent system for ingesting, validating, and serving regulatory intelligence across jurisdictions.

## Structure

src/
├── schema/         # Master canonical schema
├── validation/     # Rule-based validation engine
├── contradiction/  # Contradiction detection
├── confidence/     # Deterministic confidence scoring
├── audit/          # Append-only audit logging
├── versioning/     # Delta tracking
├── governance/     # Source authority management
└── agents/         # Multi-agent layer (next phase)

## Setup
pip install -e ".[dev]"

## Tests
pytest --cov=src tests/

## Docs
See docs/architecture.md