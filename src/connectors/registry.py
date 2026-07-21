from __future__ import annotations

from typing import TYPE_CHECKING

from src.authority.models import CapabilityType, ParserType
from src.connectors.exceptions import ConnectorRegistrationError

if TYPE_CHECKING:
    from src.connectors.base import Connector


class ConnectorRegistry:
    """Registry of connector classes, keyed by parser type and capability."""

    def __init__(self) -> None:
        self._by_parser: dict[ParserType, list[type[Connector]]] = {}
        self._by_capability: dict[CapabilityType, list[type[Connector]]] = {}
        self._all_classes: dict[str, type[Connector]] = {}

    def register(self, connector_class: type[Connector]) -> None:
        meta = connector_class.metadata()
        name = meta.name
        if name in self._all_classes:
            raise ConnectorRegistrationError(
                f"Connector already registered: {name} (existing={self._all_classes[name]})"
            )

        caps = connector_class.capabilities()

        for pt in meta.parser_types:
            if pt not in self._by_parser:
                self._by_parser[pt] = []
            self._by_parser[pt].append(connector_class)

        for ct in caps.capability_types:
            if ct not in self._by_capability:
                self._by_capability[ct] = []
            self._by_capability[ct].append(connector_class)

        if not caps.capability_types:
            for pt in meta.parser_types:
                ct_val = _parser_to_capability(pt)
                if ct_val is not None:
                    if ct_val not in self._by_capability:
                        self._by_capability[ct_val] = []
                    if connector_class not in self._by_capability[ct_val]:
                        self._by_capability[ct_val].append(connector_class)

        self._all_classes[name] = connector_class

    def unregister(self, name: str) -> None:
        if name not in self._all_classes:
            raise ConnectorRegistrationError(f"Connector not registered: {name}")
        cls = self._all_classes.pop(name)

        for parser_type in self._by_parser:
            self._by_parser[parser_type] = [c for c in self._by_parser[parser_type] if c is not cls]
        for capability in self._by_capability:
            self._by_capability[capability] = [
                c for c in self._by_capability[capability] if c is not cls
            ]

    def lookup_by_parser(self, parser_type: ParserType) -> list[type[Connector]]:
        return list(self._by_parser.get(parser_type, []))

    def lookup_by_capability(self, capability: CapabilityType) -> list[type[Connector]]:
        return list(self._by_capability.get(capability, []))

    def list_registered(self) -> list[str]:
        return sorted(self._all_classes.keys())

    def get(self, name: str) -> type[Connector]:
        if name not in self._all_classes:
            raise ConnectorRegistrationError(f"Connector not registered: {name}")
        return self._all_classes[name]

    def validate_registrations(self) -> list[str]:
        warnings: list[str] = []
        for name, cls in self._all_classes.items():
            meta = cls.metadata()
            caps = cls.capabilities()

            if not meta.parser_types:
                warnings.append(f"{name}: no parser types declared in metadata")

            for pt in meta.parser_types:
                if pt is ParserType.MANUAL:
                    continue
                ct = _parser_to_capability(pt)
                if ct is not None and ct not in caps.capability_types:
                    warnings.append(
                        f"{name}: parser type '{pt.value}' typically requires "
                        f"capability '{ct.value}', but it is not declared"
                    )

        return warnings


def _parser_to_capability(parser: ParserType) -> CapabilityType | None:
    mapping: dict[ParserType, CapabilityType] = {
        ParserType.HTML: CapabilityType.HTML,
        ParserType.PDF: CapabilityType.PDF,
        ParserType.API: CapabilityType.API,
        ParserType.RSS: CapabilityType.RSS,
    }
    return mapping.get(parser)
