from __future__ import annotations
from src.schema.schema import (
    RegulatoryEntry,
    ValidationReport,
    ValidationResult,
    ValidationStatus,
)


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


class SilentNullProhibitionRule(ValidationRule):
    rule_id = "VAL_018"
    rule_description = "Critical fields must not be silently None"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        results: list[ValidationResult] = []
        for field_name in ("tax_summary", "aml_kyc_framework", "passporting_notes"):
            if getattr(entry, field_name, None) is None:
                results.append(
                    ValidationResult(
                        rule_id=self.rule_id,
                        rule_description=self.rule_description,
                        status=ValidationStatus.WARNING,
                        field_path=field_name,
                        message="Field is None — populate or use explicit Not Applicable string",
                    )
                )
        if results:
            return results[0]
        return ValidationResult(
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            status=ValidationStatus.PASSED,
            field_path="tax_summary",
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
    SilentNullProhibitionRule(),
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
