"""Integration test — full end-to-end pipeline."""

import pytest
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
    ValidationStatus,
)
from src.governance.source_governance import SourceGovernanceManager
from src.validation.validators import ValidationEngine
from src.confidence.scorer import ConfidenceScorer
from src.contradiction.detector import CitationContradictionDetector
from src.audit.logger import AuditLogger
from src.versioning.delta_tracker import DeltaTracker


@pytest.fixture
def full_entry():
    manager = SourceGovernanceManager()
    manager.add_citation(CitationRecord(
        source_name="UAE SCA",
        source_url="https://sca.gov.ae",
        authority=SourceAuthority.PRIMARY,
        publication_date=datetime(2024, 1, 1),
        reliability_score=0.95,
    ))
    manager.add_citation(CitationRecord(
        source_name="Legal Commentary",
        source_url="https://legal.example.com",
        authority=SourceAuthority.SECONDARY,
        reliability_score=0.75,
    ))
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
        tax_summary="No corporate tax on fund income.",
        withholding_tax_rate=Decimal("0"),
        aml_kyc_framework="UAE AML Law No. 20 of 2018",
        passporting_available=False,
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
        import copy
        new_entry = full_entry.model_copy(
            update={"primary_regulator": "DFSA"}
        )
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