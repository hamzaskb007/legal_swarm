from __future__ import annotations
from datetime import datetime, timedelta
from src.schema.schema import ConfidenceLevel, ConfidenceScore, RegulatoryEntry, SourceAuthority

AUTHORITY_WEIGHT = {
    SourceAuthority.PRIMARY: 1.0,
    SourceAuthority.SECONDARY: 0.6,
    SourceAuthority.TERTIARY: 0.3,
}
MAX_CITATION_BONUS = 0.2
RECENCY_THRESHOLD_DAYS = 365
RECENCY_PENALTY = 0.1
CONTRADICTION_PENALTY = 0.15


def _level_from_score(score: float) -> ConfidenceLevel:
    if score >= 0.75:
        return ConfidenceLevel.HIGH
    elif score >= 0.5:
        return ConfidenceLevel.MEDIUM
    elif score >= 0.4:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.UNVERIFIED


class ConfidenceScorer:
    def score(self, entry: RegulatoryEntry) -> ConfidenceScore:
        factors: list[str] = []
        base = AUTHORITY_WEIGHT.get(entry.source_governance.dominant_source, 0.3)
        factors.append(f"Base authority score ({entry.source_governance.dominant_source}): {base:.2f}")

        all_citations = (entry.source_governance.primary_citations
                         + entry.source_governance.secondary_citations
                         + entry.source_governance.tertiary_citations)
        total = len(all_citations)
        citation_bonus = min(total * 0.05, MAX_CITATION_BONUS)
        factors.append(f"Citation volume bonus ({total} citations): +{citation_bonus:.2f}")

        threshold = datetime.utcnow() - timedelta(days=RECENCY_THRESHOLD_DAYS)
        stale = sum(1 for c in all_citations if c.publication_date and c.publication_date < threshold)
        recency_penalty = stale * RECENCY_PENALTY
        if stale:
            factors.append(f"Recency penalty ({stale} stale): -{recency_penalty:.2f}")

        unresolved = sum(1 for c in entry.contradictions if not c.resolved)
        contradiction_penalty = unresolved * CONTRADICTION_PENALTY
        if unresolved:
            factors.append(f"Contradiction penalty ({unresolved} unresolved): -{contradiction_penalty:.2f}")

        final = max(0.0, min(1.0, base + citation_bonus - recency_penalty - contradiction_penalty))
        return ConfidenceScore(
            level=_level_from_score(final),
            score=round(final, 4),
            rationale=f"Scored from {total} citations, {unresolved} contradictions, {stale} stale sources.",
            contributing_factors=factors,
        )