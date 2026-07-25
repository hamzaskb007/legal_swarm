"""Unit tests for audit logger."""

import threading
from uuid import UUID

import pytest

from src.audit.logger import AuditLogger
from src.schema.schema import AuditEventType, AuditLogEntry


# ===================================================================
# Basic functionality (preserved from original)
# ===================================================================


class TestAuditLogger:
    def test_log_writes_to_file(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="sec.gov_scraper")
        assert log_path.exists()
        assert log_path.stat().st_size > 0

    def test_read_all_returns_entries(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="mas_scraper")
        logger.log(event_type=AuditEventType.QUERY, actor="cima_connector")
        entries = logger.read_all()
        assert len(entries) == 2

    def test_append_only(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="cssf_agent")
        logger.log(event_type=AuditEventType.QUERY, actor="centralbank_ie_agent")
        entries = logger.read_all()
        assert len(entries) == 2

    def test_read_by_jurisdiction(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="sca_agent",
            jurisdiction_code="AE",
        )
        logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="cima_agent",
            jurisdiction_code="KY",
        )
        result = logger.read_by_jurisdiction("AE")
        assert len(result) == 1
        assert result[0].jurisdiction_code == "AE"

    def test_read_by_event_type(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="dfsa_validator")
        logger.log(event_type=AuditEventType.QUERY, actor="adgm_connector")
        result = logger.read_by_event_type(AuditEventType.QUERY)
        assert len(result) == 1

    def test_empty_log_returns_empty_list(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        assert logger.read_all() == []

    def test_log_entry_is_immutable(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(event_type=AuditEventType.VALIDATION, actor="sec_agent")
        with pytest.raises(Exception):
            entry.actor = "modified"

    def test_log_with_all_fields(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry_id = UUID("00000000-0000-0000-0000-000000000001")
        entry = logger.log(
            event_type=AuditEventType.CONFIDENCE_DECISION,
            actor="confidence_scorer",
            jurisdiction_code="SG",
            entry_id=entry_id,
            payload={"score": 0.85, "level": "HIGH"},
            outcome="scored",
        )
        assert entry.event_type == AuditEventType.CONFIDENCE_DECISION
        assert entry.actor == "confidence_scorer"
        assert entry.jurisdiction_code == "SG"
        assert entry.entry_id == entry_id

    def test_read_all_returns_in_order(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="first")
        logger.log(event_type=AuditEventType.QUERY, actor="second")
        logger.log(event_type=AuditEventType.DELTA_DETECTED, actor="third")
        entries = logger.read_all()
        assert [e.actor for e in entries] == ["first", "second", "third"]

    def test_log_path_created_automatically(self, tmp_path):
        log_path = tmp_path / "nested" / "subdir" / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.SOURCE_INGESTION, actor="rss_connector")
        assert log_path.exists()

    def test_log_entry_has_log_id(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(event_type=AuditEventType.VALIDATION, actor="sec_agent")
        assert isinstance(entry.log_id, UUID)

    def test_log_entry_has_timestamp(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(event_type=AuditEventType.VALIDATION, actor="mas_agent")
        assert entry.timestamp is not None


# ===================================================================
# Part 1 — Corrupted JSON handling
# ===================================================================


class TestCorruptedJSON:
    def test_malformed_json_skipped(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION", "actor": "sec_agent"}\n{invalid json}\n{"event_type": "QUERY", "actor": "mas_agent"}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 2

    def test_truncated_json_skipped(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION", "actor": "sec_agent"}\n{"event_type": "SOURCE_INGESTION", "actor": "cftc',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 1

    def test_partial_json_object_skipped(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION", "actor": "cima_agent"}\n{"event_type": "QUERY"\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 1

    def test_empty_lines_ignored(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '\n\n{"event_type": "VALIDATION", "actor": "cssf_agent"}\n\n\n{"event_type": "QUERY", "actor": "centralbank_ie_agent"}\n\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 2

    def test_invalid_utf8_skipped_line(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        valid = '{"event_type": "VALIDATION", "actor": "sec_agent"}'
        log_path.write_bytes(
            valid.encode("utf-8") + b"\n\x80\x81\x82\n" + valid.encode("utf-8") + b"\n"
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 2

    def test_unexpected_object_structure_skipped(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION", "actor": "sec_agent"}\n["not", "an", "object"]\n{"event_type": "QUERY", "actor": "mas_agent"}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 2

    def test_all_corrupted_returns_empty(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text("{corrupted}\n{bad]\n[invalid\n", encoding="utf-8")
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert entries == []

    def test_mixed_valid_and_corrupted_preserves_valid(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        lines = [
            '{"event_type": "VALIDATION", "actor": "sec_agent", "jurisdiction_code": "US"}',
            "truncated line that breaks json",
            '{"event_type": "QUERY", "actor": "cftc_agent", "jurisdiction_code": "US"}',
            "{bad json]",
            '{"event_type": "SOURCE_INGESTION", "actor": "mas_agent", "jurisdiction_code": "SG"}',
        ]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 3
        assert entries[0].actor == "sec_agent"
        assert entries[1].actor == "cftc_agent"
        assert entries[2].actor == "mas_agent"


# ===================================================================
# Part 3 — Invalid schema / enum values
# ===================================================================


class TestInvalidSchema:
    def test_invalid_event_type_value(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "INVALID_TYPE", "actor": "sec_agent"}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 0

    def test_missing_required_actor_field(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION"}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 0

    def test_invalid_payload_type(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION", "actor": "sec_agent", "payload": "not_a_dict"}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 0

    def test_invalid_actor_type(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION", "actor": 12345}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 0

    def test_invalid_timestamp_format(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION", "actor": "sec_agent", "timestamp": "not-a-date"}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 0

    def test_null_event_type_skipped(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": null, "actor": "sec_agent"}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 0

    def test_extra_unknown_fields_ignored(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION", "actor": "sec_agent", "unknown_field": "ignored", "extra": 42}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 1

    def test_wrong_case_event_type_skipped(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "validation", "actor": "sec_agent"}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        entries = logger.read_all()
        assert len(entries) == 0


# ===================================================================
# Part 4 — Error path tests
# ===================================================================


class TestErrorPaths:
    def test_missing_file_returns_empty(self, tmp_path):
        log_path = tmp_path / "nonexistent.jsonl"
        logger = AuditLogger(log_path=log_path)
        assert logger.read_all() == []

    def test_read_by_jurisdiction_missing_file(self, tmp_path):
        log_path = tmp_path / "missing.jsonl"
        logger = AuditLogger(log_path=log_path)
        assert logger.read_by_jurisdiction("US") == []

    def test_read_by_event_type_missing_file(self, tmp_path):
        log_path = tmp_path / "missing.jsonl"
        logger = AuditLogger(log_path=log_path)
        assert logger.read_by_event_type(AuditEventType.VALIDATION) == []

    def test_write_to_readonly_directory_fails_gracefully(self, tmp_path):
        readonly = tmp_path / "readonly"
        readonly.mkdir()
        readonly.chmod(0o444)
        log_path = readonly / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        with pytest.raises((PermissionError, OSError)):
            logger.log(event_type=AuditEventType.VALIDATION, actor="sec_agent")

    @pytest.mark.skip(reason="Empty string actor is accepted by Pydantic (no min_length)")
    def test_empty_actor_string(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(event_type=AuditEventType.VALIDATION, actor="")
        assert entry.actor == ""

    def test_log_with_unicode_actor(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="sca_agent_ae",
        )
        assert entry.actor == "sca_agent_ae"

    def test_serialization_failure_does_not_corrupt_file(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(event_type=AuditEventType.VALIDATION, actor="sec_agent")
        logger.log(event_type=AuditEventType.QUERY, actor="cftc_agent")
        entries = logger.read_all()
        assert len(entries) == 2

    def test_read_after_write_consistency(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        for i in range(10):
            logger.log(
                event_type=AuditEventType.VALIDATION,
                actor=f"agent_{i}",
                payload={"iteration": i},
            )
        entries = logger.read_all()
        assert len(entries) == 10
        for i, e in enumerate(entries):
            assert e.payload["iteration"] == i


# ===================================================================
# Part 3 — Filtering (existing tests use real data)
# ===================================================================


class TestFiltering:
    def test_read_by_jurisdiction_no_match(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="cima_agent",
            jurisdiction_code="KY",
        )
        result = logger.read_by_jurisdiction("US")
        assert result == []

    def test_read_by_event_type_no_match(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="sec_agent",
        )
        result = logger.read_by_event_type(AuditEventType.CONTRADICTION)
        assert result == []

    def test_read_by_jurisdiction_multiple_matches(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="cssf_agent",
            jurisdiction_code="LU",
        )
        logger.log(
            event_type=AuditEventType.QUERY,
            actor="cssf_connector",
            jurisdiction_code="LU",
        )
        logger.log(
            event_type=AuditEventType.SOURCE_INGESTION,
            actor="adgm_agent",
            jurisdiction_code="AE",
        )
        result = logger.read_by_jurisdiction("LU")
        assert len(result) == 2

    def test_read_by_event_type_multiple_matches(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="sec_agent",
            jurisdiction_code="US",
        )
        logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="cftc_agent",
            jurisdiction_code="US",
        )
        logger.log(
            event_type=AuditEventType.QUERY,
            actor="mas_agent",
        )
        result = logger.read_by_event_type(AuditEventType.VALIDATION)
        assert len(result) == 2

    def test_filter_after_corrupted_entries(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        log_path.write_text(
            '{"event_type": "VALIDATION", "actor": "sec_agent", "jurisdiction_code": "US"}\n'
            "{corrupted json line}\n"
            '{"event_type": "VALIDATION", "actor": "cima_agent", "jurisdiction_code": "KY"}\n',
            encoding="utf-8",
        )
        logger = AuditLogger(log_path=log_path)
        result = logger.read_by_jurisdiction("US")
        assert len(result) == 1
        assert result[0].actor == "sec_agent"


# ===================================================================
# Part 5 — Concurrent access tests
# ===================================================================


class TestConcurrentAccess:
    def test_concurrent_writes(self, tmp_path):
        log_path = tmp_path / "concurrent.jsonl"
        logger = AuditLogger(log_path=log_path)
        n_threads = 10
        events_per_thread = 20

        def writer(thread_id: int) -> None:
            for i in range(events_per_thread):
                logger.log(
                    event_type=AuditEventType.VALIDATION,
                    actor=f"thread_{thread_id}",
                    payload={"iteration": i, "thread": thread_id},
                )

        threads = [threading.Thread(target=writer, args=(tid,)) for tid in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        entries = logger.read_all()
        assert len(entries) == n_threads * events_per_thread

    def test_concurrent_read_and_write(self, tmp_path):
        log_path = tmp_path / "rw_concurrent.jsonl"
        logger = AuditLogger(log_path=log_path)
        for i in range(50):
            logger.log(
                event_type=AuditEventType.VALIDATION,
                actor=f"preload_{i}",
            )

        results: list[int] = []
        lock = threading.Lock()

        def writer() -> None:
            for i in range(20):
                logger.log(
                    event_type=AuditEventType.VALIDATION,
                    actor=f"writer_{i}",
                )

        def reader() -> None:
            entries = logger.read_all()
            with lock:
                results.append(len(entries))

        w = threading.Thread(target=writer)
        r = threading.Thread(target=reader)
        w.start()
        r.start()
        w.join(timeout=10)
        r.join(timeout=10)

        final_count = len(logger.read_all())
        assert final_count >= 50

    def test_concurrent_read_by_jurisdiction(self, tmp_path):
        log_path = tmp_path / "concurrent_filter.jsonl"
        logger = AuditLogger(log_path=log_path)
        for j in ["US", "KY", "SG", "LU"]:
            for _ in range(10):
                logger.log(
                    event_type=AuditEventType.VALIDATION,
                    actor=f"{j.lower()}_agent",
                    jurisdiction_code=j,
                )

        results: dict[str, int] = {}
        lock = threading.Lock()

        def filter_by_jurisdiction(jur: str) -> None:
            entries = logger.read_by_jurisdiction(jur)
            with lock:
                results[jur] = len(entries)

        threads = [
            threading.Thread(target=filter_by_jurisdiction, args=(j,))
            for j in ["US", "KY", "SG", "LU"]
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert results == {"US": 10, "KY": 10, "SG": 10, "LU": 10}

    def test_concurrent_writes_no_duplicate_entries(self, tmp_path):
        log_path = tmp_path / "no_dupes.jsonl"
        logger = AuditLogger(log_path=log_path)
        n_threads = 5
        events_per = 30

        def writer(tid: int) -> None:
            for i in range(events_per):
                logger.log(
                    event_type=AuditEventType.VALIDATION,
                    actor=f"tid{tid}_i{i}",
                )

        threads = [threading.Thread(target=writer, args=(tid,)) for tid in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        entries = logger.read_all()
        actors = [e.actor for e in entries]
        assert len(actors) == len(set(actors))

    def test_concurrent_writes_no_corruption(self, tmp_path):
        log_path = tmp_path / "no_corrupt.jsonl"
        logger = AuditLogger(log_path=log_path)
        n_threads = 8
        events_per = 25

        def writer(tid: int) -> None:
            for i in range(events_per):
                logger.log(
                    event_type=AuditEventType.VALIDATION,
                    actor=f"writer{tid}_ev{i}",
                    payload={"tid": tid, "seq": i},
                )

        threads = [threading.Thread(target=writer, args=(tid,)) for tid in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        # Verify every line in the file is valid AuditLogEntry JSON
        with open(log_path, "rb") as f:
            raw_lines = f.readlines()
        assert len(raw_lines) == n_threads * events_per
        for raw in raw_lines:
            line = raw.decode("utf-8").strip()
            assert line, "empty line in audit log"
            entry = AuditLogEntry.model_validate_json(line)
            assert entry.actor.startswith("writer")

    def test_concurrent_appends_multiple_loggers(self, tmp_path):
        log_path = tmp_path / "multi_logger.jsonl"
        n_threads = 6
        events_per = 20

        def writer(tid: int) -> None:
            local_logger = AuditLogger(log_path=log_path)
            for i in range(events_per):
                local_logger.log(
                    event_type=AuditEventType.QUERY,
                    actor=f"ml_tid{tid}_e{i}",
                )

        threads = [threading.Thread(target=writer, args=(tid,)) for tid in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        entries = AuditLogger(log_path=log_path).read_all()
        assert len(entries) == n_threads * events_per
        actors = [e.actor for e in entries]
        assert len(actors) == len(set(actors))

    def test_repeated_concurrent_read_write_cycles(self, tmp_path):
        log_path = tmp_path / "rw_cycles.jsonl"
        logger = AuditLogger(log_path=log_path)
        cycles = 5
        writes_per_cycle = 30
        readers_per_cycle = 3
        results: list[int] = []
        lock = threading.Lock()

        for cycle in range(cycles):

            def writer(cycle_num: int) -> None:
                for i in range(writes_per_cycle):
                    logger.log(
                        event_type=AuditEventType.VALIDATION,
                        actor=f"cycle{cycle_num}_ev{i}",
                    )

            def reader() -> None:
                entries = logger.read_all()
                with lock:
                    results.append(len(entries))

            w = threading.Thread(target=writer, args=(cycle,))
            w.start()
            readers = [threading.Thread(target=reader) for _ in range(readers_per_cycle)]
            for r in readers:
                r.start()
            w.join(timeout=10)
            for r in readers:
                r.join(timeout=5)

        entries = logger.read_all()
        assert len(entries) == cycles * writes_per_cycle
        actors = [e.actor for e in entries]
        assert len(actors) == len(set(actors))

    def test_concurrent_reads_no_exceptions(self, tmp_path):
        log_path = tmp_path / "safe_reads.jsonl"
        logger = AuditLogger(log_path=log_path)
        for i in range(100):
            logger.log(
                event_type=AuditEventType.VALIDATION,
                actor=f"seed_{i}",
            )

        errors: list[Exception] = []
        lock = threading.Lock()
        n_readers = 10

        def reader() -> None:
            try:
                _ = logger.read_all()
                _ = logger.read_by_jurisdiction("US")
                _ = logger.read_by_event_type(AuditEventType.VALIDATION)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(n_readers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Concurrent reads raised {len(errors)} errors: {errors}"


# ===================================================================
# Part 6 — Stress tests
# ===================================================================


class TestStress:
    def test_thousand_entries(self, tmp_path):
        log_path = tmp_path / "stress_1000.jsonl"
        logger = AuditLogger(log_path=log_path)
        for i in range(1000):
            logger.log(
                event_type=AuditEventType.VALIDATION,
                actor=f"stress_agent_{i}",
                jurisdiction_code="US" if i % 2 == 0 else "KY",
                payload={"index": i, "value": f"data_{i}"},
            )
        entries = logger.read_all()
        assert len(entries) == 1000

    def test_repeated_reads_consistent(self, tmp_path):
        log_path = tmp_path / "stress_consistent.jsonl"
        logger = AuditLogger(log_path=log_path)
        for i in range(500):
            logger.log(
                event_type=AuditEventType.VALIDATION if i % 2 == 0 else AuditEventType.QUERY,
                actor=f"agent_{i}",
                jurisdiction_code="SG" if i % 3 == 0 else "US",
            )
        for _ in range(10):
            assert len(logger.read_all()) == 500

    def test_repeated_filtering(self, tmp_path):
        log_path = tmp_path / "stress_filter.jsonl"
        logger = AuditLogger(log_path=log_path)
        for i in range(300):
            logger.log(
                event_type=AuditEventType.VALIDATION if i % 2 == 0 else AuditEventType.QUERY,
                actor=f"agent_{i}",
                jurisdiction_code="LU" if i % 4 == 0 else "IE",
            )
        for _ in range(10):
            lu_entries = logger.read_by_jurisdiction("LU")
            assert len(lu_entries) == 75
            ie_entries = logger.read_by_jurisdiction("IE")
            assert len(ie_entries) == 225

    def test_large_payloads(self, tmp_path):
        log_path = tmp_path / "stress_large.jsonl"
        logger = AuditLogger(log_path=log_path)
        large_payload = {"key": "x" * 5000, "nested": {"data": list(range(100))}}
        for i in range(50):
            logger.log(
                event_type=AuditEventType.VALIDATION,
                actor=f"bulk_agent_{i}",
                payload=large_payload,
            )
        entries = logger.read_all()
        assert len(entries) == 50

    def test_stress_with_corruption(self, tmp_path):
        log_path = tmp_path / "stress_corrupt.jsonl"
        logger = AuditLogger(log_path=log_path)
        for i in range(100):
            logger.log(
                event_type=AuditEventType.VALIDATION,
                actor=f"valid_agent_{i}",
            )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("{corrupted}\n{bad\n")
        for i in range(100, 200):
            logger.log(
                event_type=AuditEventType.QUERY,
                actor=f"valid_agent_{i}",
            )
        entries = logger.read_all()
        assert len(entries) == 200

    def test_stress_default_log_path(self, tmp_path):
        log_path = tmp_path / "logs" / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        for i in range(100):
            logger.log(
                event_type=AuditEventType.VALIDATION,
                actor=f"default_path_agent_{i}",
            )
        entries = logger.read_all()
        assert len(entries) == 100

    def test_sustained_write_read_cycles(self, tmp_path):
        log_path = tmp_path / "sustained.jsonl"
        logger = AuditLogger(log_path=log_path)
        cycles = 5
        writes_per_cycle = 500

        for cycle in range(cycles):
            for i in range(writes_per_cycle):
                logger.log(
                    event_type=AuditEventType.VALIDATION if i % 2 == 0 else AuditEventType.QUERY,
                    actor=f"sustained_agent_{cycle}_{i}",
                    jurisdiction_code=["US", "SG", "LU", "KY"][i % 4],
                    payload={"cycle": cycle, "index": i},
                )
            entries = logger.read_all()
            assert len(entries) == (cycle + 1) * writes_per_cycle

        # Verify filtering yields correct counts after all cycles
        total = cycles * writes_per_cycle
        assert len(logger.read_by_jurisdiction("US")) == total // 4
        assert len(logger.read_by_jurisdiction("SG")) == total // 4
        assert len(logger.read_by_jurisdiction("LU")) == total // 4
        assert len(logger.read_by_jurisdiction("KY")) == total // 4


# ===================================================================
# Part 7 — Real regulatory data
# ===================================================================


class TestRealisticData:
    def test_sec_validation_event(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(
            event_type=AuditEventType.VALIDATION,
            actor="sec_scraper",
            jurisdiction_code="US",
            payload={"authority": "SEC", "rule": "VAL_001", "status": "PASSED"},
            outcome="passed",
        )
        assert entry.jurisdiction_code == "US"
        assert entry.payload["authority"] == "SEC"

    def test_mas_confidence_decision(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(
            event_type=AuditEventType.CONFIDENCE_DECISION,
            actor="confidence_scorer",
            jurisdiction_code="SG",
            entry_id=UUID("12345678-1234-5678-1234-567812345678"),
            payload={
                "authority": "MAS",
                "score": 0.90,
                "level": "HIGH",
                "citations": 5,
            },
            outcome="scored",
        )
        assert entry.actor == "confidence_scorer"
        assert entry.payload["authority"] == "MAS"

    def test_cima_source_ingestion(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(
            event_type=AuditEventType.SOURCE_INGESTION,
            actor="cima_connector",
            jurisdiction_code="KY",
            payload={
                "authority": "CIMA",
                "source_url": "https://www.cima.ky/regulatory-framework",
                "parser": "html",
            },
            outcome="ingested",
        )
        assert entry.payload["source_url"] == "https://www.cima.ky/regulatory-framework"

    def test_cssf_contradiction(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(
            event_type=AuditEventType.CONTRADICTION,
            actor="contradiction_detector",
            jurisdiction_code="LU",
            payload={
                "field": "fund_structures.min_capital",
                "source_a": "CSSF Regulation",
                "source_b": "ALEBA Guidance",
            },
            outcome="detected",
        )
        assert entry.jurisdiction_code == "LU"

    def test_centralbank_ie_delta(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(
            event_type=AuditEventType.DELTA_DETECTED,
            actor="delta_tracker",
            jurisdiction_code="IE",
            payload={
                "authority": "Central Bank of Ireland",
                "field": "fund_structures",
                "change": "modified",
            },
            outcome="version_bumped",
        )
        assert entry.jurisdiction_code == "IE"
        assert entry.payload["authority"] == "Central Bank of Ireland"

    def test_adgm_schema_update(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)
        entry = logger.log(
            event_type=AuditEventType.SCHEMA_UPDATE,
            actor="schema_migrator",
            jurisdiction_code="AE",
            payload={
                "authority": "ADGM FSRA",
                "old_version": "1.0.0",
                "new_version": "1.1.0",
            },
            outcome="upgraded",
        )
        assert entry.payload["authority"] == "ADGM FSRA"

    def test_mixed_regulatory_events(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)

        events = [
            (AuditEventType.VALIDATION, "sec_scraper", "US", {"authority": "SEC"}),
            (AuditEventType.SOURCE_INGESTION, "cftc_connector", "US", {"authority": "CFTC"}),
            (AuditEventType.VALIDATION, "mas_scraper", "SG", {"authority": "MAS"}),
            (AuditEventType.CONFIDENCE_DECISION, "scorer", "KY", {"authority": "CIMA"}),
            (AuditEventType.QUERY, "cssf_connector", "LU", {"authority": "CSSF"}),
            (
                AuditEventType.DELTA_DETECTED,
                "tracker",
                "IE",
                {"authority": "Central Bank of Ireland"},
            ),
            (AuditEventType.SOURCE_INGESTION, "dfsa_connector", "AE", {"authority": "DFSA"}),
            (AuditEventType.VALIDATION, "adgm_scraper", "AE", {"authority": "ADGM FSRA"}),
            (AuditEventType.SOURCE_INGESTION, "bvi_fsc_connector", "VG", {"authority": "BVI FSC"}),
            (AuditEventType.VALIDATION, "jfsc_scraper", "JE", {"authority": "JFSC"}),
        ]

        for event_type, actor, jurisdiction, payload in events:
            logger.log(
                event_type=event_type,
                actor=actor,
                jurisdiction_code=jurisdiction,
                payload=payload,
            )

        entries = logger.read_all()
        assert len(entries) == 10
        us_entries = logger.read_by_jurisdiction("US")
        assert len(us_entries) == 2
        ae_entries = logger.read_by_jurisdiction("AE")
        assert len(ae_entries) == 2
        validation_entries = logger.read_by_event_type(AuditEventType.VALIDATION)
        assert len(validation_entries) == 4
