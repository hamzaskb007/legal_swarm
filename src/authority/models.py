from __future__ import annotations

from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.schema.schema import SourceAuthority


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AuthorityLevel(IntEnum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5

    def to_source_authority(self) -> SourceAuthority:
        mapping = {
            AuthorityLevel.LEVEL_1: SourceAuthority.PRIMARY,
            AuthorityLevel.LEVEL_2: SourceAuthority.PRIMARY,
            AuthorityLevel.LEVEL_3: SourceAuthority.PRIMARY,
            AuthorityLevel.LEVEL_4: SourceAuthority.SECONDARY,
            AuthorityLevel.LEVEL_5: SourceAuthority.TERTIARY,
        }
        return mapping[self]

    @property
    def label(self) -> str:
        labels = {
            1: "Official regulator",
            2: "Government legislation database",
            3: "Government gazette",
            4: "Recognized legal firm",
            5: "Professional advisory",
        }
        return labels[self.value]


class ParserType(StrEnum):
    HTML = "html"
    PDF = "pdf"
    API = "api"
    RSS = "rss"
    MANUAL = "manual"


class DocumentType(StrEnum):
    ACT = "Act"
    REGULATION = "Regulation"
    RULE = "Rule"
    GUIDANCE = "Guidance"
    CIRCULAR = "Circular"
    NOTICE = "Notice"
    CONSULTATION = "Consultation"
    FAQ = "FAQ"
    PRESS_RELEASE = "Press Release"
    ENFORCEMENT_ACTION = "Enforcement Action"
    FORM = "Form"
    FILING_REQUIREMENT = "Filing Requirement"
    POLICY_STATEMENT = "Policy Statement"
    HANDBOOK = "Handbook"
    GAZETTE = "Gazette"
    DIRECTIVE = "Directive"


class RelationshipType(StrEnum):
    PUBLISHES = "publishes"
    ENFORCES = "enforces"
    REFERENCES = "references"
    SUPERSEDES = "supersedes"
    DELEGATES = "delegates"
    RECOGNIZES = "recognizes"


class CapabilityType(StrEnum):
    HTML = "html"
    PDF = "pdf"
    API = "api"
    RSS = "rss"
    JSON = "json"
    XML = "xml"
    SEARCH = "search"
    DOWNLOAD = "download"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class Endpoint(BaseModel):
    type: str
    url: str
    description: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class Relationship(BaseModel):
    type: RelationshipType
    target_id: str


class VersionInfo(BaseModel):
    version: str = "1.0.0"
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)
    deprecated: bool = False
    deprecation_date: datetime | None = None
    change_log: list[dict[str, str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Main Authority Model
# ---------------------------------------------------------------------------

class Authority(BaseModel):
    id: str
    hierarchical_id: str | None = None
    jurisdiction: str
    aliases: list[str] = Field(default_factory=list)
    name: str
    level: AuthorityLevel
    authority_type: str
    base_url: str | None = None
    search_url: str | None = None
    legislation_url: str | None = None
    endpoints: list[Endpoint] = Field(default_factory=list)
    parser: ParserType = ParserType.HTML
    capabilities: list[CapabilityType] = Field(default_factory=list)
    refresh_interval: int = Field(default=24, ge=1, description="Refresh interval in hours")
    reliability_score: float = Field(default=0.85, ge=0.0, le=1.0)
    base_reliability: float | None = None
    enabled: bool = True
    relationships: list[Relationship] = Field(default_factory=list)
    document_types: list[DocumentType] = Field(default_factory=list)
    version: VersionInfo = Field(default_factory=VersionInfo)
    metadata: dict[str, str] = Field(default_factory=dict)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    contacts: dict[str, str] = Field(default_factory=dict)
    notes: str | None = None
    refresh_policy: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("hierarchical_id") is None:
                if not data.get("id", "").startswith("authority."):
                    data["hierarchical_id"] = f"authority.{data.get('jurisdiction', 'unknown').lower()}.{data['id']}"
                else:
                    data["hierarchical_id"] = data["id"]
            if not data.get("endpoints"):
                endpoints: list[dict[str, str]] = []
                if data.get("base_url"):
                    endpoints.append({"type": "homepage", "url": data["base_url"]})
                if data.get("search_url"):
                    endpoints.append({"type": "search", "url": data["search_url"]})
                if data.get("legislation_url"):
                    endpoints.append({"type": "legislation", "url": data["legislation_url"]})
                data["endpoints"] = endpoints
            if not data.get("capabilities"):
                parser = data.get("parser", "html")
                parser_to_capability = {"html": "html", "pdf": "pdf", "api": "api", "rss": "rss"}
                mapped = parser_to_capability.get(parser)
                if mapped:
                    data["capabilities"] = [mapped]
            if not data.get("base_reliability") and data.get("reliability_score"):
                data["base_reliability"] = data["reliability_score"]
        return data

    def to_source_authority(self) -> SourceAuthority:
        return self.level.to_source_authority()

    def get_endpoint_url(self, endpoint_type: str) -> str | None:
        for ep in self.endpoints:
            if ep.type == endpoint_type:
                return ep.url
        return None

    def has_capability(self, capability: str | CapabilityType) -> bool:
        if isinstance(capability, CapabilityType):
            capability = capability.value
        return capability in {c.value if isinstance(c, CapabilityType) else c for c in self.capabilities}
