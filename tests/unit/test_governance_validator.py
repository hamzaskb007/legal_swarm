from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.authority.models import Authority, AuthorityLevel, Relationship, RelationshipType
from src.authority.registry import AuthorityRegistry
from src.schema.schema import CitationRecord, SourceAuthority, SourceGovernanceRecord
from src.validation import AuthorityGovernanceValidator, ValidationResult, ValidationStatus
from src.validation.enums import ValidationCode, ValidationSeverity
from src.validation.exceptions import ValidationConfigurationError
from src.validation.models import ValidationContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_citation(**kwargs) -> CitationRecord:
    defaults = dict(
        source_name="Test Source",
        authority=SourceAuthority.PRIMARY,
        reliability_score=0.9,
    )
    defaults.update(kwargs)
    return CitationRecord(**defaults)


def make_mock_authority(
    authority_id: str = "auth-1",
    level: AuthorityLevel = AuthorityLevel.LEVEL_1,
    jurisdiction: str = "XX",
    enabled: bool = True,
    relationships: list | None = None,
) -> MagicMock:
    auth = MagicMock(spec=Authority)
    auth.id = authority_id
    auth.level = level
    auth.jurisdiction = jurisdiction
    auth.enabled = enabled
    auth.name = f"Authority {authority_id}"
    auth.relationships = relationships or []
    auth.to_source_authority.return_value = (
        SourceAuthority.PRIMARY
        if level in (AuthorityLevel.LEVEL_1, AuthorityLevel.LEVEL_2, AuthorityLevel.LEVEL_3)
        else SourceAuthority.SECONDARY
        if level == AuthorityLevel.LEVEL_4
        else SourceAuthority.TERTIARY
    )
    return auth


def make_registry(
    authorities: list[MagicMock] | None = None,
) -> MagicMock:
    registry = MagicMock(spec=AuthorityRegistry)
    auth_map: dict[str, MagicMock] = {}
    if authorities:
        for a in authorities:
            auth_map[a.id] = a

    def get_by_id(aid: str) -> Authority:
        if aid in auth_map:
            return auth_map[aid]
        raise KeyError(aid)

    def contains(aid: str) -> bool:
        return aid in auth_map

    def get_by_jurisdiction(jur: str) -> list[Authority]:
        return [a for a in auth_map.values() if a.jurisdiction == jur]

    registry.get_by_id.side_effect = get_by_id
    registry.__contains__.side_effect = contains
    registry.get_by_jurisdiction.side_effect = get_by_jurisdiction
    return registry


def make_validator(
    registry: MagicMock | None = None,
    min_citations: int = 3,
    min_primary: int = 2,
) -> AuthorityGovernanceValidator:
    return AuthorityGovernanceValidator(
        authority_registry=registry,
        min_citations_per_entry=min_citations,
        min_primary_citations=min_primary,
    )


def make_governance_construct(**kwargs) -> SourceGovernanceRecord:
    defaults = dict(
        primary_citations=[],
        secondary_citations=[],
        tertiary_citations=[],
    )
    defaults.update(kwargs)
    return SourceGovernanceRecord.model_construct(**defaults)


def make_governance(
    primary: int = 2,
    secondary: int = 0,
    tertiary: int = 0,
    **overrides,
) -> SourceGovernanceRecord:
    primaries = [
        make_citation(
            source_url=f"https://example.gov/primary/{i}",
            authority_id="auth-1",
            authority=SourceAuthority.PRIMARY,
        )
        for i in range(primary)
    ]
    secondaries = [
        make_citation(
            source_url=f"https://example.gov/sec/{i}",
            authority_id="auth-4",
            authority=SourceAuthority.SECONDARY,
        )
        for i in range(secondary)
    ]
    tertiaries = [
        make_citation(
            source_url=f"https://example.gov/ter/{i}",
            authority_id="auth-5",
            authority=SourceAuthority.TERTIARY,
        )
        for i in range(tertiary)
    ]
    return SourceGovernanceRecord(
        primary_citations=primaries,
        secondary_citations=secondaries,
        tertiary_citations=tertiaries,
        **overrides,
    )


# ===================================================================
# Part 2 — Authority Hierarchy Validation
# ===================================================================


