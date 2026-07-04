from __future__ import annotations
from typing import Any
from src.schema.schema import CitationRecord, ContradictionRecord, RegulatoryEntry


def _get_nested(obj: Any, path: str) -> Any:
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


class CitationContradictionDetector:
    def detect(self, entry: RegulatoryEntry) -> list[ContradictionRecord]:
        contradictions: list[ContradictionRecord] = []
        primary_scores = [c.reliability_score for c in entry.source_governance.primary_citations]
        if not primary_scores:
            return contradictions
        max_primary_score = max(primary_scores)
        for citation in (entry.source_governance.secondary_citations + entry.source_governance.tertiary_citations):
            if citation.reliability_score > max_primary_score:
                primary_citation = max(entry.source_governance.primary_citations, key=lambda c: c.reliability_score)
                contradictions.append(ContradictionRecord(
                    field_path="source_governance.reliability_score",
                    source_a=primary_citation,
                    source_b=citation,
                    value_a=str(max_primary_score),
                    value_b=str(citation.reliability_score),
                    resolution=None,
                    resolved=False,
                ))
        return contradictions


COMPARABLE_FIELDS = [
    "primary_regulator", "passporting_available", "withholding_tax_rate",
    "investor_requirements.qualified_investor_required", "investor_requirements.min_investment_usd",
    "substance_requirements.local_office_required",
    "substance_requirements.local_directors_required",
    "beneficial_ownership_rules.register_public",
    "beneficial_ownership_rules.threshold_percentage",
]


class CrossEntryContradictionDetector:
    def __init__(self, fields: list[str] | None = None) -> None:
        self.fields = fields or COMPARABLE_FIELDS

    def detect(
        self,
        entry_a: RegulatoryEntry,
        entry_b: RegulatoryEntry,
        source_a: CitationRecord,
        source_b: CitationRecord,
    ) -> list[ContradictionRecord]:
        contradictions: list[ContradictionRecord] = []
        for field_path in self.fields:
            val_a = _get_nested(entry_a, field_path)
            val_b = _get_nested(entry_b, field_path)
            if val_a is None or val_b is None:
                continue
            if str(val_a) != str(val_b):
                contradictions.append(ContradictionRecord(
                    field_path=field_path,
                    source_a=source_a,
                    source_b=source_b,
                    value_a=str(val_a),
                    value_b=str(val_b),
                    resolution=None,
                    resolved=False,
                ))
        return contradictions