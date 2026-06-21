"""Unit tests for validation engine."""

import pytest
from src.schema.schema import ConfidenceLevel, ConfidenceScore, JurisdictionTier, SourceAuthority, ValidationStatus
from src.validation.validators import (
    ValidationEngine,
    HasPrimaryRegulatorRule,
    HasAtLeastOneFundStructureRule,
    ConfidenceThresholdRule,
    HasSourceCitationsRule,
    FilingObligationsRule,
)
from tests.unit.test_schema import make_citation, make_confidence, make_entry, make_governance, make_version
from src.schema.schema import (
    CitationRecord,
    FundStructure,
    RegulatoryFiling,
    SourceGovernanceRecord,
    RegulatoryEntry,
)


class TestHasPrimaryRegulatorRule:
    def test_passes_with_regulator(self):
        entry = make_entry(primary_regulator="SCA")
        result = HasPrimaryRegulatorRule().check(entry)
        assert result.status == ValidationStatus.PASSED

    def test_fails_with_empty_regulator(self):
        entry = make_entry.__wrapped__ if hasattr(make_entry, '__wrapped__') else None
        # Build manually to bypass regulator check
        from src.schema.schema import RegulatoryEntry, JurisdictionTier
        entry = RegulatoryEntry(
            jurisdiction_code="AE",
            jurisdiction_name="UAE",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="   ",
            source_governance=make_governance(),
            confidence=make_confidence(),
            version=make_version(),
        )
        result = HasPrimaryRegulatorRule().check(entry)
        assert result.status == ValidationStatus.FAILED


class TestHasAtLeastOneFundStructureRule:
    def test_warns_when_no_structures(self):
        entry = make_entry()
        result = HasAtLeastOneFundStructureRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_structure(self):
        from src.schema.schema import FundStructure
        entry = make_entry(permitted_fund_structures=[
            FundStructure(structure_type="Open-Ended", is_permitted=True)
        ])
        result = HasAtLeastOneFundStructureRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestConfidenceThresholdRule:
    def test_passes_high_confidence(self):
        entry = make_entry(confidence=make_confidence(score=0.9, level=ConfidenceLevel.HIGH))
        result = ConfidenceThresholdRule().check(entry)
        assert result.status == ValidationStatus.PASSED

    def test_passes_unverified_low_score(self):
        entry = make_entry(confidence=make_confidence(score=0.3, level=ConfidenceLevel.UNVERIFIED))
        result = ConfidenceThresholdRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestHasSourceCitationsRule:
    def test_passes_with_primary_citation(self):
        entry = make_entry()
        result = HasSourceCitationsRule().check(entry)
        assert result.status == ValidationStatus.PASSED

    def test_fails_without_primary_citation(self):
        from src.schema.schema import RegulatoryEntry, JurisdictionTier, SourceGovernanceRecord
        c = make_citation(authority=SourceAuthority.SECONDARY)
        governance = SourceGovernanceRecord(secondary_citations=[c])
        entry = RegulatoryEntry(
            jurisdiction_code="AE",
            jurisdiction_name="UAE",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="SCA",
            source_governance=governance,
            confidence=make_confidence(),
            version=make_version(),
        )
        result = HasSourceCitationsRule().check(entry)
        assert result.status == ValidationStatus.FAILED


class TestFilingObligationsRule:
    def test_warns_when_no_filings(self):
        entry = make_entry()
        result = FilingObligationsRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_filing(self):
        from src.schema.schema import RegulatoryFiling
        entry = make_entry(filing_obligations=[
            RegulatoryFiling(filing_type="Annual Report", frequency="Annual", regulator="SCA")
        ])
        result = FilingObligationsRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestValidationEngine:
    def test_engine_returns_report(self):
        engine = ValidationEngine()
        entry = make_entry()
        report = engine.validate(entry)
        assert report is not None
        assert len(report.results) == 5

    def test_engine_add_rule(self):
        from src.validation.validators import ValidationRule
        from src.schema.schema import ValidationResult, ValidationStatus

        class DummyRule(ValidationRule):
            rule_id = "VAL_999"
            rule_description = "Dummy"
            def check(self, entry):
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_description=self.rule_description,
                    status=ValidationStatus.PASSED,
                )

        engine = ValidationEngine()
        engine.add_rule(DummyRule())
        entry = make_entry()
        report = engine.validate(entry)
        assert len(report.results) == 6