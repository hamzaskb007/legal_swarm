from __future__ import annotations
from src.schema.schema import (
    RegulatoryEntry, ValidationReport, ValidationResult, ValidationStatus,
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
                rule_id=self.rule_id, rule_description=self.rule_description,
                status=ValidationStatus.FAILED, field_path="primary_regulator",
                message="primary_regulator is empty",
            )
        return ValidationResult(
            rule_id=self.rule_id, rule_description=self.rule_description,
            status=ValidationStatus.PASSED, field_path="primary_regulator",
        )


class HasAtLeastOneFundStructureRule(ValidationRule):
    rule_id = "VAL_002"
    rule_description = "Entry must define at least one permitted fund structure"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.permitted_fund_structures:
            return ValidationResult(
                rule_id=self.rule_id, rule_description=self.rule_description,
                status=ValidationStatus.WARNING, field_path="permitted_fund_structures",
                message="No fund structures defined; may be incomplete",
            )
        return ValidationResult(
            rule_id=self.rule_id, rule_description=self.rule_description,
            status=ValidationStatus.PASSED, field_path="permitted_fund_structures",
        )


class ConfidenceThresholdRule(ValidationRule):
    rule_id = "VAL_003"
    rule_description = "Confidence score must be >= 0.4 for non-UNVERIFIED entries"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        from src.schema.schema import ConfidenceLevel
        if entry.confidence.score < 0.4 and entry.confidence.level != ConfidenceLevel.UNVERIFIED:
            return ValidationResult(
                rule_id=self.rule_id, rule_description=self.rule_description,
                status=ValidationStatus.FAILED, field_path="confidence.score",
                message=f"Score {entry.confidence.score} below minimum threshold of 0.4",
            )
        return ValidationResult(
            rule_id=self.rule_id, rule_description=self.rule_description,
            status=ValidationStatus.PASSED, field_path="confidence.score",
        )


class HasSourceCitationsRule(ValidationRule):
    rule_id = "VAL_004"
    rule_description = "Entry must have at least one primary citation"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.source_governance.primary_citations:
            return ValidationResult(
                rule_id=self.rule_id, rule_description=self.rule_description,
                status=ValidationStatus.FAILED, field_path="source_governance.primary_citations",
                message="No primary citations found",
            )
        return ValidationResult(
            rule_id=self.rule_id, rule_description=self.rule_description,
            status=ValidationStatus.PASSED, field_path="source_governance.primary_citations",
        )


class FilingObligationsRule(ValidationRule):
    rule_id = "VAL_005"
    rule_description = "Entry should define filing obligations"

    def check(self, entry: RegulatoryEntry) -> ValidationResult:
        if not entry.filing_obligations:
            return ValidationResult(
                rule_id=self.rule_id, rule_description=self.rule_description,
                status=ValidationStatus.WARNING, field_path="filing_obligations",
                message="No filing obligations defined; may be incomplete",
            )
        return ValidationResult(
            rule_id=self.rule_id, rule_description=self.rule_description,
            status=ValidationStatus.PASSED, field_path="filing_obligations",
        )


DEFAULT_RULES: list[ValidationRule] = [
    HasPrimaryRegulatorRule(),
    HasAtLeastOneFundStructureRule(),
    ConfidenceThresholdRule(),
    HasSourceCitationsRule(),
    FilingObligationsRule(),
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