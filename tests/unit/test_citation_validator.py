from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.authority.models import Authority, AuthorityLevel
from src.authority.registry import AuthorityRegistry
from src.schema.schema import CitationRecord, SourceAuthority
from src.validation import CitationValidator, ValidationResult, ValidationStatus
from src.validation.enums import ValidationCode, ValidationSeverity
from src.validation.exceptions import ValidationConfigurationError
from src.validation.models import ValidationContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_citation(**kwargs) -> CitationRecord:
    defaults = dict(
        source_name="Test Source",
        source_url="https://example.gov/test-source",
        authority=SourceAuthority.PRIMARY,
        reliability_score=0.9,
        publication_date=datetime(2024, 1, 1),
        regulatory_relevance_tag="Test Regulatory Area",
        last_verified_timestamp=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return CitationRecord(**defaults)


def make_unvalidated_citation(**kwargs) -> CitationRecord:
    defaults = dict(
        source_name="Test Source",
        source_url="https://example.gov/test-source",
        authority=SourceAuthority.PRIMARY,
        reliability_score=0.9,
        publication_date=datetime(2024, 1, 1),
        regulatory_relevance_tag="Test Regulatory Area",
        last_verified_timestamp=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return CitationRecord.model_construct(**defaults)


def make_validator(registry: AuthorityRegistry | None = None) -> CitationValidator:
    return CitationValidator(authority_registry=registry)


def make_mock_registry(with_id: str = "auth-1") -> MagicMock:
    registry = MagicMock(spec=AuthorityRegistry)
    auth = MagicMock(spec=Authority)
    auth.id = with_id
    auth.enabled = True
    auth.level = AuthorityLevel.LEVEL_1
    auth.name = "Test Authority"
    auth.jurisdiction = "XX"
    registry.get_by_id.return_value = auth
    registry.__contains__.return_value = True
    return registry


def make_disabled_registry(with_id: str = "auth-1") -> MagicMock:
    registry = MagicMock(spec=AuthorityRegistry)
    auth = MagicMock(spec=Authority)
    auth.id = with_id
    auth.enabled = False
    auth.level = AuthorityLevel.LEVEL_1
    auth.name = "Disabled Authority"
    auth.jurisdiction = "XX"
    registry.get_by_id.return_value = auth
    registry.__contains__.return_value = True
    return registry


# ===================================================================
# Part 2 — Required Field Validation
# ===================================================================


class TestRequiredFields:
    def test_valid_citation_passes_required_fields(self):
        c = make_citation(
            source_name="Valid Source",
            source_url="https://example.gov/law",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.SUCCESS
        error_issues = [i for i in result.issues if i.code == ValidationCode.MISSING_REQUIRED_FIELD]
        assert len(error_issues) == 0

    def test_missing_source_name(self):
        c = make_unvalidated_citation(
            source_name="",
            source_url="https://example.gov",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.MISSING_REQUIRED_FIELD]
        assert any("source_name" in i.field_path for i in issues)

    def test_whitespace_source_name(self):
        c = make_citation(
            source_name="   ",
            source_url="https://example.gov",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.MISSING_REQUIRED_FIELD]
        assert any("source_name" in i.field_path for i in issues)

    def test_missing_source_url(self):
        c = make_unvalidated_citation(
            source_name="Test",
            source_url=None,
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.MISSING_REQUIRED_FIELD]
        assert any("source_url" in i.field_path for i in issues)

    def test_empty_source_url(self):
        c = make_unvalidated_citation(
            source_name="Test",
            source_url="",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.MISSING_REQUIRED_FIELD]
        assert any("source_url" in i.field_path for i in issues)

    def test_missing_authority_id(self):
        c = make_citation(
            source_name="Test",
            source_url="https://example.gov",
            authority_id=None,
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.MISSING_REQUIRED_FIELD]
        assert any("authority_id" in i.field_path for i in issues)

    def test_empty_authority_id(self):
        c = make_citation(
            source_name="Test",
            source_url="https://example.gov",
            authority_id="",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.MISSING_REQUIRED_FIELD]
        assert any("authority_id" in i.field_path for i in issues)

    def test_multiple_missing_fields(self):
        c = make_unvalidated_citation(
            source_name="",
            source_url=None,
            authority_id=None,
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        missing = [i for i in result.issues if i.code == ValidationCode.MISSING_REQUIRED_FIELD]
        assert len(missing) == 3

    def test_missing_field_severity_is_high(self):
        c = make_unvalidated_citation(
            source_name="",
            source_url="https://example.gov",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        for issue in result.issues:
            if issue.code == ValidationCode.MISSING_REQUIRED_FIELD:
                assert issue.severity == ValidationSeverity.HIGH


# ===================================================================
# Part 3 — Authority Validation
# ===================================================================


class TestAuthorityValidation:
    def test_registered_authority_passes(self):
        registry = make_mock_registry("auth-1")
        c = make_citation(source_url="https://example.gov", authority_id="auth-1")
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        missing = [i for i in result.issues if i.code == ValidationCode.MISSING_AUTHORITY]
        assert len(missing) == 0

    def test_unknown_authority_detected(self):
        registry = make_mock_registry("auth-1")
        registry.__contains__.return_value = False
        c = make_citation(source_url="https://example.gov", authority_id="unknown-auth")
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        missing = [i for i in result.issues if i.code == ValidationCode.MISSING_AUTHORITY]
        assert len(missing) > 0
        assert "unknown-auth" in missing[0].message

    def test_authority_key_error_handled(self):
        registry = make_mock_registry("auth-1")
        registry.__contains__.return_value = True
        registry.get_by_id.side_effect = KeyError("unknown")
        c = make_citation(source_url="https://example.gov", authority_id="fail-auth")
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        missing = [i for i in result.issues if i.code == ValidationCode.MISSING_AUTHORITY]
        assert len(missing) > 0

    def test_no_registry_skips_authority_check(self):
        c = make_citation(source_url="https://example.gov", authority_id="any-id")
        validator = make_validator(registry=None)
        result = validator.validate_citation(c)
        auth_issues = [
            i
            for i in result.issues
            if i.code in (ValidationCode.MISSING_AUTHORITY, ValidationCode.AUTHORITY_NOT_ENABLED)
        ]
        assert len(auth_issues) == 0

    def test_disabled_authority_warning(self):
        registry = make_disabled_registry("auth-1")
        c = make_citation(source_url="https://example.gov", authority_id="auth-1")
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        disabled = [i for i in result.issues if i.code == ValidationCode.AUTHORITY_NOT_ENABLED]
        assert len(disabled) == 1
        assert disabled[0].severity == ValidationSeverity.MEDIUM

    def test_authority_none_skipped_when_no_registry(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id=None,
        )
        validator = make_validator(registry=None)
        result = validator.validate_citation(c)
        auth_issues = [
            i
            for i in result.issues
            if i.code in (ValidationCode.MISSING_AUTHORITY, ValidationCode.AUTHORITY_NOT_ENABLED)
        ]
        assert len(auth_issues) == 0

    def test_disabled_authority_does_not_cause_failure(self):
        registry = make_disabled_registry("auth-1")
        c = make_citation(source_url="https://example.gov", authority_id="auth-1")
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.WARNING

    def test_authority_validation_with_details(self):
        registry = make_mock_registry("auth-1")
        registry.__contains__.return_value = False
        c = make_citation(source_url="https://example.gov", authority_id="missing-auth")
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        missing = [i for i in result.issues if i.code == ValidationCode.MISSING_AUTHORITY]
        assert len(missing) == 1
        assert missing[0].details.get("authority_id") == "missing-auth"


# ===================================================================
# Part 4 — Citation Structure Validation
# ===================================================================


class TestStructureValidation:
    def test_valid_url_passes(self):
        c = make_citation(source_url="https://example.gov/statute")
        validator = make_validator()
        result = validator.validate_citation(c)
        url_issues = [i for i in result.issues if i.field_path == "source_url"]
        assert len([i for i in url_issues if i.code == ValidationCode.INVALID_FIELD_VALUE]) == 0

    def test_url_missing_scheme(self):
        c = make_unvalidated_citation(source_url="example.gov/statute")
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        assert any("source_url" in i.field_path for i in issues)

    def test_url_unsupported_scheme(self):
        c = make_unvalidated_citation(source_url="ftp://example.gov/file")
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        assert any("source_url" in i.field_path for i in issues)

    def test_url_missing_hostname(self):
        c = make_unvalidated_citation(source_url="https://")
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        assert any("source_url" in i.field_path for i in issues)

    def test_url_malformed_raises_issue(self):
        c = make_unvalidated_citation(source_url="://broken")
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        url_issues = [i for i in issues if i.field_path == "source_url"]
        assert len(url_issues) >= 1

    def test_valid_publication_date_passes(self):
        c = make_citation(publication_date=datetime(2024, 1, 1))
        validator = make_validator()
        result = validator.validate_citation(c)
        date_issues = [
            i
            for i in result.issues
            if i.field_path in ("publication_date", "retrieved_at")
            and i.code == ValidationCode.INVALID_FIELD_VALUE
        ]
        assert len(date_issues) == 0

    def test_reliability_score_out_of_range_high(self):
        c = make_unvalidated_citation(reliability_score=1.5)
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        assert any("reliability_score" in i.field_path for i in issues)

    def test_reliability_score_out_of_range_low(self):
        c = make_unvalidated_citation(reliability_score=-0.1)
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        assert any("reliability_score" in i.field_path for i in issues)

    def test_raw_excerpt_too_long(self):
        c = make_unvalidated_citation(raw_excerpt="x" * 2001)
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        assert any("raw_excerpt" in i.field_path for i in issues)

    def test_raw_excerpt_within_limit_passes(self):
        c = make_citation(raw_excerpt="x" * 2000)
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        excerpt_issues = [i for i in issues if i.field_path == "raw_excerpt"]
        assert len(excerpt_issues) == 0

    def test_authority_level_out_of_range_low(self):
        c = make_unvalidated_citation(authority_level=0)
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        assert any("authority_level" in i.field_path for i in issues)

    def test_authority_level_out_of_range_high(self):
        c = make_unvalidated_citation(authority_level=6)
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        assert any("authority_level" in i.field_path for i in issues)

    def test_authority_level_valid_passes(self):
        c = make_citation(authority_level=3)
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        level_issues = [i for i in issues if i.field_path == "authority_level"]
        assert len(level_issues) == 0

    def test_malformed_date_handled(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
            publication_date=datetime(2020, 1, 1),
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.SUCCESS


# ===================================================================
# Part 5 — Duplicate Detection
# ===================================================================


class TestDuplicateDetection:
    def test_no_duplicates_single_citation(self):
        c = make_citation(source_url="https://example.gov/1")
        validator = make_validator()
        results = validator.validate_citations([c])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 0

    def test_no_duplicates_different_citations(self):
        c1 = make_citation(source_url="https://example.gov/1")
        c2 = make_citation(source_url="https://example.gov/2")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 0

    def test_duplicate_url_detected(self):
        c1 = make_citation(source_url="https://example.gov/law")
        c2 = make_citation(source_url="https://example.gov/law")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 1
        assert any(i.code == ValidationCode.DUPLICATE_CITATION for i in dup_results[0].issues)

    def test_duplicate_url_normalized_trailing_slash(self):
        c1 = make_citation(source_url="https://example.gov/law")
        c2 = make_citation(source_url="https://example.gov/law/")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 1

    def test_duplicate_citation_id_detected(self):
        common_id = uuid4()
        c1 = make_citation(
            source_url="https://example.gov/1",
            citation_id=common_id,
        )
        c2 = make_citation(
            source_url="https://example.gov/2",
            citation_id=common_id,
        )
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 1
        assert any(i.code == ValidationCode.DUPLICATE_CITATION for i in dup_results[0].issues)

    def test_multiple_duplicates_detected(self):
        c1 = make_citation(source_url="https://example.gov/a")
        c2 = make_citation(source_url="https://example.gov/a")
        c3 = make_citation(source_url="https://example.gov/b")
        c4 = make_citation(source_url="https://example.gov/b")
        validator = make_validator()
        results = validator.validate_citations([c1, c2, c3, c4])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 1
        assert len(dup_results[0].issues) >= 2

    def test_duplicate_issue_has_details(self):
        c1 = make_citation(source_url="https://example.gov/law")
        c2 = make_citation(source_url="https://example.gov/law")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        issue = dup_results[0].issues[0]
        assert "source_url" in issue.details or "citation_id" in issue.details

    def test_duplicate_severity_for_url(self):
        c1 = make_citation(source_url="https://example.gov/law")
        c2 = make_citation(source_url="https://example.gov/law")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        url_issues = [
            i
            for i in dup_results[0].issues
            if i.code == ValidationCode.DUPLICATE_CITATION and "source_url" in str(i.field_path)
        ]
        if url_issues:
            assert url_issues[0].severity == ValidationSeverity.MEDIUM

    def test_duplicate_status_is_warning(self):
        c1 = make_citation(source_url="https://example.gov/law")
        c2 = make_citation(source_url="https://example.gov/law")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert dup_results[0].status == ValidationStatus.WARNING

    def test_empty_citations_no_duplicate_result(self):
        validator = make_validator()
        results = validator.validate_citations([])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 0

    def test_single_citation_no_duplicate_result(self):
        c1 = make_citation(source_url="https://example.gov/1")
        validator = make_validator()
        results = validator.validate_citations([c1])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert len(dup_results) == 0

    def test_duplicate_detection_context_type(self):
        c1 = make_citation(source_url="https://example.gov/law")
        c2 = make_citation(source_url="https://example.gov/law")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert dup_results[0].context.context_type == "duplicate_detection"

    def test_duplicate_detection_metadata(self):
        c1 = make_citation(source_url="https://example.gov/a")
        c2 = make_citation(source_url="https://example.gov/a")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        dup_results = [r for r in results if "duplicate" in r.validator_name]
        assert dup_results[0].metadata.get("citation_count") == 2


# ===================================================================
# Part 6 — Source Type Validation
# ===================================================================


class TestSourceTypeValidation:
    def test_primary_source_passes(self):
        c = make_citation(authority=SourceAuthority.PRIMARY)
        validator = make_validator()
        result = validator.validate_citation(c)
        source_issues = [i for i in result.issues if i.code == ValidationCode.INVALID_SOURCE]
        assert len(source_issues) == 0

    def test_secondary_source_passes(self):
        c = make_citation(authority=SourceAuthority.SECONDARY)
        validator = make_validator()
        result = validator.validate_citation(c)
        source_issues = [i for i in result.issues if i.code == ValidationCode.INVALID_SOURCE]
        assert len(source_issues) == 0

    def test_tertiary_source_passes(self):
        c = make_citation(authority=SourceAuthority.TERTIARY)
        validator = make_validator()
        result = validator.validate_citation(c)
        source_issues = [i for i in result.issues if i.code == ValidationCode.INVALID_SOURCE]
        assert len(source_issues) == 0

    def test_source_type_issue_severity_high(self):
        c = make_citation(authority=SourceAuthority.PRIMARY)
        validator = make_validator()
        result = validator.validate_citation(c)
        source_issues = [i for i in result.issues if i.code == ValidationCode.INVALID_SOURCE]
        for issue in source_issues:
            assert issue.severity == ValidationSeverity.HIGH

    def test_source_type_issue_has_details(self):
        c = make_citation(authority=SourceAuthority.PRIMARY)
        validator = make_validator()
        result = validator.validate_citation(c)
        source_issues = [i for i in result.issues if i.code == ValidationCode.INVALID_SOURCE]
        for issue in source_issues:
            assert "unsupported_value" in issue.details
            assert "valid_values" in issue.details

    def test_source_type_validates_field_path(self):
        c = make_citation(authority=SourceAuthority.PRIMARY)
        validator = make_validator()
        result = validator.validate_citation(c)
        source_issues = [i for i in result.issues if i.code == ValidationCode.INVALID_SOURCE]
        for issue in source_issues:
            assert issue.field_path == "authority"


# ===================================================================
# Part 7 — Citation Consistency
# ===================================================================


class TestCitationConsistency:
    def test_publication_before_retrieved_passes(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
            publication_date=datetime(2024, 1, 1),
            retrieved_at=datetime(2024, 6, 1),
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        consistency_issues = [
            i
            for i in result.issues
            if i.code == ValidationCode.INVALID_FIELD_VALUE and i.field_path == "publication_date"
        ]
        assert len(consistency_issues) == 0

    def test_publication_after_retrieved_is_warning(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
            publication_date=datetime(2024, 6, 1),
            retrieved_at=datetime(2024, 1, 1),
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        consistency_issues = [
            i
            for i in result.issues
            if i.code == ValidationCode.INVALID_FIELD_VALUE and i.field_path == "publication_date"
        ]
        assert len(consistency_issues) == 1
        assert consistency_issues[0].severity == ValidationSeverity.MEDIUM

    def test_publication_equals_retrieved_passes(self):
        now = datetime(2024, 3, 15, 12, 0, 0)
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
            publication_date=now,
            retrieved_at=now,
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        consistency_issues = [
            i
            for i in result.issues
            if i.code == ValidationCode.INVALID_FIELD_VALUE and i.field_path == "publication_date"
        ]
        assert len(consistency_issues) == 0

    def test_no_publication_date_no_consistency_check(self):
        c = make_unvalidated_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
            publication_date=None,
            retrieved_at=datetime(2024, 6, 1),
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        consistency_issues = [
            i
            for i in result.issues
            if i.code == ValidationCode.INVALID_FIELD_VALUE and i.field_path == "publication_date"
        ]
        assert len(consistency_issues) == 0

    def test_consistency_issue_has_details(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
            publication_date=datetime(2024, 12, 31),
            retrieved_at=datetime(2024, 6, 1),
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        consistency_issues = [
            i
            for i in result.issues
            if i.code == ValidationCode.INVALID_FIELD_VALUE and i.field_path == "publication_date"
        ]
        assert len(consistency_issues) == 1
        assert "publication_date" in consistency_issues[0].details
        assert "retrieved_at" in consistency_issues[0].details


# ===================================================================
# Part 8 — Validation Result
# ===================================================================


class TestValidationResultOutput:
    def test_successful_validation_returns_success(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.SUCCESS

    def test_failed_validation_returns_failed(self):
        c = make_unvalidated_citation(
            source_name="",
            source_url=None,
            authority_id=None,
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.FAILED

    def test_warning_validation_returns_warning(self):
        registry = make_disabled_registry("auth-1")
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.WARNING

    def test_result_contains_issues(self):
        c = make_unvalidated_citation(
            source_name="",
            source_url=None,
            authority_id=None,
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert len(result.issues) > 0

    def test_result_has_validator_name(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.validator_name == "citation_validator"

    def test_result_has_timestamps(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at

    def test_result_has_duration(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    def test_result_has_metadata(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert "citation_id" in result.metadata

    def test_result_serialization_roundtrip(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        data = result.model_dump()
        restored = ValidationResult.model_validate(data)
        assert restored.status == result.status
        assert restored.validator_name == result.validator_name
        assert len(restored.issues) == len(result.issues)

    def test_result_json_roundtrip(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        json_str = result.model_dump_json()
        restored = ValidationResult.model_validate_json(json_str)
        assert restored.status == result.status

    def test_result_has_context_when_provided(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        ctx = ValidationContext(document_id="doc-123", context_type="manual")
        validator = make_validator()
        result = validator.validate_citation(c, context=ctx)
        assert result.context.document_id == "doc-123"
        assert result.context.context_type == "manual"

    def test_result_auto_context(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.context.context_type == "citation"
        assert result.context.citation_id == str(c.citation_id)

    def test_validate_citations_returns_list(self):
        c1 = make_citation(source_url="https://example.gov/1")
        c2 = make_citation(source_url="https://example.gov/2")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        assert len(results) == 2
        assert all(isinstance(r, ValidationResult) for r in results)

    def test_validate_citations_with_duplicates_extra_result(self):
        c1 = make_citation(source_url="https://example.gov/law")
        c2 = make_citation(source_url="https://example.gov/law")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        assert len(results) == 3

    def test_validate_citations_empty_list(self):
        validator = make_validator()
        results = validator.validate_citations([])
        assert results == []


# ===================================================================
# Part 9 — Exceptions
# ===================================================================


class TestExceptions:
    def test_empty_validator_name_raises(self):
        with pytest.raises(ValidationConfigurationError):
            CitationValidator(validator_name="")

    def test_whitespace_validator_name_raises(self):
        with pytest.raises(ValidationConfigurationError):
            CitationValidator(validator_name="   ")

    def test_valid_validator_name_ok(self):
        validator = CitationValidator(validator_name="my_validator")
        assert validator._validator_name == "my_validator"

    def test_default_validator_name(self):
        validator = CitationValidator()
        assert validator._validator_name == "citation_validator"


# ===================================================================
# Edge Cases
# ===================================================================


class TestEdgeCases:
    def test_citation_with_all_none_optional_fields(self):
        c = make_unvalidated_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
            publication_date=None,
            section_reference=None,
            raw_excerpt=None,
            regulatory_relevance_tag=None,
            last_verified_timestamp=None,
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.SUCCESS

    def test_citation_with_valid_optional_fields(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
            publication_date=datetime(2024, 1, 1),
            section_reference="§ 3.2",
            raw_excerpt="Short excerpt",
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime(2024, 6, 1),
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.SUCCESS

    def test_validate_citations_reuses_context(self):
        c1 = make_citation(source_url="https://example.gov/1")
        c2 = make_citation(source_url="https://example.gov/2")
        ctx = ValidationContext(document_id="shared-doc")
        validator = make_validator()
        results = validator.validate_citations([c1, c2], context=ctx)
        for r in results:
            if "duplicate" not in r.validator_name:
                assert r.context.document_id == "shared-doc"

    def test_http_url_valid(self):
        c = make_citation(source_url="http://example.gov/law")
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        url_issues = [i for i in issues if i.field_path == "source_url"]
        assert len(url_issues) == 0

    def test_citation_with_no_issues_is_success(self):
        c = CitationRecord(
            source_name="Complete Source",
            source_url="https://example.gov/law",
            authority_id="auth-1",
            authority=SourceAuthority.PRIMARY,
            authority_level=3,
            reliability_score=0.85,
            publication_date=datetime(2024, 1, 1),
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        )
        registry = make_mock_registry("auth-1")
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.SUCCESS

    def test_citation_issue_location_contains_field_path(self):
        c = make_unvalidated_citation(
            source_name="",
            source_url="https://example.gov",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        for issue in result.issues:
            assert issue.field_path is not None

    def test_required_fields_only_no_authority_check(self):
        c = make_citation(
            source_name="Test",
            source_url="https://example.gov",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.SUCCESS

    def test_validate_citations_preserves_order(self):
        c1 = make_citation(source_url="https://example.gov/a")
        c2 = make_citation(source_url="https://example.gov/b")
        validator = make_validator()
        results = validator.validate_citations([c1, c2])
        individual = [r for r in results if "duplicate" not in r.validator_name]
        assert len(individual) == 2

    def test_reliability_score_valid(self):
        c = make_citation(reliability_score=0.5)
        validator = make_validator()
        result = validator.validate_citation(c)
        issues = [i for i in result.issues if i.code == ValidationCode.INVALID_FIELD_VALUE]
        score_issues = [i for i in issues if i.field_path == "reliability_score"]
        assert len(score_issues) == 0

    def test_authority_id_not_checked_without_registry(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="any-id",
        )
        validator = make_validator(registry=None)
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.SUCCESS

    def test_url_none_no_url_validation(self):
        c = make_unvalidated_citation(
            source_url=None,
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        url_issues = [i for i in result.issues if i.field_path == "source_url"]
        missing = [i for i in url_issues if i.code == ValidationCode.MISSING_REQUIRED_FIELD]
        assert len(missing) == 1


# ===================================================================
# Integration — Full Citation Runs
# ===================================================================


class TestFullCitationValidation:
    def test_complete_valid_citation(self):
        registry = make_mock_registry("sec")
        c = make_citation(
            source_name="SEC Rule 10b-5",
            source_url="https://www.sec.gov/rules/10b-5",
            authority_id="sec",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            reliability_score=0.95,
            publication_date=datetime(2023, 1, 1),
            retrieved_at=datetime(2024, 6, 1),
        )
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.SUCCESS
        assert result.issue_count == 0

    def test_complete_invalid_citation_multiple_issues(self):
        c = make_unvalidated_citation(
            source_name="",
            source_url="not-a-valid-url",
            authority_id="",
            authority=SourceAuthority.PRIMARY,
            reliability_score=-0.5,
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.FAILED
        assert result.issue_count >= 3

    def test_citation_with_all_warnings(self):
        registry = make_disabled_registry("warn-auth")
        c = make_citation(
            source_url="https://example.gov",
            source_name="Warning Test",
            authority_id="warn-auth",
            reliability_score=0.5,
        )
        validator = make_validator(registry)
        result = validator.validate_citation(c)
        assert result.status == ValidationStatus.WARNING

    def test_multiple_valid_citations(self):
        citations = [
            make_citation(
                source_url=f"https://example.gov/{i}",
                source_name=f"Source {i}",
                authority_id="auth-1",
            )
            for i in range(5)
        ]
        registry = make_mock_registry("auth-1")
        validator = make_validator(registry)
        results = validator.validate_citations(citations)
        individual = [r for r in results if "duplicate" not in r.validator_name]
        assert len(individual) == 5
        for r in individual:
            assert r.status == ValidationStatus.SUCCESS

    def test_result_frozen_immutable(self):
        c = make_citation(
            source_url="https://example.gov",
            source_name="Test",
            authority_id="auth-1",
        )
        validator = make_validator()
        result = validator.validate_citation(c)
        with pytest.raises(Exception):
            result.status = ValidationStatus.FAILED
