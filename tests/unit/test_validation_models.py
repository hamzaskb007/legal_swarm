from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import pytest

from src.validation import (
    ValidationCode,
    ValidationConfigurationError,
    ValidationContext,
    ValidationContextError,
    ValidationError,
    ValidationExecutionError,
    ValidationIssue,
    ValidationModelError,
    ValidationResult,
    ValidationResultError,
    ValidationSeverity,
    ValidationStatus,
)


# ===================================================================
# Enums — ValidationStatus
# ===================================================================


class TestValidationStatus:
    def test_success_value(self):
        assert ValidationStatus.SUCCESS.value == "SUCCESS"

    def test_warning_value(self):
        assert ValidationStatus.WARNING.value == "WARNING"

    def test_failed_value(self):
        assert ValidationStatus.FAILED.value == "FAILED"

    def test_skipped_value(self):
        assert ValidationStatus.SKIPPED.value == "SKIPPED"

    def test_error_value(self):
        assert ValidationStatus.ERROR.value == "ERROR"

    def test_is_str_enum(self):
        assert issubclass(ValidationStatus, str)

    def test_members_count(self):
        assert len(ValidationStatus) == 5

    def test_from_string_success(self):
        assert ValidationStatus("SUCCESS") == ValidationStatus.SUCCESS

    def test_from_string_failed(self):
        assert ValidationStatus("FAILED") == ValidationStatus.FAILED

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ValidationStatus("UNKNOWN")


# ===================================================================
# Enums — ValidationSeverity
# ===================================================================


class TestValidationSeverity:
    def test_info_value(self):
        assert ValidationSeverity.INFO.value == "INFO"

    def test_low_value(self):
        assert ValidationSeverity.LOW.value == "LOW"

    def test_medium_value(self):
        assert ValidationSeverity.MEDIUM.value == "MEDIUM"

    def test_high_value(self):
        assert ValidationSeverity.HIGH.value == "HIGH"

    def test_critical_value(self):
        assert ValidationSeverity.CRITICAL.value == "CRITICAL"

    def test_is_str_enum(self):
        assert issubclass(ValidationSeverity, str)

    def test_members_count(self):
        assert len(ValidationSeverity) == 5

    def test_numeric_info(self):
        assert ValidationSeverity.INFO.numeric == 0

    def test_numeric_low(self):
        assert ValidationSeverity.LOW.numeric == 1

    def test_numeric_medium(self):
        assert ValidationSeverity.MEDIUM.numeric == 2

    def test_numeric_high(self):
        assert ValidationSeverity.HIGH.numeric == 3

    def test_numeric_critical(self):
        assert ValidationSeverity.CRITICAL.numeric == 4

    def test_numeric_ordering(self):
        sev = list(ValidationSeverity)
        for i in range(len(sev) - 1):
            assert sev[i].numeric < sev[i + 1].numeric

    def test_from_string_high(self):
        assert ValidationSeverity("HIGH") == ValidationSeverity.HIGH

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ValidationSeverity("INVALID")


# ===================================================================
# Enums — ValidationCode
# ===================================================================


