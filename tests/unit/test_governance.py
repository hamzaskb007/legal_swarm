"""Unit tests for source governance manager."""

import pytest
from src.governance.source_governance import SourceGovernanceManager
from src.schema.schema import SourceAuthority
from tests.unit.test_schema import make_citation


class TestSourceGovernanceManager:
    def test_add_primary_citation(self):
        manager = SourceGovernanceManager()
        c = make_citation(authority=SourceAuthority.PRIMARY)
        result = manager.add_citation(c)
        assert result is True
        assert manager.citation_count() == 1

    def test_add_secondary_citation(self):
        manager = SourceGovernanceManager()
        c = make_citation(authority=SourceAuthority.SECONDARY)
        manager.add_citation(c)
        governance = manager.build()
        assert len(governance.secondary_citations) == 1

    def test_deduplication_by_url(self):
        manager = SourceGovernanceManager()
        c1 = make_citation(source_url="https://example.com")
        c2 = make_citation(source_url="https://example.com")
        manager.add_citation(c1)
        result = manager.add_citation(c2)
        assert result is False
        assert manager.citation_count() == 1

    def test_no_url_not_deduplicated(self):
        manager = SourceGovernanceManager()
        c1 = make_citation(source_url=None)
        c2 = make_citation(source_url=None)
        manager.add_citation(c1)
        manager.add_citation(c2)
        assert manager.citation_count() == 2

    def test_dominant_source_primary(self):
        manager = SourceGovernanceManager()
        manager.add_citation(make_citation(authority=SourceAuthority.PRIMARY))
        governance = manager.build()
        assert governance.dominant_source == SourceAuthority.PRIMARY

    def test_dominant_source_secondary_when_no_primary(self):
        manager = SourceGovernanceManager()
        manager.add_citation(make_citation(authority=SourceAuthority.SECONDARY))
        governance = manager.build()
        assert governance.dominant_source == SourceAuthority.SECONDARY

    def test_average_reliability(self):
        manager = SourceGovernanceManager()
        manager.add_citation(make_citation(reliability_score=0.8))
        manager.add_citation(
            make_citation(
                authority=SourceAuthority.SECONDARY,
                reliability_score=0.6,
                source_url="https://other.com",
            )
        )
        avg = manager.average_reliability()
        assert avg == pytest.approx(0.7)

    def test_empty_manager_average_reliability(self):
        manager = SourceGovernanceManager()
        assert manager.average_reliability() == 0.0
