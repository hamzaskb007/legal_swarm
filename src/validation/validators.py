from __future__ import annotations

from urllib.parse import urlparse
from uuid import UUID

from src.schema.schema import CitationRecord, RegulatoryEntry, SourceAuthority
from src.validation.models import ValidationReport, ValidationResult
from src.validation.enums import ValidationStatus


class ValidationRule:
    rule_id: str = "BASE"
    rule_description: str = "Base rule"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        raise NotImplementedError


class HasPrimaryRegulatorRule(ValidationRule):
    rule_id = "VAL_001"
    rule_description = "Entry must have a primary regulator defined"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.primary_regulator.strip():
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.FAILED,
                field_path="primary_regulator",
                message="primary_regulator is empty",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="primary_regulator",
        )


class HasAtLeastOneFundStructureRule(ValidationRule):
    rule_id = "VAL_002"
    rule_description = "Entry must define at least one permitted fund structure"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.permitted_fund_structures:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="permitted_fund_structures",
                message="No fund structures defined; may be incomplete",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="permitted_fund_structures",
        )


class ConfidenceThresholdRule(ValidationRule):
    rule_id = "VAL_003"
    rule_description = "Confidence score must be >= 0.4 for non-UNVERIFIED entries"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        from src.schema.schema import ConfidenceLevel

        if entry.confidence.score < 0.4 and entry.confidence.level != ConfidenceLevel.UNVERIFIED:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.FAILED,
                field_path="confidence.score",
                message=f"Score {entry.confidence.score} below minimum threshold of 0.4",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="confidence.score",
        )


class HasSourceCitationsRule(ValidationRule):
    rule_id = "VAL_004"
    rule_description = "Entry must have at least one primary citation"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.source_governance.primary_citations:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.FAILED,
                field_path="source_governance.primary_citations",
                message="No primary citations found",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="source_governance.primary_citations",
        )


class FilingObligationsRule(ValidationRule):
    rule_id = "VAL_005"
    rule_description = "Entry should define filing obligations"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.filing_obligations:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="filing_obligations",
                message="No filing obligations defined; may be incomplete",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="filing_obligations",
        )


class LicensingRequirementsRule(ValidationRule):
    rule_id = "VAL_006"
    rule_description = "licensing_requirements must not be None or empty"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.licensing_requirements:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="licensing_requirements",
                message="licensing_requirements is None or empty",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="licensing_requirements",
        )


class SubstanceRequirementsRule(ValidationRule):
    rule_id = "VAL_007"
    rule_description = "substance_requirements must not be None"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if entry.substance_requirements is None:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="substance_requirements",
                message="substance_requirements is None",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="substance_requirements",
        )


class RegulatoryTimelinesRule(ValidationRule):
    rule_id = "VAL_008"
    rule_description = "regulatory_timelines must not be None or empty"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.regulatory_timelines:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="regulatory_timelines",
                message="regulatory_timelines is None or empty",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="regulatory_timelines",
        )


class RegulatoryCostsRule(ValidationRule):
    rule_id = "VAL_009"
    rule_description = "regulatory_costs must not be None or empty"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.regulatory_costs:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="regulatory_costs",
                message="regulatory_costs is None or empty",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="regulatory_costs",
        )


class PenaltyExposureRule(ValidationRule):
    rule_id = "VAL_010"
    rule_description = "penalty_exposure must not be None or empty"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.penalty_exposure:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="penalty_exposure",
                message="penalty_exposure is None or empty",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="penalty_exposure",
        )


class WindDownProcedureRule(ValidationRule):
    rule_id = "VAL_011"
    rule_description = "wind_down_procedure must not be None"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if entry.wind_down_procedure is None:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="wind_down_procedure",
                message="wind_down_procedure is None",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="wind_down_procedure",
        )


class FundManagerRequirementsRule(ValidationRule):
    rule_id = "VAL_012"
    rule_description = "fund_manager_requirements must not be None"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if entry.fund_manager_requirements is None:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="fund_manager_requirements",
                message="fund_manager_requirements is None",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="fund_manager_requirements",
        )


class BeneficialOwnershipRulesRule(ValidationRule):
    rule_id = "VAL_013"
    rule_description = "beneficial_ownership_rules must not be None"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if entry.beneficial_ownership_rules is None:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="beneficial_ownership_rules",
                message="beneficial_ownership_rules is None",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="beneficial_ownership_rules",
        )


class RecordRetentionPoliciesRule(ValidationRule):
    rule_id = "VAL_014"
    rule_description = "record_retention_policies must not be None or empty"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.record_retention_policies:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="record_retention_policies",
                message="record_retention_policies is None or empty",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="record_retention_policies",
        )


