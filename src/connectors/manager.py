from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.audit.logger import AuditLogger
from src.authority.models import Authority
from src.authority.resolver import AuthorityResolver
from src.connectors.exceptions import ConnectorInitializationError
from src.connectors.factory import ConnectorFactory
from src.connectors.models import ConnectionHealth
from src.connectors.registry import ConnectorRegistry
from src.schema.schema import AuditEventType

if TYPE_CHECKING:
    from src.connectors.base import Connector


class ConnectorManager:
    """Manages connector lifecycle, reuse, health, and statistics."""

    def __init__(
        self,
        factory: ConnectorFactory,
        registry: ConnectorRegistry,
        audit_logger: AuditLogger | None = None,
        resolver: AuthorityResolver | None = None,
    ) -> None:
        self._factory = factory
        self._registry = registry
        self._audit = audit_logger or AuditLogger()
        self._resolver = resolver or AuthorityResolver()
        self._instances: dict[str, Connector] = {}
        self._stats: ConnectorStats = ConnectorStats()

    @property
    def stats(self) -> ConnectorStats:
        return self._stats

    def get_connector(self, authority_id: str) -> Connector:
        auth = self._resolve_authority(authority_id)
        if authority_id in self._instances:
            self._stats.lookups += 1
            return self._instances[authority_id]

        connector = self._factory.create(auth)
        result = connector.connect()
        if not result.success:
            raise ConnectorInitializationError(
                f"Failed to initialize connector for {authority_id}: {result.message}"
            )

        self._instances[authority_id] = connector
        self._stats.created += 1
        self._stats.lookups += 1
        self._audit.log(
            event_type=AuditEventType.SOURCE_INGESTION,
            actor="connector_manager",
            entry_id=None,
            payload={
                "action": "connector_created",
                "authority_id": authority_id,
                "connector": type(connector).__name__,
            },
        )
        return connector

    def shutdown(self, authority_id: str | None = None) -> None:
        if authority_id is not None:
            connector = self._instances.pop(authority_id, None)
            if connector is not None:
                connector.close()
                self._stats.shutdowns += 1
                self._audit.log(
                    event_type=AuditEventType.SOURCE_INGESTION,
                    actor="connector_manager",
                    entry_id=None,
                    payload={"action": "connector_shutdown", "authority_id": authority_id},
                )
            return

        for aid, connector in list(self._instances.items()):
            connector.close()
            self._stats.shutdowns += 1
            self._audit.log(
                event_type=AuditEventType.SOURCE_INGESTION,
                actor="connector_manager",
                entry_id=None,
                payload={"action": "connector_shutdown", "authority_id": aid},
            )
        self._instances.clear()

    def health(self, authority_id: str | None = None) -> dict[str, ConnectionHealth]:
        if authority_id is not None:
            connector = self._instances.get(authority_id)
            if connector is None:
                return {}
            return {authority_id: connector.health()}
        return {aid: c.health() for aid, c in self._instances.items()}

    def list_authorities(self) -> list[str]:
        return sorted(self._instances.keys())

    def _resolve_authority(self, authority_id: str) -> Authority:
        return self._resolver.get_by_id(authority_id)


class ConnectorStats:
    """Immutable-style statistics container for connector lifecycle."""

    def __init__(self) -> None:
        self.created: int = 0
        self.lookups: int = 0
        self.shutdowns: int = 0
        self.errors: int = 0
        self.last_error: str | None = None
        self.last_error_at: datetime | None = None

    def record_error(self, message: str) -> None:
        self.errors += 1
        self.last_error = message
        self.last_error_at = datetime.utcnow()

    @property
    def active_connectors(self) -> int:
        return self.created - self.shutdowns

    def snapshot(self) -> dict[str, int | str | None]:
        return {
            "created": self.created,
            "lookups": self.lookups,
            "shutdowns": self.shutdowns,
            "errors": self.errors,
            "active": self.active_connectors,
            "last_error": self.last_error,
        }
