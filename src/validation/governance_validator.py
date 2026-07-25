from __future__ import annotations

import logging
from datetime import datetime

from src.authority.models import Authority, AuthorityLevel
from src.authority.registry import AuthorityRegistry
from src.schema.schema import CitationRecord, SourceAuthority, SourceGovernanceRecord
from src.validation.enums import ValidationCode, ValidationSeverity, ValidationStatus
from src.validation.exceptions import ValidationConfigurationError
from src.validation.models import ValidationContext, ValidationIssue, ValidationResult

logger = logging.getLogger(__name__)

AUTHORITY_LEVEL_MAP: dict[AuthorityLevel, SourceAuthority] = {
    AuthorityLevel.LEVEL_1: SourceAuthority.PRIMARY,
    AuthorityLevel.LEVEL_2: SourceAuthority.PRIMARY,
    AuthorityLevel.LEVEL_3: SourceAuthority.PRIMARY,
    AuthorityLevel.LEVEL_4: SourceAuthority.SECONDARY,
    AuthorityLevel.LEVEL_5: SourceAuthority.TERTIARY,
}

PRIMARY_LEVELS: frozenset[AuthorityLevel] = frozenset(
    {AuthorityLevel.LEVEL_1, AuthorityLevel.LEVEL_2, AuthorityLevel.LEVEL_3}
)
SECONDARY_LEVELS: frozenset[AuthorityLevel] = frozenset({AuthorityLevel.LEVEL_4})
TERTIARY_LEVELS: frozenset[AuthorityLevel] = frozenset({AuthorityLevel.LEVEL_5})


