"""Unit tests for Tier 1 jurisdiction builders."""

import pytest
from decimal import Decimal

from src.schema.schema import (
    ConfidenceLevel,
    JurisdictionTier,
    SourceAuthority,
    ValidationStatus,
)
from src.jurisdictions.base import JurisdictionBuilder
from src.jurisdictions.tier1.cayman_islands import CaymanIslandsBuilder
from src.jurisdictions.tier1.luxembourg import LuxembourgBuilder
from src.jurisdictions.tier1.ireland import IrelandBuilder
from src.jurisdictions.tier1.singapore import SingaporeBuilder
from src.jurisdictions.tier1.bvi import BviBuilder
from src.jurisdictions.tier1.uae import UaeBuilder
from src.jurisdictions.tier1.jersey import JerseyBuilder
from src.jurisdictions.tier1.delaware import DelawareBuilder
from src.validation.validators import ValidationEngine
from src.confidence.scorer import ConfidenceScorer
from src.contradiction.detector import CitationContradictionDetector


ALL_BUILDERS = [
    CaymanIslandsBuilder,
    LuxembourgBuilder,
    IrelandBuilder,
    SingaporeBuilder,
    BviBuilder,
    UaeBuilder,
    JerseyBuilder,
    DelawareBuilder,
]


@pytest.fixture(params=ALL_BUILDERS, ids=lambda cls: cls.__name__)
def builder(request):
    return request.param()


