"""Unit tests for the Authority Registry and Resolver (expanded)."""

from pathlib import Path

import pytest
import yaml

from src.authority.discovery import AuthorityDiscovery
from src.authority.models import (
    Authority,
    AuthorityLevel,
    CapabilityType,
    DocumentType,
    Endpoint,
    ParserType,
    Relationship,
    RelationshipType,
)
from src.authority.registry import AuthorityRegistry
from src.authority.reliability import ReliabilityConfig, ReliabilityScorer
from src.authority.resolver import AuthorityResolver
from src.authority.jurisdiction import normalize_jurisdiction
from src.schema.schema import SourceAuthority


_COUNTER = 0


def _authority(**overrides) -> dict:
    global _COUNTER
    _COUNTER += 1
    n = _COUNTER
    base = {
        "id": f"test_reg{n}",
        "jurisdiction": "XX",
        "name": f"Test Regulator {n}",
        "level": 1,
        "authority_type": "regulator",
        "base_url": f"https://www.testreg{n}.gov",
        "search_url": f"https://www.testreg{n}.gov/search",
        "parser": "html",
        "refresh_interval": 24,
        "reliability_score": 0.95,
        "enabled": True,
        "metadata": {"country": "Testland", "acronym": "TR"},
    }
    base.update(**overrides)
    return base


def _write_yaml(tmpdir: Path, data: dict, filename: str = "test.yaml") -> Path:
    path = tmpdir / filename
    with open(path, "w") as f:
        yaml.dump(data, f)
    return path


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestAuthorityLevel:
    def test_level_values(self):
        assert AuthorityLevel.LEVEL_1.value == 1
        assert AuthorityLevel.LEVEL_5.value == 5

    def test_to_source_authority_mapping(self):
        assert AuthorityLevel.LEVEL_1.to_source_authority() == SourceAuthority.PRIMARY
        assert AuthorityLevel.LEVEL_2.to_source_authority() == SourceAuthority.PRIMARY
        assert AuthorityLevel.LEVEL_3.to_source_authority() == SourceAuthority.PRIMARY
        assert AuthorityLevel.LEVEL_4.to_source_authority() == SourceAuthority.SECONDARY
        assert AuthorityLevel.LEVEL_5.to_source_authority() == SourceAuthority.TERTIARY

    def test_label(self):
        assert "Official regulator" in AuthorityLevel.LEVEL_1.label
        assert "Recognized legal firm" in AuthorityLevel.LEVEL_4.label
        assert "Professional advisory" in AuthorityLevel.LEVEL_5.label


class TestParserType:
    def test_values(self):
        assert ParserType.HTML == "html"
        assert ParserType.PDF == "pdf"
        assert ParserType.API == "api"
        assert ParserType.RSS == "rss"
        assert ParserType.MANUAL == "manual"


class TestDocumentType:
    def test_values(self):
        assert DocumentType.ACT == "Act"
        assert DocumentType.REGULATION == "Regulation"
        assert DocumentType.GUIDANCE == "Guidance"
        assert DocumentType.CIRCULAR == "Circular"
        assert DocumentType.DIRECTIVE == "Directive"


class TestCapabilityType:
    def test_values(self):
        assert CapabilityType.HTML == "html"
        assert CapabilityType.PDF == "pdf"
        assert CapabilityType.API == "api"
        assert CapabilityType.RSS == "rss"
        assert CapabilityType.JSON == "json"
        assert CapabilityType.SEARCH == "search"
        assert CapabilityType.DOWNLOAD == "download"


class TestRelationshipType:
    def test_values(self):
        assert RelationshipType.PUBLISHES == "publishes"
        assert RelationshipType.ENFORCES == "enforces"
        assert RelationshipType.SUPERSEDES == "supersedes"


# ---------------------------------------------------------------------------
# Authority Model
# ---------------------------------------------------------------------------