class TestAuthorityHierarchy:
    def test_valid_hierarchy_level_1(self):
        auth = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        hierarchy_issues = [i for i in result.issues if i.code == ValidationCode.HIERARCHY_MISMATCH]
        assert len(hierarchy_issues) == 0

    def test_valid_hierarchy_level_5(self):
        auth = make_mock_authority("auth-5", AuthorityLevel.LEVEL_5)
        validator = make_validator()
        result = validator.validate_authority(auth)
        hierarchy_issues = [i for i in result.issues if i.code == ValidationCode.HIERARCHY_MISMATCH]
        assert len(hierarchy_issues) == 0

    def test_relationship_to_unknown_target_detected(self):
        rel = Relationship(type=RelationshipType.REFERENCES, target_id="nonexistent")
        auth = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1, relationships=[rel])
        registry = make_registry([auth])
        validator = make_validator(registry)
        result = validator.validate_authority(auth)
        chain_issues = [
            i for i in result.issues if i.code == ValidationCode.INVALID_REFERENCE_CHAIN
        ]
        assert len(chain_issues) == 1
        assert "nonexistent" in chain_issues[0].message

    def test_relationship_to_valid_target_passes(self):
        auth2 = make_mock_authority("auth-2", AuthorityLevel.LEVEL_2)
        rel = Relationship(type=RelationshipType.REFERENCES, target_id="auth-2")
        auth1 = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1, relationships=[rel])
        registry = make_registry([auth1, auth2])
        validator = make_validator(registry)
        result = validator.validate_authority(auth1)
        chain_issues = [
            i for i in result.issues if i.code == ValidationCode.INVALID_REFERENCE_CHAIN
        ]
        assert len(chain_issues) == 0

    def test_relationship_check_skipped_without_registry(self):
        rel = Relationship(type=RelationshipType.REFERENCES, target_id="nonexistent")
        auth = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1, relationships=[rel])
        validator = make_validator(registry=None)
        result = validator.validate_authority(auth)
        chain_issues = [
            i for i in result.issues if i.code == ValidationCode.INVALID_REFERENCE_CHAIN
        ]
        assert len(chain_issues) == 0

    def test_multiple_invalid_relationships(self):
        rels = [
            Relationship(type=RelationshipType.REFERENCES, target_id="missing-1"),
            Relationship(type=RelationshipType.PUBLISHES, target_id="missing-2"),
        ]
        auth = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1, relationships=rels)
        registry = make_registry([auth])
        validator = make_validator(registry)
        result = validator.validate_authority(auth)
        chain_issues = [
            i for i in result.issues if i.code == ValidationCode.INVALID_REFERENCE_CHAIN
        ]
        assert len(chain_issues) == 2

    def test_hierarchy_issue_severity_high(self):
        rel = Relationship(type=RelationshipType.REFERENCES, target_id="missing")
        auth = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1, relationships=[rel])
        registry = make_registry([auth])
        validator = make_validator(registry)
        result = validator.validate_authority(auth)
        for issue in result.issues:
            if issue.code == ValidationCode.INVALID_REFERENCE_CHAIN:
                assert issue.severity == ValidationSeverity.HIGH

    def test_hierarchy_issue_has_details(self):
        rel = Relationship(type=RelationshipType.REFERENCES, target_id="missing")
        auth = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1, relationships=[rel])
        registry = make_registry([auth])
        validator = make_validator(registry)
        result = validator.validate_authority(auth)
        chain_issues = [
            i for i in result.issues if i.code == ValidationCode.INVALID_REFERENCE_CHAIN
        ]
        assert "target_id" in chain_issues[0].details
        assert chain_issues[0].details["target_id"] == "missing"


# ===================================================================
# Part 3 — Authority Level Enforcement
# ===================================================================


