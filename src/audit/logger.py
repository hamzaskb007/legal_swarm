from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from src.schema.schema import AuditEventType, AuditLogEntry

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self, log_path: Path = Path("logs/audit.jsonl")):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event_type: AuditEventType,
        actor: str,
        jurisdiction_code: str | None = None,
        entry_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
        outcome: str | None = None,
    ) -> AuditLogEntry:
        record = AuditLogEntry(
            event_type=event_type,
            actor=actor,
            jurisdiction_code=jurisdiction_code,
            entry_id=entry_id,
            payload=payload or {},
            outcome=outcome,
        )
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
        return record

    def read_all(self) -> list[AuditLogEntry]:
        if not self.log_path.exists():
            return []
        entries: list[AuditLogEntry] = []
        with open(self.log_path, "rb") as f:
            for line_no, raw_line in enumerate(f, start=1):
                try:
                    line = raw_line.decode("utf-8").strip()
                except UnicodeDecodeError:
                    logger.warning("Skipping corrupted audit log entry at line %d", line_no)
                    continue
                if not line:
                    continue
                try:
                    entry = self._parse_line(line, line_no)
                    if entry is not None:
                        entries.append(entry)
                except (json.JSONDecodeError, ValidationError):
                    logger.warning("Skipping corrupted audit log entry at line %d", line_no)
        return entries

    def read_by_jurisdiction(self, jurisdiction_code: str) -> list[AuditLogEntry]:
        return self._filter(lambda e: e.jurisdiction_code == jurisdiction_code)

    def read_by_event_type(self, event_type: AuditEventType) -> list[AuditLogEntry]:
        return self._filter(lambda e: e.event_type == event_type)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _filter(self, predicate: Callable[[AuditLogEntry], bool]) -> list[AuditLogEntry]:
        return [e for e in self.read_all() if predicate(e)]

    def _parse_line(self, raw: str, line_no: int) -> AuditLogEntry | None:
        return AuditLogEntry.model_validate_json(raw)
