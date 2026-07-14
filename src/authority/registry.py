from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.authority.jurisdiction import normalize_jurisdiction
from src.authority.models import (
    Authority,
    AuthorityLevel,
    CapabilityType,
    DocumentType,
    ParserType,
    VersionInfo,
)


YAML_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "authorities"


class HealthDiagnostic(BaseModel):
    total_authorities: int = 0
    duplicate_ids: list[str] = Field(default_factory=list)
    duplicate_urls: list[str] = Field(default_factory=list)
    invalid_yaml: list[str] = Field(default_factory=list)
    invalid_endpoint_types: list[str] = Field(default_factory=list)
    invalid_parser_types: list[str] = Field(default_factory=list)
    invalid_jurisdictions: list[str] = Field(default_factory=list)
    deprecated_authorities: list[str] = Field(default_factory=list)
    orphan_relationships: list[str] = Field(default_factory=list)
    missing_metadata: list[str] = Field(default_factory=list)
    invalid_reliability: list[str] = Field(default_factory=list)
    invalid_capabilities: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    healthy: bool = True


class AuthorityRegistry:
    def __init__(self, yaml_dir: str | Path | None = None) -> None:
        self._authorities: dict[str, Authority] = {}
        self._hierarchical_index: dict[str, str] = {}
        self._yaml_dir = Path(yaml_dir) if yaml_dir else YAML_DIR
        self._load_all()

    def _load_all(self) -> None:
        yaml_files = sorted(self._yaml_dir.glob("*.yaml"))
        if not yaml_files:
            raise FileNotFoundError(f"No YAML authority files found in {self._yaml_dir}")

        loaded: list[Authority] = []
        for path in yaml_files:
            try:
                with open(path) as f:
                    data = yaml.safe_load(f)
                authority = Authority.model_validate(data)
                loaded.append(authority)
            except Exception as e:
                raise ValueError(f"Failed to load {path.name}: {e}")

        self._validate(loaded)

        for a in loaded:
            self._authorities[a.id] = a
            if a.hierarchical_id:
                self._hierarchical_index[a.hierarchical_id] = a.id

    @staticmethod
    def _validate(authorities: list[Authority]) -> None:
        ids: set[str] = set()
        hierarchical_ids: set[str] = set()
        names: set[str] = set()
        urls: set[str] = set()

        for a in authorities:
            if a.id in ids:
                raise ValueError(f"Duplicate authority id: {a.id}")
            ids.add(a.id)

            if a.hierarchical_id:
                if a.hierarchical_id in hierarchical_ids:
                    raise ValueError(f"Duplicate hierarchical id: {a.hierarchical_id}")
                hierarchical_ids.add(a.hierarchical_id)

            if a.name.lower() in names:
                raise ValueError(f"Duplicate authority name: {a.name}")
            names.add(a.name.lower())

            for ep in a.endpoints:
                if ep.url in urls:
                    raise ValueError(f"Duplicate endpoint URL for {a.id}: {ep.url}")
                urls.add(ep.url)

    def get_by_id(self, authority_id: str) -> Authority:
        if authority_id in self._hierarchical_index:
            return self._authorities[self._hierarchical_index[authority_id]]
        if authority_id not in self._authorities:
            raise KeyError(f"Unknown authority id: {authority_id}")
        return self._authorities[authority_id]

    def get_all(self) -> list[Authority]:
        return list(self._authorities.values())

    def get_by_jurisdiction(self, jurisdiction: str) -> list[Authority]:
        norm = normalize_jurisdiction(jurisdiction)
        return [a for a in self._authorities.values() if a.jurisdiction == norm]

    def get_by_level(self, level: int | AuthorityLevel) -> list[Authority]:
        if isinstance(level, int):
            level = AuthorityLevel(level)
        return [a for a in self._authorities.values() if a.level == level]

    def get_enabled(self) -> list[Authority]:
        return [a for a in self._authorities.values() if a.enabled]

    def get_by_name(self, name: str, case_sensitive: bool = False) -> Authority | None:
        for a in self._authorities.values():
            if case_sensitive and a.name == name:
                return a
            if not case_sensitive and a.name.lower() == name.lower():
                return a
        return None

    def get_by_endpoint_type(self, endpoint_type: str) -> list[Authority]:
        return [a for a in self._authorities.values() if a.get_endpoint_url(endpoint_type) is not None]

    def get_by_document_type(self, doc_type: str | DocumentType) -> list[Authority]:
        dt = doc_type.value if isinstance(doc_type, DocumentType) else doc_type
        return [a for a in self._authorities.values() if dt in [d.value if hasattr(d, 'value') else d for d in a.document_types]]

    def get_relationship_targets(self, authority_id: str, rel_type: str | None = None) -> list[Authority]:
        auth = self.get_by_id(authority_id)
        targets: list[Authority] = []
        for rel in auth.relationships:
            if rel_type is None or rel.type.value == rel_type:
                try:
                    targets.append(self.get_by_id(rel.target_id))
                except KeyError:
                    continue
        return targets

    def health(self) -> HealthDiagnostic:
        diag = HealthDiagnostic()
        all_ids: list[str] = []
        all_urls: list[str] = []
        authority_ids = set(self._authorities.keys())
        known_endpoint_types = {"homepage", "legislation", "rules", "guidance", "api", "rss", "search", "filings", "enforcement", "news", "consultation", "forms"}
        valid_capabilities = {c.value for c in CapabilityType}

        for a in self._authorities.values():
            all_ids.append(a.id)
            all_urls.extend(ep.url for ep in a.endpoints)

        id_counts = Counter(all_ids)
        url_counts = Counter(all_urls)

        diag.duplicate_ids = [k for k, v in id_counts.items() if v > 1]
        diag.duplicate_urls = [k for k, v in url_counts.items() if v > 1]

        for a in self._authorities.values():
            if a.version.deprecated:
                diag.deprecated_authorities.append(a.id)

            for ep in a.endpoints:
                if ep.type not in known_endpoint_types:
                    diag.invalid_endpoint_types.append(f"{a.id}:{ep.type}")

            for rel in a.relationships:
                if rel.target_id not in authority_ids:
                    diag.orphan_relationships.append(f"{a.id} -> {rel.target_id} ({rel.type.value})")

            if not a.metadata:
                diag.missing_metadata.append(a.id)

            for cap in a.capabilities:
                cap_val = cap.value if hasattr(cap, 'value') else cap
                if cap_val not in valid_capabilities:
                    diag.invalid_capabilities.append(f"{a.id}:{cap_val}")

        if any([diag.duplicate_ids, diag.duplicate_urls, diag.orphan_relationships,
                diag.invalid_endpoint_types, diag.invalid_capabilities]):
            diag.healthy = False

        diag.total_authorities = len(self._authorities)
        return diag

    def get_version_history(self, authority_id: str) -> VersionInfo | None:
        try:
            return self.get_by_id(authority_id).version
        except KeyError:
            return None

    def __len__(self) -> int:
        return len(self._authorities)

    def __contains__(self, authority_id: str) -> bool:
        return authority_id in self._authorities or authority_id in self._hierarchical_index