class TestAuthorityLevelEnforcement:
    def test_level_1_is_valid_primary(self):
        auth = make_mock_authority("sec", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        level_issues = [
            i
            for i in result.issues
            if i.code in (ValidationCode.INVALID_AUTHORITY_LEVEL, ValidationCode.HIERARCHY_MISMATCH)
        ]
        assert len(level_issues) == 0

    def test_level_2_is_valid_primary(self):
        auth = make_mock_authority("statute", AuthorityLevel.LEVEL_2)
        validator = make_validator()
        result = validator.validate_authority(auth)
        level_issues = [
            i
            for i in result.issues
            if i.code in (ValidationCode.INVALID_AUTHORITY_LEVEL, ValidationCode.HIERARCHY_MISMATCH)
        ]
        assert len(level_issues) == 0

    def test_level_3_is_valid_primary(self):
        auth = make_mock_authority("gazette", AuthorityLevel.LEVEL_3)
        validator = make_validator()
        result = validator.validate_authority(auth)
        level_issues = [
            i
            for i in result.issues
            if i.code in (ValidationCode.INVALID_AUTHORITY_LEVEL, ValidationCode.HIERARCHY_MISMATCH)
        ]
        assert len(level_issues) == 0

    def test_level_4_is_secondary(self):
        auth = make_mock_authority("legal_firm", AuthorityLevel.LEVEL_4)
        validator = make_validator()
        result = validator.validate_authority(auth)
        level_issues = [
            i
            for i in result.issues
            if i.code in (ValidationCode.INVALID_AUTHORITY_LEVEL, ValidationCode.HIERARCHY_MISMATCH)
        ]
        assert len(level_issues) == 0

    def test_level_5_is_tertiary(self):
        auth = make_mock_authority("advisor", AuthorityLevel.LEVEL_5)
        validator = make_validator()
        result = validator.validate_authority(auth)
        level_issues = [
            i
            for i in result.issues
            if i.code in (ValidationCode.INVALID_AUTHORITY_LEVEL, ValidationCode.HIERARCHY_MISMATCH)
        ]
        assert len(level_issues) == 0

    def test_level_maps_to_correct_source_authority(self):
        auth = make_mock_authority("sec", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        assert result.status == ValidationStatus.SUCCESS

    def test_disabled_authority_identified(self):
        auth = make_mock_authority("disabled-auth", AuthorityLevel.LEVEL_1, enabled=False)
        validator = make_validator()
        result = validator.validate_authority(auth)
        assert result.metadata["authority_enabled"] is False


# ===================================================================
# Part 4 — Secondary Source Referencing
# ===================================================================


class TestSecondarySourceReferencing:
    def test_primary_citation_no_referencing_check(self):
        auth1 = make_mock_authority("primary", AuthorityLevel.LEVEL_1, jurisdiction="XX")
        registry = make_registry([auth1])
        c = make_citation(authority_id="primary", authority=SourceAuthority.PRIMARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 0

    def test_secondary_with_primary_in_jurisdiction_passes(self):
        auth1 = make_mock_authority("primary", AuthorityLevel.LEVEL_1, jurisdiction="XX")
        auth4 = make_mock_authority("legal", AuthorityLevel.LEVEL_4, jurisdiction="XX")
        registry = make_registry([auth1, auth4])
        c = make_citation(authority_id="legal", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 0

    def test_orphan_secondary_detected(self):
        auth4 = make_mock_authority("legal", AuthorityLevel.LEVEL_4, jurisdiction="XX")
        registry = make_registry([auth4])
        c = make_citation(authority_id="legal", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 1
        assert orphan_issues[0].severity == ValidationSeverity.MEDIUM

    def test_orphan_tertiary_detected(self):
        auth5 = make_mock_authority("advisor", AuthorityLevel.LEVEL_5, jurisdiction="XX")
        registry = make_registry([auth5])
        c = make_citation(authority_id="advisor", authority=SourceAuthority.TERTIARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 1
        assert orphan_issues[0].severity == ValidationSeverity.LOW

    def test_orphan_check_skipped_without_registry(self):
        c = make_citation(authority_id="legal", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry=None)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 0

    def test_orphan_check_skipped_for_unknown_authority(self):
        registry = make_registry([])
        c = make_citation(authority_id="unknown", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 0

    def test_orphan_check_skipped_for_disabled_authority(self):
        auth4 = make_mock_authority(
            "legal", AuthorityLevel.LEVEL_4, jurisdiction="XX", enabled=False
        )
        registry = make_registry([auth4])
        c = make_citation(authority_id="legal", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 0

    def test_orphan_issue_has_details(self):
        auth4 = make_mock_authority("legal", AuthorityLevel.LEVEL_4, jurisdiction="XX")
        registry = make_registry([auth4])
        c = make_citation(authority_id="legal", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert "authority_id" in orphan_issues[0].details
        assert "jurisdiction" in orphan_issues[0].details

    def test_secondary_with_other_secondary_in_jurisdiction(self):
        auth_a = make_mock_authority("legal-a", AuthorityLevel.LEVEL_4, jurisdiction="XX")
        auth_b = make_mock_authority("legal-b", AuthorityLevel.LEVEL_4, jurisdiction="XX")
        registry = make_registry([auth_a, auth_b])
        c = make_citation(authority_id="legal-b", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 1

    def test_orphan_secondary_without_authority_id(self):
        c = make_citation(authority_id=None, authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry=make_registry([]))
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 0


# ===================================================================
# Part 5 — Citation Density Validation
# ===================================================================


class TestCitationDensity:
    def test_sufficient_citations_passes(self):
        governance = make_governance(primary=2)
        validator = make_validator(min_citations=2, min_primary=1)
        result = validator.validate_governance(governance)
        density_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_CITATIONS
        ]
        assert len(density_issues) == 0

    def test_insufficient_total_citations(self):
        governance = make_governance(primary=1)
        validator = make_validator(min_citations=5, min_primary=1)
        result = validator.validate_governance(governance)
        density_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_CITATIONS
        ]
        assert len(density_issues) >= 1

    def test_insufficient_primary_citations(self):
        governance = make_governance(primary=1)
        validator = make_validator(min_citations=1, min_primary=2)
        result = validator.validate_governance(governance)
        density_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_CITATIONS
        ]
        assert len(density_issues) >= 1

    def test_zero_minimum_passes_any_count(self):
        governance = make_governance_construct()
        validator = make_validator(min_citations=0, min_primary=0)
        result = validator.validate_governance(governance)
        density_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_CITATIONS
        ]
        assert len(density_issues) == 0

    def test_density_issue_severity_high(self):
        governance = make_governance(primary=1)
        validator = make_validator(min_citations=10, min_primary=5)
        result = validator.validate_governance(governance)
        density_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_CITATIONS
        ]
        assert all(i.severity == ValidationSeverity.HIGH for i in density_issues)

    def test_density_issue_has_details(self):
        governance = make_governance_construct()
        validator = make_validator(min_citations=5, min_primary=2)
        result = validator.validate_governance(governance)
        density_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_CITATIONS
        ]
        for issue in density_issues:
            assert "minimum" in issue.details

    def test_density_uses_configured_thresholds(self):
        governance = make_governance(primary=3, secondary=1)
        validator = make_validator(min_citations=3, min_primary=2)
        result = validator.validate_governance(governance)
        density_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_CITATIONS
        ]
        assert len(density_issues) == 0


# ===================================================================
# Part 6 — Minimum Evidence Requirements
# ===================================================================


class TestMinimumEvidence:
    def test_required_evidence_present(self):
        governance = make_governance(primary=2)
        validator = make_validator()
        result = validator.validate_governance(governance)
        evidence_issues = [
            i
            for i in result.issues
            if i.code
            in (
                ValidationCode.MISSING_SOURCE_GOVERNANCE,
                ValidationCode.INSUFFICIENT_AUTHORITY_COVERAGE,
            )
        ]
        assert len(evidence_issues) == 0

    def test_missing_primary_authority_detected(self):
        governance = make_governance(primary=0, secondary=2)
        validator = make_validator()
        result = validator.validate_governance(governance)
        coverage_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_AUTHORITY_COVERAGE
        ]
        assert len(coverage_issues) >= 1

    def test_empty_governance_detected(self):
        governance = make_governance_construct()
        validator = make_validator(min_citations=0, min_primary=0)
        result = validator.validate_governance(governance)
        missing = [i for i in result.issues if i.code == ValidationCode.MISSING_SOURCE_GOVERNANCE]
        assert len(missing) >= 1

    def test_no_enabled_authorities_warning(self):
        auth1 = make_mock_authority("primary", AuthorityLevel.LEVEL_1, enabled=False)
        registry = make_registry([auth1])
        c = make_citation(
            source_url="https://example.gov",
            authority_id="primary",
            authority=SourceAuthority.PRIMARY,
        )
        governance = SourceGovernanceRecord(primary_citations=[c])
        validator = make_validator(registry, min_citations=0, min_primary=0)
        result = validator.validate_governance(governance)
        coverage_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_AUTHORITY_COVERAGE
        ]
        assert len(coverage_issues) >= 1

    def test_enabled_authority_satisfies_evidence(self):
        auth1 = make_mock_authority("primary", AuthorityLevel.LEVEL_1, enabled=True)
        registry = make_registry([auth1])
        c = make_citation(
            source_url="https://example.gov",
            authority_id="primary",
            authority=SourceAuthority.PRIMARY,
        )
        governance = SourceGovernanceRecord(primary_citations=[c])
        validator = make_validator(registry, min_citations=0, min_primary=0)
        result = validator.validate_governance(governance)
        coverage_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_AUTHORITY_COVERAGE
        ]
        assert len(coverage_issues) == 0

    def test_evidence_issue_details(self):
        governance = make_governance(primary=0, secondary=2)
        validator = make_validator()
        result = validator.validate_governance(governance)
        coverage_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_AUTHORITY_COVERAGE
        ]
        for issue in coverage_issues:
            assert "secondary_count" in issue.details or "unique_authority_ids" in issue.details

    def test_missing_evidence_severity_high(self):
        governance = make_governance_construct()
        validator = make_validator(min_citations=0, min_primary=0)
        result = validator.validate_governance(governance)
        for issue in result.issues:
            if issue.code == ValidationCode.MISSING_SOURCE_GOVERNANCE:
                assert issue.severity == ValidationSeverity.HIGH


