"""Unit tests for validation engine."""

from src.schema.schema import ConfidenceLevel, JurisdictionTier, SourceAuthority, ValidationStatus
from src.validation.validators import (
    ValidationEngine,
    HasPrimaryRegulatorRule,
    HasAtLeastOneFundStructureRule,
    ConfidenceThresholdRule,
    HasSourceCitationsRule,
    FilingObligationsRule,
    LicensingRequirementsRule,
    SubstanceRequirementsRule,
    RegulatoryTimelinesRule,
    RegulatoryCostsRule,
    PenaltyExposureRule,
    WindDownProcedureRule,
    FundManagerRequirementsRule,
    BeneficialOwnershipRulesRule,
    RecordRetentionPoliciesRule,
    MinimumPrimaryCitationsRule,
    TaxCitationForTaxSummaryRule,
    CapitalCitationForCapitalRequirementsRule,
    SilentNullProhibitionRule,
)
from tests.unit.test_schema import make_citation, make_confidence, make_entry, make_governance, make_version
from src.schema.schema import (
    CapitalRequirement,
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
        from src.schema.schema import SourceGovernanceRecord
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
        entry = make_entry(filing_obligations=[
            RegulatoryFiling(filing_type="Annual Report", frequency="Annual", regulator="SCA")
        ])
        result = FilingObligationsRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestLicensingRequirementsRule:
    def test_warns_when_none(self):
        entry = make_entry(licensing_requirements=None)
        result = LicensingRequirementsRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_warns_when_empty(self):
        entry = make_entry(licensing_requirements=[])
        result = LicensingRequirementsRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_licensing(self):
        from src.schema.schema import LicensingRequirement
        entry = make_entry(licensing_requirements=[
            LicensingRequirement(licence_type="Test", issuing_authority="SCA", applies_to="Fund")
        ])
        result = LicensingRequirementsRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestSubstanceRequirementsRule:
    def test_warns_when_none(self):
        entry = make_entry(substance_requirements=None)
        result = SubstanceRequirementsRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_substance(self):
        from src.schema.schema import SubstanceRequirement
        entry = make_entry(substance_requirements=SubstanceRequirement(
            local_office_required=True, local_directors_required=True, local_staff_required=True,
        ))
        result = SubstanceRequirementsRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestRegulatoryTimelinesRule:
    def test_warns_when_none(self):
        entry = make_entry(regulatory_timelines=None)
        result = RegulatoryTimelinesRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_warns_when_empty(self):
        entry = make_entry(regulatory_timelines=[])
        result = RegulatoryTimelinesRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_timeline(self):
        from src.schema.schema import RegulatoryTimeline
        entry = make_entry(regulatory_timelines=[
            RegulatoryTimeline(process_name="Fund Registration")
        ])
        result = RegulatoryTimelinesRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestRegulatoryCostsRule:
    def test_warns_when_none(self):
        entry = make_entry(regulatory_costs=None)
        result = RegulatoryCostsRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_warns_when_empty(self):
        entry = make_entry(regulatory_costs=[])
        result = RegulatoryCostsRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_cost(self):
        from src.schema.schema import RegulatoryCost
        entry = make_entry(regulatory_costs=[
            RegulatoryCost(cost_type="Formation Fee", currency="USD", frequency="One-time")
        ])
        result = RegulatoryCostsRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestPenaltyExposureRule:
    def test_warns_when_none(self):
        entry = make_entry(penalty_exposure=None)
        result = PenaltyExposureRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_warns_when_empty(self):
        entry = make_entry(penalty_exposure=[])
        result = PenaltyExposureRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_penalty(self):
        from src.schema.schema import PenaltyExposure
        entry = make_entry(penalty_exposure=[
            PenaltyExposure(breach_type="Late Filing")
        ])
        result = PenaltyExposureRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestWindDownProcedureRule:
    def test_warns_when_none(self):
        entry = make_entry(wind_down_procedure=None)
        result = WindDownProcedureRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_procedure(self):
        from src.schema.schema import WindDownProcedure
        entry = make_entry(wind_down_procedure=WindDownProcedure())
        result = WindDownProcedureRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestFundManagerRequirementsRule:
    def test_warns_when_none(self):
        entry = make_entry(fund_manager_requirements=None)
        result = FundManagerRequirementsRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_requirements(self):
        from src.schema.schema import FundManagerRequirement
        entry = make_entry(fund_manager_requirements=FundManagerRequirement())
        result = FundManagerRequirementsRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestBeneficialOwnershipRulesRule:
    def test_warns_when_none(self):
        entry = make_entry(beneficial_ownership_rules=None)
        result = BeneficialOwnershipRulesRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_rules(self):
        from src.schema.schema import BeneficialOwnershipRule
        entry = make_entry(beneficial_ownership_rules=BeneficialOwnershipRule())
        result = BeneficialOwnershipRulesRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestRecordRetentionPoliciesRule:
    def test_warns_when_none(self):
        entry = make_entry(record_retention_policies=None)
        result = RecordRetentionPoliciesRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_warns_when_empty(self):
        entry = make_entry(record_retention_policies=[])
        result = RecordRetentionPoliciesRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_passes_with_policies(self):
        from src.schema.schema import RecordRetentionPolicy
        entry = make_entry(record_retention_policies=[
            RecordRetentionPolicy(minimum_retention_years=7, applies_to="All Fund Records")
        ])
        result = RecordRetentionPoliciesRule().check(entry)
        assert result.status == ValidationStatus.PASSED


class TestMinimumPrimaryCitationsRule:
    def test_passes_with_two_or_more(self):
        c1 = make_citation(authority=SourceAuthority.PRIMARY)
        c2 = make_citation(authority=SourceAuthority.PRIMARY)
        governance = SourceGovernanceRecord(primary_citations=[c1, c2])
        entry = make_entry(source_governance=governance)
        result = MinimumPrimaryCitationsRule().check(entry)
        assert result.status == ValidationStatus.PASSED

    def test_fails_with_one_primary(self):
        c = make_citation(authority=SourceAuthority.PRIMARY)
        governance = SourceGovernanceRecord(primary_citations=[c])
        entry = make_entry(source_governance=governance)
        result = MinimumPrimaryCitationsRule().check(entry)
        assert result.status == ValidationStatus.FAILED


class TestTaxCitationForTaxSummaryRule:
    def test_passes_with_tax_citation(self):
        c = make_citation(regulatory_relevance_tag="Tax Framework")
        governance = SourceGovernanceRecord(primary_citations=[c])
        entry = make_entry(tax_summary="Some tax rules", source_governance=governance)
        result = TaxCitationForTaxSummaryRule().check(entry)
        assert result.status == ValidationStatus.PASSED

    def test_passes_when_tax_summary_none(self):
        entry = make_entry(tax_summary=None)
        result = TaxCitationForTaxSummaryRule().check(entry)
        assert result.status == ValidationStatus.PASSED

    def test_warns_with_no_tax_citation(self):
        c = make_citation(regulatory_relevance_tag="Licensing")
        governance = SourceGovernanceRecord(primary_citations=[c])
        entry = make_entry(tax_summary="Some tax", source_governance=governance)
        result = TaxCitationForTaxSummaryRule().check(entry)
        assert result.status == ValidationStatus.WARNING


class TestCapitalCitationForCapitalRequirementsRule:
    def test_passes_with_capital_citation(self):
        from decimal import Decimal
        c = make_citation(regulatory_relevance_tag="Capital Requirements")
        governance = SourceGovernanceRecord(primary_citations=[c])
        entry = make_entry(
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Test", is_permitted=True,
                    min_capital=CapitalRequirement(amount=Decimal("1000"), currency="USD"),
                )
            ],
            source_governance=governance,
        )
        result = CapitalCitationForCapitalRequirementsRule().check(entry)
        assert result.status == ValidationStatus.PASSED

    def test_passes_no_capital(self):
        entry = make_entry(permitted_fund_structures=[])
        result = CapitalCitationForCapitalRequirementsRule().check(entry)
        assert result.status == ValidationStatus.PASSED

    def test_warns_no_capital_citation(self):
        from decimal import Decimal
        c = make_citation(regulatory_relevance_tag="Licensing")
        governance = SourceGovernanceRecord(primary_citations=[c])
        entry = make_entry(
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Test", is_permitted=True,
                    min_capital=CapitalRequirement(amount=Decimal("1000"), currency="USD"),
                )
            ],
            source_governance=governance,
        )
        result = CapitalCitationForCapitalRequirementsRule().check(entry)
        assert result.status == ValidationStatus.WARNING