class TestAuthorityModel:
    def test_valid_authority(self):
        a = Authority.model_validate(_authority())
        assert a.id.startswith("test_reg")
        assert a.jurisdiction == "XX"
        assert a.level == AuthorityLevel.LEVEL_1
        assert a.reliability_score == 0.95
        assert a.base_reliability == 0.95
        assert a.enabled is True

    def test_hierarchical_id_generated(self):
        a = Authority.model_validate(_authority(id="myreg", jurisdiction="GB"))
        assert a.hierarchical_id == "authority.gb.myreg"

    def test_hierarchical_id_preserved(self):
        a = Authority.model_validate(_authority(hierarchical_id="custom.id"))
        assert a.hierarchical_id == "custom.id"

    def test_endpoints_migrated_from_legacy(self):
        a = Authority.model_validate(
            _authority(base_url="https://example.gov", search_url="https://example.gov/search")
        )
        urls = {ep.type: ep.url for ep in a.endpoints}
        assert urls["homepage"] == "https://example.gov"
        assert urls["search"] == "https://example.gov/search"

    def test_capabilities_migrated(self):
        a = Authority.model_validate(_authority(parser="rss"))
        assert CapabilityType.RSS in a.capabilities

    def test_no_capabilities_for_manual(self):
        a = Authority.model_validate(_authority(parser="manual", capabilities=[]))
        assert a.capabilities == []

    def test_to_source_authority_primary(self):
        a = Authority.model_validate(_authority())
        assert a.to_source_authority() == SourceAuthority.PRIMARY

    def test_to_source_authority_secondary(self):
        a = Authority.model_validate(_authority(level=4))
        assert a.to_source_authority() == SourceAuthority.SECONDARY

    def test_to_source_authority_tertiary(self):
        a = Authority.model_validate(_authority(level=5))
        assert a.to_source_authority() == SourceAuthority.TERTIARY

    def test_reliability_score_validation(self):
        with pytest.raises(Exception):
            Authority.model_validate(_authority(reliability_score=1.5))

    def test_get_endpoint_url(self):
        a = Authority.model_validate(
            _authority(endpoints=[Endpoint(type="homepage", url="https://example.gov")])
        )
        assert a.get_endpoint_url("homepage") == "https://example.gov"
        assert a.get_endpoint_url("nonexistent") is None

    def test_has_capability(self):
        a = Authority.model_validate(
            _authority(capabilities=[CapabilityType.API, CapabilityType.RSS])
        )
        assert a.has_capability(CapabilityType.API)
        assert a.has_capability("api")
        assert not a.has_capability(CapabilityType.PDF)

    def test_version_defaults(self):
        a = Authority.model_validate(_authority())
        assert a.version.version == "1.0.0"
        assert a.version.deprecated is False

    def test_relationships(self):
        a = Authority.model_validate(
            _authority(
                relationships=[Relationship(type=RelationshipType.PUBLISHES, target_id="some_doc")]
            )
        )
        assert len(a.relationships) == 1
        assert a.relationships[0].type == RelationshipType.PUBLISHES

    def test_document_types(self):
        a = Authority.model_validate(
            _authority(document_types=[DocumentType.ACT, DocumentType.REGULATION])
        )
        assert DocumentType.ACT in a.document_types


class TestJurisdictionNormalization:
    def test_canonical_code(self):
        assert normalize_jurisdiction("US") == "US"

    def test_alias_full_name(self):
        assert normalize_jurisdiction("united states") == "US"
        assert normalize_jurisdiction("United Kingdom") == "GB"

    def test_alias_common(self):
        assert normalize_jurisdiction("uk") == "GB"
        assert normalize_jurisdiction("uae") == "AE"
        assert normalize_jurisdiction("bvi") == "VG"

    def test_unknown_returns_uppercase(self):
        assert normalize_jurisdiction("zz") == "ZZ"

    def test_case_insensitive(self):
        assert normalize_jurisdiction("Cayman Islands") == "KY"
        assert normalize_jurisdiction("SINGAPORE") == "SG"

    def test_trailing_whitespace(self):
        assert normalize_jurisdiction("  jersey  ") == "JE"