class TestJurisdictionBuilders:
    def test_builder_is_valid_subclass(self, builder):
        assert isinstance(builder, JurisdictionBuilder)

    def test_entry_has_correct_tier(self, builder):
        entry = builder.build_entry()
        assert entry.tier == JurisdictionTier.TIER_1

    def test_entry_has_code(self, builder):
        entry = builder.build_entry()
        assert len(entry.jurisdiction_code) >= 2
        assert entry.jurisdiction_code.isupper()

    def test_entry_has_name(self, builder):
        entry = builder.build_entry()
        assert len(entry.jurisdiction_name) > 0

    def test_entry_has_primary_regulator(self, builder):
        entry = builder.build_entry()
        assert len(entry.primary_regulator.strip()) > 0

    def test_entry_has_source_governance(self, builder):
        entry = builder.build_entry()
        sg = entry.source_governance
        total = len(sg.primary_citations) + len(sg.secondary_citations) + len(sg.tertiary_citations)
        assert total >= 1
        assert sg.dominant_source in (
            SourceAuthority.PRIMARY,
            SourceAuthority.SECONDARY,
            SourceAuthority.TERTIARY,
        )

    def test_entry_has_primary_citations(self, builder):
        entry = builder.build_entry()
        assert len(entry.source_governance.primary_citations) >= 1

    def test_entry_has_fund_structures(self, builder):
        entry = builder.build_entry()
        assert len(entry.permitted_fund_structures) >= 1

    def test_entry_has_filing_obligations(self, builder):
        entry = builder.build_entry()
        assert len(entry.filing_obligations) >= 1

    def test_entry_has_investor_requirements(self, builder):
        entry = builder.build_entry()
        assert entry.investor_requirements is not None

    def test_entry_has_tax_summary(self, builder):
        entry = builder.build_entry()
        assert entry.tax_summary is not None

    def test_entry_has_aml_kyc_framework(self, builder):
        entry = builder.build_entry()
        assert entry.aml_kyc_framework is not None

    def test_entry_has_version_record(self, builder):
        entry = builder.build_entry()
        assert entry.version.version_id == "1.0.0"
        assert entry.version.author is not None

    def test_entry_has_placeholder_confidence(self, builder):
        entry = builder.build_entry()
        assert entry.confidence.level == ConfidenceLevel.UNVERIFIED
        assert entry.confidence.score == 0.0

    def test_all_citations_have_real_urls(self, builder):
        entry = builder.build_entry()
        sg = entry.source_governance
        # Primary citations use source_url=None with section_reference instead
        for c in sg.primary_citations:
            assert c.section_reference is not None, f"{c.source_name} has no section_reference"
            assert len(c.section_reference) > 0
            assert c.reliability_score > 0
            assert c.authority == SourceAuthority.PRIMARY

        # Secondary/tertiary citations must have stable homepage URLs
        for c in sg.secondary_citations + sg.tertiary_citations:
            assert c.source_url is not None, f"{c.source_name} has no URL"
            assert c.source_url.startswith("https://"), (
                f"{c.source_name} URL not HTTPS: {c.source_url}"
            )
            assert c.reliability_score > 0

    def test_citations_have_dates(self, builder):
        entry = builder.build_entry()
        sg = entry.source_governance
        all_citations = sg.primary_citations + sg.secondary_citations + sg.tertiary_citations
        for c in all_citations:
            assert c.publication_date is not None, f"{c.source_name} has no publication_date"

    def test_no_contradictions_at_build_time(self, builder):
        entry = builder.build_entry()
        assert entry.contradictions == []

    def test_entry_has_licensing_requirements(self, builder):
        entry = builder.build_entry()
        assert entry.licensing_requirements is not None
        assert len(entry.licensing_requirements) >= 1
        lr = entry.licensing_requirements[0]
        assert len(lr.licence_type) > 0
        assert len(lr.issuing_authority) > 0

    def test_entry_has_substance_requirements(self, builder):
        entry = builder.build_entry()
        assert entry.substance_requirements is not None
        sr = entry.substance_requirements
        assert sr.local_office_required is not None
        assert sr.local_directors_required is not None

    def test_entry_has_regulatory_timelines(self, builder):
        entry = builder.build_entry()
        assert entry.regulatory_timelines is not None
        assert len(entry.regulatory_timelines) >= 1
        rt = entry.regulatory_timelines[0]
        assert rt.minimum_days > 0

    def test_entry_has_regulatory_costs(self, builder):
        entry = builder.build_entry()
        assert entry.regulatory_costs is not None
        assert len(entry.regulatory_costs) >= 1
        rc = entry.regulatory_costs[0]
        assert rc.amount > 0

    def test_entry_has_penalty_exposure(self, builder):
        entry = builder.build_entry()
        assert entry.penalty_exposure is not None
        assert len(entry.penalty_exposure) >= 1
        pe = entry.penalty_exposure[0]
        assert pe.maximum_fine_usd > 0

    def test_entry_has_wind_down_procedure(self, builder):
        entry = builder.build_entry()
        assert entry.wind_down_procedure is not None
        wd = entry.wind_down_procedure
        assert wd.voluntary_liquidation_available is not None
        assert wd.typical_duration_days > 0

    def test_entry_has_fund_manager_requirements(self, builder):
        entry = builder.build_entry()
        assert entry.fund_manager_requirements is not None
        fm = entry.fund_manager_requirements
        assert fm.local_manager_required is not None
        assert fm.fit_and_proper_required is not None

    def test_entry_has_marketing_restrictions(self, builder):
        entry = builder.build_entry()
        assert entry.marketing_restrictions is not None
        assert len(entry.marketing_restrictions) >= 1
        mr = entry.marketing_restrictions[0]
        assert len(mr.target_investor_type) > 0

    def test_entry_has_beneficial_ownership_rules(self, builder):
        entry = builder.build_entry()
        assert entry.beneficial_ownership_rules is not None
        bo = entry.beneficial_ownership_rules
        assert bo.register_required is not None
        assert len(bo.filing_authority) > 0

    def test_entry_has_record_retention_policies(self, builder):
        entry = builder.build_entry()
        assert entry.record_retention_policies is not None
        assert len(entry.record_retention_policies) >= 1
        rr = entry.record_retention_policies[0]
        assert rr.minimum_retention_years > 0


class TestJurisdictionPipeline:
    def test_pipeline_confidence_scored(self, builder):
        entry = builder.build_entry()
        scorer = ConfidenceScorer()
        confidence = scorer.score(entry)
        assert 0.0 <= confidence.score <= 1.0
        assert confidence.level in ConfidenceLevel

    def test_pipeline_validation_passes(self, builder):
        entry = builder.build_entry()
        scorer = ConfidenceScorer()
        confidence = scorer.score(entry)
        entry = entry.model_copy(update={"confidence": confidence})

        engine = ValidationEngine()
        report = engine.validate(entry)
        assert report.overall_status != ValidationStatus.FAILED, (
            f"Validation FAILED for {entry.jurisdiction_code}: {[r for r in report.results if r.status == ValidationStatus.FAILED]}"
        )

    def test_pipeline_contradiction_detection(self, builder):
        entry = builder.build_entry()
        detector = CitationContradictionDetector()
        contradictions = detector.detect(entry)
        assert isinstance(contradictions, list)

    def test_pipeline_deterministic_confidence(self, builder):
        entry = builder.build_entry()
        scorer = ConfidenceScorer()
        r1 = scorer.score(entry)
        r2 = scorer.score(entry)
        assert r1.score == r2.score
        assert r1.level == r2.level

    def test_pipeline_full_run_via_builder(self, builder):
        entry = builder.build_entry()
        entry, report = builder.run_pipeline(entry)
        assert entry.confidence.level != ConfidenceLevel.UNVERIFIED
        assert entry.confidence.score > 0
        assert isinstance(entry.contradictions, list)
        assert report is not None


