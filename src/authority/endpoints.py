from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EndpointType(StrEnum):
    HOMEPAGE = "homepage"
    LEGISLATION = "legislation"
    RULES = "rules"
    GUIDANCE = "guidance"
    API = "api"
    RSS = "rss"
    SEARCH = "search"
    FILINGS = "filings"
    ENFORCEMENT = "enforcement"
    NEWS = "news"
    CONSULTATION = "consultation"
    FORMS = "forms"


class Endpoint(BaseModel):
    type: str
    url: str
    description: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class EndpointManager(BaseModel):
    endpoints: list[Endpoint] = Field(default_factory=list)

    def get_url(self, endpoint_type: str) -> str | None:
        for ep in self.endpoints:
            if ep.type == endpoint_type:
                return ep.url
        return None

    def get_all_of_type(self, endpoint_type: str) -> list[Endpoint]:
        return [ep for ep in self.endpoints if ep.type == endpoint_type]

    def has_type(self, endpoint_type: str) -> bool:
        return any(ep.type == endpoint_type for ep in self.endpoints)

    def get_types(self) -> list[str]:
        return list({ep.type for ep in self.endpoints})