# ---------------------------------------------------------------------------
# Authority Registry
# ---------------------------------------------------------------------------


class TestAuthorityRegistry:
    def test_load_single(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="abc"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        assert len(registry) == 1
        assert "abc" in registry

    def test_get_by_id(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="findme"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        a = registry.get_by_id("findme")
        assert a is not None

    def test_get_by_hierarchical_id(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(
            tmp,
            _authority(id="myreg", jurisdiction="GB", hierarchical_id="authority.gb.myreg"),
            "reg.yaml",
        )
        registry = AuthorityRegistry(yaml_dir=tmp)
        a = registry.get_by_id("authority.gb.myreg")
        assert a.id == "myreg"

    def test_get_by_id_unknown(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="known"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        with pytest.raises(KeyError):
            registry.get_by_id("nonexistent")

    def test_get_by_jurisdiction(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="a", jurisdiction="XX", name="A"), "a.yaml")
        _write_yaml(tmp, _authority(id="b", jurisdiction="YY", name="B"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        assert len(registry.get_by_jurisdiction("XX")) == 1
        assert len(registry.get_by_jurisdiction("YY")) == 1

    def test_get_by_jurisdiction_with_alias(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="reg", jurisdiction="GB", name="GB Reg"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        assert len(registry.get_by_jurisdiction("uk")) == 1
        assert len(registry.get_by_jurisdiction("united kingdom")) == 1

    def test_get_by_level(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="l1", level=1, name="L1"), "a.yaml")
        _write_yaml(tmp, _authority(id="l4", level=4, name="L4"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        assert len(registry.get_by_level(AuthorityLevel.LEVEL_1)) == 1
        assert len(registry.get_by_level(AuthorityLevel.LEVEL_4)) == 1

    def test_get_enabled(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="on", enabled=True, name="On"), "a.yaml")
        _write_yaml(tmp, _authority(id="off", enabled=False, name="Off"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        enabled = registry.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].id == "on"

    def test_get_by_name(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="byname", name="Unique Name"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        a = registry.get_by_name("Unique Name")
        assert a is not None
        assert a.id == "byname"

    def test_get_by_name_case_insensitive(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="caseid", name="Case Name"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        a = registry.get_by_name("case name")
        assert a is not None
        assert a.id == "caseid"

    def test_get_by_name_not_found(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="exist"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        assert registry.get_by_name("Nonexistent") is None

    def test_get_all(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="a", name="A"), "a.yaml")
        _write_yaml(tmp, _authority(id="b", name="B"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        assert len(registry.get_all()) == 2

    def test_duplicate_id_rejected(self, tmpdir: Path):
        tmp = Path(tmpdir)
        data = _authority(id="dup")
        _write_yaml(tmp, data, "a.yaml")
        _write_yaml(tmp, data, "b.yaml")
        with pytest.raises(ValueError, match="Duplicate authority id"):
            AuthorityRegistry(yaml_dir=tmp)

    def test_duplicate_name_rejected(self, tmpdir: Path):
        tmp = Path(tmpdir)
        data = _authority(id="a", name="Same")
        _write_yaml(tmp, data, "a.yaml")
        dup = dict(data, id="b", base_url="https://other.gov")
        _write_yaml(tmp, dup, "b.yaml")
        with pytest.raises(ValueError, match="Duplicate authority name"):
            AuthorityRegistry(yaml_dir=tmp)

    def test_duplicate_hierarchical_id_rejected(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="a", name="A", hierarchical_id="same.id"), "a.yaml")
        _write_yaml(tmp, _authority(id="b", name="B", hierarchical_id="same.id"), "b.yaml")
        with pytest.raises(ValueError, match="Duplicate hierarchical id"):
            AuthorityRegistry(yaml_dir=tmp)

    def test_duplicate_endpoint_url_rejected(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(
            tmp,
            _authority(
                id="a", name="A", endpoints=[{"type": "homepage", "url": "https://shared.gov"}]
            ),
            "a.yaml",
        )
        _write_yaml(
            tmp,
            _authority(
                id="b", name="B", endpoints=[{"type": "homepage", "url": "https://shared.gov"}]
            ),
            "b.yaml",
        )
        with pytest.raises(ValueError, match="Duplicate endpoint URL"):
            AuthorityRegistry(yaml_dir=tmp)

    def test_no_yaml_files_raises(self, tmpdir: Path):
        with pytest.raises(FileNotFoundError):
            AuthorityRegistry(yaml_dir=Path(tmpdir))

    def test_contains(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="present"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        assert "present" in registry
        assert "missing" not in registry

    def test_len(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="a", name="A"), "a.yaml")
        _write_yaml(tmp, _authority(id="b", name="B"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        assert len(registry) == 2

    def test_get_by_endpoint_type(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(
            tmp,
            _authority(
                id="has_api",
                name="API Source",
                endpoints=[{"type": "api", "url": "https://api.gov"}],
            ),
            "a.yaml",
        )
        _write_yaml(tmp, _authority(id="no_api", name="No API"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        found = registry.get_by_endpoint_type("api")
        assert len(found) == 1
        assert found[0].id == "has_api"

    def test_load_real_config(self):
        registry = AuthorityRegistry()
        assert len(registry) >= 14
        assert "sec" in registry
        assert "cima" in registry
        assert "authority.us.sec" in registry


class TestRegistryHealth:
    def test_healthy(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="healthy"), "h.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        diag = registry.health()
        assert diag.healthy is True

    def test_detects_deprecated(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="active", name="Active"), "a.yaml")
        _write_yaml(
            tmp,
            _authority(
                id="old",
                name="Old",
                version={
                    "version": "0.9.0",
                    "deprecated": True,
                    "created": "2020-01-01T00:00:00",
                    "updated": "2020-01-01T00:00:00",
                },
            ),
            "b.yaml",
        )
        registry = AuthorityRegistry(yaml_dir=tmp)
        diag = registry.health()
        assert "old" in diag.deprecated_authorities

    def test_detects_missing_metadata(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="minimal", name="Min", metadata={}), "a.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        diag = registry.health()
        assert "minimal" in diag.missing_metadata


# ---------------------------------------------------------------------------
# Authority Resolver
# ---------------------------------------------------------------------------


class TestAuthorityResolver:
    def test_get_primary_authority(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="primary", level=1, name="Primary"), "a.yaml")
        # Add a level 4 that should NOT be primary
        _write_yaml(tmp, _authority(id="legal", level=4, name="Legal"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        primary = resolver.get_primary_authority("XX")
        assert primary is not None
        assert primary.id == "primary"

    def test_get_primary_authority_no_match(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="reg"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        assert resolver.get_primary_authority("ZZ") is None

    def test_get_all_authorities(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="a", name="A"), "a.yaml")
        _write_yaml(tmp, _authority(id="b", name="B"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        assert len(resolver.get_all_authorities("XX")) == 2

    def test_get_by_level_int(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="l1", level=1, name="L1"), "a.yaml")
        _write_yaml(tmp, _authority(id="l4", level=4, name="L4"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        assert len(resolver.get_by_level(1)) == 1
        assert len(resolver.get_by_level(AuthorityLevel.LEVEL_4)) == 1

    def test_get_enabled(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="on", enabled=True, name="On"), "a.yaml")
        _write_yaml(tmp, _authority(id="off", enabled=False, name="Off"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        assert len(resolver.get_enabled()) == 1

    def test_resolve_for_citation(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="cite"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        auth = resolver.resolve_for_citation("cite")
        assert auth.id == "cite"

    def test_get_endpoint(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(
            tmp,
            _authority(id="ep_test", endpoints=[{"type": "api", "url": "https://api.example.gov"}]),
            "reg.yaml",
        )
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        assert resolver.get_endpoint("ep_test", "api") == "https://api.example.gov"
        assert resolver.get_endpoint("ep_test", "nonexistent") is None

    def test_get_by_name(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="named", name="Findable Reg"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        a = resolver.get_by_name("Findable Reg")
        assert a is not None
        assert a.id == "named"

    def test_create_citation_uses_defaults(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="cit", name="Citation Source"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        cit = resolver.create_citation("cit", section_reference="Sec 1")
        assert cit.authority_id == "cit"
        assert cit.authority == SourceAuthority.PRIMARY
        assert cit.authority_level == 1
        assert cit.reliability_score == 0.95
        assert cit.section_reference == "Sec 1"

    def test_create_citation_overrides(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="over"), "reg.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        resolver = AuthorityResolver(registry)
        cit = resolver.create_citation(
            "over",
            source_name="Custom Name",
            source_url="https://custom.xx",
            authority_level=2,
            reliability_score=0.80,
            regulatory_relevance_tag="Test",
        )
        assert cit.source_name == "Custom Name"
        assert cit.source_url == "https://custom.xx"
        assert cit.authority_level == 2
        assert cit.reliability_score == 0.80
        assert cit.regulatory_relevance_tag == "Test"


# ---------------------------------------------------------------------------
# Authority Discovery
# ---------------------------------------------------------------------------


class TestAuthorityDiscovery:
    def test_discover_primary(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="primary", level=1, name="Primary"), "a.yaml")
        _write_yaml(tmp, _authority(id="legal", level=4, name="Legal"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        discovery = AuthorityDiscovery(registry)
        primary = discovery.discover_primary("XX")
        assert primary is not None
        assert primary.id == "primary"

    def test_discover_legislation(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(
            tmp,
            _authority(
                id="has_leg",
                name="Has Leg",
                endpoints=[{"type": "legislation", "url": "https://law.gov"}],
            ),
            "a.yaml",
        )
        _write_yaml(tmp, _authority(id="no_leg", name="No Leg"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        discovery = AuthorityDiscovery(registry)
        found = discovery.discover_legislation("XX")
        assert found is not None
        assert found.id == "has_leg"

    def test_discover_search(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(
            tmp,
            _authority(
                id="s",
                name="S",
                endpoints=[
                    {"type": "homepage", "url": "https://home.gov"},
                    {"type": "search", "url": "https://search.gov"},
                ],
            ),
            "a.yaml",
        )
        registry = AuthorityRegistry(yaml_dir=tmp)
        discovery = AuthorityDiscovery(registry)
        result = discovery.discover_search("XX")
        assert result.homepage_url == "https://home.gov"
        assert result.search_url == "https://search.gov"

    def test_discover_rss(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="rss_auth", name="RSS Src", capabilities=["rss"]), "a.yaml")
        _write_yaml(tmp, _authority(id="no_rss", name="No RSS"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        discovery = AuthorityDiscovery(registry)
        rss = discovery.discover_rss("XX")
        assert len(rss) == 1
        assert rss[0].id == "rss_auth"

    def test_discover_all(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="a", name="A"), "a.yaml")
        _write_yaml(tmp, _authority(id="b", name="B"), "b.yaml")
        _write_yaml(tmp, _authority(id="off", enabled=False, name="Off"), "c.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        discovery = AuthorityDiscovery(registry)
        all_a = discovery.discover_all("XX")
        assert len(all_a) == 2

    def test_discover_by_capability(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(
            tmp, _authority(id="api_src", name="API Source", capabilities=["api"]), "a.yaml"
        )
        _write_yaml(tmp, _authority(id="no_api", name="No API"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        discovery = AuthorityDiscovery(registry)
        found = discovery.discover_by_capability(CapabilityType.API)
        assert len(found) == 1


# ---------------------------------------------------------------------------
# Reliability Scorer
# ---------------------------------------------------------------------------


class TestReliabilityScorer:
    def test_score_with_base_authority(self):
        config = ReliabilityConfig()
        scorer = ReliabilityScorer(config)
        authority = Authority.model_validate(
            _authority(level=1, authority_type="regulator", reliability_score=0.95)
        )
        result = scorer.score(authority)
        assert 0.0 <= result.score <= 1.0
        assert len(result.contributing_factors) >= 5

    def test_lower_level_lower_score(self):
        config = ReliabilityConfig()
        scorer = ReliabilityScorer(config)
        high = Authority.model_validate(_authority(id="h", level=1, authority_type="regulator"))
        low = Authority.model_validate(_authority(id="l", level=5, authority_type="advisory"))
        high_result = scorer.score(high)
        low_result = scorer.score(low)
        assert high_result.score >= low_result.score

    def test_freshness_boost(self):
        config = ReliabilityConfig()
        scorer = ReliabilityScorer(config)
        authority = Authority.model_validate(_authority())
        from datetime import datetime, timedelta

        fresh = scorer.score(authority, publication_date=datetime.utcnow())
        stale = scorer.score(authority, publication_date=datetime.utcnow() - timedelta(days=2000))
        assert fresh.freshness_score >= stale.freshness_score

    def test_document_type_impact(self):
        config = ReliabilityConfig()
        scorer = ReliabilityScorer(config)
        authority = Authority.model_validate(_authority())
        act = scorer.score(authority, document_type="Act")
        faq = scorer.score(authority, document_type="FAQ")
        assert act.publication_type_score >= faq.publication_type_score

    def test_completeness_boost(self):
        config = ReliabilityConfig()
        scorer = ReliabilityScorer(config)
        authority = Authority.model_validate(_authority())
        complete = scorer.score(authority, has_section_reference=True, has_excerpt=True)
        incomplete = scorer.score(authority, has_section_reference=False, has_excerpt=False)
        assert complete.completeness_score > incomplete.completeness_score

    def test_verification_impact(self):
        config = ReliabilityConfig()
        scorer = ReliabilityScorer(config)
        authority = Authority.model_validate(_authority())
        verified = scorer.score(authority, verification_success=True)
        unverified = scorer.score(authority, verification_success=False)
        assert verified.verification_score > unverified.verification_score

    def test_config_customization(self):
        config = ReliabilityConfig(level_weight=0.5, freshness_weight=0.05)
        scorer = ReliabilityScorer(config)
        authority = Authority.model_validate(_authority(level=1))
        result = scorer.score(authority)
        assert result.level_score > 0
        assert result.freshness_score >= 0

    def test_deterministic(self):
        config = ReliabilityConfig()
        scorer = ReliabilityScorer(config)
        authority = Authority.model_validate(_authority())
        r1 = scorer.score(authority)
        r2 = scorer.score(authority)
        assert r1.score == r2.score


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------


class TestHealthChecks:
    def test_health_check_healthy(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="h1", name="H1"), "a.yaml")
        _write_yaml(tmp, _authority(id="h2", name="H2"), "b.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        diag = registry.health()
        assert diag.healthy is True

    def test_deprecated_in_report(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(
            tmp,
            _authority(
                id="dep",
                name="Dep",
                version={
                    "version": "0.5.0",
                    "deprecated": True,
                    "created": "2020-01-01T00:00:00",
                    "updated": "2020-01-01T00:00:00",
                },
            ),
            "a.yaml",
        )
        registry = AuthorityRegistry(yaml_dir=tmp)
        diag = registry.health()
        assert "dep" in diag.deprecated_authorities

    def test_missing_metadata_in_report(self, tmpdir: Path):
        tmp = Path(tmpdir)
        _write_yaml(tmp, _authority(id="meta", name="Meta", metadata={}), "a.yaml")
        registry = AuthorityRegistry(yaml_dir=tmp)
        diag = registry.health()
        assert "meta" in diag.missing_metadata
