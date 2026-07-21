"""Unit tests for confidence scorer."""

from datetime import datetime, timedelta
from src.confidence.scorer import ConfidenceScorer, _level_from_score
from src.schema.schema import ConfidenceLevel, SourceAuthority
from tests.unit.test_schema import make_citation, make_entry, make_confidence
from src.schema.schema import SourceGovernanceRecord


class TestLevelFromScore:
    def test_high(self):
        assert _level_from_score(0.75) == ConfidenceLevel.HIGH
        assert _level_from_score(1.0) == ConfidenceLevel.HIGH

    def test_medium(self):
        assert _level_from_score(0.50) == ConfidenceLevel.MEDIUM
        assert _level_from_score(0.74) == ConfidenceLevel.MEDIUM

    def test_low(self):
        assert _level_from_score(0.40) == ConfidenceLevel.LOW
        assert _level_from_score(0.49) == ConfidenceLevel.LOW

    def test_unverified(self):
        assert _level_from_score(0.39) == ConfidenceLevel.UNVERIFIED
        assert _level_from_score(0.0) == ConfidenceLevel.UNVERIFIED


class TestConfidenceScorer:
    def test_primary_source_high_score(self):
        entry = make_entry()
        scorer = ConfidenceScorer()
        result = scorer.score(entry)
        assert result.score >= 0.9

    def test_tertiary_source_lower_score(self):
        c = make_citation(authority=SourceAuthority.TERTIARY)
        governance = SourceGovernanceRecord(
            tertiary_citations=[c],
            dominant_source=SourceAuthority.TERTIARY,
        )
        entry = make_entry(
            source_governance=governance,
            confidence=make_confidence(score=0.5, level=ConfidenceLevel.MEDIUM),
        )
        scorer = ConfidenceScorer()
        result = scorer.score(entry)
        assert result.score < 0.9

    def test_stale_citation_penalized(self):
        old_date = datetime.utcnow() - timedelta(days=400)
        c = make_citation(publication_date=old_date)
        governance = SourceGovernanceRecord(primary_citations=[c])
        entry = make_entry(source_governance=governance)
        scorer = ConfidenceScorer()
        result = scorer.score(entry)
        assert any("stale" in f.lower() for f in result.contributing_factors)

    def test_score_clamped_between_0_and_1(self):
        entry = make_entry()
        scorer = ConfidenceScorer()
        result = scorer.score(entry)
        assert 0.0 <= result.score <= 1.0

    def test_deterministic(self):
        entry = make_entry()
        scorer = ConfidenceScorer()
        r1 = scorer.score(entry)
        r2 = scorer.score(entry)
        assert r1.score == r2.score

    def test_contributing_factors_populated(self):
        entry = make_entry()
        scorer = ConfidenceScorer()
        result = scorer.score(entry)
        assert len(result.contributing_factors) > 0

    def test_completeness_bonus_full(self):
        from src.schema.schema import (
            SubstanceRequirement,
            RegulatoryTimeline,
            RegulatoryCost,
            PenaltyExposure,
            WindDownProcedure,
            FundManagerRequirement,
            MarketingRestriction,
            BeneficialOwnershipRule,
            RecordRetentionPolicy,
            InvestorRequirements,
        )

        entry = make_entry(
            licensing_requirements=[],
            substance_requirements=SubstanceRequirement(
                local_office_required=True, local_directors_required=True, local_staff_required=True
            ),
            regulatory_timelines=[RegulatoryTimeline(process_name="Test")],
            regulatory_costs=[RegulatoryCost(cost_type="T", currency="USD", frequency="One-time")],
            penalty_exposure=[PenaltyExposure(breach_type="T")],
            wind_down_procedure=WindDownProcedure(),
            fund_manager_requirements=FundManagerRequirement(),
            marketing_restrictions=[MarketingRestriction(target_investor_type="T")],
            beneficial_ownership_rules=BeneficialOwnershipRule(),
            record_retention_policies=[
                RecordRetentionPolicy(minimum_retention_years=5, applies_to="All")
            ],
            investor_requirements=InvestorRequirements(),
        )
        scorer = ConfidenceScorer()
        result = scorer.score(entry)
        assert any("completeness" in f.lower() for f in result.contributing_factors)
        bonus_str = [f for f in result.contributing_factors if "completeness" in f.lower()][0]
        assert "+0.1000" in bonus_str or "+0.1" in bonus_str

    def test_completeness_bonus_partial(self):
        from src.schema.schema import SubstanceRequirement

        entry = make_entry(
            substance_requirements=SubstanceRequirement(
                local_office_required=True, local_directors_required=True, local_staff_required=True
            )
        )
        scorer = ConfidenceScorer()
        result = scorer.score(entry)
        assert any("completeness" in f.lower() for f in result.contributing_factors)

    def test_refresh_recency_penalty_applied(self):
        old_date = datetime.utcnow() - timedelta(days=365)
        entry = make_entry(last_updated_at=old_date)
        scorer = ConfidenceScorer()
        result = scorer.score(entry)
        assert any("refresh" in f.lower() for f in result.contributing_factors)

    def test_refresh_recency_no_penalty_recent(self):
        entry = make_entry()
        scorer = ConfidenceScorer()
        result = scorer.score(entry)
        refresh_factors = [f for f in result.contributing_factors if "refresh" in f.lower()]
        assert len(refresh_factors) == 0
