from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from src.authority.models import Authority, AuthorityLevel, RelationshipType
from src.authority.registry import AuthorityRegistry
from src.schema.schema import SourceAuthority
from src.validation.enums import ValidationCode, ValidationSeverity, ValidationStatus
from src.validation.exceptions import ValidationConfigurationError
from src.validation.models import ValidationContext, ValidationIssue, ValidationResult

if TYPE_CHECKING:
    from src.schema.schema import CitationRecord, SourceGovernanceRecord

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
     7. Level 4-5 reference requirement — every Level 4 or 5 citation must
        reference a Level 1-3 source
     8. Citation density by category — per-regulatory-category minimum counts
     9. Independent citations — no duplicate citations within a category
    10. Authoritative citation for compliance — Compliance Obligations must
        include at least one PRIMARY source

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
        category_density_requirements: dict[str, int] | None = None,
        compliance_requires_authoritative: bool = True,
    ) -> None:
        if not validator_name or not validator_name.strip():
            raise ValidationConfigurationError("validator_name must not be empty")
        if min_citations_per_entry < 0:
            raise ValidationConfigurationError("min_citations_per_entry must be >= 0")
        if min_primary_citations < 0:
            raise ValidationConfigurationError("min_primary_citations must be >= 0")
        self._registry = authority_registry
        self._validator_name = validator_name
        self._min_citations_per_entry = min_citations_per_entry
        self._min_primary_citations = min_primary_citations
        self._category_density_requirements = dict(category_density_requirements or {})
        for tag, count in self._category_density_requirements.items():
            if count < 0:
                raise ValidationConfigurationError(
                    f"category_density_requirements[{tag!r}] must be >= 0, got {count}"
                )
        self._compliance_requires_authoritative = compliance_requires_authoritative

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
        issues.extend(self._check_level_45_references_single(citation))

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
        issues.extend(self._check_level_45_references_governance(source_governance))
        issues.extend(self._check_citation_density_by_category(source_governance))
        issues.extend(self._check_independent_citations(source_governance))
        issues.extend(self._check_authoritative_compliance(source_governance))

        completed_at = datetime.utcnow()
        status = self._compute_status(issues)

        all_authority_ids = [c.authority_id for c in all_citations if c.authority_id]

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

    def _check_level_enforcement(self, authority: Authority) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        expected = AUTHORITY_LEVEL_MAP.get(authority.level)
        if expected is None:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_AUTHORITY_LEVEL,
                    message=(
                        f"Authority '{authority.id}' has unrecognised level {authority.level.value}"
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

    def _check_secondary_referencing(self, citation: CitationRecord) -> list[ValidationIssue]:
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
            a.enabled and a.level in PRIMARY_LEVELS
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
                        f"Total citations ({total}) below minimum ({self._min_citations_per_entry})"
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
                        "No primary authority citations found; at least one PRIMARY source required"
                    ),
                    severity=ValidationSeverity.HIGH,
                    field_path="source_governance.primary_citations",
                    details={
                        "secondary_count": len(source_governance.secondary_citations),
                        "tertiary_count": len(source_governance.tertiary_citations),
                    },
                )
            )

        if self._registry is not None:
            unique_authority_ids = {c.authority_id for c in all_citations if c.authority_id}
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
                        message=("No enabled authorities found among citation references"),
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
            context=context or ValidationContext(context_type="duplicate_authority_detection"),
            started_at=started_at,
            completed_at=completed_at,
            metadata={"citation_count": len(citations)},
        )

    # ------------------------------------------------------------------
    # Part 8 — Level 4-5 Single Citation Reference Validation
    # ------------------------------------------------------------------

    def _check_level_45_references_single(self, citation: CitationRecord) -> list[ValidationIssue]:
        """Check that a Level 4 or 5 citation references a Level 1-3 source.

        Uses two mechanisms:
        1. ``references_citation_id`` on the CitationRecord (direct citation ref)
        2. Authority ``REFERENCES`` relationship chain via the registry
        """
        issues: list[ValidationIssue] = []

        if citation.authority_level < 4:
            return issues

        if citation.references_citation_id is not None:
            return issues

        if self._registry is not None and citation.authority_id is not None:
            if citation.authority_id in self._registry:
                try:
                    authority = self._registry.get_by_id(citation.authority_id)
                    for rel in authority.relationships:
                        if rel.type == RelationshipType.REFERENCES:
                            try:
                                target = self._registry.get_by_id(rel.target_id)
                                if target.level in PRIMARY_LEVELS:
                                    return issues
                            except KeyError:
                                continue
                except KeyError:
                    pass

        issues.append(
            ValidationIssue(
                code=ValidationCode.LEVEL45_MISSING_REFERENCE,
                message=(
                    f"Level {citation.authority_level} citation "
                    f"'{citation.citation_id}' does not reference "
                    f"a Level 1-3 source"
                ),
                severity=ValidationSeverity.HIGH,
                field_path="references_citation_id",
                details={
                    "citation_id": str(citation.citation_id),
                    "authority_level": citation.authority_level,
                    "authority_id": citation.authority_id or "",
                },
            )
        )
        return issues

    # ------------------------------------------------------------------
    # Part 9 — Governance-Level Level 4-5 Reference Validation
    # ------------------------------------------------------------------

    def _check_level_45_references_governance(
        self, source_governance: SourceGovernanceRecord
    ) -> list[ValidationIssue]:
        """Cross-reference check across all citations in a governance record."""
        issues: list[ValidationIssue] = []
        all_citations = (
            source_governance.primary_citations
            + source_governance.secondary_citations
            + source_governance.tertiary_citations
        )

        level_45_citations = [c for c in all_citations if c.authority_level >= 4]
        level_13_ids = {c.citation_id for c in all_citations if c.authority_level <= 3}

        for citation in level_45_citations:
            if citation.references_citation_id is not None:
                if citation.references_citation_id in level_13_ids:
                    continue

            if self._registry is not None and citation.authority_id is not None:
                if citation.authority_id in self._registry:
                    try:
                        authority = self._registry.get_by_id(citation.authority_id)
                        for rel in authority.relationships:
                            if rel.type == RelationshipType.REFERENCES:
                                try:
                                    target = self._registry.get_by_id(rel.target_id)
                                    if target.level in PRIMARY_LEVELS:
                                        continue
                                except KeyError:
                                    continue
                    except KeyError:
                        pass

            issues.append(
                ValidationIssue(
                    code=ValidationCode.LEVEL45_MISSING_REFERENCE,
                    message=(
                        f"Level {citation.authority_level} citation "
                        f"'{citation.citation_id}' does not reference "
                        f"a Level 1-3 source"
                    ),
                    severity=ValidationSeverity.HIGH,
                    field_path="references_citation_id",
                    details={
                        "citation_id": str(citation.citation_id),
                        "authority_level": citation.authority_level,
                        "authority_id": citation.authority_id or "",
                    },
                )
            )

        return issues

    # ------------------------------------------------------------------
    # Part 10 — Citation Density by Category
    # ------------------------------------------------------------------

    CATEGORY_REGULATORY_FRAMEWORK = "Regulatory Framework"
    CATEGORY_CAPITAL_REQUIREMENTS = "Capital Requirements"
    CATEGORY_TAX_CLAIMS = "Tax Claims"
    CATEGORY_COMPLIANCE_OBLIGATIONS = "Compliance Obligations"

    def _check_citation_density_by_category(
        self, source_governance: SourceGovernanceRecord
    ) -> list[ValidationIssue]:
        """Validate minimum citation counts per regulatory category."""
        issues: list[ValidationIssue] = []
        all_citations = (
            source_governance.primary_citations
            + source_governance.secondary_citations
            + source_governance.tertiary_citations
        )

        by_tag: dict[str, list[CitationRecord]] = {}
        for c in all_citations:
            tag = c.regulatory_relevance_tag
            if tag not in by_tag:
                by_tag[tag] = []
            by_tag[tag].append(c)

        for tag, required in self._category_density_requirements.items():
            actual = len(by_tag.get(tag, []))
            if actual < required:
                issues.append(
                    ValidationIssue(
                        code=ValidationCode.INSUFFICIENT_CITATION_DENSITY,
                        message=(
                            f"Category '{tag}' has {actual} citation(s), "
                            f"minimum {required} required"
                        ),
                        severity=ValidationSeverity.HIGH,
                        field_path="source_governance",
                        details={
                            "category": tag,
                            "actual": actual,
                            "required": required,
                        },
                    )
                )

        return issues

    # ------------------------------------------------------------------
    # Part 11 — Independent Citation Detection
    # ------------------------------------------------------------------

    def _check_independent_citations(
        self, source_governance: SourceGovernanceRecord
    ) -> list[ValidationIssue]:
        """Detect non-independent (duplicate) citations within each category.

        A citation is considered a duplicate (dependent) if another citation
        in the same category shares the same:
        - ``citation_id``
        - ``source_url``
        - ``source_name``
        """
        issues: list[ValidationIssue] = []
        all_citations = (
            source_governance.primary_citations
            + source_governance.secondary_citations
            + source_governance.tertiary_citations
        )

        if not self._category_density_requirements:
            return issues

        by_tag: dict[str, list[CitationRecord]] = {}
        for c in all_citations:
            tag = c.regulatory_relevance_tag
            if tag not in self._category_density_requirements:
                continue
            if tag not in by_tag:
                by_tag[tag] = []
            by_tag[tag].append(c)

        for tag, citations in by_tag.items():
            seen_ids: set[UUID] = set()
            seen_urls: set[str] = set()
            seen_names: set[str] = set()

            for c in citations:
                dup_reasons: list[str] = []
                if c.citation_id in seen_ids:
                    dup_reasons.append("duplicate citation_id")
                if c.source_url in seen_urls:
                    dup_reasons.append("duplicate source_url")
                if c.source_name in seen_names:
                    dup_reasons.append("duplicate source_name")

                if dup_reasons:
                    issues.append(
                        ValidationIssue(
                            code=ValidationCode.DEPENDENT_CITATION,
                            message=(
                                f"Citation '{c.citation_id}' in category "
                                f"'{tag}' is not independent: "
                                f"{'; '.join(dup_reasons)}"
                            ),
                            severity=ValidationSeverity.MEDIUM,
                            field_path="source_governance",
                            details={
                                "citation_id": str(c.citation_id),
                                "category": tag,
                                "reasons": dup_reasons,
                                "source_url": c.source_url,
                                "source_name": c.source_name,
                            },
                        )
                    )

                seen_ids.add(c.citation_id)
                seen_urls.add(c.source_url)
                seen_names.add(c.source_name)

        return issues

    # ------------------------------------------------------------------
    # Part 12 — Authoritative Citation for Compliance Obligations
    # ------------------------------------------------------------------

    def _check_authoritative_compliance(
        self, source_governance: SourceGovernanceRecord
    ) -> list[ValidationIssue]:
        """Ensure Compliance Obligations citations include at least one
        authoritative (PRIMARY) source."""
        issues: list[ValidationIssue] = []

        if not self._compliance_requires_authoritative:
            return issues

        all_citations = (
            source_governance.primary_citations
            + source_governance.secondary_citations
            + source_governance.tertiary_citations
        )

        compliance_citations = [
            c
            for c in all_citations
            if c.regulatory_relevance_tag == self.CATEGORY_COMPLIANCE_OBLIGATIONS
        ]

        if not compliance_citations:
            return issues

        has_authoritative = any(
            c.authority == SourceAuthority.PRIMARY for c in compliance_citations
        )

        if not has_authoritative:
            primary_count = sum(
                1 for c in compliance_citations if c.authority == SourceAuthority.PRIMARY
            )
            issues.append(
                ValidationIssue(
                    code=ValidationCode.INSUFFICIENT_CITATION_DENSITY,
                    message=(
                        "Compliance Obligations citations must include at least "
                        "one authoritative (PRIMARY) source"
                    ),
                    severity=ValidationSeverity.HIGH,
                    field_path="source_governance",
                    details={
                        "category": self.CATEGORY_COMPLIANCE_OBLIGATIONS,
                        "compliance_citations_count": len(compliance_citations),
                        "primary_citations_count": primary_count,
                    },
                )
            )

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
