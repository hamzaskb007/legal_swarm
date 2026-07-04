"""Unit tests for audit logger."""

import pytest
from src.audit.logger import AuditLogger
from src.schema.schema import AuditEventType


class TestAuditLogger:
    def test_log_writes_to_file(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="test")
        assert log_path.exists()
        assert log_path.stat().st_size > 0

    def test_read_all_returns_entries(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="test")
        logger.log(event_type=AuditEventType.QUERY, actor="test")
        entries = logger.read_all()
        assert len(entries) == 2

    def test_append_only(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="test")
        logger.log(event_type=AuditEventType.QUERY, actor="test")
        entries = logger.read_all()
        assert len(entries) == 2

    def test_read_by_jurisdiction(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="test", jurisdiction_code="AE")
        logger.log(event_type=AuditEventType.VALIDATION, actor="test", jurisdiction_code="KY")
        result = logger.read_by_jurisdiction("AE")
        assert len(result) == 1
        assert result[0].jurisdiction_code == "AE"

    def test_read_by_event_type(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="test")
        logger.log(event_type=AuditEventType.QUERY, actor="test")
        result = logger.read_by_event_type(AuditEventType.QUERY)
        assert len(result) == 1

    def test_empty_log_returns_empty_list(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        assert logger.read_all() == []

    def test_log_entry_is_immutable(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(event_type=AuditEventType.VALIDATION, actor="test")
        with pytest.raises(Exception):
            entry.actor = "modified"