class TestValidationCode:
    def test_missing_authority(self):
        assert ValidationCode.MISSING_AUTHORITY.value == "MISSING_AUTHORITY"

    def test_invalid_authority_level(self):
        assert ValidationCode.INVALID_AUTHORITY_LEVEL.value == "INVALID_AUTHORITY_LEVEL"

    def test_authority_not_enabled(self):
        assert ValidationCode.AUTHORITY_NOT_ENABLED.value == "AUTHORITY_NOT_ENABLED"

    def test_unreachable_endpoint(self):
        assert ValidationCode.UNREACHABLE_ENDPOINT.value == "UNREACHABLE_ENDPOINT"

    def test_invalid_citation(self):
        assert ValidationCode.INVALID_CITATION.value == "INVALID_CITATION"

    def test_duplicate_citation(self):
        assert ValidationCode.DUPLICATE_CITATION.value == "DUPLICATE_CITATION"

    def test_invalid_source(self):
        assert ValidationCode.INVALID_SOURCE.value == "INVALID_SOURCE"

    def test_low_citation_density(self):
        assert ValidationCode.LOW_CITATION_DENSITY.value == "LOW_CITATION_DENSITY"

    def test_missing_citation_date(self):
        assert ValidationCode.MISSING_CITATION_DATE.value == "MISSING_CITATION_DATE"

    def test_citation_reliability_too_low(self):
        assert ValidationCode.CITATION_RELIABILITY_TOO_LOW.value == "CITATION_RELIABILITY_TOO_LOW"

    def test_missing_title(self):
        assert ValidationCode.MISSING_TITLE.value == "MISSING_TITLE"

    def test_missing_content(self):
        assert ValidationCode.MISSING_CONTENT.value == "MISSING_CONTENT"

    def test_empty_document(self):
        assert ValidationCode.EMPTY_DOCUMENT.value == "EMPTY_DOCUMENT"

    def test_unsupported_content_type(self):
        assert ValidationCode.UNSUPPORTED_CONTENT_TYPE.value == "UNSUPPORTED_CONTENT_TYPE"

    def test_missing_required_field(self):
        assert ValidationCode.MISSING_REQUIRED_FIELD.value == "MISSING_REQUIRED_FIELD"

    def test_invalid_field_value(self):
        assert ValidationCode.INVALID_FIELD_VALUE.value == "INVALID_FIELD_VALUE"

    def test_schema_mismatch(self):
        assert ValidationCode.SCHEMA_MISMATCH.value == "SCHEMA_MISMATCH"

    def test_missing_source_governance(self):
        assert ValidationCode.MISSING_SOURCE_GOVERNANCE.value == "MISSING_SOURCE_GOVERNANCE"

    def test_dominant_source_mismatch(self):
        assert ValidationCode.DOMINANT_SOURCE_MISMATCH.value == "DOMINANT_SOURCE_MISMATCH"

    def test_insufficient_citations(self):
        assert ValidationCode.INSUFFICIENT_CITATIONS.value == "INSUFFICIENT_CITATIONS"

    def test_validation_skipped(self):
        assert ValidationCode.VALIDATION_SKIPPED.value == "VALIDATION_SKIPPED"

    def test_validation_error(self):
        assert ValidationCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"

    def test_unknown_issue(self):
        assert ValidationCode.UNKNOWN_ISSUE.value == "UNKNOWN_ISSUE"

    def test_all_codes_count(self):
        assert len(ValidationCode) == 28

    def test_from_string_duplicate(self):
        assert ValidationCode("DUPLICATE_CITATION") == ValidationCode.DUPLICATE_CITATION

    def test_invalid_code_raises(self):
        with pytest.raises(ValueError):
            ValidationCode("NONEXISTENT_CODE")


# ===================================================================
# Model — ValidationIssue
# ===================================================================


