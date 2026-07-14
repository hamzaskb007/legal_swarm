from __future__ import annotations

from pydantic import BaseModel, Field

from src.authority.jurisdiction import normalize_jurisdiction
from src.authority.models import Authority, AuthorityLevel, CapabilityType
from src.authority.registry import AuthorityRegistry


class DiscoveryResult(BaseModel):
    authority: Authority | None = None
    homepage_url: str | None = None
    legislation_url: str | None = None
    search_url: str | None = None
    rss_url: str | None = None
    api_url: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)


class AuthorityDiscovery:
    def __init__(self, registry: AuthorityRegistry) -> None:
        self._registry = registry

    def discover_primary(self, jurisdiction: str) -> Authority | None:
        norm = normalize_jurisdiction(jurisdiction)
        for a in self._registry.get_by_jurisdiction(norm):
            if a.level == AuthorityLevel.LEVEL_1 and a.enabled:
                return a
        return None

    def discover_legislation(self, jurisdiction: str) -> Authority | None:
        norm = normalize_jurisdiction(jurisdiction)
        for a in self._registry.get_by_jurisdiction(norm):
            if a.enabled and a.get_endpoint_url("legislation"):
                return a
        return None

    def discover_search(self, jurisdiction: str) -> DiscoveryResult:
        norm = normalize_jurisdiction(jurisdiction)
        result = DiscoveryResult()
        for a in self._registry.get_by_jurisdiction(norm):
            if not a.enabled:
                continue
            if result.authority is None:
                result.authority = a
            result.homepage_url = result.homepage_url or a.get_endpoint_url("homepage")
            result.legislation_url = result.legislation_url or a.get_endpoint_url("legislation")
            result.search_url = result.search_url or a.get_endpoint_url("search")
            result.rss_url = result.rss_url or a.get_endpoint_url("rss")
            result.api_url = result.api_url or a.get_endpoint_url("api")
            if a.capabilities:
                result.capabilities = list({c.value if hasattr(c, 'value') else c for c in a.capabilities})
            if a.document_types:
                result.document_types = list({d.value if hasattr(d, 'value') else d for d in a.document_types})
        return result

    def discover_rss(self, jurisdiction: str) -> list[Authority]:
        norm = normalize_jurisdiction(jurisdiction)
        return [
            a for a in self._registry.get_by_jurisdiction(norm)
            if a.enabled and a.has_capability(CapabilityType.RSS)
        ]

    def discover_all(self, jurisdiction: str) -> list[Authority]:
        norm = normalize_jurisdiction(jurisdiction)
        return [a for a in self._registry.get_by_jurisdiction(norm) if a.enabled]

    def discover_by_capability(self, capability: str | CapabilityType) -> list[Authority]:
        cap = capability.value if isinstance(capability, CapabilityType) else capability
        return [a for a in self._registry.get_all() if a.enabled and a.has_capability(cap)]
