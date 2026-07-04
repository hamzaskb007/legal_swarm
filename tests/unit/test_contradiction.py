"""Unit tests for contradiction detection."""

from src.contradiction.detector import CitationContradictionDetector, CrossEntryContradictionDetector
from src.schema.schema import SourceAuthority
from tests.unit.test_schema import make_citation, make_entry
from src.schema.schema import SourceGovernanceRecord


class TestCitationContradictionDetector:
    def test_no_contradiction_normal_case(self):
        entry = make_entry()
        detector = CitationContradictionDetector()
        result = detector.detect(entry)
        assert result == []

    def test_detects_secondary_higher_than_primary(self):
        primary = make_citation(authority=SourceAuthority.PRIMARY, reliability_score=0.5)
        secondary = make_citation(authority=SourceAuthority.SECONDARY, reliability_score=0.9)
        governance = SourceGovernanceRecord(
            primary_citations=[primary],
            secondary_citations=[secondary],
        )
        entry = make_entry(source_governance=governance)
        detector = CitationContradictionDetector()
        result = detector.detect(entry)
        assert len(result) == 1
        assert result[0].field_path == "source_governance.reliability_score"

    def test_no_primary_returns_empty(self):
        secondary = make_citation(authority=SourceAuthority.SECONDARY, reliability_score=0.9)
        governance = SourceGovernanceRecord(secondary_citations=[secondary])
        entry = make_entry(source_governance=governance,)
        detector = CitationContradictionDetector()
        result = detector.detect(entry)
        assert result == []


class TestCrossEntryContradictionDetector:
    def test_no_contradiction_identical_entries(self):
        entry_a = make_entry()
        entry_b = make_entry()
        source_a = make_citation()
        source_b = make_citation()
        detector = CrossEntryContradictionDetector()
        result = detector.detect(entry_a, entry_b, source_a, source_b)
        assert result == []

    def test_detects_regulator_mismatch(self):
        entry_a = make_entry(primary_regulator="SCA")
        entry_b = make_entry(primary_regulator="DFSA")
        source_a = make_citation()
        source_b = make_citation()
        detector = CrossEntryContradictionDetector(fields=["primary_regulator"])
        result = detector.detect(entry_a, entry_b, source_a, source_b)
        assert len(result) == 1
        assert result[0].field_path == "primary_regulator"
        assert result[0].value_a == "SCA"
        assert result[0].value_b == "DFSA"

    def test_contradiction_record_has_both_sources(self):
        entry_a = make_entry(primary_regulator="SCA")
        entry_b = make_entry(primary_regulator="DFSA")
        source_a = make_citation(source_name="Source A")
        source_b = make_citation(source_name="Source B")
        detector = CrossEntryContradictionDetector(fields=["primary_regulator"])
        result = detector.detect(entry_a, entry_b, source_a, source_b)
        assert result[0].source_a.source_name == "Source A"
        assert result[0].source_b.source_name == "Source B"