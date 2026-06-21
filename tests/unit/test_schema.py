"""Unit tests for master canonical schema."""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from src.schema.schema import (
    CitationRecord,
    ConfidenceLevel,
    ConfidenceScore,
    SourceAuthority,
    SourceGovernanceRecord,
    CapitalRequirement,
    ContradictionRecord,
    ValidationResult,
    ValidationReport,
    ValidationStatus,
    FieldDelta,
    VersionRecord,
    ChangeType,
    AuditLogEntry,
    AuditEventType,
    FundStructure,
    InvestorRequirements,
    RegulatoryFiling,
    RegulatoryEntry,
    JurisdictionTier,
)


def make_citation(**kwargs) -> CitationRecord:
    defaults = dict(
        source_name="Test Source",
        authority=SourceAuthority.PRIMARY,
        reliability_score=0.9,
    )
    defaults.update(kwargs)
    return CitationRecord(**defaults)


def make_governance(citations=None) -> SourceGovernanceRecord:
    citations = citations or [make_citation()]
    return SourceGovernanceRecord(primary_citations=citations)


def make_confidence(**kwargs) -> ConfidenceScore:
    defaults = dict(level=ConfidenceLevel.HIGH, score=0.9, rationale="Test")
    defaults.update(kwargs)
    return ConfidenceScore(**defaults)


def make_version(**kwargs) -> VersionRecord:
    defaults = dict(version_id="1.0.0", author="test")
    defaults.update(kwargs)
    return VersionRecord(**defaults)


def make_entry(**kwargs) -> RegulatoryEntry:
    defaults = dict(
        jurisdiction_code="AE",
        jurisdiction_name="United Arab Emirates",
        tier=JurisdictionTier.TIER_1,
        primary_regulator="SCA",
        source_governance=make_governance(),
        confidence=make_confidence(),
        version=make_version(),
    )
    defaults.update(kwargs)
    return RegulatoryEntry(**defaults)


# ---------------------------------------------------------------------------
# CitationRecord
# ---------------------------------------------------------------------------

class TestCitationRecord:
    def test_valid_citation(self):
        c = make_citation()
        assert c.source_name == "Test Source"
        assert c.reliability_score == 0.9

    def test_reliability_score_bounds(self):
        with pytest.raises(Exception):
            make_citation(reliability_score=1.5)
        with pytest.raises(Exception):
            make_citation(reliability_score=-0.1)

    def test_excerpt_length_cap(self):
        with pytest.raises(Exception):
            make_citation(raw_excerpt="x" * 2001)

    def test_excerpt_within_limit(self):
        c = make_citation(raw_excerpt="x" * 2000)
        assert len(c.raw_excerpt) == 2000

    def test_uuid_auto_generated(self):
        c = make_citation()
        assert c.citation_id is not None


# ---------------------------------------------------------------------------
# SourceGovernanceRecord
# ---------------------------------------------------------------------------

class TestSourceGovernanceRecord:
    def test_requires_at_least_one_citation(self):
        with pytest.raises(Exception):
            SourceGovernanceRecord()

    def test_valid_with_primary(self):
        g = make_governance()
        assert len(g.primary_citations) == 1

    def test_dominant_source_defaults_to_primary(self):
        g = make_governance()
        assert g.dominant_source == SourceAuthority.PRIMARY

    def test_secondary_only(self):
        c = make_citation(authority=SourceAuthority.SECONDARY)
        g = SourceGovernanceRecord(secondary_citations=[c])
        assert g.dominant_source == SourceAuthority.PRIMARY  # default field value


# ---------------------------------------------------------------------------
# CapitalRequirement
# ---------------------------------------------------------------------------

class TestCapitalRequirement:
    def test_decimal_precision(self):
        cap = CapitalRequirement(
            amount=Decimal("10000000.50"),
            currency="USD",
            amount_usd_equivalent=Decimal("10000000.50"),
        )
        assert cap.amount == Decimal("10000000.50")

    def test_currency_code(self):
        cap = CapitalRequirement(amount=Decimal("1000"), currency="AED")
        assert cap.currency == "AED"


