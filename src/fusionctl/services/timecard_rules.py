from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal

from fusionctl.models.timesheet import TimeEntry, TimeType

PUBLIC_HOLIDAY_CARRYOVER_HOURS = Decimal("1")


@dataclass(frozen=True)
class TimeAllocation:
    """Hours to create for one date and Oracle time type."""

    date: Date
    hours: Decimal
    time_type: TimeType


def allocate_regular_day(
    entry_date: Date,
    hours: Decimal,
    existing_entries: list[TimeEntry],
) -> list[TimeAllocation]:
    """Split a working day before a public holiday into regular and holiday time."""
    if hours <= 0:
        raise ValueError("Hours must be greater than zero")
    if _has_prefilled_non_working_entry(existing_entries, entry_date):
        return []
    if not _is_working_day(entry_date):
        return [TimeAllocation(date=entry_date, hours=hours, time_type=TimeType.REGULAR)]

    next_day = entry_date + timedelta(days=1)
    if _has_public_holiday(existing_entries, next_day):
        if hours <= PUBLIC_HOLIDAY_CARRYOVER_HOURS:
            raise ValueError("Hours must be greater than 1 before a public holiday")
        return [
            TimeAllocation(
                date=entry_date,
                hours=hours - PUBLIC_HOLIDAY_CARRYOVER_HOURS,
                time_type=TimeType.REGULAR,
            ),
            TimeAllocation(
                date=entry_date,
                hours=PUBLIC_HOLIDAY_CARRYOVER_HOURS,
                time_type=TimeType.PUBLIC_HOLIDAY,
            ),
        ]

    return [TimeAllocation(date=entry_date, hours=hours, time_type=TimeType.REGULAR)]


def _has_public_holiday(entries: list[TimeEntry], target_date: Date) -> bool:
    return any(
        entry.date == target_date and entry.time_type == TimeType.PUBLIC_HOLIDAY
        for entry in entries
    )


def _has_prefilled_non_working_entry(entries: list[TimeEntry], target_date: Date) -> bool:
    return any(
        entry.date == target_date
        and (entry.time_type == TimeType.PUBLIC_HOLIDAY or entry.is_prefilled_absence)
        for entry in entries
    )


def _is_working_day(target_date: Date) -> bool:
    return target_date.weekday() < 5