class MinimumPrimaryCitationsRule(ValidationRule):
    rule_id = "VAL_015"
    rule_description = "Entry must have at least 2 primary citations (SRS Section 5.3)"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        count = len(entry.source_governance.primary_citations)
        if count < 2:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.FAILED,
                field_path="source_governance.primary_citations",
                message="Minimum 2 primary citations required per SRS Section 5.3",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="source_governance.primary_citations",
        )


class TaxCitationForTaxSummaryRule(ValidationRule):
    rule_id = "VAL_016"
    rule_description = "Tax summary must be backed by a Tax Framework citation"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if entry.tax_summary is None:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.PASSED,
                field_path="source_governance",
            )
        all_citations = (
            entry.source_governance.primary_citations
            + entry.source_governance.secondary_citations
            + entry.source_governance.tertiary_citations
        )
        has_tax_tag = any(
            getattr(c, "regulatory_relevance_tag", None) == "Tax Framework" for c in all_citations
        )
        if not has_tax_tag:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="source_governance",
                message="Tax summary present but no Tax Framework citation found",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="source_governance",
        )


class CapitalCitationForCapitalRequirementsRule(ValidationRule):
    rule_id = "VAL_017"
    rule_description = "Capital requirements must be backed by a Capital Requirements citation"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        has_capital = any(
            fs.min_capital is not None
            and fs.min_capital.amount is not None
            and fs.min_capital.amount > 0
            for fs in entry.permitted_fund_structures
        )
        if not has_capital:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.PASSED,
                field_path="source_governance",
            )
        all_citations = (
            entry.source_governance.primary_citations
            + entry.source_governance.secondary_citations
            + entry.source_governance.tertiary_citations
        )
        has_capital_tag = any(
            getattr(c, "regulatory_relevance_tag", None) == "Capital Requirements"
            for c in all_citations
        )
        if not has_capital_tag:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.WARNING,
                field_path="source_governance",
                message="Capital requirements present but no Capital Requirements citation found",
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="source_governance",
        )


