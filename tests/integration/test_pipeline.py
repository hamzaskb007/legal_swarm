"""Integration test — full end-to-end pipeline."""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from src.schema.schema import (
    BeneficialOwnershipRule,
    CapitalRequirement,
    CitationRecord,
    ConfidenceLevel,
    ConfidenceScore,
    FundManagerRequirement,
    FundStructure,
    InvestorRequirements,
    JurisdictionTier,
    LicensingRequirement,
    PenaltyExposure,
    RecordRetentionPolicy,
    RegulatoryCost,
    RegulatoryEntry,
    RegulatoryFiling,
    RegulatoryTimeline,
    SourceAuthority,
    SubstanceRequirement,
    AuditEventType,
    VersionRecord,
    WindDownProcedure,
)
from src.validation import ValidationStatus
from src.governance.source_governance import SourceGovernanceManager
from src.validation.validators import ValidationEngine
from src.confidence.scorer import ConfidenceScorer
from src.contradiction.detector import CitationContradictionDetector
from src.audit.logger import AuditLogger
from src.versioning.delta_tracker import DeltaTracker


@pytest.fixture
def full_entry():
    manager = SourceGovernanceManager()

    # Regulatory Framework citation 1
    c1_citation_id = uuid4()
    manager.add_citation(
        CitationRecord(
            citation_id=c1_citation_id,
            source_name="UAE SCA Regulatory Framework",
            source_url="https://sca.gov.ae",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            publication_date=datetime(2024, 1, 1),
            reliability_score=0.95,
            regulatory_relevance_tag="Regulatory Framework",
            last_verified_timestamp=datetime.utcnow(),
        )
    )

    # Regulatory Framework citation 2
    c2_citation_id = uuid4()
    manager.add_citation(
        CitationRecord(
            citation_id=c2_citation_id,
            source_name="UAE Federal Law No. 4 of 2000",
            source_url="https://www.sca.gov.ae/legislation/federal-law-no-4-2000",
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2000, 1, 1),
            section_reference="Article 12",
            reliability_score=0.95,
            regulatory_relevance_tag="Regulatory Framework",
            last_verified_timestamp=datetime.utcnow(),
        )
    )

    # Capital Requirements citation 1
    manager.add_citation(
        CitationRecord(
            source_name="UAE Fund Capital Rules",
            source_url="https://www.sca.gov.ae/legislation/capital-rules",
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2023, 1, 1),
            section_reference="Chapter 4",
            reliability_score=0.95,
            regulatory_relevance_tag="Capital Requirements",
            last_verified_timestamp=datetime.utcnow(),
        )
    )

    # Capital Requirements citation 2
    manager.add_citation(
        CitationRecord(
            source_name="UAE Minimum Capital Requirements",
            source_url="https://www.sca.gov.ae/legislation/minimum-capital",
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2023, 6, 1),
            section_reference="Section 8",
            reliability_score=0.94,
            regulatory_relevance_tag="Capital Requirements",
            last_verified_timestamp=datetime.utcnow(),
        )
    )

    # Tax Framework citation 1
    manager.add_citation(
        CitationRecord(
            source_name="UAE Tax Law",
            source_url="https://www.sca.gov.ae/legislation/tax-law",
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2022, 1, 1),
            section_reference="Article 15",
            reliability_score=0.95,
            regulatory_relevance_tag="Tax Framework",
            last_verified_timestamp=datetime.utcnow(),
        )
    )

    # Tax Framework citation 2 (Level 4 referencing c1)
    manager.add_citation(
        CitationRecord(
            source_name="Legal Commentary on UAE Tax",
            source_url="https://www.legal500.com/guides/chapter/uae-tax/",
            authority=SourceAuthority.SECONDARY,
            authority_level=4,
            publication_date=datetime(2024, 6, 1),
            reliability_score=0.75,
            regulatory_relevance_tag="Tax Framework",
            references_citation_id=c1_citation_id,
            last_verified_timestamp=datetime.utcnow(),
        )
    )

    # Compliance Obligations citation (authoritative)
    manager.add_citation(
        CitationRecord(
            source_name="UAE AML Compliance Requirements",
            source_url="https://www.sca.gov.ae/legislation/aml-rules",
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2023, 3, 1),
            section_reference="Part 2",
            reliability_score=0.95,
            regulatory_relevance_tag="Compliance Obligations",
            last_verified_timestamp=datetime.utcnow(),
        )
    )

    governance = manager.build()

    return RegulatoryEntry(
        jurisdiction_code="AE",
        jurisdiction_name="United Arab Emirates",
        tier=JurisdictionTier.TIER_1,
        primary_regulator="Securities and Commodities Authority",
        permitted_fund_structures=[
            FundStructure(
                structure_type="Public Fund",
                is_permitted=True,
                min_capital=CapitalRequirement(
                    amount=Decimal("10000000"),
                    currency="AED",
                    amount_usd_equivalent=Decimal("2722000"),
                ),
            )
        ],
        investor_requirements=InvestorRequirements(
            qualified_investor_required=True,
            min_investment_usd=Decimal("500000"),
        ),
        filing_obligations=[
            RegulatoryFiling(
                filing_type="Annual Report",
                frequency="Annual",
                regulator="SCA",
            )
        ],
        licensing_requirements=[
            LicensingRequirement(
                licence_type="Fund Licence", issuing_authority="SCA", applies_to="Fund"
            ),
        ],
        substance_requirements=SubstanceRequirement(
            local_office_required=True,
            local_directors_required=True,
            local_staff_required=True,
        ),
        regulatory_timelines=[
            RegulatoryTimeline(process_name="Fund Registration"),
        ],
        regulatory_costs=[
            RegulatoryCost(cost_type="Formation Fee", currency="USD", frequency="One-time"),
        ],
        penalty_exposure=[
            PenaltyExposure(breach_type="Late Filing"),
        ],
        wind_down_procedure=WindDownProcedure(),
        fund_manager_requirements=FundManagerRequirement(),
        beneficial_ownership_rules=BeneficialOwnershipRule(),
        record_retention_policies=[
            RecordRetentionPolicy(minimum_retention_years=7, applies_to="All Fund Records"),
        ],
        tax_summary="No corporate tax on fund income.",
        withholding_tax_rate=Decimal("0"),
        aml_kyc_framework="UAE AML Law No. 20 of 2018",
        passporting_available=False,
        passporting_notes="Not Applicable — no passporting regime exists for this jurisdiction",
        source_governance=governance,
        confidence=ConfidenceScore(
            level=ConfidenceLevel.HIGH,
            score=0.90,
            rationale="Primary government source.",
        ),
        version=VersionRecord(version_id="1.0.0", author="test"),
    )