class TestValidationIssue:
    def test_minimal_construction(self):
        issue = ValidationIssue(
            code=ValidationCode.MISSING_TITLE,
            message="Title is required",
            severity=ValidationSeverity.HIGH,
        )
        assert issue.code == ValidationCode.MISSING_TITLE
        assert issue.message == "Title is required"
        assert issue.severity == ValidationSeverity.HIGH

    def test_defaults(self):
        issue = ValidationIssue(
            code=ValidationCode.UNKNOWN_ISSUE,
            message="Unknown issue",
            severity=ValidationSeverity.INFO,
        )
        assert issue.field_path is None
        assert issue.location is None
        assert issue.details == {}

    def test_with_all_fields(self):
        issue = ValidationIssue(
            code=ValidationCode.INVALID_CITATION,
            message="Citation format is invalid",
            severity=ValidationSeverity.HIGH,
            field_path="citations[0].source",
            location="§ 3.2",
            details={"expected": "URI", "received": "free_text"},
        )
        assert issue.field_path == "citations[0].source"
        assert issue.location == "§ 3.2"
        assert issue.details["expected"] == "URI"

    def test_frozen(self):
        issue = ValidationIssue(
            code=ValidationCode.MISSING_TITLE,
            message="Title is required",
            severity=ValidationSeverity.HIGH,
        )
        with pytest.raises(Exception):
            issue.message = "Changed"

    def test_serialization_roundtrip(self):
        issue = ValidationIssue(
            code=ValidationCode.DUPLICATE_CITATION,
            message="Duplicate found",
            severity=ValidationSeverity.MEDIUM,
            field_path="citations",
            details={"count": 2},
        )
        data = issue.model_dump()
        restored = ValidationIssue.model_validate(data)
        assert restored.code == issue.code
        assert restored.message == issue.message
        assert restored.details == {"count": 2}

    def test_json_roundtrip(self):
        issue = ValidationIssue(
            code=ValidationCode.EMPTY_DOCUMENT,
            message="Document is empty",
            severity=ValidationSeverity.HIGH,
        )
        json_str = issue.model_dump_json()
        restored = ValidationIssue.model_validate_json(json_str)
        assert restored.code == ValidationCode.EMPTY_DOCUMENT
        assert restored.severity == ValidationSeverity.HIGH

    def test_schema_generation(self):
        schema = ValidationIssue.model_json_schema()
        assert schema["title"] == "ValidationIssue"
        assert "code" in schema["properties"]
        assert "message" in schema["properties"]
        assert "severity" in schema["properties"]

    def test_details_mutable_default_not_shared(self):
        a = ValidationIssue(
            code=ValidationCode.UNKNOWN_ISSUE,
            message="A",
            severity=ValidationSeverity.INFO,
        )
        b = ValidationIssue(
            code=ValidationCode.UNKNOWN_ISSUE,
            message="B",
            severity=ValidationSeverity.INFO,
        )
        assert a.details is not b.details
        a.details["key"] = "value"
        assert "key" not in b.details


# ===================================================================
# Model — ValidationContext
# ===================================================================


class TestValidationContext:
    def test_defaults(self):
        ctx = ValidationContext()
        assert ctx.document_id is None
        assert ctx.authority_id is None
        assert ctx.citation_id is None
        assert ctx.source_url is None
        assert ctx.context_type == "generic"

    def test_with_all_fields(self):
        ctx = ValidationContext(
            document_id="doc-123",
            authority_id="auth-456",
            citation_id="cit-789",
            source_url="https://example.gov/law",
            context_type="document",
        )
        assert ctx.document_id == "doc-123"
        assert ctx.authority_id == "auth-456"
        assert ctx.citation_id == "cit-789"
        assert ctx.source_url == "https://example.gov/law"
        assert ctx.context_type == "document"

    def test_frozen(self):
        ctx = ValidationContext(document_id="doc-1")
        with pytest.raises(Exception):
            ctx.document_id = "changed"

    def test_serialization_roundtrip(self):
        ctx = ValidationContext(
            document_id="doc-1",
            authority_id="auth-1",
            context_type="citation",
        )
        data = ctx.model_dump()
        restored = ValidationContext.model_validate(data)
        assert restored.document_id == "doc-1"
        assert restored.context_type == "citation"

    def test_json_roundtrip(self):
        ctx = ValidationContext(
            citation_id="cit-999",
            source_url="https://example.gov/statute",
        )
        json_str = ctx.model_dump_json()
        restored = ValidationContext.model_validate_json(json_str)
        assert restored.citation_id == "cit-999"
        assert restored.source_url == "https://example.gov/statute"

    def test_schema_generation(self):
        schema = ValidationContext.model_json_schema()
        assert schema["title"] == "ValidationContext"
        assert "context_type" in schema["properties"]

    def test_custom_context_type(self):
        ctx = ValidationContext(context_type="governance")
        assert ctx.context_type == "governance"


