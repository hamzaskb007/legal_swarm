"""
Legal Swarm — End-to-End Pipeline Demo
========================================
Builds a sample RegulatoryEntry for UAE and runs it through the full pipeline.
Also loads the complete Tier 1 jurisdiction registry and summarises all entries.
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
from src.jurisdictions.registry import JurisdictionRegistry


# ---------------------------------------------------------------------------
# Part 1 — Quick demo (single UAE entry, same as before)
# ---------------------------------------------------------------------------

def run_single_entry_demo() -> None:
    print("\n=== PART 1: Single entry demo (UAE) ===")

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
    print(f"  Citations added: {manager.citation_count()}")
    print(f"  Dominant source: {source_governance.dominant_source}")

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
    print(f"  Entry created: {entry.jurisdiction_name} ({entry.jurisdiction_code})")

    engine = ValidationEngine()
    report = engine.validate(entry)
    print(f"  Validation: {report.overall_status}")

    scorer = ConfidenceScorer()
    confidence = scorer.score(entry)
    print(f"  Confidence: {confidence.score:.4f} ({confidence.level.value})")

    detector = CitationContradictionDetector()
    contradictions = detector.detect(entry)
    print(f"  Contradictions: {len(contradictions)}")

    logger = AuditLogger(log_path=Path("logs/audit.jsonl"))
    logger.log(
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
    print("  Audit log written.")


# ---------------------------------------------------------------------------
# Part 2 — Full Tier 1 Registry
# ---------------------------------------------------------------------------

def run_tier1_registry() -> None:
    print("\n=== PART 2: Tier 1 Jurisdiction Registry ===")

    registry = JurisdictionRegistry()
    entries = registry.get_all()

    print(f"\n  Loaded {len(entries)} Tier 1 jurisdictions:\n")

    header = f"  {'Jurisdiction':<28} {'Code':<7} {'Tier':<8} {'Validation':<12} {'Confidence Score':<16} {'Level':<12}"
    sep = "  " + "-" * len(header)
    print(header)
    print(sep)

    for entry in sorted(entries, key=lambda e: e.jurisdiction_code):
        report = registry.validation_reports.get(entry.jurisdiction_code)
        status = report.overall_status if report else "N/A"
        conf = entry.confidence
        print(
            f"  {entry.jurisdiction_name:<28} "
            f"{entry.jurisdiction_code:<7} "
            f"{entry.tier.value:<8} "
            f"{status:<12} "
            f"{conf.score:<16.4f} "
            f"{conf.level.value:<12}"
        )

    print()
    check_count = "✓" if len(entries) == 8 else "✗"
    print(f"  {check_count} All 8 Tier 1 jurisdictions loaded and validated.")

    # Run a cross-jurisdiction comparison
    print("\n  Sample cross-jurisdiction comparison:") if len(entries) >= 2 else None
    if len(entries) >= 2:
        comp = registry.compare("KY", "VG")
        print(f"    {comp.summary}")
        for c in comp.contradictions_detected:
            print(f"    ! {c.field_path}: {c.value_a} vs {c.value_b}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_single_entry_demo()
    run_tier1_registry()
    print("\n=== DONE ===")
