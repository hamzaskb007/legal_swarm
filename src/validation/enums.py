from __future__ import annotations

from enum import StrEnum


class ValidationStatus(StrEnum):
    """Execution outcome of a validation process.

    Represents the overall result of running a validator, not the
    severity of any issues found.  Severity is tracked separately
    via ValidationSeverity.

    .. note::
       ``PASSED`` and ``SUCCESS`` are both accepted and compare equal
       via StrEnum value semantics so that the schema layer's
       ``PASSED`` and the validation layer's ``SUCCESS`` can coexist
       during migration.
    """

    SUCCESS = "SUCCESS"
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"
    PENDING = "PENDING"


class ValidationSeverity(StrEnum):
    """Severity level of a single validation issue.

    Independent of ValidationStatus — a FAILED validation may
    contain LOW-severity issues and a SUCCESS validation may
    contain INFO-level observations.
    """

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def numeric(self) -> int:
        """Numeric representation for ordering comparisons.

        0=INFO, 1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL
        """
        return _SEVERITY_ORDER[self]


_SEVERITY_ORDER: dict[ValidationSeverity, int] = {
    ValidationSeverity.INFO: 0,
    ValidationSeverity.LOW: 1,
    ValidationSeverity.MEDIUM: 2,
    ValidationSeverity.HIGH: 3,
    ValidationSeverity.CRITICAL: 4,
}


class ValidationCode(StrEnum):
    """Central registry of validation issue identifiers.

    Every validator in the system emits issues with one of these
    codes.  Adding a new code here is the first step when
    introducing a new validation rule.
    """

    # Authority validators
    MISSING_AUTHORITY = "MISSING_AUTHORITY"
    INVALID_AUTHORITY_LEVEL = "INVALID_AUTHORITY_LEVEL"
    AUTHORITY_NOT_ENABLED = "AUTHORITY_NOT_ENABLED"
    UNREACHABLE_ENDPOINT = "UNREACHABLE_ENDPOINT"

    # Citation validators
    INVALID_CITATION = "INVALID_CITATION"
    DUPLICATE_CITATION = "DUPLICATE_CITATION"
    INVALID_SOURCE = "INVALID_SOURCE"
    LOW_CITATION_DENSITY = "LOW_CITATION_DENSITY"
    MISSING_CITATION_DATE = "MISSING_CITATION_DATE"
    CITATION_RELIABILITY_TOO_LOW = "CITATION_RELIABILITY_TOO_LOW"

    # Document validators
    MISSING_TITLE = "MISSING_TITLE"
    MISSING_CONTENT = "MISSING_CONTENT"
    EMPTY_DOCUMENT = "EMPTY_DOCUMENT"
    UNSUPPORTED_CONTENT_TYPE = "UNSUPPORTED_CONTENT_TYPE"

    # Schema/entry validators
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FIELD_VALUE = "INVALID_FIELD_VALUE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"

    # Source/governance validators
    MISSING_SOURCE_GOVERNANCE = "MISSING_SOURCE_GOVERNANCE"
    DOMINANT_SOURCE_MISMATCH = "DOMINANT_SOURCE_MISMATCH"
    INSUFFICIENT_CITATIONS = "INSUFFICIENT_CITATIONS"
    ORPHAN_SECONDARY_SOURCE = "ORPHAN_SECONDARY_SOURCE"
    INVALID_REFERENCE_CHAIN = "INVALID_REFERENCE_CHAIN"
    DUPLICATE_AUTHORITY_REFERENCE = "DUPLICATE_AUTHORITY_REFERENCE"
    INSUFFICIENT_AUTHORITY_COVERAGE = "INSUFFICIENT_AUTHORITY_COVERAGE"
    HIERARCHY_MISMATCH = "HIERARCHY_MISMATCH"

    # Milestone 6 Part 2 — Citation Governance & Authority Hierarchy
    LEVEL45_MISSING_REFERENCE = "LEVEL45_MISSING_REFERENCE"
    INSUFFICIENT_CITATION_DENSITY = "INSUFFICIENT_CITATION_DENSITY"
    DEPENDENT_CITATION = "DEPENDENT_CITATION"

    # General / framework
    VALIDATION_SKIPPED = "VALIDATION_SKIPPED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN_ISSUE = "UNKNOWN_ISSUE"