# ===================================================================
# Model — ValidationResult
# ===================================================================


class TestValidationResult:
    def test_minimal_construction(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="citation_check",
        )
        assert result.status == ValidationStatus.SUCCESS
        assert result.validator_name == "citation_check"
        assert result.issues == []
        assert result.report_id is not None

    def test_defaults(self):
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
        )
        assert result.issues == []
        assert isinstance(result.context, ValidationContext)
        assert result.started_at is None
        assert result.completed_at is None
        assert result.metadata == {}

    def test_with_issues(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.MISSING_TITLE,
                message="Title missing",
                severity=ValidationSeverity.HIGH,
            ),
            ValidationIssue(
                code=ValidationCode.LOW_CITATION_DENSITY,
                message="Too few citations",
                severity=ValidationSeverity.LOW,
            ),
        ]
        result = ValidationResult(
            status=ValidationStatus.WARNING,
            validator_name="comprehensive",
            issues=issues,
        )
        assert len(result.issues) == 2
        assert result.issues[0].code == ValidationCode.MISSING_TITLE

    def test_frozen(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
        )
        with pytest.raises(Exception):
            result.status = ValidationStatus.FAILED

    def test_report_id_is_uuid(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
        )
        assert isinstance(result.report_id, UUID)

    def test_unique_report_ids(self):
        a = ValidationResult(status=ValidationStatus.SUCCESS, validator_name="a")
        b = ValidationResult(status=ValidationStatus.SUCCESS, validator_name="b")
        assert a.report_id != b.report_id

    def test_serialization_roundtrip(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.INVALID_CITATION,
                message="Bad format",
                severity=ValidationSeverity.HIGH,
            )
        ]
        ctx = ValidationContext(document_id="doc-1")
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="cite_validator",
            issues=issues,
            context=ctx,
        )
        data = result.model_dump()
        restored = ValidationResult.model_validate(data)
        assert restored.status == ValidationStatus.FAILED
        assert restored.validator_name == "cite_validator"
        assert len(restored.issues) == 1
        assert restored.context.document_id == "doc-1"
        assert restored.report_id == result.report_id

    def test_json_roundtrip(self):
        result = ValidationResult(
            status=ValidationStatus.SKIPPED,
            validator_name="skip_check",
            metadata={"reason": "not applicable"},
        )
        json_str = result.model_dump_json()
        restored = ValidationResult.model_validate_json(json_str)
        assert restored.status == ValidationStatus.SKIPPED
        assert restored.metadata["reason"] == "not applicable"

    def test_schema_generation(self):
        schema = ValidationResult.model_json_schema()
        assert schema["title"] == "ValidationResult"
        assert "status" in schema["properties"]
        assert "validator_name" in schema["properties"]

    def test_with_timing(self):
        started = datetime(2024, 1, 1, 12, 0, 0)
        completed = started + timedelta(seconds=1, milliseconds=500)
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="timed",
            started_at=started,
            completed_at=completed,
        )
        assert result.started_at == started
        assert result.completed_at == completed

    def test_metadata_custom(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="meta_test",
            metadata={"version": "1.0", "run_id": "run-42"},
        )
        assert result.metadata["version"] == "1.0"
        assert result.metadata["run_id"] == "run-42"

    def test_metadata_default_factory(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="no_meta",
        )
        assert result.metadata == {}

    def test_issue_count_zero(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="empty",
        )
        assert result.issue_count == 0

    def test_issue_count_nonzero(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.UNKNOWN_ISSUE,
                message="1",
                severity=ValidationSeverity.INFO,
            )
            for _ in range(5)
        ]
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="many_issues",
            issues=issues,
        )
        assert result.issue_count == 5


# ===================================================================
# Convenience properties — has_errors / has_warnings
# ===================================================================


