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
)
from src.validation.validators import ValidationEngine


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

    def run_pipeline(self, entry: RegulatoryEntry, *, audit_log_path: Path = Path("logs/audit.jsonl")) -> RegulatoryEntry:
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

        return entry

    @staticmethod
    def _placeholder_confidence() -> ConfidenceScore:
        return ConfidenceScore(
            level=ConfidenceLevel.UNVERIFIED,
            score=0.0,
            rationale="Placeholder – will be overwritten by ConfidenceScorer",
        )
