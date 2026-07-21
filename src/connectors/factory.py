from __future__ import annotations

from typing import TYPE_CHECKING

from src.authority.models import Authority
from src.connectors.base import Connector
from src.connectors.exceptions import UnsupportedConnectorError
from src.connectors.registry import ConnectorRegistry
from src.connectors.scoring import (
    CAPABILITY_MATCH_SCORE,
    EXACT_PARSER_MATCH_SCORE,
    FULL_COMPATIBILITY_BONUS,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class ConnectorFactory:
    """Creates connector instances from Authority metadata via registry."""

    def __init__(self, registry: ConnectorRegistry) -> None:
        self._registry = registry

    def create(self, authority: Authority) -> Connector:
        candidates = self._resolve_candidates(authority)
        if not candidates:
            raise UnsupportedConnectorError(
                f"No connector registered for authority '{authority.id}' "
                f"(parser={authority.parser.value}, "
                f"capabilities={[c.value for c in authority.capabilities]})"
            )

        if len(candidates) > 1:
            candidates = self._best_match(candidates, authority)

        connector = candidates[0](authority)
        return connector

    def create_all(self, authorities: Sequence[Authority]) -> list[Connector]:
        connectors: list[Connector] = []
        errors: list[tuple[str, Exception]] = []
        for auth in authorities:
            try:
                connectors.append(self.create(auth))
            except UnsupportedConnectorError as e:
                errors.append((auth.id, e))
        if errors:
            msg = "; ".join(f"{aid}: {exc}" for aid, exc in errors)
            raise UnsupportedConnectorError(
                f"Failed to create connectors for {len(errors)} authority(ies): {msg}"
            )
        return connectors

    def _resolve_candidates(self, authority: Authority) -> list[type[Connector]]:
        candidates: list[type[Connector]] = []

        by_parser = self._registry.lookup_by_parser(authority.parser)
        candidates.extend(by_parser)

        for cap in authority.capabilities:
            by_cap = self._registry.lookup_by_capability(cap)
            candidates.extend(by_cap)

        seen: set[type[Connector]] = set()
        unique: list[type[Connector]] = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique.append(c)

        return unique

    @staticmethod
    def _best_match(
        candidates: list[type[Connector]], authority: Authority
    ) -> list[type[Connector]]:
        scored: list[tuple[int, type[Connector]]] = []
        for cls in candidates:
            score = 0
            meta = cls.metadata()
            caps = cls.capabilities()

            if authority.parser in meta.parser_types:
                score += EXACT_PARSER_MATCH_SCORE

            for auth_cap in authority.capabilities:
                if auth_cap in caps.capability_types:
                    score += CAPABILITY_MATCH_SCORE

            if caps.compatible_with(authority):
                score += FULL_COMPATIBILITY_BONUS

            scored.append((score, cls))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [cls for _, cls in scored]
