"""Unit tests for the Connector Framework."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.authority.models import Authority, CapabilityType, ParserType
from src.authority.registry import AuthorityRegistry
from src.authority.resolver import AuthorityResolver
from src.connectors.base import Connector
from src.connectors.exceptions import (
    CapabilityError,
    ConnectionError,
    ConnectorConfigurationError,
    ConnectorError,
    ConnectorInitializationError,
    ConnectorRegistrationError,
    UnsupportedConnectorError,
)
from src.connectors.factory import ConnectorFactory
from src.connectors.manager import ConnectorManager
from src.connectors.models import (
    ConnectionHealth,
    ConnectionResult,
    ConnectionStatus,
    ConnectorCapabilities,
    ConnectorMetadata,
    FetchRequest,
    FetchResult,
)
from src.connectors.registry import ConnectorRegistry

# ---------------------------------------------------------------------------
# Concrete connector implementations for testing
# ---------------------------------------------------------------------------


class _TestHTMLConnector(Connector):
    _COUNTER = 0

    def __init__(self, authority: Authority) -> None:
        super().__init__(authority)
        _TestHTMLConnector._COUNTER += 1
        self._instance_id = _TestHTMLConnector._COUNTER
        self._connected = False
        self._closed = False

    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="TestHTMLConnector",
            version="1.0.0",
            description="Test HTML connector",
            parser_types=[ParserType.HTML],
            capabilities=[CapabilityType.HTML],
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            parser_types={ParserType.HTML},
            capability_types={CapabilityType.HTML, CapabilityType.SEARCH},
            supports_search=True,
        )

    def connect(self) -> ConnectionResult:
        self._connected = True
        self._initialized = True
        return ConnectionResult(
            success=True,
            status=ConnectionStatus.CONNECTED,
            message="Connected",
            connected_at=datetime.utcnow(),
        )

    def health(self) -> ConnectionHealth:
        return ConnectionHealth(
            initialized=self._initialized,
            available=self._connected,
            status=ConnectionStatus.CONNECTED if self._connected else ConnectionStatus.INITIALIZED,
            parser_supported=True,
            capabilities=[CapabilityType.HTML, CapabilityType.SEARCH],
            version="1.0.0",
        )

    def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(
            success=True,
            data="<html></html>",
            content_type="text/html",
            size_bytes=13,
        )

    def close(self) -> None:
        self._closed = True
        self._connected = False

    @property
    def instance_id(self) -> int:
        return self._instance_id


class _TestRSSConnector(Connector):
    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="TestRSSConnector",
            parser_types=[ParserType.RSS],
            capabilities=[CapabilityType.RSS],
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            parser_types={ParserType.RSS},
            capability_types={CapabilityType.RSS},
            supports_streaming=True,
        )

    def connect(self) -> ConnectionResult:
        return ConnectionResult(success=True, status=ConnectionStatus.CONNECTED)

    def health(self) -> ConnectionHealth:
        return ConnectionHealth(initialized=True, available=True, status=ConnectionStatus.CONNECTED)

    def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(
            success=True, data="<rss></rss>", content_type="application/rss+xml", size_bytes=12
        )

    def close(self) -> None:
        pass


class _TestPDFConnector(Connector):
    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="TestPDFConnector",
            parser_types=[ParserType.PDF],
            capabilities=[CapabilityType.PDF],
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            parser_types={ParserType.PDF}, capability_types={CapabilityType.PDF}
        )

    def connect(self) -> ConnectionResult:
        return ConnectionResult(success=True, status=ConnectionStatus.CONNECTED)

    def health(self) -> ConnectionHealth:
        return ConnectionHealth(initialized=True, available=True, status=ConnectionStatus.CONNECTED)

    def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(success=True, data="%PDF", content_type="application/pdf", size_bytes=4)

    def close(self) -> None:
        pass


class _FailingConnector(Connector):
    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="FailingConnector",
            parser_types=[ParserType.HTML],
            capabilities=[CapabilityType.HTML],
        )

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            parser_types={ParserType.HTML}, capability_types={CapabilityType.HTML}
        )

    def connect(self) -> ConnectionResult:
        return ConnectionResult(
            success=False, status=ConnectionStatus.ERROR, message="Connection refused"
        )

    def health(self) -> ConnectionHealth:
        return ConnectionHealth(
            initialized=True,
            available=False,
            status=ConnectionStatus.ERROR,
            details={"error": "Connection refused"},
        )

    def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(success=False)

    def close(self) -> None:
        pass


class _GenericHTMLConnector(Connector):
    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(name="GenericHTML", parser_types=[ParserType.HTML])

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(parser_types={ParserType.HTML}, capability_types=set())

    def connect(self) -> ConnectionResult:
        return ConnectionResult(success=True, status=ConnectionStatus.CONNECTED)

    def health(self) -> ConnectionHealth:
        return ConnectionHealth()

    def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(success=True)

    def close(self) -> None:
        pass


class _BadConnector(Connector):
    @classmethod
    def metadata(cls) -> ConnectorMetadata:
        return ConnectorMetadata(name="BadConnector", parser_types=[ParserType.PDF])

    @classmethod
    def capabilities(cls) -> ConnectorCapabilities:
        return ConnectorCapabilities(parser_types={ParserType.PDF}, capability_types=set())

    def connect(self) -> ConnectionResult:
        return ConnectionResult(success=True, status=ConnectionStatus.CONNECTED)

    def health(self) -> ConnectionHealth:
        return ConnectionHealth()

    def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(success=True)

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_COUNTER = 0


def _authority_dict(**overrides: Any) -> dict[str, Any]:
    global _TEST_COUNTER
    _TEST_COUNTER += 1
    base = {
        "id": f"test_auth{_TEST_COUNTER}",
        "jurisdiction": "XX",
        "name": f"Test Authority {_TEST_COUNTER}",
        "level": 1,
        "authority_type": "regulator",
        "base_url": f"https://testauth{_TEST_COUNTER}.gov",
        "parser": "html",
        "capabilities": ["html", "search"],
        "reliability_score": 0.95,
        "enabled": True,
        "metadata": {"country": "Testland"},
    }
    base.update(**overrides)
    return base


def _make_authority(**overrides: Any) -> Authority:
    return Authority.model_validate(_authority_dict(**overrides))


def _disabled_authority(**overrides: Any) -> Authority:
    return Authority.model_validate(_authority_dict(enabled=False, **overrides))


def _write_authority_yaml(tmpdir: Path, **overrides: Any) -> str:
    """Write an authority YAML to tmpdir and return its id."""
    data = _authority_dict(**overrides)
    path = Path(tmpdir) / f"{data['id']}.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f)
    return str(data["id"])


def _resolver_for(tmpdir: Path) -> AuthorityResolver:
    """Build an AuthorityResolver that loads from tmpdir YAML files."""
    registry = AuthorityRegistry(yaml_dir=str(tmpdir))
    return AuthorityResolver(registry)


# ===================================================================
# Models
# ===================================================================


class TestConnectorMetadata:
    def test_defaults(self):
        m = ConnectorMetadata(name="Test")
        assert m.name == "Test"
        assert m.version == "1.0.0"
        assert m.description == ""
        assert m.parser_types == []
        assert m.capabilities == []

    def test_frozen(self):
        m = ConnectorMetadata(name="Test")
        with pytest.raises(Exception):
            m.name = "Changed"

    def test_with_parser_types(self):
        m = ConnectorMetadata(name="T", parser_types=[ParserType.HTML, ParserType.PDF])
        assert ParserType.HTML in m.parser_types

    def test_with_capabilities(self):
        m = ConnectorMetadata(name="T", capabilities=[CapabilityType.API, CapabilityType.RSS])
        assert CapabilityType.API in m.capabilities


class TestConnectorCapabilities:
    def test_defaults(self):
        c = ConnectorCapabilities()
        assert c.parser_types == frozenset()
        assert not c.supports_search
        assert not c.supports_streaming

    def test_frozen(self):
        c = ConnectorCapabilities()
        with pytest.raises(Exception):
            c.supports_search = True

    def test_supports_parser(self):
        c = ConnectorCapabilities(parser_types={ParserType.HTML, ParserType.PDF})
        assert c.supports_parser(ParserType.HTML)
        assert c.supports_parser(ParserType.PDF)
        assert not c.supports_parser(ParserType.RSS)

    def test_has_capability(self):
        c = ConnectorCapabilities(capability_types={CapabilityType.API, CapabilityType.RSS})
        assert c.has_capability(CapabilityType.API)
        assert not c.has_capability(CapabilityType.HTML)

    def test_compatible_with(self):
        auth = _make_authority(parser="html", capabilities=["html", "search"])
        c = ConnectorCapabilities(
            parser_types={ParserType.HTML},
            capability_types={CapabilityType.HTML, CapabilityType.SEARCH},
        )
        assert c.compatible_with(auth)

    def test_compatible_with_missing_parser(self):
        auth = _make_authority(parser="pdf", capabilities=["pdf"])
        c = ConnectorCapabilities(
            parser_types={ParserType.HTML},
            capability_types={CapabilityType.HTML},
        )
        assert not c.compatible_with(auth)

    def test_compatible_with_missing_capability(self):
        auth = _make_authority(parser="html", capabilities=["html", "api"])
        c = ConnectorCapabilities(
            parser_types={ParserType.HTML},
            capability_types={CapabilityType.HTML},
        )
        assert not c.compatible_with(auth)


class TestConnectionResult:
    def test_defaults(self):
        r = ConnectionResult(success=True, status=ConnectionStatus.CONNECTED)
        assert r.success is True
        assert r.message == ""

    def test_frozen(self):
        r = ConnectionResult(success=True, status=ConnectionStatus.CONNECTED)
        with pytest.raises(Exception):
            r.success = False


class TestFetchRequest:
    def test_defaults(self):
        r = FetchRequest(url="https://example.gov")
        assert r.url == "https://example.gov"
        assert r.parser_type is None
        assert r.capabilities == []
        assert r.parameters == {}


class TestFetchResult:
    def test_defaults(self):
        r = FetchResult(success=True)
        assert r.data == ""
        assert r.content_type == ""
        assert r.size_bytes == 0

    def test_frozen(self):
        r = FetchResult(success=True)
        with pytest.raises(Exception):
            r.success = False


class TestConnectionHealth:
    def test_defaults(self):
        h = ConnectionHealth()
        assert h.initialized is False
        assert h.available is False
        assert h.status == ConnectionStatus.INITIALIZED

    def test_frozen(self):
        h = ConnectionHealth()
        with pytest.raises(Exception):
            h.initialized = True


# ===================================================================
# Exception hierarchy
# ===================================================================


class TestExceptionHierarchy:
    def test_connector_error_base(self):
        assert issubclass(ConnectorConfigurationError, ConnectorError)
        assert issubclass(UnsupportedConnectorError, ConnectorError)
        assert issubclass(ConnectorRegistrationError, ConnectorError)
        assert issubclass(ConnectorInitializationError, ConnectorError)
        assert issubclass(ConnectionError, ConnectorError)
        assert issubclass(CapabilityError, ConnectorError)

    def test_connector_error_raise(self):
        with pytest.raises(ConnectorError):
            raise ConnectorConfigurationError("bad config")

    def test_unsupported_connector(self):
        with pytest.raises(UnsupportedConnectorError):
            raise UnsupportedConnectorError("not supported")

    def test_registration_error(self):
        with pytest.raises(ConnectorRegistrationError):
            raise ConnectorRegistrationError("duplicate")

    def test_initialization_error(self):
        with pytest.raises(ConnectorInitializationError):
            raise ConnectorInitializationError("init failed")

    def test_connection_error(self):
        with pytest.raises(ConnectionError):
            raise ConnectionError("cannot connect")

    def test_capability_error(self):
        with pytest.raises(CapabilityError):
            raise CapabilityError("missing capability")

    def test_message_preserved(self):
        try:
            raise ConnectorConfigurationError("custom message")
        except ConnectorConfigurationError as e:
            assert str(e) == "custom message"


# ===================================================================
# Connector interface
# ===================================================================


class TestConnectorInterface:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Connector(_make_authority())  # type: ignore[abstract]

    def test_rejects_disabled_authority(self):
        with pytest.raises(ConnectorInitializationError):
            _TestHTMLConnector(_disabled_authority())

    def test_metadata_returns_correct_values(self):
        meta = _TestHTMLConnector.metadata()
        assert meta.name == "TestHTMLConnector"
        assert ParserType.HTML in meta.parser_types

    def test_capabilities_returns_correct_values(self):
        caps = _TestHTMLConnector.capabilities()
        assert CapabilityType.HTML in caps.capability_types
        assert caps.supports_search

    def test_connect(self):
        c = _TestHTMLConnector(_make_authority())
        result = c.connect()
        assert result.success
        assert result.status == ConnectionStatus.CONNECTED

    def test_health(self):
        c = _TestHTMLConnector(_make_authority())
        c.connect()
        h = c.health()
        assert h.initialized
        assert h.available
        assert h.status == ConnectionStatus.CONNECTED

    def test_fetch(self):
        c = _TestHTMLConnector(_make_authority())
        result = c.fetch(FetchRequest(url="https://example.gov"))
        assert result.success
        assert result.data == "<html></html>"

    def test_close(self):
        c = _TestHTMLConnector(_make_authority())
        c.close()
        assert c._closed

    def test_supports_parser(self):
        c = _TestHTMLConnector(_make_authority())
        assert c.supports(parser_type=ParserType.HTML)
        assert not c.supports(parser_type=ParserType.RSS)

    def test_supports_capability(self):
        c = _TestHTMLConnector(_make_authority())
        assert c.supports(capability=CapabilityType.HTML)
        assert c.supports(capability=CapabilityType.SEARCH)
        assert not c.supports(capability=CapabilityType.API)

    def test_authority_property(self):
        auth = _make_authority()
        c = _TestHTMLConnector(auth)
        assert c.authority.id == auth.id
        assert c.authority.name == auth.name

    def test_initialized_property(self):
        c = _TestHTMLConnector(_make_authority())
        assert not c.initialized
        c.connect()
        assert c.initialized


# ===================================================================
# Connector Registry
# ===================================================================


class TestConnectorRegistry:
    def test_register_and_list(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        assert "TestHTMLConnector" in registry.list_registered()

    def test_register_multiple(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        registry.register(_TestRSSConnector)
        assert len(registry.list_registered()) == 2

    def test_duplicate_registration_raises(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        with pytest.raises(ConnectorRegistrationError):
            registry.register(_TestHTMLConnector)

    def test_unregister(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        registry.unregister("TestHTMLConnector")
        assert "TestHTMLConnector" not in registry.list_registered()

    def test_unregister_nonexistent_raises(self):
        registry = ConnectorRegistry()
        with pytest.raises(ConnectorRegistrationError):
            registry.unregister("Nonexistent")

    def test_lookup_by_parser(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        registry.register(_TestRSSConnector)
        html = registry.lookup_by_parser(ParserType.HTML)
        assert _TestHTMLConnector in html
        assert _TestRSSConnector not in html

    def test_lookup_by_capability(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        registry.register(_TestRSSConnector)
        html_cap = registry.lookup_by_capability(CapabilityType.HTML)
        assert _TestHTMLConnector in html_cap

    def test_lookup_unknown_parser(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        assert registry.lookup_by_parser(ParserType.API) == []

    def test_lookup_unknown_capability(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        assert registry.lookup_by_capability(CapabilityType.API) == []

    def test_get_registered_class(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        cls = registry.get("TestHTMLConnector")
        assert cls is _TestHTMLConnector

    def test_get_nonexistent_raises(self):
        registry = ConnectorRegistry()
        with pytest.raises(ConnectorRegistrationError):
            registry.get("Nonexistent")

    def test_validate_registrations_clean(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        warnings = registry.validate_registrations()
        assert warnings == []

    def test_validate_registrations_warns_missing_capability(self):
        registry = ConnectorRegistry()
        registry.register(_BadConnector)
        warnings = registry.validate_registrations()
        assert len(warnings) >= 1
        assert "pdf" in warnings[0].lower()

    def test_auto_registers_capability_from_parser(self):
        registry = ConnectorRegistry()
        registry.register(_TestRSSConnector)
        rss_cap = registry.lookup_by_capability(CapabilityType.RSS)
        assert _TestRSSConnector in rss_cap


# ===================================================================
# Connector Factory
# ===================================================================


class TestConnectorFactory:
    def test_create_from_authority(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth = _make_authority(parser="html", capabilities=["html", "search"])
        connector = factory.create(auth)
        assert isinstance(connector, _TestHTMLConnector)

    def test_create_all(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        registry.register(_TestRSSConnector)
        factory = ConnectorFactory(registry)
        auth1 = _make_authority(parser="html", capabilities=["html"])
        auth2 = _make_authority(parser="rss", capabilities=["rss"])
        connectors = factory.create_all([auth1, auth2])
        assert len(connectors) == 2

    def test_create_all_partial_failure(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth1 = _make_authority(parser="html", capabilities=["html"])
        auth2 = _make_authority(parser="rss", capabilities=["rss"])
        with pytest.raises(UnsupportedConnectorError):
            factory.create_all([auth1, auth2])

    def test_unsupported_parser_raises(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth = _make_authority(parser="api", capabilities=["api"])
        with pytest.raises(UnsupportedConnectorError):
            factory.create(auth)

    def test_resolves_best_match(self):
        registry = ConnectorRegistry()
        registry.register(_GenericHTMLConnector)
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth = _make_authority(parser="html", capabilities=["html", "search"])
        connector = factory.create(auth)
        assert isinstance(connector, _TestHTMLConnector)

    def test_empty_registry_raises(self):
        registry = ConnectorRegistry()
        factory = ConnectorFactory(registry)
        auth = _make_authority(parser="html", capabilities=["html"])
        with pytest.raises(UnsupportedConnectorError):
            factory.create(auth)

    def test_create_with_enabled_authority(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth = _make_authority(parser="html", capabilities=["html", "search"], enabled=True)
        connector = factory.create(auth)
        assert isinstance(connector, _TestHTMLConnector)

    def test_factory_injects_authority(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth = _make_authority(id="specific", parser="html", capabilities=["html"])
        connector = factory.create(auth)
        assert connector.authority.id == "specific"

    def test_best_match_scoring_values(self):
        from src.connectors.scoring import (
            CAPABILITY_MATCH_SCORE,
            EXACT_PARSER_MATCH_SCORE,
            FULL_COMPATIBILITY_BONUS,
        )

        assert isinstance(EXACT_PARSER_MATCH_SCORE, int)
        assert isinstance(CAPABILITY_MATCH_SCORE, int)
        assert isinstance(FULL_COMPATIBILITY_BONUS, int)
        assert EXACT_PARSER_MATCH_SCORE > 0
        assert CAPABILITY_MATCH_SCORE > 0
        assert FULL_COMPATIBILITY_BONUS > 0

    def test_best_match_known_scores(self):
        from src.connectors.scoring import (
            CAPABILITY_MATCH_SCORE,
            EXACT_PARSER_MATCH_SCORE,
            FULL_COMPATIBILITY_BONUS,
        )

        registry = ConnectorRegistry()
        registry.register(_GenericHTMLConnector)
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth = _make_authority(parser="html", capabilities=["html", "search"])

        generic_score = EXACT_PARSER_MATCH_SCORE
        test_score = (
            EXACT_PARSER_MATCH_SCORE + 2 * CAPABILITY_MATCH_SCORE + FULL_COMPATIBILITY_BONUS
        )
        assert test_score > generic_score

        connector = factory.create(auth)
        assert isinstance(connector, _TestHTMLConnector)

    def test_no_identical_scoring_connector_selected(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        registry.register(_TestRSSConnector)
        factory = ConnectorFactory(registry)
        auth = _make_authority(parser="html", capabilities=["html", "search"])
        connector = factory.create(auth)
        assert isinstance(connector, _TestHTMLConnector)

    def test_deterministic_ordering_same_score(self):
        registry = ConnectorRegistry()
        registry.register(_GenericHTMLConnector)
        factory = ConnectorFactory(registry)
        auth = _make_authority(parser="html", capabilities=["html"])
        results = []
        for _ in range(10):
            connector = factory.create(auth)
            results.append(type(connector).__name__)
        assert len(set(results)) == 1


# ===================================================================
# Connector Manager
# ===================================================================


class TestConnectorManager:
    def test_get_connector(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth_id = _write_authority_yaml(
            Path(tmpdir), id="man_test", parser="html", capabilities=["html", "search"]
        )
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        connector = manager.get_connector(auth_id)
        assert isinstance(connector, _TestHTMLConnector)
        assert connector.initialized

    def test_get_connector_reuses_instance(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth_id = _write_authority_yaml(
            Path(tmpdir), id="reuse", parser="html", capabilities=["html", "search"]
        )
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        c1 = manager.get_connector(auth_id)
        c2 = manager.get_connector(auth_id)
        assert c1 is c2

    def test_list_authorities(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth_id = _write_authority_yaml(
            Path(tmpdir), id="list_me", parser="html", capabilities=["html"]
        )
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        manager.get_connector(auth_id)
        assert auth_id in manager.list_authorities()

    def test_health(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth_id = _write_authority_yaml(
            Path(tmpdir), id="health_test", parser="html", capabilities=["html"]
        )
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        manager.get_connector(auth_id)
        health = manager.health(auth_id)
        assert auth_id in health
        assert health[auth_id].available

    def test_health_all(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        aid1 = _write_authority_yaml(Path(tmpdir), id="ha1", parser="html", capabilities=["html"])
        aid2 = _write_authority_yaml(Path(tmpdir), id="ha2", parser="html", capabilities=["html"])
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        manager.get_connector(aid1)
        manager.get_connector(aid2)
        health = manager.health()
        assert len(health) == 2

    def test_shutdown_single(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth_id = _write_authority_yaml(
            Path(tmpdir), id="shut", parser="html", capabilities=["html"]
        )
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        connector = manager.get_connector(auth_id)
        manager.shutdown(auth_id)
        assert auth_id not in manager.list_authorities()
        assert connector._closed

    def test_shutdown_all(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        aid1 = _write_authority_yaml(Path(tmpdir), id="sa1", parser="html", capabilities=["html"])
        aid2 = _write_authority_yaml(Path(tmpdir), id="sa2", parser="html", capabilities=["html"])
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        manager.get_connector(aid1)
        manager.get_connector(aid2)
        manager.shutdown()
        assert manager.list_authorities() == []

    def test_stats_after_creation(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth_id = _write_authority_yaml(
            Path(tmpdir), id="stat1", parser="html", capabilities=["html"]
        )
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        manager.get_connector(auth_id)
        assert manager.stats.created == 1
        assert manager.stats.lookups == 1

    def test_stats_after_shutdown(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth_id = _write_authority_yaml(
            Path(tmpdir), id="stat2", parser="html", capabilities=["html"]
        )
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        manager.get_connector(auth_id)
        manager.shutdown(auth_id)
        assert manager.stats.shutdowns == 1
        assert manager.stats.active_connectors == 0

    def test_stats_snapshot(self, tmpdir: Path):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        auth_id = _write_authority_yaml(
            Path(tmpdir), id="snap", parser="html", capabilities=["html"]
        )
        resolver = _resolver_for(Path(tmpdir))
        manager = ConnectorManager(factory, registry, resolver=resolver)
        manager.get_connector(auth_id)
        snap = manager.stats.snapshot()
        assert snap["created"] == 1
        assert snap["active"] == 1

    def test_get_connector_nonexistent_authority(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        manager = ConnectorManager(factory, registry)
        with pytest.raises(Exception):
            manager.get_connector("nonexistent")

    def test_health_for_unknown_authority(self):
        registry = ConnectorRegistry()
        registry.register(_TestHTMLConnector)
        factory = ConnectorFactory(registry)
        manager = ConnectorManager(factory, registry)
        assert manager.health("unknown") == {}

    def test_shutdown_nonexistent_no_error(self):
        registry = ConnectorRegistry()
        factory = ConnectorFactory(registry)
        manager = ConnectorManager(factory, registry)
        manager.shutdown("nonexistent")

    def test_stats_record_error(self):
        stats = ConnectorManager(
            ConnectorFactory(ConnectorRegistry()),
            ConnectorRegistry(),
        ).stats
        stats.record_error("something broke")
        assert stats.errors == 1
        assert stats.last_error == "something broke"
        assert stats.last_error_at is not None