class TestValidationResultHasErrors:
    def test_no_issues_no_errors(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
        )
        assert not result.has_errors

    def test_high_severity_is_error(self):
        issue = ValidationIssue(
            code=ValidationCode.MISSING_TITLE,
            message="Missing",
            severity=ValidationSeverity.HIGH,
        )
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=[issue],
        )
        assert result.has_errors

    def test_critical_severity_is_error(self):
        issue = ValidationIssue(
            code=ValidationCode.EMPTY_DOCUMENT,
            message="Empty",
            severity=ValidationSeverity.CRITICAL,
        )
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=[issue],
        )
        assert result.has_errors

    def test_info_severity_not_error(self):
        issue = ValidationIssue(
            code=ValidationCode.UNKNOWN_ISSUE,
            message="Info",
            severity=ValidationSeverity.INFO,
        )
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
            issues=[issue],
        )
        assert not result.has_errors

    def test_low_severity_not_error(self):
        issue = ValidationIssue(
            code=ValidationCode.LOW_CITATION_DENSITY,
            message="Low",
            severity=ValidationSeverity.LOW,
        )
        result = ValidationResult(
            status=ValidationStatus.WARNING,
            validator_name="test",
            issues=[issue],
        )
        assert not result.has_errors

    def test_medium_severity_not_error(self):
        issue = ValidationIssue(
            code=ValidationCode.DUPLICATE_CITATION,
            message="Dup",
            severity=ValidationSeverity.MEDIUM,
        )
        result = ValidationResult(
            status=ValidationStatus.WARNING,
            validator_name="test",
            issues=[issue],
        )
        assert not result.has_errors


class TestValidationResultHasWarnings:
    def test_no_issues_no_warnings(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
        )
        assert not result.has_warnings

    def test_medium_severity_is_warning(self):
        issue = ValidationIssue(
            code=ValidationCode.DUPLICATE_CITATION,
            message="Dup",
            severity=ValidationSeverity.MEDIUM,
        )
        result = ValidationResult(
            status=ValidationStatus.WARNING,
            validator_name="test",
            issues=[issue],
        )
        assert result.has_warnings

    def test_low_severity_is_warning(self):
        issue = ValidationIssue(
            code=ValidationCode.LOW_CITATION_DENSITY,
            message="Low",
            severity=ValidationSeverity.LOW,
        )
        result = ValidationResult(
            status=ValidationStatus.WARNING,
            validator_name="test",
            issues=[issue],
        )
        assert result.has_warnings

    def test_info_severity_not_warning(self):
        issue = ValidationIssue(
            code=ValidationCode.UNKNOWN_ISSUE,
            message="Info",
            severity=ValidationSeverity.INFO,
        )
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
            issues=[issue],
        )
        assert not result.has_warnings

    def test_high_severity_not_warning(self):
        issue = ValidationIssue(
            code=ValidationCode.MISSING_TITLE,
            message="High",
            severity=ValidationSeverity.HIGH,
        )
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=[issue],
        )
        assert not result.has_warnings

    def test_critical_severity_not_warning(self):
        issue = ValidationIssue(
            code=ValidationCode.EMPTY_DOCUMENT,
            message="Crit",
            severity=ValidationSeverity.CRITICAL,
        )
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=[issue],
        )
        assert not result.has_warnings

    def test_mixed_severities(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.MISSING_TITLE,
                message="High",
                severity=ValidationSeverity.HIGH,
            ),
            ValidationIssue(
                code=ValidationCode.LOW_CITATION_DENSITY,
                message="Low",
                severity=ValidationSeverity.LOW,
            ),
        ]
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=issues,
        )
        assert result.has_errors
        assert result.has_warnings


# ===================================================================
# Convenience properties — severity_counts / code_counts
# ===================================================================


