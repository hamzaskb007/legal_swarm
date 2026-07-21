from __future__ import annotations

from abc import ABC, abstractmethod

from src.authority.models import Authority, CapabilityType, ParserType
from src.connectors.exceptions import ConnectorInitializationError
from src.connectors.models import (
    ConnectorCapabilities,
    ConnectorMetadata,
    ConnectionHealth,
    ConnectionResult,
    FetchRequest,
    FetchResult,
)


class Connector(ABC):
    """Abstract base for all data source connectors."""

    def __init__(self, authority: Authority) -> None:
        if not authority.enabled:
            raise ConnectorInitializationError(
                f"Cannot initialize connector for disabled authority: {authority.id}"
            )
        self._authority = authority
        self._initialized = False

    @property
    def authority(self) -> Authority:
        return self._authority

    @property
    def initialized(self) -> bool:
        return self._initialized

    @classmethod
    @abstractmethod
    def metadata(cls) -> ConnectorMetadata: ...

    @classmethod
    @abstractmethod
    def capabilities(cls) -> ConnectorCapabilities: ...

    @abstractmethod
    def connect(self) -> ConnectionResult: ...

    @abstractmethod
    def health(self) -> ConnectionHealth: ...

    @abstractmethod
    def fetch(self, request: FetchRequest) -> FetchResult: ...

    @abstractmethod
    def close(self) -> None: ...

    def supports(
        self, parser_type: ParserType | None = None, capability: CapabilityType | None = None
    ) -> bool:
        caps = self.capabilities()
        if parser_type is not None and not caps.supports_parser(parser_type):
            return False
        if capability is not None and not caps.has_capability(capability):
            return False
        return True