class TestFullPipeline:
    def test_entry_constructed(self, full_entry):
        assert full_entry.jurisdiction_code == "AE"

    def test_validation_passes(self, full_entry):
        engine = ValidationEngine()
        report = engine.validate(full_entry)
        assert report.overall_status == ValidationStatus.PASSED

    def test_confidence_scored(self, full_entry):
        scorer = ConfidenceScorer()
        result = scorer.score(full_entry)
        assert result.score > 0
        assert result.level is not None

    def test_no_contradictions(self, full_entry):
        detector = CitationContradictionDetector()
        result = detector.detect(full_entry)
        assert result == []

    def test_audit_logged(self, full_entry, tmp_path):
        logger = AuditLogger(log_path=tmp_path / "audit.jsonl")
        entry = logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="integration-test",
            jurisdiction_code=full_entry.jurisdiction_code,
            entry_id=full_entry.entry_id,
            payload={"status": "PASSED"},
        )
        assert entry.event_type == AuditEventType.VALIDATION
        logs = logger.read_all()
        assert len(logs) == 1

    def test_delta_tracking(self, full_entry):
        new_entry = full_entry.model_copy(update={"primary_regulator": "DFSA"})
        tracker = DeltaTracker(tracked_fields=["primary_regulator"])
        record = tracker.compute_delta(full_entry, new_entry)
        assert len(record.deltas) == 1
        assert record.version_id == "1.0.1"

    def test_pipeline_is_deterministic(self, full_entry):
        engine = ValidationEngine()
        scorer = ConfidenceScorer()
        r1 = engine.validate(full_entry)
        r2 = engine.validate(full_entry)
        s1 = scorer.score(full_entry)
        s2 = scorer.score(full_entry)
        assert r1.overall_status == r2.overall_status
        assert s1.score == s2.score

    def test_hard_gate_accepts_valid_entry(self, full_entry):
        from src.jurisdictions.base import JurisdictionBuilder

        class PassthroughBuilder(JurisdictionBuilder):
            def build_entry(self):
                return full_entry

        builder = PassthroughBuilder()
        entry, report = builder.run_pipeline(full_entry)
        assert report.overall_status != ValidationStatus.FAILED

    def test_hard_gate_rejects_failed_entry(self):
        from src.jurisdictions.base import JurisdictionBuilder
        from src.governance.source_governance import SourceGovernanceManager
        from src.schema.schema import (
            CitationRecord, ConfidenceScore, ConfidenceLevel,
            FundStructure, InvestorRequirements, JurisdictionTier,
            RegulatoryEntry, SourceAuthority, VersionRecord,
        )

        manager = SourceGovernanceManager()
        manager.add_citation(
            CitationRecord(
                source_name="Test Source",
                source_url="https://test.gov/rule",
                authority=SourceAuthority.SECONDARY,
                authority_level=4,
                publication_date=datetime(2026, 1, 1),
                reliability_score=0.5,
                regulatory_relevance_tag="Regulatory Framework",
                last_verified_timestamp=datetime.utcnow(),
            )
        )
        governance = manager.build()

        bad_entry = RegulatoryEntry(
            jurisdiction_code="XX",
            jurisdiction_name="Test",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="Test Regulator",
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Test Fund",
                    is_permitted=True,
                    min_capital=CapitalRequirement(amount=Decimal("1000000"), currency="USD"),
                )
            ],
            investor_requirements=InvestorRequirements(qualified_investor_required=True),
            tax_summary="N/A",
            aml_kyc_framework="N/A",
            passporting_notes="N/A",
            source_governance=governance,
            confidence=ConfidenceScore(
                level=ConfidenceLevel.UNVERIFIED, score=0.0,
                rationale="Test placeholder",
            ),
            version=VersionRecord(version_id="1.0.0", author="test"),
        )

        class FailingBuilder(JurisdictionBuilder):
            def build_entry(self):
                return bad_entry

        builder = FailingBuilder()
        with pytest.raises(ValueError, match="validation FAILED"):
            builder.run_pipeline(bad_entry)
