from __future__ import annotations
from pathlib import Path
from typing import Any
from uuid import UUID
from src.schema.schema import AuditEventType, AuditLogEntry


class AuditLogger:
    def __init__(self, log_path: Path = Path("logs/audit.jsonl")):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event_type: AuditEventType, actor: str,
            jurisdiction_code: str | None = None, entry_id: UUID | None = None,
            payload: dict[str, Any] | None = None, outcome: str | None = None) -> AuditLogEntry:
        record = AuditLogEntry(
            event_type=event_type, actor=actor,
            jurisdiction_code=jurisdiction_code, entry_id=entry_id,
            payload=payload or {}, outcome=outcome,
        )
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")
        return record

    def read_all(self) -> list[AuditLogEntry]:
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(AuditLogEntry.model_validate_json(line))
        return entries
    
    def read_by_jurisdiction(self, jurisdiction_code: str) -> list[AuditLogEntry]:
        return [e for e in self.read_all() if e.jurisdiction_code == jurisdiction_code]

    def read_by_event_type(self, event_type: AuditEventType) -> list[AuditLogEntry]:
        return [e for e in self.read_all() if e.event_type == event_type]