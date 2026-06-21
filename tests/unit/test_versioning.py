"""Unit tests for delta tracker."""

import pytest
from src.versioning.delta_tracker import DeltaTracker, _bump_version
from src.schema.schema import ChangeType
from tests.unit.test_schema import make_entry


class TestBumpVersion:
    def test_bumps_patch(self):
        assert _bump_version("1.0.0") == "1.0.1"
        assert _bump_version("1.0.9") == "1.0.10"

    def test_invalid_version_returns_default(self):
        assert _bump_version("invalid") == "1.0.1"


class TestDeltaTracker:
    def test_no_deltas_identical_entries(self):
        entry = make_entry()
        tracker = DeltaTracker()
        record = tracker.compute_delta(entry, entry)
        assert record.deltas == []

    def test_detects_regulator_change(self):
        old = make_entry(primary_regulator="SCA")
        new = make_entry(primary_regulator="DFSA")
        tracker = DeltaTracker(tracked_fields=["primary_regulator"])
        record = tracker.compute_delta(old, new)
        assert len(record.deltas) == 1
        assert record.deltas[0].field_path == "primary_regulator"
        assert record.deltas[0].change_type == ChangeType.MODIFIED
        assert record.deltas[0].old_value == "SCA"
        assert record.deltas[0].new_value == "DFSA"

    def test_version_bumped(self):
        old = make_entry(primary_regulator="SCA")
        new = make_entry(primary_regulator="DFSA")
        tracker = DeltaTracker(tracked_fields=["primary_regulator"])
        record = tracker.compute_delta(old, new)
        assert record.version_id == "1.0.1"
        assert record.previous_version_id == "1.0.0"

    def test_author_recorded(self):
        entry = make_entry()
        tracker = DeltaTracker()
        record = tracker.compute_delta(entry, entry, author="test-agent")
        assert record.author == "test-agent"

    def test_change_summary_auto_generated(self):
        old = make_entry(primary_regulator="SCA")
        new = make_entry(primary_regulator="DFSA")
        tracker = DeltaTracker(tracked_fields=["primary_regulator"])
        record = tracker.compute_delta(old, new)
        assert "1" in record.change_summary