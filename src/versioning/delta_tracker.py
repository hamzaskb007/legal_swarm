from __future__ import annotations
from typing import Any
from src.schema.schema import ChangeType, FieldDelta, RegulatoryEntry, VersionRecord

TRACKED_FIELDS = [
    "jurisdiction_code",
    "jurisdiction_name",
    "tier",
    "primary_regulator",
    "secondary_regulators",
    "passporting_available",
    "withholding_tax_rate",
    "tax_summary",
    "aml_kyc_framework",
]


def _get(obj: Any, field: str) -> Any:
    return getattr(obj, field, None)


def _bump_version(v: str) -> str:
    parts = v.split(".")
    if len(parts) != 3:
        return "1.0.1"
    try:
        parts[2] = str(int(parts[2]) + 1)
    except ValueError:
        parts[2] = "1"
    return ".".join(parts)


class DeltaTracker:
    def __init__(self, tracked_fields: list[str] | None = None):
        self.tracked_fields = tracked_fields or TRACKED_FIELDS

    def compute_delta(
        self,
        old_entry: RegulatoryEntry,
        new_entry: RegulatoryEntry,
        author: str = "system",
        change_summary: str | None = None,
    ) -> VersionRecord:
        deltas: list[FieldDelta] = []
        for field in self.tracked_fields:
            old_val = _get(old_entry, field)
            new_val = _get(new_entry, field)
            if old_val is None and new_val is not None:
                ct = ChangeType.ADDED
            elif old_val is not None and new_val is None:
                ct = ChangeType.REMOVED
            elif str(old_val) != str(new_val):
                ct = ChangeType.MODIFIED
            else:
                continue
            deltas.append(
                FieldDelta(field_path=field, change_type=ct, old_value=old_val, new_value=new_val)
            )

        return VersionRecord(
            version_id=_bump_version(old_entry.version.version_id),
            previous_version_id=old_entry.version.version_id,
            author=author,
            change_summary=change_summary or f"{len(deltas)} field(s) changed",
            deltas=deltas,
        )
