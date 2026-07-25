from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.validation.enums import ValidationCode, ValidationSeverity, ValidationStatus


class ValidationIssue(BaseModel, frozen=True):
    """A single issue found during a validation check.

    Forms the atomic unit of validation output.  Every issue
    carries a code (machine-readable), a human-readable message,
    and a severity level.  Optional fields allow attaching it to
    a specific location in the source data.
    """

    code: ValidationCode
    message: str
    severity: ValidationSeverity
    field_path: str | None = None
    location: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationContext(BaseModel, frozen=True):
    """Contextual metadata describing what was validated and why.

    This model holds references (strings/UUIDs) to the entities
    involved in validation, never the full domain objects
    themselves.  The ``context_type`` discriminator tells
    downstream consumers what kind of validation was performed.
    """

    document_id: str | None = None
    authority_id: str | None = None
    citation_id: str | None = None
    source_url: str | None = None
    context_type: str = "generic"


class ValidationResult(BaseModel, frozen=True):
    """Immutable result envelope produced by a single validation run.

    Expected usage::

        result = ValidationResult(
            report_id=uuid4(),
            status=ValidationStatus.FAILED,
            validator_name="citation_check",
            issues=[...],
            context=ValidationContext(citation_id="..."),
        )
    """

    report_id: UUID = Field(default_factory=uuid4)
    status: ValidationStatus
    validator_name: str
    issues: list[ValidationIssue] = Field(default_factory=list)
    context: ValidationContext = Field(default_factory=ValidationContext)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def has_errors(self) -> bool:
        """True when at least one issue has HIGH or CRITICAL severity."""
        return any(
            i.severity in (ValidationSeverity.HIGH, ValidationSeverity.CRITICAL)
            for i in self.issues
        )

    @property
    def has_warnings(self) -> bool:
        """True when at least one issue has MEDIUM or LOW severity."""
        return any(
            i.severity in (ValidationSeverity.MEDIUM, ValidationSeverity.LOW) for i in self.issues
        )

    @property
    def issue_count(self) -> int:
        """Total number of issues in this result."""
        return len(self.issues)

    @property
    def severity_counts(self) -> dict[str, int]:
        """Count of issues per severity level.

        Returns a dict keyed by severity value, e.g.
        ``{"HIGH": 2, "LOW": 1}``.
        """
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
        return counts

    @property
    def code_counts(self) -> dict[ValidationCode, int]:
        """Count of issues per ValidationCode."""
        counts: dict[ValidationCode, int] = {}
        for issue in self.issues:
            counts[issue.code] = counts.get(issue.code, 0) + 1
        return counts

    @property
    def duration_ms(self) -> float | None:
        """Wall-clock duration in milliseconds, or None if timing is missing."""
        if self.started_at is None or self.completed_at is None:
            return None
        delta = self.completed_at - self.started_at
        return delta.total_seconds() * 1000.0