class TestSilentNullProhibitionRule:
    def test_passes_when_all_populated(self):
        entry = make_entry(tax_summary="N/A", aml_kyc_framework="N/A", passporting_notes="N/A")
        result = SilentNullProhibitionRule().check(entry)
        assert result.status == ValidationStatus.PASSED

    def test_warns_when_tax_summary_none(self):
        entry = make_entry(tax_summary=None, aml_kyc_framework="N/A", passporting_notes="N/A")
        result = SilentNullProhibitionRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_warns_when_aml_none(self):
        entry = make_entry(tax_summary="N/A", aml_kyc_framework=None, passporting_notes="N/A")
        result = SilentNullProhibitionRule().check(entry)
        assert result.status == ValidationStatus.WARNING

    def test_warns_when_passporting_none(self):
        entry = make_entry(tax_summary="N/A", aml_kyc_framework="N/A", passporting_notes=None)
        result = SilentNullProhibitionRule().check(entry)
        assert result.status == ValidationStatus.WARNING


class TestValidationEngine:
    def test_engine_returns_report(self):
        engine = ValidationEngine()
        entry = make_entry(tax_summary="N/A", aml_kyc_framework="N/A", passporting_notes="N/A")
        report = engine.validate(entry)
        assert report is not None
        assert len(report.results) == 18

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
        entry = make_entry(tax_summary="N/A", aml_kyc_framework="N/A", passporting_notes="N/A")
        report = engine.validate(entry)
        assert len(report.results) == 19