class TestSpecificJurisdictions:
    def test_cayman_cima_regulator(self):
        entry = CaymanIslandsBuilder().build_entry()
        assert (
            "CIMA" in entry.primary_regulator
            or "Cayman Islands Monetary Authority" in entry.primary_regulator
        )

    def test_luxembourg_cssf_regulator(self):
        entry = LuxembourgBuilder().build_entry()
        assert "CSSF" in entry.primary_regulator

    def test_ireland_central_bank_regulator(self):
        entry = IrelandBuilder().build_entry()
        assert "Central Bank of Ireland" in entry.primary_regulator

    def test_singapore_mas_regulator(self):
        entry = SingaporeBuilder().build_entry()
        assert (
            "MAS" in entry.primary_regulator
            or "Monetary Authority of Singapore" in entry.primary_regulator
        )

    def test_bvi_fsc_regulator(self):
        entry = BviBuilder().build_entry()
        assert (
            "FSC" in entry.primary_regulator
            or "Financial Services Commission" in entry.primary_regulator
        )

    def test_uae_sca_regulator(self):
        entry = UaeBuilder().build_entry()
        assert (
            "SCA" in entry.primary_regulator
            or "Securities and Commodities Authority" in entry.primary_regulator
        )

    def test_jersey_jfsc_regulator(self):
        entry = JerseyBuilder().build_entry()
        assert (
            "JFSC" in entry.primary_regulator
            or "Jersey Financial Services Commission" in entry.primary_regulator
        )

    def test_delaware_sec_regulator(self):
        entry = DelawareBuilder().build_entry()
        assert (
            "SEC" in entry.primary_regulator
            or "Securities and Exchange Commission" in entry.primary_regulator
        )

    def test_luxembourg_has_ucits(self):
        entry = LuxembourgBuilder().build_entry()
        structures = [s.structure_type for s in entry.permitted_fund_structures]
        assert "UCITS Part I" in structures

    def test_singapore_has_vcc(self):
        entry = SingaporeBuilder().build_entry()
        structures = [s.structure_type for s in entry.permitted_fund_structures]
        assert "Variable Capital Company (VCC)" in structures

    def test_delaware_has_withholding_tax(self):
        entry = DelawareBuilder().build_entry()
        assert entry.withholding_tax_rate == Decimal("30")

    def test_cayman_zero_withholding(self):
        entry = CaymanIslandsBuilder().build_entry()
        assert entry.withholding_tax_rate == Decimal("0")

    def test_delaware_has_sec_primary_authority(self):
        entry = DelawareBuilder().build_entry()
        src = entry.source_governance.primary_citations
        sec_citations = [
            c for c in src if "SEC" in c.source_name or "sec.gov" in (c.source_url or "")
        ]
        assert len(sec_citations) >= 1

    def test_luxembourg_has_two_year_timeline(self):
        entry = LuxembourgBuilder().build_entry()
        timelines = entry.regulatory_timelines
        assert timelines is not None
        assert len(timelines) >= 1
        events = [t for t in timelines if "authorisation" in t.process_name.lower()]
        assert len(events) >= 1
        assert events[0].maximum_days >= 180

    def test_cayman_beneficial_ownership_threshold(self):
        entry = CaymanIslandsBuilder().build_entry()
        rules = entry.beneficial_ownership_rules
        assert rules is not None
        assert rules.threshold_percentage == Decimal("25")

    def test_singapore_record_retention(self):
        entry = SingaporeBuilder().build_entry()
        policies = entry.record_retention_policies
        assert policies is not None
        assert len(policies) >= 1
        assert policies[0].minimum_retention_years >= 5


class TestJurisdictionBuilderBase:
    def test_placeholder_confidence(self):
        c = JurisdictionBuilder._placeholder_confidence()
        assert c.level == ConfidenceLevel.UNVERIFIED
        assert c.score == 0.0
        assert c.rationale is not None
