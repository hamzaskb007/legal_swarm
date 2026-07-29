from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from src.audit.logger import AuditLogger
from src.confidence.scorer import ConfidenceScorer
from src.contradiction.detector import CitationContradictionDetector
from src.schema.schema import (
    AuditEventType,
    ConfidenceLevel,
    ConfidenceScore,
    RegulatoryEntry,
    RegulatoryRelevanceTag,
)
from src.validation.models import ValidationReport
from src.validation.validators import ValidationEngine

_REQUIRED_TAG_COVERAGE: list[tuple[str, RegulatoryRelevanceTag, str]] = [
    (
        "tax_summary",
        RegulatoryRelevanceTag.TAX_FRAMEWORK,
        "populated tax_summary requires at least one citation with "
        "regulatory_relevance_tag='Tax Framework' — tag an existing tax-related "
        "citation or add a new CitationRecord with the correct tag",
    ),
    (
        "permitted_fund_structures",
        RegulatoryRelevanceTag.CAPITAL_REQUIREMENTS,
        "permitted_fund_structures with min_capital.amount > 0 require at least "
        "one citation with regulatory_relevance_tag='Capital Requirements' — tag "
        "an existing capital-related citation or add a new CitationRecord",
    ),
]


class JurisdictionBuilder(ABC):
    """Abstract base for all jurisdiction builders.

    Subclasses must implement :meth:`build_entry` to return a fully populated
    :class:`RegulatoryEntry`.  The :meth:`run_pipeline` method then pushes that
    entry through confidence scoring, validation, contradiction detection and
    audit logging.
    """

    @abstractmethod
    def build_entry(self) -> RegulatoryEntry:
        """Construct and return a :class:`RegulatoryEntry` for this jurisdiction.

        The returned entry must carry a **placeholder** confidence score
        (:attr:`ConfidenceLevel.UNVERIFIED`, score 0.0) because the real score
        is computed later by :class:`ConfidenceScorer` inside
        :meth:`run_pipeline`.
        """
        ...

    @staticmethod
    def _check_citation_tag_coverage(entry: RegulatoryEntry) -> None:
        """Build-time self-check: raise ``ValueError`` if a populated field
        lacks the required citation tag coverage.

        Mirrors the logic of VAL_016 / VAL_017 but fires early (at
        construction time) so a developer can't finish writing a new
        jurisdiction file without realising they missed a required tag.

        Raises
        ------
        ValueError
            Describing the first missing tag requirement found.
        """
        all_citations = (
            list(entry.source_governance.primary_citations)
            + list(entry.source_governance.secondary_citations)
            + list(entry.source_governance.tertiary_citations)
        )
        tags = {c.regulatory_relevance_tag for c in all_citations}

        for field_name, required_tag, hint in _REQUIRED_TAG_COVERAGE:
            if field_name == "tax_summary":
                if entry.tax_summary is None:
                    continue
            elif field_name == "permitted_fund_structures":
                has_capital = any(
                    fs.min_capital is not None
                    and fs.min_capital.amount is not None
                    and fs.min_capital.amount > 0
                    for fs in entry.permitted_fund_structures
                )
                if not has_capital:
                    continue

            if required_tag.value not in tags:
                raise ValueError(f"{entry.jurisdiction_code}: {hint} (found tags: {sorted(tags)})")

    def run_pipeline(
        self, entry: RegulatoryEntry, *, audit_log_path: Path = Path("logs/audit.jsonl")
    ) -> tuple[RegulatoryEntry, ValidationReport]:
        scorer = ConfidenceScorer()
        confidence = scorer.score(entry)
        entry = entry.model_copy(update={"confidence": confidence})

        engine = ValidationEngine()
        report = engine.validate(entry)

        detector = CitationContradictionDetector()
        contradictions = detector.detect(entry)
        if contradictions:
            entry = entry.model_copy(update={"contradictions": contradictions})

        logger = AuditLogger(log_path=audit_log_path)
        logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="jurisdiction-builder",
            jurisdiction_code=entry.jurisdiction_code,
            entry_id=entry.entry_id,
            payload={
                "validation_status": report.overall_status.value,
                "confidence_score": float(confidence.score),
                "contradictions_found": len(contradictions),
            },
            outcome="Pipeline completed",
        )

        return entry, report

    @staticmethod
    def _placeholder_confidence() -> ConfidenceScore:
        return ConfidenceScore(
            level=ConfidenceLevel.UNVERIFIED,
            score=0.0,
            rationale="Placeholder – will be overwritten by ConfidenceScorer",
        )
