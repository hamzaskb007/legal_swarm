from __future__ import annotations

from pathlib import Path
from typing import Any

from src.audit.logger import AuditLogger
from src.confidence.scorer import ConfidenceScorer
from src.contradiction.detector import (
    COMPARABLE_FIELDS,
    CitationContradictionDetector,
    CrossEntryContradictionDetector,
)
from src.jurisdictions.base import JurisdictionBuilder
from src.jurisdictions.tier1.cayman_islands import CaymanIslandsBuilder
from src.jurisdictions.tier1.luxembourg import LuxembourgBuilder
from src.jurisdictions.tier1.ireland import IrelandBuilder
from src.jurisdictions.tier1.singapore import SingaporeBuilder
from src.jurisdictions.tier1.bvi import BviBuilder
from src.jurisdictions.tier1.uae import UaeBuilder
from src.jurisdictions.tier1.jersey import JerseyBuilder
from src.jurisdictions.tier1.delaware import DelawareBuilder
from src.schema.schema import (
    AuditEventType,
    CrossJurisdictionComparison,
    JurisdictionComparisonField,
    RegulatoryEntry,
)
from src.validation.validators import ValidationEngine

_TIER1_BUILDERS: list[type[JurisdictionBuilder]] = [
    CaymanIslandsBuilder,
    LuxembourgBuilder,
    IrelandBuilder,
    SingaporeBuilder,
    BviBuilder,
    UaeBuilder,
    JerseyBuilder,
    DelawareBuilder,
]


class JurisdictionRegistry:
    """Central registry that holds all populated jurisdiction entries."""

    def __init__(self, *, audit_log_path: Path = Path("logs/audit.jsonl")) -> None:
        self._entries: dict[str, RegulatoryEntry] = {}
        self._validation_reports: dict[str, Any] = {}
        self._audit_logger = AuditLogger(log_path=audit_log_path)
        self._scorer = ConfidenceScorer()
        self._engine = ValidationEngine()
        self._detector = CitationContradictionDetector()
        self._load_all()

    def _run_pipeline(self, builder: JurisdictionBuilder) -> RegulatoryEntry:
        entry = builder.build_entry()
        entry = builder.run_pipeline(entry)
        return entry

    def _load_all(self) -> None:
        for builder_cls in _TIER1_BUILDERS:
            builder = builder_cls()
            entry = self._run_pipeline(builder)
            self._entries[entry.jurisdiction_code] = entry
            report = self._engine.validate(entry)
            self._validation_reports[entry.jurisdiction_code] = report

    def get_entry(self, jurisdiction_code: str) -> RegulatoryEntry:
        code = jurisdiction_code.upper().strip()
        entry = self._entries.get(code)
        if entry is None:
            self._audit_logger.log(
                event_type=AuditEventType.QUERY,
                actor="jurisdiction-registry",
                jurisdiction_code=code,
                outcome="NOT_FOUND",
            )
            raise KeyError(f"No entry found for jurisdiction code: {code!r}")
        self._audit_logger.log(
            event_type=AuditEventType.QUERY,
            actor="jurisdiction-registry",
            jurisdiction_code=code,
            entry_id=entry.entry_id,
            outcome="FOUND",
        )
        return entry

    def get_all(self) -> list[RegulatoryEntry]:
        entries = list(self._entries.values())
        self._audit_logger.log(
            event_type=AuditEventType.QUERY,
            actor="jurisdiction-registry",
            payload={"count": len(entries)},
            outcome="ALL_RETURNED",
        )
        return entries

    def compare(self, code_a: str, code_b: str) -> CrossJurisdictionComparison:
        entry_a = self.get_entry(code_a)
        entry_b = self.get_entry(code_b)

        detector = CrossEntryContradictionDetector(fields=COMPARABLE_FIELDS)
        cross_sources = _pick_citations(entry_a, entry_b)
        contradictions = detector.detect(
            entry_a, entry_b,
            source_a=cross_sources["source_a"],
            source_b=cross_sources["source_b"],
        )

        results: list[JurisdictionComparisonField] = []
        for field_path in COMPARABLE_FIELDS:
            val_a = _get_nested(entry_a, field_path)
            val_b = _get_nested(entry_b, field_path)
            if val_a is not None:
                results.append(JurisdictionComparisonField(
                    field_name=field_path,
                    jurisdiction_code=entry_a.jurisdiction_code,
                    value=str(val_a),
                    confidence=entry_a.confidence,
                ))
            if val_b is not None:
                results.append(JurisdictionComparisonField(
                    field_name=field_path,
                    jurisdiction_code=entry_b.jurisdiction_code,
                    value=str(val_b),
                    confidence=entry_b.confidence,
                ))

        comparison = CrossJurisdictionComparison(
            jurisdictions=[code_a, code_b],
            fields_compared=list(COMPARABLE_FIELDS),
            results=results,
            contradictions_detected=contradictions,
            summary=f"Compared {entry_a.jurisdiction_name} vs {entry_b.jurisdiction_name}: "
                    f"{len(contradictions)} contradiction(s) found",
        )

        self._audit_logger.log(
            event_type=AuditEventType.QUERY,
            actor="jurisdiction-registry",
            payload={
                "comparison": f"{code_a} vs {code_b}",
                "contradictions_found": len(contradictions),
            },
            outcome="COMPARISON_COMPLETED",
        )
        return comparison

    @property
    def validation_reports(self) -> dict[str, Any]:
        return dict(self._validation_reports)

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, code: str) -> bool:
        return code.upper().strip() in self._entries

    def __iter__(self) -> Any:
        return iter(self._entries)


def _get_nested(obj: Any, path: str) -> Any:
    parts = path.split(".")
    current: Any = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def _pick_citations(entry_a: RegulatoryEntry, entry_b: RegulatoryEntry) -> dict[str, Any]:
    """Pick a representative citation from each entry for cross-entry comparison."""
    def first_citation(entry: RegulatoryEntry) -> Any:
        sg = entry.source_governance
        if sg.primary_citations:
            return sg.primary_citations[0]
        if sg.secondary_citations:
            return sg.secondary_citations[0]
        if sg.tertiary_citations:
            return sg.tertiary_citations[0]
        return None

    return {"source_a": first_citation(entry_a), "source_b": first_citation(entry_b)}