# ---------------------------------------------------------------------------
# ConfidenceScore
# ---------------------------------------------------------------------------

class TestConfidenceScore:
    def test_valid_score(self):
        c = make_confidence(score=0.75, level=ConfidenceLevel.HIGH)
        assert c.score == 0.75

    def test_score_out_of_bounds_high(self):
        with pytest.raises(Exception):
            make_confidence(score=1.1)

    def test_score_out_of_bounds_low(self):
        with pytest.raises(Exception):
            make_confidence(score=-0.1)

    def test_rationale_required(self):
        with pytest.raises(Exception):
            ConfidenceScore(level=ConfidenceLevel.HIGH, score=0.9, rationale="")


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------

class TestValidationReport:
    def make_result(self, status: ValidationStatus) -> ValidationResult:
        return ValidationResult(
            rule_id="VAL_001",
            rule_description="Test rule",
            status=status,
        )

    def test_overall_failed_if_any_failed(self):
        entry_id = uuid4()
        report = ValidationReport(
            entry_id=entry_id,
            jurisdiction_code="AE",
            schema_version="1.0.0",
            results=[
                self.make_result(ValidationStatus.PASSED),
                self.make_result(ValidationStatus.FAILED),
            ],
        )
        assert report.overall_status == ValidationStatus.FAILED

    def test_overall_warning_if_no_failures(self):
        entry_id = uuid4()
        report = ValidationReport(
            entry_id=entry_id,
            jurisdiction_code="AE",
            schema_version="1.0.0",
            results=[
                self.make_result(ValidationStatus.PASSED),
                self.make_result(ValidationStatus.WARNING),
            ],
        )
        assert report.overall_status == ValidationStatus.WARNING

    def test_overall_passed_if_all_passed(self):
        entry_id = uuid4()
        report = ValidationReport(
            entry_id=entry_id,
            jurisdiction_code="AE",
            schema_version="1.0.0",
            results=[
                self.make_result(ValidationStatus.PASSED),
                self.make_result(ValidationStatus.PASSED),
            ],
        )
        assert report.overall_status == ValidationStatus.PASSED


# ---------------------------------------------------------------------------
# AuditLogEntry
# ---------------------------------------------------------------------------

class TestAuditLogEntry:
    def test_frozen_record(self):
        log = AuditLogEntry(
            event_type=AuditEventType.VALIDATION,
            actor="test",
        )
        with pytest.raises(Exception):
            log.actor = "modified"

    def test_auto_timestamp(self):
        log = AuditLogEntry(event_type=AuditEventType.QUERY, actor="test")
        assert log.timestamp is not None


# ---------------------------------------------------------------------------
# RegulatoryEntry
# ---------------------------------------------------------------------------

class TestRegulatoryEntry:
    def test_valid_entry(self):
        entry = make_entry()
        assert entry.jurisdiction_code == "AE"

    def test_jurisdiction_code_normalized_to_uppercase(self):
        entry = make_entry(jurisdiction_code="ae")
        assert entry.jurisdiction_code == "AE"

    def test_confidence_threshold_gate_rejects_low_score(self):
        with pytest.raises(Exception):
            make_entry(confidence=make_confidence(
                score=0.3,
                level=ConfidenceLevel.LOW,
            ))

    def test_confidence_threshold_gate_allows_unverified(self):
        entry = make_entry(confidence=make_confidence(
            score=0.3,
            level=ConfidenceLevel.UNVERIFIED,
        ))
        assert entry.confidence.level == ConfidenceLevel.UNVERIFIED

    def test_entry_id_auto_generated(self):
        entry = make_entry()
        assert entry.entry_id is not None

    def test_schema_version_default(self):
        entry = make_entry()
        assert entry.schema_version == "1.0.0"