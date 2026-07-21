from __future__ import annotations

from datetime import datetime

from src.authority.jurisdiction import normalize_jurisdiction
from src.authority.models import Authority, AuthorityLevel
from src.authority.registry import AuthorityRegistry
from src.schema.schema import CitationRecord


class AuthorityResolver:
    def __init__(self, registry: AuthorityRegistry | None = None) -> None:
        self._registry = registry or AuthorityRegistry()

    @property
    def registry(self) -> AuthorityRegistry:
        return self._registry

    def get_primary_authority(self, jurisdiction: str) -> Authority | None:
        norm = normalize_jurisdiction(jurisdiction)
        for a in self._registry.get_by_jurisdiction(norm):
            if a.level == AuthorityLevel.LEVEL_1 and a.enabled:
                return a
        return None

    def get_all_authorities(self, jurisdiction: str) -> list[Authority]:
        norm = normalize_jurisdiction(jurisdiction)
        return self._registry.get_by_jurisdiction(norm)

    def get_by_name(self, name: str, case_sensitive: bool = False) -> Authority | None:
        return self._registry.get_by_name(name, case_sensitive)

    def get_by_level(self, level: int | AuthorityLevel) -> list[Authority]:
        return self._registry.get_by_level(level)

    def get_enabled(self) -> list[Authority]:
        return self._registry.get_enabled()

    def get_by_id(self, authority_id: str) -> Authority:
        return self._registry.get_by_id(authority_id)

    def resolve_for_citation(self, authority_id: str) -> Authority:
        return self._registry.get_by_id(authority_id)

    def get_endpoint(self, authority_id: str, endpoint_type: str) -> str | None:
        try:
            auth = self._registry.get_by_id(authority_id)
            return auth.get_endpoint_url(endpoint_type)
        except KeyError:
            return None

    def create_citation(
        self,
        authority_id: str,
        *,
        source_name: str | None = None,
        source_url: str | None = None,
        authority_level: int | None = None,
        reliability_score: float | None = None,
        publication_date: datetime | None = None,
        section_reference: str | None = None,
        raw_excerpt: str | None = None,
        regulatory_relevance_tag: str | None = None,
    ) -> CitationRecord:
        authority = self._registry.get_by_id(authority_id)

        return CitationRecord(
            authority_id=authority_id,
            source_name=source_name or authority.name,
            source_url=source_url
            or authority.get_endpoint_url("homepage")
            or authority.base_url
            or "",
            authority=authority.to_source_authority(),
            authority_level=authority_level or authority.level.value,
            reliability_score=reliability_score or authority.reliability_score,
            publication_date=publication_date or datetime.utcnow(),
            section_reference=section_reference or "",
            raw_excerpt=raw_excerpt,
            regulatory_relevance_tag=regulatory_relevance_tag or "",
            last_verified_timestamp=datetime.utcnow(),
        )
