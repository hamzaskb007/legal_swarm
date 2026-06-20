"""
Legal Swarm — End-to-End Pipeline Demo
Builds a sample RegulatoryEntry for UAE and runs it through the full pipeline.
"""

from decimal import Decimal
from datetime import datetime
from pathlib import Path

from src.schema.schema import (
    CitationRecord,
    ConfidenceLevel,
    ConfidenceScore,
    FundStructure,
    CapitalRequirement,
    InvestorRequirements,
    JurisdictionTier,
    RegulatoryFiling,
    RegulatoryEntry,
    SourceAuthority,
    AuditEventType,
    VersionRecord,
)
from src.governance.source_governance import SourceGovernanceManager
from src.validation.validators import ValidationEngine
from src.confidence.scorer import ConfidenceScorer
from src.contradiction.detector import CitationContradictionDetector
from src.audit.logger import AuditLogger


# ---------------------------------------------------------------------------
# Step 1 — Build citations
# ---------------------------------------------------------------------------
print("\n=== STEP 1: Building source governance ===")

manager = SourceGovernanceManager()

manager.add_citation(CitationRecord(
    source_name="UAE Securities and Commodities Authority",
    source_url="https://www.sca.gov.ae/regulations/funds",
    authority=SourceAuthority.PRIMARY,
    publication_date=datetime(2024, 1, 15),
    section_reference="Article 12, Fund Regulations 2024",
    reliability_score=0.95,
    raw_excerpt="All funds must register with SCA prior to offering units to the public.",
))

manager.add_citation(CitationRecord(
    source_name="Clifford Chance UAE Fund Guide 2024",
    source_url="https://www.cliffordchance.com/uae-fund-guide",
    authority=SourceAuthority.SECONDARY,
    publication_date=datetime(2024, 3, 1),
    section_reference="Chapter 3",
    reliability_score=0.80,
))

source_governance = manager.build()
print(f"Citations added: {manager.citation_count()}")
print(f"Dominant source: {source_governance.dominant_source}")


# ---------------------------------------------------------------------------
# Step 2 — Build RegulatoryEntry
# ---------------------------------------------------------------------------
print("\n=== STEP 2: Building RegulataryEntry for UAE ===")

entry = RegulatoryEntry(
    jurisdiction_code="AE",
    jurisdiction_name="United Arab Emirates",
    tier=JurisdictionTier.TIER_1,
    primary_regulator="Securities and Commodities Authority (SCA)",
    secondary_regulators=["Dubai Financial Services Authority (DFSA)", "ADGM Financial Services Regulatory Authority"],
    permitted_fund_structures=[
        FundStructure(
            structure_type="Public Fund",
            is_permitted=True,
            min_capital=CapitalRequirement(
                amount=Decimal("10000000"),
                currency="AED",
                amount_usd_equivalent=Decimal("2722000"),
            ),
        ),
        FundStructure(
            structure_type="Private Fund",
            is_permitted=True,
            min_capital=CapitalRequirement(
                amount=Decimal("50000000"),
                currency="AED",
                amount_usd_equivalent=Decimal("13610000"),
            ),
        ),
    ],
    investor_requirements=InvestorRequirements(
        qualified_investor_required=True,
        min_investment_usd=Decimal("500000"),
        residency_restrictions=[],
        accreditation_standard="SCA Qualified Investor Definition",
    ),
    filing_obligations=[
        RegulatoryFiling(
            filing_type="Annual Report",
            frequency="Annual",
            regulator="SCA",
            deadline_description="Within 4 months of fiscal year end",
            format_required="XBRL",
        ),
        RegulatoryFiling(
            filing_type="AUM Disclosure",
            frequency="Quarterly",
            regulator="SCA",
            deadline_description="Within 30 days of quarter end",
        ),
    ],
    tax_summary="No corporate tax on fund income. VAT at 5% applies to management fees.",
    withholding_tax_rate=Decimal("0"),
    aml_kyc_framework="UAE AML/CFT Law No. 20 of 2018",
    passporting_available=False,
    passporting_notes="No formal passporting regime; cross-border distribution requires separate approval.",
    source_governance=source_governance,
    confidence=ConfidenceScore(
        level=ConfidenceLevel.HIGH,
        score=0.90,
        rationale="Based on primary SCA source with secondary legal commentary.",
        contributing_factors=["Primary government source", "Recent publication 2024"],
    ),
    version=VersionRecord(
        version_id="1.0.0",
        author="legal-swarm-system",
        change_summary="Initial entry",
    ),
)

print(f"Entry created: {entry.jurisdiction_name} ({entry.jurisdiction_code})")
print(f"Fund structures: {len(entry.permitted_fund_structures)}")
print(f"Filing obligations: {len(entry.filing_obligations)}")


# ---------------------------------------------------------------------------
# Step 3 — Validate
# ---------------------------------------------------------------------------
print("\n=== STEP 3: Running validation ===")

engine = ValidationEngine()
report = engine.validate(entry)

print(f"Overall status: {report.overall_status}")
for result in report.results:
    icon = "✓" if result.status.value == "PASSED" else ("⚠" if result.status.value == "WARNING" else "✗")
    print(f"  {icon} [{result.rule_id}] {result.rule_description} → {result.status.value}")


# ---------------------------------------------------------------------------
# Step 4 — Confidence scoring
# ---------------------------------------------------------------------------
print("\n=== STEP 4: Confidence scoring ===")

scorer = ConfidenceScorer()
confidence = scorer.score(entry)

print(f"Score: {confidence.score}")
print(f"Level: {confidence.level}")
print(f"Rationale: {confidence.rationale}")
for factor in confidence.contributing_factors:
    print(f"  - {factor}")


# ---------------------------------------------------------------------------
# Step 5 — Contradiction detection
# ---------------------------------------------------------------------------
print("\n=== STEP 5: Contradiction detection ===")

detector = CitationContradictionDetector()
contradictions = detector.detect(entry)

if contradictions:
    for c in contradictions:
        print(f"  ! Contradiction on {c.field_path}: {c.value_a} vs {c.value_b}")
else:
    print("  No contradictions detected.")


# ---------------------------------------------------------------------------
# Step 6 — Audit log
# ---------------------------------------------------------------------------
print("\n=== STEP 6: Audit logging ===")

logger = AuditLogger(log_path=Path("logs/audit.jsonl"))
log_entry = logger.log(
    event_type=AuditEventType.VALIDATION,
    actor="main.py",
    jurisdiction_code=entry.jurisdiction_code,
    entry_id=entry.entry_id,
    payload={
        "validation_status": report.overall_status.value,
        "confidence_score": float(confidence.score),
        "contradictions_found": len(contradictions),
    },
    outcome="Pipeline completed successfully",
)

print(f"Audit log written → logs/audit.jsonl")
print(f"Log ID: {log_entry.log_id}")
print(f"Event: {log_entry.event_type}")

print("\n=== DONE ===")
print(f"Entry ID: {entry.entry_id}")
print(f"Schema version: {entry.schema_version}")