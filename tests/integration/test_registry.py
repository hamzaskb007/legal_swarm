"""Integration tests for the full Tier 1 jurisdiction registry."""

import pytest
from pathlib import Path

from src.jurisdictions.registry import JurisdictionRegistry
from src.schema.schema import (
    JurisdictionTier,
    ValidationStatus,
    ConfidenceLevel,
)


class TestJurisdictionRegistry:
    @pytest.fixture
    def registry(self):
        return JurisdictionRegistry()

    def test_registry_loads_all_tier1_jurisdictions(self, registry):
        entries = registry.get_all()
        assert len(entries) == 8

    def test_registry_contains_expected_codes(self, registry):
        codes = {e.jurisdiction_code for e in registry.get_all()}
        expected = {"AE", "IE", "JE", "KY", "LU", "SG", "VG", "US-DE"}
        assert codes == expected

    def test_get_entry_returns_entry(self, registry):
        entry = registry.get_entry("KY")
        assert entry.jurisdiction_code == "KY"
        assert entry.tier == JurisdictionTier.TIER_1

    def test_get_entry_normalizes_code(self, registry):
        entry = registry.get_entry("ky")
        assert entry.jurisdiction_code == "KY"

    def test_get_entry_raises_key_error(self, registry):
        with pytest.raises(KeyError):
            registry.get_entry("ZZ")

    def test_get_all_returns_all_entries(self, registry):
        entries = registry.get_all()
        assert len(entries) == 8

    def test_registry_length(self, registry):
        assert len(registry) == 8

    def test_registry_contains(self, registry):
        assert "KY" in registry
        assert "ky" in registry
        assert "ZZ" not in registry

    def test_all_jurisdictions_are_tier1(self, registry):
        for entry in registry.get_all():
            assert entry.tier == JurisdictionTier.TIER_1

    def test_all_entries_pass_validation(self, registry):
        for code in registry:
            report = registry.validation_reports[code]
            assert report.overall_status != ValidationStatus.FAILED, \
                f"{code} validation FAILED"

    def test_all_entries_have_confidence_scored(self, registry):
        for entry in registry.get_all():
            assert entry.confidence.score > 0
            assert entry.confidence.level != ConfidenceLevel.UNVERIFIED

    def test_all_entries_have_primary_citations(self, registry):
        for entry in registry.get_all():
            assert len(entry.source_governance.primary_citations) >= 1

    def test_all_entries_have_fund_structures(self, registry):
        for entry in registry.get_all():
            assert len(entry.permitted_fund_structures) >= 1

    def test_all_entries_have_filing_obligations(self, registry):
        for entry in registry.get_all():
            assert len(entry.filing_obligations) >= 1

    def test_compare_returns_comparison(self, registry):
        comp = registry.compare("KY", "VG")
        assert comp.jurisdictions == ["KY", "VG"]
        assert len(comp.fields_compared) > 0
        assert len(comp.results) > 0

    def test_compare_detects_contradictions(self, registry):
        comp = registry.compare("KY", "VG")
        assert isinstance(comp.contradictions_detected, list)

    def test_compare_different_jurisdictions(self, registry):
        comp = registry.compare("AE", "LU")
        assert comp.summary is not None
        assert "United Arab Emirates" in comp.summary or "AE" in comp.summary
        assert "Luxembourg" in comp.summary or "LU" in comp.summary

    def test_registry_audit_logs_access(self, registry, tmp_path):
        log_path = tmp_path / "registry_audit.jsonl"
        registry = JurisdictionRegistry(audit_log_path=log_path)
        registry.get_entry("KY")
        logs = log_path.read_text()
        assert "KY" in logs
        assert "QUERY" in logs

    def test_registry_is_deterministic(self):
        r1 = JurisdictionRegistry()
        r2 = JurisdictionRegistry()
        for e1, e2 in zip(r1.get_all(), r2.get_all()):
            assert e1.confidence.score == e2.confidence.score


class TestRegistryAudit:
    def test_all_entries_audit_logged(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        registry = JurisdictionRegistry(audit_log_path=log_path)
        registry.get_all()
        log_text = log_path.read_text()
        assert "QUERY" in log_text
        assert "8" in log_text or "ALL_RETURNED" in log_text

    def test_audit_log_path_respected(self, tmp_path):
        log_path = tmp_path / "custom_audit.jsonl"
        default_path = Path("logs/audit.jsonl")
        before_default = default_path.read_text() if default_path.exists() else ""
        registry = JurisdictionRegistry(audit_log_path=log_path)
        _ = registry.get_all()
        custom_logs = log_path.read_text()
        assert "QUERY" in custom_logs
        assert "ALL_RETURNED" in custom_logs
        after_default = default_path.read_text() if default_path.exists() else ""
        new_default_lines = len(after_default.splitlines()) - len(before_default.splitlines())
        assert new_default_lines == 0, "Audit log leaked to default path"