class TestValidationResultSeverityCounts:
    def test_empty_issues(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
        )
        assert result.severity_counts == {}

    def test_single_severity(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.UNKNOWN_ISSUE,
                message="A",
                severity=ValidationSeverity.HIGH,
            ),
            ValidationIssue(
                code=ValidationCode.UNKNOWN_ISSUE,
                message="B",
                severity=ValidationSeverity.HIGH,
            ),
        ]
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=issues,
        )
        assert result.severity_counts == {"HIGH": 2}

    def test_multiple_severities(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.UNKNOWN_ISSUE,
                message="H",
                severity=ValidationSeverity.HIGH,
            ),
            ValidationIssue(
                code=ValidationCode.UNKNOWN_ISSUE,
                message="L",
                severity=ValidationSeverity.LOW,
            ),
            ValidationIssue(
                code=ValidationCode.UNKNOWN_ISSUE,
                message="M",
                severity=ValidationSeverity.MEDIUM,
            ),
        ]
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=issues,
        )
        assert result.severity_counts == {"HIGH": 1, "LOW": 1, "MEDIUM": 1}

    def test_severity_counts_keys_are_strings(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.UNKNOWN_ISSUE,
                message="C",
                severity=ValidationSeverity.CRITICAL,
            ),
        ]
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=issues,
        )
        assert isinstance(list(result.severity_counts.keys())[0], str)


class TestValidationResultCodeCounts:
    def test_empty_issues(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
        )
        assert result.code_counts == {}

    def test_single_code(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.MISSING_TITLE,
                message="A",
                severity=ValidationSeverity.HIGH,
            ),
            ValidationIssue(
                code=ValidationCode.MISSING_TITLE,
                message="B",
                severity=ValidationSeverity.HIGH,
            ),
        ]
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=issues,
        )
        assert result.code_counts == {ValidationCode.MISSING_TITLE: 2}

    def test_multiple_codes(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.MISSING_TITLE,
                message="Title",
                severity=ValidationSeverity.HIGH,
            ),
            ValidationIssue(
                code=ValidationCode.MISSING_CONTENT,
                message="Content",
                severity=ValidationSeverity.HIGH,
            ),
            ValidationIssue(
                code=ValidationCode.MISSING_TITLE,
                message="Title2",
                severity=ValidationSeverity.LOW,
            ),
        ]
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=issues,
        )
        assert result.code_counts == {
            ValidationCode.MISSING_TITLE: 2,
            ValidationCode.MISSING_CONTENT: 1,
        }

    def test_code_counts_keys_are_enums(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.UNKNOWN_ISSUE,
                message="X",
                severity=ValidationSeverity.INFO,
            ),
        ]
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=issues,
        )
        key = list(result.code_counts.keys())[0]
        assert isinstance(key, ValidationCode)


# ===================================================================
# Convenience properties — duration_ms
# ===================================================================


class TestValidationResultDuration:
    def test_no_timing_returns_none(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
        )
        assert result.duration_ms is None

    def test_only_started_returns_none(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        assert result.duration_ms is None

    def test_only_completed_returns_none(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
            completed_at=datetime(2024, 1, 1, 12, 0, 1),
        )
        assert result.duration_ms is None

    def test_with_both_timestamps(self):
        started = datetime(2024, 1, 1, 12, 0, 0)
        completed = started + timedelta(seconds=2, milliseconds=500)
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
            started_at=started,
            completed_at=completed,
        )
        assert result.duration_ms == 2500.0

    def test_exact_second(self):
        started = datetime(2024, 1, 1, 12, 0, 0)
        completed = started + timedelta(seconds=1)
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
            started_at=started,
            completed_at=completed,
        )
        assert result.duration_ms == 1000.0

    def test_zero_duration(self):
        now = datetime(2024, 1, 1, 12, 0, 0)
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
            started_at=now,
            completed_at=now,
        )
        assert result.duration_ms == 0.0

    def test_negative_duration(self):
        started = datetime(2024, 1, 1, 12, 0, 1)
        completed = datetime(2024, 1, 1, 12, 0, 0)
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="test",
            started_at=started,
            completed_at=completed,
        )
        assert result.duration_ms == -1000.0