# ===================================================================
# Part 7 — Duplicate Authority Detection
# ===================================================================


class TestDuplicateAuthorityDetection:
    def test_unique_authorities_no_duplicates(self):
        citations = [
            make_citation(authority_id="auth-1", source_url="https://ex.gov/1"),
            make_citation(authority_id="auth-2", source_url="https://ex.gov/2"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 0

    def test_duplicate_authority_id_detected(self):
        citations = [
            make_citation(authority_id="auth-1", source_url="https://ex.gov/1"),
            make_citation(authority_id="auth-1", source_url="https://ex.gov/2"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 1
        issues = dup_results[0].issues
        assert any(i.code == ValidationCode.DUPLICATE_AUTHORITY_REFERENCE for i in issues)

    def test_duplicate_authority_severity_low(self):
        citations = [
            make_citation(authority_id="auth-1", source_url="https://ex.gov/1"),
            make_citation(authority_id="auth-1", source_url="https://ex.gov/2"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        for issue in dup_results[0].issues:
            if issue.code == ValidationCode.DUPLICATE_AUTHORITY_REFERENCE:
                assert issue.severity == ValidationSeverity.LOW

    def test_duplicate_authority_has_details(self):
        citations = [
            make_citation(authority_id="auth-1", source_url="https://ex.gov/1"),
            make_citation(authority_id="auth-1", source_url="https://ex.gov/2"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        issue = dup_results[0].issues[0]
        assert "authority_id" in issue.details
        assert "reference_count" in issue.details
        assert issue.details["reference_count"] == 2

    def test_multiple_duplicate_authorities(self):
        citations = [
            make_citation(authority_id="auth-1", source_url="https://ex.gov/1"),
            make_citation(authority_id="auth-1", source_url="https://ex.gov/2"),
            make_citation(authority_id="auth-2", source_url="https://ex.gov/3"),
            make_citation(authority_id="auth-2", source_url="https://ex.gov/4"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 1
        assert len(dup_results[0].issues) == 2

    def test_duplicate_detection_skipped_single_citation(self):
        c = make_citation(authority_id="auth-1")
        validator = make_validator()
        results = validator.validate_citations([c])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 0

    def test_duplicate_detection_skipped_empty(self):
        validator = make_validator()
        results = validator.validate_citations([])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 0

    def test_duplicate_detection_context_type(self):
        citations = [
            make_citation(authority_id="auth-1", source_url="https://ex.gov/1"),
            make_citation(authority_id="auth-1", source_url="https://ex.gov/2"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert dup_results[0].context.context_type == "duplicate_authority_detection"

    def test_duplicate_detection_metadata(self):
        citations = [
            make_citation(authority_id="auth-1", source_url="https://ex.gov/1"),
            make_citation(authority_id="auth-1", source_url="https://ex.gov/2"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert dup_results[0].metadata["citation_count"] == 2

    def test_authority_id_none_ignored(self):
        citations = [
            make_citation(authority_id=None, source_url="https://ex.gov/1"),
            make_citation(authority_id=None, source_url="https://ex.gov/2"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 0

    def test_authority_id_empty_ignored(self):
        citations = [
            make_citation(authority_id="", source_url="https://ex.gov/1"),
            make_citation(authority_id="", source_url="https://ex.gov/2"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 0


# ===================================================================
# Validation Output
# ===================================================================


class TestValidationOutput:
    def test_successful_validation_returns_success(self):
        auth = make_mock_authority("valid", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        assert result.status == ValidationStatus.SUCCESS

    def test_failed_validation_returns_failed(self):
        governance = make_governance_construct()
        validator = make_validator(min_citations=5, min_primary=3)
        result = validator.validate_governance(governance)
        assert result.status == ValidationStatus.FAILED

    def test_warning_validation_returns_warning(self):
        auth4 = make_mock_authority("legal", AuthorityLevel.LEVEL_4, jurisdiction="XX")
        registry = make_registry([auth4])
        c = make_citation(authority_id="legal", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.WARNING

    def test_result_has_issues(self):
        governance = make_governance_construct()
        validator = make_validator(min_citations=1, min_primary=1)
        result = validator.validate_governance(governance)
        assert len(result.issues) > 0

    def test_result_has_validator_name(self):
        auth = make_mock_authority("valid", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        assert result.validator_name == "authority_governance_validator"

    def test_result_has_timestamps(self):
        auth = make_mock_authority("valid", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at

    def test_result_has_duration(self):
        auth = make_mock_authority("valid", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    def test_result_has_metadata(self):
        auth = make_mock_authority("valid", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        assert "authority_id" in result.metadata

    def test_result_serialization_roundtrip(self):
        auth = make_mock_authority("valid", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        data = result.model_dump()
        restored = ValidationResult.model_validate(data)
        assert restored.status == result.status
        assert restored.validator_name == result.validator_name

    def test_result_json_roundtrip(self):
        auth = make_mock_authority("valid", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        json_str = result.model_dump_json()
        restored = ValidationResult.model_validate_json(json_str)
        assert restored.status == result.status

    def test_result_context_when_provided(self):
        auth = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1)
        ctx = ValidationContext(document_id="doc-123")
        validator = make_validator()
        result = validator.validate_authority(auth, context=ctx)
        assert result.context.document_id == "doc-123"

    def test_result_auto_context_authority(self):
        auth = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        assert result.context.context_type == "authority_governance"
        assert result.context.authority_id == "auth-1"

    def test_result_auto_context_citation(self):
        c = make_citation(authority_id="auth-1", authority=SourceAuthority.PRIMARY)
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.context.context_type == "citation_governance"
        assert result.context.citation_id == str(c.citation_id)

    def test_validate_citations_returns_list(self):
        c1 = make_citation(authority_id="auth-1")
        c2 = make_citation(authority_id="auth-2")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        assert len(results) == 2
        assert all(isinstance(r, ValidationResult) for r in results)

    def test_validate_citations_empty_list(self):
        validator = make_validator()
        results = validator.validate_citations([])
        assert results == []


# ===================================================================
# Exceptions
# ===================================================================


class TestExceptions:
    def test_empty_validator_name_raises(self):
        with pytest.raises(ValidationConfigurationError):
            AuthorityGovernanceValidator(validator_name="")

    def test_whitespace_validator_name_raises(self):
        with pytest.raises(ValidationConfigurationError):
            AuthorityGovernanceValidator(validator_name="   ")

    def test_valid_validator_name_ok(self):
        v = AuthorityGovernanceValidator(validator_name="custom")
        assert v._validator_name == "custom"

    def test_default_validator_name(self):
        v = AuthorityGovernanceValidator()
        assert v._validator_name == "authority_governance_validator"

    def test_negative_min_citations_raises(self):
        with pytest.raises(ValidationConfigurationError):
            AuthorityGovernanceValidator(min_citations_per_entry=-1)

    def test_negative_min_primary_raises(self):
        with pytest.raises(ValidationConfigurationError):
            AuthorityGovernanceValidator(min_primary_citations=-1)

    def test_zero_min_citations_ok(self):
        v = AuthorityGovernanceValidator(min_citations_per_entry=0)
        assert v._min_citations_per_entry == 0

    def test_zero_min_primary_ok(self):
        v = AuthorityGovernanceValidator(min_primary_citations=0)
        assert v._min_primary_citations == 0


# ===================================================================
# Edge Cases
# ===================================================================


class TestEdgeCases:
    def test_validate_authority_without_registry(self):
        auth = make_mock_authority("auth-1", AuthorityLevel.LEVEL_1)
        validator = make_validator(registry=None)
        result = validator.validate_authority(auth)
        assert result.status == ValidationStatus.SUCCESS

    def test_citation_without_authority_id_no_orphan_check(self):
        c = make_citation(authority_id=None, authority=SourceAuthority.SECONDARY)
        registry = make_registry([])
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 0

    def test_governance_with_mixed_authorities(self):
        governance = make_governance(primary=3, secondary=2, tertiary=1)
        validator = make_validator(min_citations=3, min_primary=2)
        result = validator.validate_governance(governance)
        assert result.status == ValidationStatus.SUCCESS

    def test_full_citation_list_with_mixed_authorities(self):
        c1 = make_citation(authority_id="auth-1", source_url="https://ex.gov/1")
        c2 = make_citation(authority_id="auth-4", source_url="https://ex.gov/2")
        c3 = make_citation(authority_id="auth-1", source_url="https://ex.gov/3")
        validator = make_validator()
        results = validator.validate_citations([c1, c2, c3])
        individual = [r for r in results if "duplicate" not in r.validator_name]
        assert len(individual) == 3

    def test_authority_hierarchy_metadata(self):
        auth = make_mock_authority("my-auth", AuthorityLevel.LEVEL_3)
        validator = make_validator()
        result = validator.validate_authority(auth)
        assert result.metadata["authority_id"] == "my-auth"
        assert result.metadata["authority_level"] == 3
        assert result.metadata["authority_enabled"] is True

    def test_governance_output_metadata(self):
        governance = make_governance(primary=2, secondary=1)
        validator = make_validator(min_citations=1, min_primary=1)
        result = validator.validate_governance(governance)
        assert result.metadata["total_citations"] == 3
        assert result.metadata["primary_count"] == 2
        assert result.metadata["secondary_count"] == 1
        assert result.metadata["tertiary_count"] == 0

    def test_result_frozen_immutable(self):
        auth = make_mock_authority("valid", AuthorityLevel.LEVEL_1)
        validator = make_validator()
        result = validator.validate_authority(auth)
        with pytest.raises(Exception):
            result.status = ValidationStatus.FAILED

    def test_duplicate_authority_status_is_warning(self):
        citations = [
            make_citation(authority_id="auth-1", source_url="https://ex.gov/1"),
            make_citation(authority_id="auth-1", source_url="https://ex.gov/2"),
        ]
        validator = make_validator()
        results = validator.validate_citations(citations)
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert dup_results[0].status == ValidationStatus.WARNING

    def test_citation_governance_with_unknown_authority_skips_orphan(self):
        registry = make_registry([])
        c = make_citation(authority_id="nonexistent", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 0

    def test_validate_citations_preserves_order_and_includes_dup(self):
        c1 = make_citation(authority_id="auth-1", source_url="https://ex.gov/1")
        c2 = make_citation(authority_id="auth-1", source_url="https://ex.gov/2")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        assert len(results) == 3

    def test_disabled_authority_not_counted_for_evidence(self):
        auth1 = make_mock_authority("primary", AuthorityLevel.LEVEL_1, enabled=False)

        registry = make_registry([auth1])
        c = make_citation(
            source_url="https://ex.gov/1",
            authority_id="primary",
            authority=SourceAuthority.PRIMARY,
        )
        governance = SourceGovernanceRecord(primary_citations=[c])
        validator = make_validator(registry, min_citations=0, min_primary=0)
        result = validator.validate_governance(governance)
        coverage_issues = [
            i for i in result.issues if i.code == ValidationCode.INSUFFICIENT_AUTHORITY_COVERAGE
        ]
        assert len(coverage_issues) >= 1

    def test_citation_governance_authority_skipped_not_in_registry(self):
        registry = make_registry([])
        c = make_citation(authority_id="unknown", authority=SourceAuthority.SECONDARY)
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        orphan_issues = [
            i for i in result.issues if i.code == ValidationCode.ORPHAN_SECONDARY_SOURCE
        ]
        assert len(orphan_issues) == 0

    def test_governance_validator_accepts_custom_name(self):
        v = AuthorityGovernanceValidator(
            validator_name="my_governance",
            min_citations_per_entry=5,
            min_primary_citations=3,
        )
        assert v._validator_name == "my_governance"
        assert v._min_citations_per_entry == 5
        assert v._min_primary_citations == 3
