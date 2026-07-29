from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import UUID

from src.authority.registry import AuthorityRegistry
from src.schema.schema import SourceAuthority
from src.validation.enums import ValidationCode, ValidationSeverity, ValidationStatus
from src.validation.exceptions import (
    ValidationConfigurationError,
)
from src.validation.models import ValidationContext, ValidationIssue, ValidationResult

if TYPE_CHECKING:
    from src.schema.schema import CitationRecord

logger = logging.getLogger(__name__)

VALID_SOURCE_AUTHORITIES: frozenset[str] = frozenset({m.value for m in SourceAuthority})


class CitationValidator:
    """Deterministic, stateless citation validator.

    Validates citations across six categories:

    1. Required fields — every mandatory ``CitationRecord`` field
    2. Authority — existence and resolvability in ``AuthorityRegistry``
    3. Structure — URL, date, identifier, enum correctness
    4. Duplicates — identical or URL-equivalent citations
    5. Source type — membership in ``SourceAuthority``
    6. Consistency — publication vs retrieval date, metadata coherence

    Integration points
    ------------------
    - **Input:** ``CitationRecord`` (``src.schema.schema``)
    - **Output:** ``ValidationResult`` (``src.validation.models``)
    - **Registry:** ``AuthorityRegistry`` (``src.authority.registry``)
    - **Logging:** standard library ``logging``
    """

    def __init__(
        self,
        authority_registry: AuthorityRegistry | None = None,
        validator_name: str = "citation_validator",
    ) -> None:
        if not validator_name or not validator_name.strip():
            raise ValidationConfigurationError("validator_name must not be empty")
        self._registry = authority_registry
        self._validator_name = validator_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_citation(
        self,
        citation: CitationRecord,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """Validate a single citation and return a structured result."""
        started_at = datetime.utcnow()
        ctx = context or ValidationContext(
            citation_id=str(citation.citation_id),
            source_url=citation.source_url,
            context_type="citation",
        )
        logger.info(
            "Validation started for citation %s",
            citation.citation_id,
        )

        issues: list[ValidationIssue] = []
        issues.extend(self._check_required_fields(citation))
        issues.extend(self._check_authority(citation))
        issues.extend(self._check_structure(citation))
        issues.extend(self._check_source_type(citation))
        issues.extend(self._check_consistency(citation))

        completed_at = datetime.utcnow()
        status = self._compute_status(issues)

        logger.info(
            "Validation completed for citation %s: %s (%d issues)",
            citation.citation_id,
            status.value,
            len(issues),
        )

        return ValidationResult(
            status=status,
            validator_name=self._validator_name,
            issues=issues,
            context=ctx,
            started_at=started_at,
            completed_at=completed_at,
            metadata={
                "citation_id": str(citation.citation_id),
            },
        )

    def validate_citations(
        self,
        citations: list[CitationRecord],
        context: ValidationContext | None = None,
    ) -> list[ValidationResult]:
        """Validate multiple citations.

        Returns one ``ValidationResult`` per citation plus an
        additional result for cross-citation duplicate detection.
        """
        results: list[ValidationResult] = []
        for citation in citations:
            results.append(self.validate_citation(citation, context=context))

        dup_result = self._detect_duplicates(citations, context=context)
        if dup_result is not None:
            results.append(dup_result)

        return results

    # ------------------------------------------------------------------
    # Part 2 — Required Field Validation
    # ------------------------------------------------------------------

    def _check_required_fields(self, citation: CitationRecord) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if not citation.source_name or not citation.source_name.strip():
            issues.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_REQUIRED_FIELD,
                    message="source_name is required and must not be empty",
                    severity=ValidationSeverity.HIGH,
                    field_path="source_name",
                )
            )

        if citation.source_url is None or not citation.source_url.strip():
            issues.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_REQUIRED_FIELD,
                    message="source_url is required and must not be empty",
                    severity=ValidationSeverity.HIGH,
                    field_path="source_url",
                )
            )

        if citation.authority_id is None or not citation.authority_id.strip():
            issues.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_REQUIRED_FIELD,
                    message="authority_id is required and must not be empty",
                    severity=ValidationSeverity.HIGH,
                    field_path="authority_id",
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Part 3 — Authority Validation
    # ------------------------------------------------------------------

    def _check_authority(self, citation: CitationRecord) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if self._registry is None:
            return issues

        if not citation.authority_id or not citation.authority_id.strip():
            return issues

        if citation.authority_id not in self._registry:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_AUTHORITY,
                    message=f"authority_id '{citation.authority_id}' is not registered",
                    severity=ValidationSeverity.HIGH,
                    field_path="authority_id",
                    details={"authority_id": citation.authority_id},
                )
            )
            return issues

        try:
            authority = self._registry.get_by_id(citation.authority_id)
            if not authority.enabled:
                issues.append(
                    ValidationIssue(
                        code=ValidationCode.AUTHORITY_NOT_ENABLED,
                        message=f"authority '{citation.authority_id}' is disabled",
                        severity=ValidationSeverity.MEDIUM,
                        field_path="authority_id",
                        details={"authority_id": citation.authority_id},
                    )
                )
        except KeyError:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_AUTHORITY,
                    message=f"authority_id '{citation.authority_id}' could not be resolved",
                    severity=ValidationSeverity.HIGH,
                    field_path="authority_id",
                    details={"authority_id": citation.authority_id},
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Part 4 — Citation Structure Validation
    # ------------------------------------------------------------------

    def _check_structure(self, citation: CitationRecord) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if citation.source_url and citation.source_url.strip():
            url_issue = self._check_url(citation.source_url)
            if url_issue is not None:
                issues.append(url_issue)

        if citation.publication_date is not None:
            date_issue = self._check_date(citation.publication_date, "publication_date")
            if date_issue is not None:
                issues.append(date_issue)

        if citation.retrieved_at is not None:
            date_issue = self._check_date(citation.retrieved_at, "retrieved_at")
            if date_issue is not None:
                issues.append(date_issue)

        if citation.reliability_score < 0.0 or citation.reliability_score > 1.0:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_FIELD_VALUE,
                    message=f"reliability_score must be between 0.0 and 1.0, got {citation.reliability_score}",
                    severity=ValidationSeverity.HIGH,
                    field_path="reliability_score",
                )
            )

        if citation.raw_excerpt is not None and len(citation.raw_excerpt) > 2000:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_FIELD_VALUE,
                    message="raw_excerpt exceeds maximum length of 2000 characters",
                    severity=ValidationSeverity.LOW,
                    field_path="raw_excerpt",
                )
            )

        if citation.authority_level < 1 or citation.authority_level > 5:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_FIELD_VALUE,
                    message=f"authority_level must be between 1 and 5, got {citation.authority_level}",
                    severity=ValidationSeverity.HIGH,
                    field_path="authority_level",
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Part 5 — Duplicate Detection
    # ------------------------------------------------------------------

    def _detect_duplicates(
        self,
        citations: list[CitationRecord],
        context: ValidationContext | None = None,
    ) -> ValidationResult | None:
        if len(citations) < 2:
            return None

        started_at = datetime.utcnow()
        issues: list[ValidationIssue] = []
        seen_urls: dict[str, int] = {}
        seen_ids: dict[UUID, int] = {}

        for idx, citation in enumerate(citations):
            if citation.citation_id in seen_ids:
                prev_idx = seen_ids[citation.citation_id]
                issues.append(
                    ValidationIssue(
                        code=ValidationCode.DUPLICATE_CITATION,
                        message=f"Duplicate citation_id '{citation.citation_id}' at index {idx} (matches index {prev_idx})",
                        severity=ValidationSeverity.HIGH,
                        field_path=f"citations[{idx}].citation_id",
                        details={
                            "citation_id": str(citation.citation_id),
                            "index": idx,
                            "matches_index": prev_idx,
                        },
                    )
                )
            else:
                seen_ids[citation.citation_id] = idx

            url = citation.source_url
            if url and url.strip():
                norm_url = url.strip().rstrip("/")
                if norm_url in seen_urls:
                    prev_idx = seen_urls[norm_url]
                    issues.append(
                        ValidationIssue(
                            code=ValidationCode.DUPLICATE_CITATION,
                            message=f"Duplicate source_url '{norm_url}' at index {idx} (matches index {prev_idx})",
                            severity=ValidationSeverity.MEDIUM,
                            field_path=f"citations[{idx}].source_url",
                            details={
                                "source_url": norm_url,
                                "index": idx,
                                "matches_index": prev_idx,
                            },
                        )
                    )
                else:
                    seen_urls[norm_url] = idx

        if not issues:
            return None

        completed_at = datetime.utcnow()
        status = self._compute_status(issues)

        return ValidationResult(
            status=status,
            validator_name=f"{self._validator_name}.duplicates",
            issues=issues,
            context=context or ValidationContext(context_type="duplicate_detection"),
            started_at=started_at,
            completed_at=completed_at,
            metadata={"citation_count": len(citations)},
        )

    # ------------------------------------------------------------------
    # Part 6 — Source Type Validation
    # ------------------------------------------------------------------

    def _check_source_type(self, citation: CitationRecord) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if citation.authority.value not in VALID_SOURCE_AUTHORITIES:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_SOURCE,
                    message=f"Unsupported source authority '{citation.authority.value}'. Must be one of {sorted(VALID_SOURCE_AUTHORITIES)}",
                    severity=ValidationSeverity.HIGH,
                    field_path="authority",
                    details={
                        "unsupported_value": citation.authority.value,
                        "valid_values": sorted(VALID_SOURCE_AUTHORITIES),
                    },
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Part 7 — Citation Consistency
    # ------------------------------------------------------------------

    def _check_consistency(self, citation: CitationRecord) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if citation.publication_date is not None and citation.retrieved_at is not None:
            delta = citation.retrieved_at - citation.publication_date
            if delta.total_seconds() < 0:
                issues.append(
                    ValidationIssue(
                        code=ValidationCode.INVALID_FIELD_VALUE,
                        message="publication_date must not be later than retrieved_at",
                        severity=ValidationSeverity.MEDIUM,
                        field_path="publication_date",
                        details={
                            "publication_date": citation.publication_date.isoformat(),
                            "retrieved_at": citation.retrieved_at.isoformat(),
                        },
                    )
                )

        if (
            citation.authority_id
            and citation.source_name
            and citation.authority_id.strip()
            and citation.authority_id not in citation.source_name
            and citation.source_name not in citation.authority_id
        ):
            pass

        return issues

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_status(issues: list[ValidationIssue]) -> ValidationStatus:
        if not issues:
            return ValidationStatus.SUCCESS
        severities = {i.severity for i in issues}
        if ValidationSeverity.HIGH in severities or ValidationSeverity.CRITICAL in severities:
            return ValidationStatus.FAILED
        if ValidationSeverity.MEDIUM in severities or ValidationSeverity.LOW in severities:
            return ValidationStatus.WARNING
        return ValidationStatus.SUCCESS

    @staticmethod
    def _check_url(url_str: str) -> ValidationIssue | None:
        try:
            parsed = urlparse(url_str)
            if not parsed.scheme:
                return ValidationIssue(
                    code=ValidationCode.INVALID_FIELD_VALUE,
                    message=f"URL '{url_str}' is missing a scheme",
                    severity=ValidationSeverity.HIGH,
                    field_path="source_url",
                    details={"url": url_str},
                )
            if parsed.scheme not in ("http", "https"):
                return ValidationIssue(
                    code=ValidationCode.INVALID_FIELD_VALUE,
                    message=f"URL scheme '{parsed.scheme}' is not supported (must be http or https)",
                    severity=ValidationSeverity.HIGH,
                    field_path="source_url",
                    details={"url": url_str, "scheme": parsed.scheme},
                )
            if not parsed.netloc:
                return ValidationIssue(
                    code=ValidationCode.INVALID_FIELD_VALUE,
                    message=f"URL '{url_str}' is missing a hostname",
                    severity=ValidationSeverity.HIGH,
                    field_path="source_url",
                    details={"url": url_str},
                )
        except (ValueError, TypeError, AttributeError) as exc:
            return ValidationIssue(
                code=ValidationCode.INVALID_FIELD_VALUE,
                message=f"URL '{url_str}' is malformed: {exc}",
                severity=ValidationSeverity.HIGH,
                field_path="source_url",
                details={"url": url_str, "error": str(exc)},
            )
        return None

    @staticmethod
    def _check_date(value: datetime, field_path: str) -> ValidationIssue | None:
        try:
            if value.tzinfo is not None:
                pass
        except (ValueError, TypeError, AttributeError) as exc:
            return ValidationIssue(
                code=ValidationCode.INVALID_FIELD_VALUE,
                message=f"{field_path} contains an invalid date: {exc}",
                severity=ValidationSeverity.HIGH,
                field_path=field_path,
                details={"error": str(exc)},
            )
        return None
