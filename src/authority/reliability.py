from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.authority.models import Authority

AUTHORITY_LEVEL_WEIGHTS: dict[int, float] = {
    1: 1.0,
    2: 0.9,
    3: 0.8,
    4: 0.6,
    5: 0.4,
}

AUTHORITY_TYPE_REPUTATION: dict[str, float] = {
    "regulator": 1.0,
    "legislation_database": 0.95,
    "government_gazette": 0.85,
    "central_bank": 0.95,
    "exchange": 0.90,
    "legal_firm": 0.65,
    "advisory": 0.50,
    "academic": 0.55,
}

PUBLICATION_TYPE_WEIGHTS: dict[str, float] = {
    "Act": 1.0,
    "Regulation": 0.98,
    "Directive": 0.98,
    "Rule": 0.95,
    "Circular": 0.90,
    "Guidance": 0.85,
    "Handbook": 0.85,
    "Policy Statement": 0.80,
    "Notice": 0.75,
    "Consultation": 0.70,
    "Press Release": 0.60,
    "FAQ": 0.50,
    "Form": 0.55,
    "Filing Requirement": 0.80,
    "Enforcement Action": 0.85,
    "Gazette": 0.90,
}

FRESHNESS_WEIGHTS: dict[str, float] = {
    "current": 1.0,
    "recent": 0.95,
    "moderate": 0.85,
    "aged": 0.70,
    "stale": 0.50,
}


def _freshness_category(publication_date: datetime | None, reference_date: datetime | None = None) -> str:
    ref = reference_date or datetime.utcnow()
    if publication_date is None:
        return "moderate"
    days = (ref - publication_date).days
    if days <= 90:
        return "current"
    elif days <= 365:
        return "recent"
    elif days <= 730:
        return "moderate"
    elif days <= 1825:
        return "aged"
    return "stale"


class ReliabilityConfig(BaseModel):
    level_weight: float = 0.25
    reputation_weight: float = 0.20
    publication_type_weight: float = 0.20
    freshness_weight: float = 0.15
    citation_completeness_weight: float = 0.10
    verification_weight: float = 0.10

    level_weights: dict[int, float] = Field(default_factory=lambda: dict(AUTHORITY_LEVEL_WEIGHTS))
    reputation_map: dict[str, float] = Field(default_factory=lambda: dict(AUTHORITY_TYPE_REPUTATION))
    publication_type_map: dict[str, float] = Field(default_factory=lambda: dict(PUBLICATION_TYPE_WEIGHTS))
    freshness_map: dict[str, float] = Field(default_factory=lambda: dict(FRESHNESS_WEIGHTS))

    max_score: float = 1.0
    min_score: float = 0.0


class ReliabilityScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    level_score: float = 0.0
    reputation_score: float = 0.0
    publication_type_score: float = 0.0
    freshness_score: float = 0.0
    completeness_score: float = 0.0
    verification_score: float = 0.0
    contributing_factors: list[str] = Field(default_factory=list)


class ReliabilityScorer:
    def __init__(self, config: ReliabilityConfig | None = None) -> None:
        self._config = config or ReliabilityConfig()

    @property
    def config(self) -> ReliabilityConfig:
        return self._config

    def score(
        self,
        authority: Authority,
        *,
        publication_date: datetime | None = None,
        document_type: str | None = None,
        has_section_reference: bool = False,
        has_excerpt: bool = False,
        verification_success: bool = True,
        retrieval_success: bool = True,
    ) -> ReliabilityScore:
        factors: list[str] = []
        ref_date = datetime.utcnow()

        level_weight = self._config.level_weights.get(authority.level.value, 0.5)
        level_score = level_weight * self._config.level_weight
        factors.append(f"Authority level {authority.level.value}: {level_weight:.2f} × {self._config.level_weight:.2f} = {level_score:.4f}")

        reputation = self._config.reputation_map.get(authority.authority_type, 0.5)
        reputation_score = reputation * self._config.reputation_weight
        factors.append(f"Authority type '{authority.authority_type}': {reputation:.2f} × {self._config.reputation_weight:.2f} = {reputation_score:.4f}")

        pub_weight = self._config.publication_type_map.get(document_type or "", 0.7)
        pub_score = pub_weight * self._config.publication_type_weight
        factors.append(f"Document type '{document_type or 'unknown'}': {pub_weight:.2f} × {self._config.publication_type_weight:.2f} = {pub_score:.4f}")

        freshness_cat = _freshness_category(publication_date, ref_date)
        fresh_weight = self._config.freshness_map.get(freshness_cat, 0.7)
        fresh_score = fresh_weight * self._config.freshness_weight
        factors.append(f"Freshness '{freshness_cat}': {fresh_weight:.2f} × {self._config.freshness_weight:.2f} = {fresh_score:.4f}")

        completeness_items = [has_section_reference, has_excerpt, retrieval_success]
        completeness_ratio = sum(1 for x in completeness_items if x) / len(completeness_items)
        completeness_score = completeness_ratio * self._config.citation_completeness_weight
        factors.append(f"Completeness ({sum(1 for x in completeness_items if x)}/{len(completeness_items)}): {completeness_ratio:.2f} × {self._config.citation_completeness_weight:.2f} = {completeness_score:.4f}")

        verification_score = (1.0 if verification_success else 0.3) * self._config.verification_weight
        factors.append(f"Verification {'success' if verification_success else 'failure'}: {'1.00' if verification_success else '0.30'} × {self._config.verification_weight:.2f} = {verification_score:.4f}")

        total = level_score + reputation_score + pub_score + fresh_score + completeness_score + verification_score
        final = max(self._config.min_score, min(self._config.max_score, total))

        return ReliabilityScore(
            score=round(final, 4),
            level_score=round(level_score, 4),
            reputation_score=round(reputation_score, 4),
            publication_type_score=round(pub_score, 4),
            freshness_score=round(fresh_score, 4),
            completeness_score=round(completeness_score, 4),
            verification_score=round(verification_score, 4),
            contributing_factors=factors,
        )