# ===================================================================
# Exception hierarchy
# ===================================================================


class TestExceptionHierarchy:
    def test_base_validation_error(self):
        assert issubclass(ValidationConfigurationError, ValidationError)
        assert issubclass(ValidationModelError, ValidationError)
        assert issubclass(ValidationExecutionError, ValidationError)
        assert issubclass(ValidationContextError, ValidationError)
        assert issubclass(ValidationResultError, ValidationError)

    def test_catch_base_exception(self):
        with pytest.raises(ValidationError):
            raise ValidationConfigurationError("bad config")

    def test_validation_configuration_error(self):
        with pytest.raises(ValidationConfigurationError):
            raise ValidationConfigurationError("misconfigured")

    def test_validation_model_error(self):
        with pytest.raises(ValidationModelError):
            raise ValidationModelError("invalid data")

    def test_validation_execution_error(self):
        with pytest.raises(ValidationExecutionError):
            raise ValidationExecutionError("runtime failure")

    def test_validation_context_error(self):
        with pytest.raises(ValidationContextError):
            raise ValidationContextError("invalid context")

    def test_validation_result_error(self):
        with pytest.raises(ValidationResultError):
            raise ValidationResultError("bad result")

    def test_message_preserved(self):
        try:
            raise ValidationConfigurationError("custom message")
        except ValidationConfigurationError as e:
            assert str(e) == "custom message"

    def test_all_exceptions_are_validation_error(self):
        exceptions = [
            ValidationConfigurationError,
            ValidationModelError,
            ValidationExecutionError,
            ValidationContextError,
            ValidationResultError,
        ]
        for exc in exceptions:
            assert issubclass(exc, ValidationError)
            assert exc.__name__ != "ValidationError"

    def test_raise_and_catch_each(self):
        for exc_cls in [
            ValidationConfigurationError,
            ValidationModelError,
            ValidationExecutionError,
            ValidationContextError,
            ValidationResultError,
        ]:
            with pytest.raises(exc_cls):
                raise exc_cls("test")

    def test_exception_is_exception(self):
        assert issubclass(ValidationError, Exception)

    def test_can_chain_exceptions(self):
        inner = ValidationModelError("inner failure")
        outer = ValidationExecutionError("outer failure")
        assert inner.__cause__ is None
        assert outer.__cause__ is None


# ===================================================================
# Package imports
# ===================================================================


class TestPackageImports:
    def test_import_validation_status(self):
        from src.validation import ValidationStatus

        assert ValidationStatus is not None

    def test_import_validation_severity(self):
        from src.validation import ValidationSeverity

        assert ValidationSeverity is not None

    def test_import_validation_code(self):
        from src.validation import ValidationCode

        assert ValidationCode is not None

    def test_import_validation_issue(self):
        from src.validation import ValidationIssue

        assert ValidationIssue is not None

    def test_import_validation_context(self):
        from src.validation import ValidationContext

        assert ValidationContext is not None

    def test_import_validation_result(self):
        from src.validation import ValidationResult

        assert ValidationResult is not None

    def test_import_all_exceptions(self):
        from src.validation import (
            ValidationConfigurationError,
            ValidationContextError,
            ValidationError,
            ValidationExecutionError,
            ValidationModelError,
            ValidationResultError,
        )

        assert all(
            e is not None
            for e in [
                ValidationConfigurationError,
                ValidationContextError,
                ValidationError,
                ValidationExecutionError,
                ValidationModelError,
                ValidationResultError,
            ]
        )

    def test_all_exports_are_in_all(self):
        from src.validation import __all__ as validation_all

        expected = {
            "ValidationStatus",
            "ValidationSeverity",
            "ValidationCode",
            "ValidationIssue",
            "ValidationContext",
            "ValidationResult",
            "CitationValidator",
            "AuthorityGovernanceValidator",
            "ValidationError",
            "ValidationConfigurationError",
            "ValidationModelError",
            "ValidationExecutionError",
            "ValidationContextError",
            "ValidationResultError",
        }
        assert set(validation_all) == expected


