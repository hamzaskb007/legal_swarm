from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.authority.models import CapabilityType, ParserType


class ConnectionStatus(StrEnum):
    INITIALIZED = "initialized"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectorMetadata(BaseModel, frozen=True):
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    parser_types: list[ParserType] = Field(default_factory=list)
    capabilities: list[CapabilityType] = Field(default_factory=list)


class ConnectorCapabilities(BaseModel, frozen=True):
    parser_types: frozenset[ParserType] = Field(default_factory=frozenset)
    capability_types: frozenset[CapabilityType] = Field(default_factory=frozenset)
    supports_search: bool = False
    supports_streaming: bool = False
    max_concurrent_requests: int = 1

    def supports_parser(self, parser: ParserType) -> bool:
        return parser in self.parser_types

    def has_capability(self, capability: CapabilityType) -> bool:
        return capability in self.capability_types

    def compatible_with(self, authority: Any) -> bool:
        if not self.supports_parser(authority.parser):
            return False
        for cap in authority.capabilities:
            if not self.has_capability(cap):
                return False
        return True


class ConnectionResult(BaseModel, frozen=True):
    success: bool
    status: ConnectionStatus
    message: str = ""
    connected_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FetchRequest(BaseModel, frozen=True):
    url: str
    parser_type: ParserType | None = None
    capabilities: list[CapabilityType] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class FetchResult(BaseModel, frozen=True):
    success: bool
    data: str = ""
    content_type: str = ""
    size_bytes: int = 0
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectionHealth(BaseModel, frozen=True):
    initialized: bool = False
    available: bool = False
    status: ConnectionStatus = ConnectionStatus.INITIALIZED
    parser_supported: bool = True
    capabilities: list[CapabilityType] = Field(default_factory=list)
    version: str = "1.0.0"
    last_health_check: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel, frozen=True):
    id: UUID = Field(default_factory=uuid4)
    authority_id: str
    source_url: str
    canonical_url: str | None = None
    title: str | None = None
    summary: str | None = None
    content: str = ""
    content_type: str = ""
    language: str | None = None
    publication_date: datetime | None = None
    last_modified: datetime | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    document_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    discovered_links: list[str] = Field(default_factory=list)
