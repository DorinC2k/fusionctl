from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

PUBLIC_HOLIDAY_DISPLAY = "Public Holiday"


def entries_to_preserve_on_clear(entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return Oracle entries that must survive a user-requested card clear."""
    return [dict(entry) for entry in entries if should_preserve_on_clear(entry)]


def should_preserve_on_clear(entry: Mapping[str, Any]) -> bool:
    """Preserve Oracle-owned non-working rows, but allow user-entered work rows to clear."""
    return bool(entry.get("AbsenceEntryFlag")) or _has_public_holiday_time_type(entry)


def _has_public_holiday_time_type(entry: Mapping[str, Any]) -> bool:
    for field in _field_values(entry):
        if field.get("DisplayValue") == PUBLIC_HOLIDAY_DISPLAY:
            return True
        if field.get("Value") == PUBLIC_HOLIDAY_DISPLAY:
            return True
    return False


def _field_values(entry: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    values = entry.get("timeCardFieldValues")
    if isinstance(values, Mapping):
        items = values.get("items", [])
        if isinstance(items, list):
            return [item for item in items if isinstance(item, Mapping)]
    if isinstance(values, list):
        return [item for item in values if isinstance(item, Mapping)]
    return []