class AuthorityGovernanceValidator:
    """Deterministic governance validator for authority relationships and evidence
    quality.

    Validation categories
    ---------------------
    1. Authority hierarchy — level validity, internal consistency
    2. Authority level enforcement — correct level-to-source mapping
    3. Secondary source referencing — higher-authority support chains
    4. Citation density — configurable minimum counts
    5. Minimum evidence — required authority coverage
    6. Duplicate authority references — redundant authority usage

    Integration points
    ------------------
    - **Input:** ``Authority``, ``CitationRecord``, ``SourceGovernanceRecord``
    - **Registry:** ``AuthorityRegistry``
    - **Output:** ``ValidationResult`` (``src.validation.models``)
    """

    def __init__(
        self,
        authority_registry: AuthorityRegistry | None = None,
        validator_name: str = "authority_governance_validator",
        min_citations_per_entry: int = 3,
        min_primary_citations: int = 2,
    ) -> None:
        if not validator_name or not validator_name.strip():
            raise ValidationConfigurationError("validator_name must not be empty")
        if min_citations_per_entry < 0:
            raise ValidationConfigurationError(
                "min_citations_per_entry must be >= 0"
            )
        if min_primary_citations < 0:
            raise ValidationConfigurationError(
                "min_primary_citations must be >= 0"
            )
        self._registry = authority_registry
        self._validator_name = validator_name
        self._min_citations_per_entry = min_citations_per_entry
        self._min_primary_citations = min_primary_citations

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_authority(
        self,
        authority: Authority,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """Validate a single authority's hierarchy and level."""
        started_at = datetime.utcnow()
        ctx = context or ValidationContext(
            authority_id=authority.id,
            context_type="authority_governance",
        )

        issues: list[ValidationIssue] = []
        issues.extend(self._check_hierarchy(authority))
        issues.extend(self._check_level_enforcement(authority))

        completed_at = datetime.utcnow()
        status = self._compute_status(issues)

        return ValidationResult(
            status=status,
            validator_name=self._validator_name,
            issues=issues,
            context=ctx,
            started_at=started_at,
            completed_at=completed_at,
            metadata={
                "authority_id": authority.id,
                "authority_level": authority.level.value,
                "authority_enabled": authority.enabled,
            },
        )

    def validate_citation(
        self,
        citation: CitationRecord,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """Validate governance aspects of a single citation.

        Checks secondary/tertiary source referencing and authority
        level alignment.
        """
        started_at = datetime.utcnow()
        ctx = context or ValidationContext(
            citation_id=str(citation.citation_id),
            authority_id=citation.authority_id,
            context_type="citation_governance",
        )

        issues: list[ValidationIssue] = []
        issues.extend(self._check_secondary_referencing(citation))

        completed_at = datetime.utcnow()
        status = self._compute_status(issues)

        return ValidationResult(
            status=status,
            validator_name=self._validator_name,
            issues=issues,
            context=ctx,
            started_at=started_at,
            completed_at=completed_at,
            metadata={
                "citation_id": str(citation.citation_id),
                "authority_id": citation.authority_id or "",
                "authority": citation.authority.value,
            },
        )

    def validate_governance(
        self,
        source_governance: SourceGovernanceRecord,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """Validate evidence requirements and citation density for a governance
        record.

        Runs density and minimum-evidence checks across all citations
        in the record.
        """
        started_at = datetime.utcnow()
        all_citations = (
            source_governance.primary_citations
            + source_governance.secondary_citations
            + source_governance.tertiary_citations
        )

        ctx = context or ValidationContext(context_type="governance_evidence")

        issues: list[ValidationIssue] = []
        issues.extend(
            self._check_citation_density(
                all_citations,
                source_governance,
            )
        )
        issues.extend(self._check_minimum_evidence(source_governance))

        completed_at = datetime.utcnow()
        status = self._compute_status(issues)

        all_authority_ids = [
            c.authority_id for c in all_citations if c.authority_id
        ]

        return ValidationResult(
            status=status,
            validator_name=self._validator_name,
            issues=issues,
            context=ctx,
            started_at=started_at,
            completed_at=completed_at,
            metadata={
                "total_citations": len(all_citations),
                "primary_count": len(source_governance.primary_citations),
                "secondary_count": len(source_governance.secondary_citations),
                "tertiary_count": len(source_governance.tertiary_citations),
                "unique_authority_ids": len(set(all_authority_ids)),
            },
        )

    def validate_citations(
        self,
        citations: list[CitationRecord],
        context: ValidationContext | None = None,
    ) -> list[ValidationResult]:
        """Validate a list of citations.

        Returns one result per citation plus a duplicate-authority
        detection result.
        """
        results: list[ValidationResult] = []
        for citation in citations:
            results.append(self.validate_citation(citation, context=context))

        dup_result = self._check_duplicate_authorities(citations, context=context)
        if dup_result is not None:
            results.append(dup_result)

        return results

    # ------------------------------------------------------------------
    # Part 2 — Authority Hierarchy Validation
    # ------------------------------------------------------------------

    def _check_hierarchy(self, authority: Authority) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if authority.level.value < 1 or authority.level.value > 5:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.HIERARCHY_MISMATCH,
                    message=(
                        f"Authority '{authority.id}' has invalid level "
                        f"{authority.level.value}; must be 1-5"
                    ),
                    severity=ValidationSeverity.HIGH,
                    field_path="level",
                    details={
                        "authority_id": authority.id,
                        "level": authority.level.value,
                    },
                )
            )

        for rel in authority.relationships:
            if self._registry is not None:
                try:
                    self._registry.get_by_id(rel.target_id)
                except KeyError:
                    issues.append(
                        ValidationIssue(
                            code=ValidationCode.INVALID_REFERENCE_CHAIN,
                            message=(
                                f"Authority '{authority.id}' relationship "
                                f"references unknown target '{rel.target_id}'"
                            ),
                            severity=ValidationSeverity.HIGH,
                            field_path="relationships",
                            details={
                                "authority_id": authority.id,
                                "target_id": rel.target_id,
                                "relationship_type": rel.type.value,
                            },
                        )
                    )

        return issues

    # ------------------------------------------------------------------
    # Part 3 — Authority Level Enforcement
    # ------------------------------------------------------------------

    def _check_level_enforcement(
        self, authority: Authority
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        expected = AUTHORITY_LEVEL_MAP.get(authority.level)
        if expected is None:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_AUTHORITY_LEVEL,
                    message=(
                        f"Authority '{authority.id}' has unrecognised level "
                        f"{authority.level.value}"
                    ),
                    severity=ValidationSeverity.HIGH,
                    field_path="level",
                    details={
                        "authority_id": authority.id,
                        "level": authority.level.value,
                    },
                )
            )
            return issues

        actual_source = authority.to_source_authority()
        if actual_source != expected:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.HIERARCHY_MISMATCH,
                    message=(
                        f"Authority '{authority.id}' level {authority.level.value} "
                        f"maps to {expected.value} but to_source_authority() "
                        f"returns {actual_source.value}"
                    ),
                    severity=ValidationSeverity.MEDIUM,
                    field_path="level",
                    details={
                        "authority_id": authority.id,
                        "level": authority.level.value,
                        "expected_source": expected.value,
                        "actual_source": actual_source.value,
                    },
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Part 4 — Secondary Source Referencing
    # ------------------------------------------------------------------

    def _check_secondary_referencing(
        self, citation: CitationRecord
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if self._registry is None:
            return issues

        if citation.authority_id is None:
            return issues

        if citation.authority_id not in self._registry:
            return issues

        try:
            authority = self._registry.get_by_id(citation.authority_id)
        except KeyError:
            return issues

        if not authority.enabled:
            return issues

        authority_source = authority.to_source_authority()

        if authority_source == SourceAuthority.PRIMARY:
            return issues

        jurisdiction = authority.jurisdiction
        same_jurisdiction = self._registry.get_by_jurisdiction(jurisdiction)

        has_primary = any(
            a.enabled
            and a.level in PRIMARY_LEVELS
            for a in same_jurisdiction
            if a.id != authority.id
        )

        if not has_primary and authority_source == SourceAuthority.SECONDARY:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.ORPHAN_SECONDARY_SOURCE,
                    message=(
                        f"Secondary authority '{authority.id}' in jurisdiction "
                        f"'{jurisdiction}' has no supporting primary authority"
                    ),
                    severity=ValidationSeverity.MEDIUM,
                    field_path="authority_id",
                    details={
                        "authority_id": authority.id,
                        "jurisdiction": jurisdiction,
                        "authority_source": authority_source.value,
                    },
                )
            )

        if not has_primary and authority_source == SourceAuthority.TERTIARY:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.ORPHAN_SECONDARY_SOURCE,
                    message=(
                        f"Tertiary authority '{authority.id}' in jurisdiction "
                        f"'{jurisdiction}' has no supporting primary authority"
                    ),
                    severity=ValidationSeverity.LOW,
                    field_path="authority_id",
                    details={
                        "authority_id": authority.id,
                        "jurisdiction": jurisdiction,
                        "authority_source": authority_source.value,
                    },
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Part 5 — Citation Density Validation
    # ------------------------------------------------------------------

    def _check_citation_density(
        self,
        all_citations: list[CitationRecord],
        source_governance: SourceGovernanceRecord,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        total = len(all_citations)
        primary_count = len(source_governance.primary_citations)

        if total < self._min_citations_per_entry:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INSUFFICIENT_CITATIONS,
                    message=(
                        f"Total citations ({total}) below minimum "
                        f"({self._min_citations_per_entry})"
                    ),
                    severity=ValidationSeverity.HIGH,
                    field_path="source_governance",
                    details={
                        "total": total,
                        "minimum": self._min_citations_per_entry,
                    },
                )
            )

        if primary_count < self._min_primary_citations:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INSUFFICIENT_CITATIONS,
                    message=(
                        f"Primary citations ({primary_count}) below minimum "
                        f"({self._min_primary_citations})"
                    ),
                    severity=ValidationSeverity.HIGH,
                    field_path="source_governance.primary_citations",
                    details={
                        "primary_count": primary_count,
                        "minimum": self._min_primary_citations,
                    },
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Part 6 — Minimum Evidence Requirements
    # ------------------------------------------------------------------

    def _check_minimum_evidence(
        self, source_governance: SourceGovernanceRecord
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        all_citations = (
            source_governance.primary_citations
            + source_governance.secondary_citations
            + source_governance.tertiary_citations
        )

        if not all_citations:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_SOURCE_GOVERNANCE,
                    message="No citations found in governance record",
                    severity=ValidationSeverity.HIGH,
                    field_path="source_governance",
                )
            )
            return issues

        if not source_governance.primary_citations:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INSUFFICIENT_AUTHORITY_COVERAGE,
                    message=(
                        "No primary authority citations found; "
                        "at least one PRIMARY source required"
                    ),
                    severity=ValidationSeverity.HIGH,
                    field_path="source_governance.primary_citations",
                    details={
                        "secondary_count": len(
                            source_governance.secondary_citations
                        ),
                        "tertiary_count": len(
                            source_governance.tertiary_citations
                        ),
                    },
                )
            )

        if self._registry is not None:
            unique_authority_ids = {
                c.authority_id
                for c in all_citations
                if c.authority_id
            }
            enabled_count = 0
            for aid in unique_authority_ids:
                if aid in self._registry:
                    try:
                        auth = self._registry.get_by_id(aid)
                        if auth.enabled:
                            enabled_count += 1
                    except KeyError:
                        pass

            if enabled_count == 0 and unique_authority_ids:
                issues.append(
                    ValidationIssue(
                        code=ValidationCode.INSUFFICIENT_AUTHORITY_COVERAGE,
                        message=(
                            "No enabled authorities found among citation "
                            "references"
                        ),
                        severity=ValidationSeverity.MEDIUM,
                        field_path="source_governance",
                        details={
                            "unique_authority_ids": len(unique_authority_ids),
                            "enabled_count": enabled_count,
                        },
                    )
                )

        return issues

    # ------------------------------------------------------------------
    # Part 7 — Duplicate Authority Detection
    # ------------------------------------------------------------------

    def _check_duplicate_authorities(
        self,
        citations: list[CitationRecord],
        context: ValidationContext | None = None,
    ) -> ValidationResult | None:
        if len(citations) < 2:
            return None

        started_at = datetime.utcnow()
        issues: list[ValidationIssue] = []
        seen: dict[str, list[int]] = {}

        for idx, citation in enumerate(citations):
            if citation.authority_id and citation.authority_id.strip():
                if citation.authority_id in seen:
                    seen[citation.authority_id].append(idx)
                else:
                    seen[citation.authority_id] = [idx]

        for authority_id, indices in seen.items():
            if len(indices) > 1:
                issues.append(
                    ValidationIssue(
                        code=ValidationCode.DUPLICATE_AUTHORITY_REFERENCE,
                        message=(
                            f"Authority '{authority_id}' referenced "
                            f"{len(indices)} times across citations"
                        ),
                        severity=ValidationSeverity.LOW,
                        field_path="authority_id",
                        details={
                            "authority_id": authority_id,
                            "citation_indices": indices,
                            "reference_count": len(indices),
                        },
                    )
                )

        if not issues:
            return None

        completed_at = datetime.utcnow()
        status = self._compute_status(issues)

        return ValidationResult(
            status=status,
            validator_name=f"{self._validator_name}.duplicates",
            issues=issues,
            context=context or ValidationContext(
                context_type="duplicate_authority_detection"
            ),
            started_at=started_at,
            completed_at=completed_at,
            metadata={"citation_count": len(citations)},
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_status(issues: list[ValidationIssue]) -> ValidationStatus:
        if not issues:
            return ValidationStatus.SUCCESS
        severities = {i.severity for i in issues}
        if (
            ValidationSeverity.HIGH in severities
            or ValidationSeverity.CRITICAL in severities
        ):
            return ValidationStatus.FAILED
        if (
            ValidationSeverity.MEDIUM in severities
            or ValidationSeverity.LOW in severities
        ):
            return ValidationStatus.WARNING
        return ValidationStatus.SUCCESS