# ===================================================================
# Edge cases
# ===================================================================


class TestEdgeCases:
    def test_validation_result_empty_issues_properties(self):
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="empty",
        )
        assert not result.has_errors
        assert not result.has_warnings
        assert result.issue_count == 0
        assert result.severity_counts == {}
        assert result.code_counts == {}
        assert result.duration_ms is None

    def test_validation_result_large_issue_list(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.UNKNOWN_ISSUE,
                message=f"Issue {i}",
                severity=ValidationSeverity.INFO,
            )
            for i in range(100)
        ]
        result = ValidationResult(
            status=ValidationStatus.WARNING,
            validator_name="large",
            issues=issues,
        )
        assert result.issue_count == 100
        assert result.severity_counts == {"INFO": 100}

    def test_validation_context_partial_fields(self):
        ctx = ValidationContext(authority_id="auth-1")
        assert ctx.authority_id == "auth-1"
        assert ctx.document_id is None
        assert ctx.citation_id is None

    def test_validation_issue_with_empty_details(self):
        issue = ValidationIssue(
            code=ValidationCode.SCHEMA_MISMATCH,
            message="Schema mismatch",
            severity=ValidationSeverity.CRITICAL,
            details={},
        )
        assert issue.details == {}

    def test_validation_issue_location_only(self):
        issue = ValidationIssue(
            code=ValidationCode.INVALID_FIELD_VALUE,
            message="Bad value",
            severity=ValidationSeverity.HIGH,
            location="paragraph 4.2",
        )
        assert issue.location == "paragraph 4.2"
        assert issue.field_path is None

    def test_validation_result_with_no_validator_name_empty(self):
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="",
        )
        assert result.validator_name == ""

    def test_validation_status_equality(self):
        assert ValidationStatus.FAILED == ValidationStatus.FAILED
        assert ValidationStatus.FAILED != ValidationStatus.ERROR

    def test_validation_severity_equality(self):
        assert ValidationSeverity.HIGH == ValidationSeverity.HIGH
        assert ValidationSeverity.HIGH != ValidationSeverity.CRITICAL

    def test_validation_code_equality(self):
        assert ValidationCode.MISSING_TITLE == ValidationCode.MISSING_TITLE
        assert ValidationCode.MISSING_TITLE != ValidationCode.MISSING_CONTENT

    def test_model_dump_excludes_unset(self):
        issue = ValidationIssue(
            code=ValidationCode.UNKNOWN_ISSUE,
            message="Test",
            severity=ValidationSeverity.INFO,
        )
        dumped = issue.model_dump(exclude_unset=True)
        assert "code" in dumped
        assert "message" in dumped
        assert "severity" in dumped
        assert "field_path" not in dumped

    def test_validation_result_dict_serialization(self):
        issues = [
            ValidationIssue(
                code=ValidationCode.MISSING_TITLE,
                message="Missing",
                severity=ValidationSeverity.HIGH,
            )
        ]
        result = ValidationResult(
            status=ValidationStatus.FAILED,
            validator_name="test",
            issues=issues,
        )
        as_dict = result.model_dump()
        assert isinstance(as_dict, dict)
        assert as_dict["status"] == "FAILED"
        assert isinstance(as_dict["issues"], list)
        assert as_dict["issues"][0]["code"] == "MISSING_TITLE"

    def test_validation_result_with_context_type_document(self):
        ctx = ValidationContext(
            document_id="doc-123",
            context_type="document",
        )
        result = ValidationResult(
            status=ValidationStatus.SUCCESS,
            validator_name="doc_validator",
            context=ctx,
        )
        assert result.context.context_type == "document"
        assert result.context.document_id == "doc-123"