def _normalize_url(url: str) -> str:
    """Normalize a URL for deterministic deduplication.

    Strips trailing slashes from the path and lowercases the scheme+netloc+path.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.lower().rstrip("/")
    query = parsed.query
    fragment = parsed.fragment
    result = f"{scheme}://{netloc}{path}"
    if query:
        result += f"?{query}"
    if fragment:
        result += f"#{fragment}"
    return result


_DEFAULT_DENSITY_REQUIREMENTS: dict[str, int] = {
    "Regulatory Framework": 2,
    "Capital Requirements": 2,
    "Tax Framework": 2,
    "Compliance Obligations": 1,
}


class CitationDensityRule(ValidationRule):
    rule_id = "VAL_018"
    rule_description = (
        "Entry must meet minimum citation counts per regulatory category (SRS §5.3)"
    )

    def __init__(
        self,
        requirements: dict[str, int] | None = None,
    ) -> None:
        self.requirements = dict(requirements) if requirements is not None else dict(
            _DEFAULT_DENSITY_REQUIREMENTS
        )

    @staticmethod
    def _independent_count(citations: list[CitationRecord]) -> int:
        """Count independent citations by deduplicating on citation_id and
        normalized source_url."""
        seen_ids: set[UUID] = set()
        seen_urls: set[str] = set()
        count = 0
        for c in citations:
            if c.citation_id in seen_ids:
                continue
            if c.source_url:
                norm = _normalize_url(c.source_url)
                if norm in seen_urls:
                    continue
                seen_urls.add(norm)
            seen_ids.add(c.citation_id)
            count += 1
        return count

    @staticmethod
    def _category_is_present(tag: str, entry: RegulatoryEntry) -> bool:
        """Determine whether a regulatory category is present in the entry.

        A category is considered present when the entry contains a field
        or structure that gives rise to a requirement in that area.
        """
        if tag == "Regulatory Framework":
            return True
        if tag == "Capital Requirements":
            return any(
                fs.min_capital is not None
                and fs.min_capital.amount is not None
                and fs.min_capital.amount > 0
                for fs in entry.permitted_fund_structures
            )
        if tag == "Tax Framework":
            return entry.tax_summary is not None
        if tag == "Compliance Obligations":
            return True
        return False

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        all_citations = (
            list(entry.source_governance.primary_citations)
            + list(entry.source_governance.secondary_citations)
            + list(entry.source_governance.tertiary_citations)
        )

        failures: list[str] = []

        for tag, required in self.requirements.items():
            if not self._category_is_present(tag, entry):
                continue

            tagged = [c for c in all_citations if c.regulatory_relevance_tag == tag]

            if tag == "Regulatory Framework":
                actual = self._independent_count(tagged)
            else:
                actual = len(tagged)

            if actual < required:
                failures.append(
                    f"Category '{tag}' has {actual} independent citation(s), "
                    f"minimum {required} required"
                )
                continue

            if tag == "Compliance Obligations":
                authoritative = any(
                    c.authority == SourceAuthority.PRIMARY for c in tagged
                )
                if not authoritative:
                    failures.append(
                        "Compliance Obligations citations must include at least "
                        "one authoritative (PRIMARY) source"
                    )

        if failures:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.FAILED,
                field_path="source_governance",
                message="; ".join(failures),
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="source_governance",
        )


class Level45ReferenceRule(ValidationRule):
    rule_id = "VAL_019"
    rule_description = "Level 4/5 citations must reference Level 1-3 sources"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        all_citations = (
            list(entry.source_governance.primary_citations)
            + list(entry.source_governance.secondary_citations)
            + list(entry.source_governance.tertiary_citations)
        )

        level_by_id: dict[UUID, int] = {}
        for c in all_citations:
            level_by_id[c.citation_id] = c.authority_level

        for citation in all_citations:
            if citation.authority_level < 4:
                continue

            ref_id = citation.references_citation_id
            if ref_id is None:
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_description=self.rule_description,
                    status=ValidationStatus.FAILED,
                    field_path="source_governance",
                    message=(
                        f"Level {citation.authority_level} citation "
                        f"'{citation.citation_id}' does not reference "
                        f"a Level 1-3 source"
                    ),
                )

            target_level = level_by_id.get(ref_id)
            if target_level is None:
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_description=self.rule_description,
                    status=ValidationStatus.FAILED,
                    field_path="source_governance",
                    message=(
                        f"Level {citation.authority_level} citation "
                        f"'{citation.citation_id}' references nonexistent "
                        f"citation '{ref_id}'"
                    ),
                )

            if target_level > 3:
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_description=self.rule_description,
                    status=ValidationStatus.FAILED,
                    field_path="source_governance",
                    message=(
                        f"Level {citation.authority_level} citation "
                        f"'{citation.citation_id}' references Level {target_level} "
                        f"citation '{ref_id}' — must reference Level 1-3"
                    ),
                )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="source_governance",
        )


class AuthorityConsistencyRule(ValidationRule):
    rule_id = "VAL_020"
    rule_description = "Citation authority and authority_level must be consistent"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        all_citations = (
            list(entry.source_governance.primary_citations)
            + list(entry.source_governance.secondary_citations)
            + list(entry.source_governance.tertiary_citations)
        )

        level_to_authority = {
            1: SourceAuthority.PRIMARY,
            2: SourceAuthority.PRIMARY,
            3: SourceAuthority.PRIMARY,
            4: SourceAuthority.SECONDARY,
            5: SourceAuthority.TERTIARY,
        }

        messages: list[str] = []
        for c in all_citations:
            expected = level_to_authority.get(c.authority_level)
            if expected is not None and c.authority != expected:
                messages.append(
                    f"Citation '{c.citation_id}' has authority={c.authority.value} "
                    f"and authority_level={c.authority_level}"
                )

        if messages:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_description=self.rule_description,
                status=ValidationStatus.FAILED,
                field_path="source_governance",
                message="; ".join(messages),
            )
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="source_governance",
        )


DEFAULT_RULES: list[ValidationRule] = [
    HasPrimaryRegulatorRule(),
    HasAtLeastOneFundStructureRule(),
    ConfidenceThresholdRule(),
    HasSourceCitationsRule(),
    FilingObligationsRule(),
    LicensingRequirementsRule(),
    SubstanceRequirementsRule(),
    RegulatoryTimelinesRule(),
    RegulatoryCostsRule(),
    PenaltyExposureRule(),
    WindDownProcedureRule(),
    FundManagerRequirementsRule(),
    BeneficialOwnershipRulesRule(),
    RecordRetentionPoliciesRule(),
    MinimumPrimaryCitationsRule(),
    TaxCitationForTaxSummaryRule(),
    CapitalCitationForCapitalRequirementsRule(),
    CitationDensityRule(),
    Level45ReferenceRule(),
    AuthorityConsistencyRule(),
]


class ValidationEngine:
    def __init__(self, rules: list[ValidationRule] | None = None, schema_version: str = "1.0.0"):
        self.rules = rules if rules is not None else DEFAULT_RULES
        self.schema_version = schema_version

    def validate(self, entry: RegulatoryEntry) -> ValidationReport:
        results = [rule.check(entry) for rule in self.rules]
        return ValidationReport(
            entry_id=entry.entry_id,
            jurisdiction_code=entry.jurisdiction_code,
            results=results,
            schema_version=self.schema_version,
        )

    def add_rule(self, rule: ValidationRule) -> None:
        self.rules.append(rule)
