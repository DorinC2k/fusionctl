from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal
from enum import Enum


class LogPeriod(str, Enum):
    CURRENT_WEEK = "current-week"
    CURRENT_MONTH = "current-month"
    LAST_MONTH = "last-month"


@dataclass(frozen=True)
class PeriodBounds:
    start: Date
    end: Date


@dataclass(frozen=True)
class PlannedLogEntry:
    date: Date
    hours: Decimal
    project: str
    task: str
    notes: str | None


def period_bounds(period: LogPeriod, *, today: Date | None = None) -> PeriodBounds:
    """Return the date bounds for a convenience log period."""
    today = today or Date.today()

    if period is LogPeriod.CURRENT_WEEK:
        start = today - timedelta(days=today.weekday())
        return PeriodBounds(start=start, end=today)

    if period is LogPeriod.CURRENT_MONTH:
        return PeriodBounds(start=today.replace(day=1), end=today)

    first_this_month = today.replace(day=1)
    last_previous_month = first_this_month - timedelta(days=1)
    first_previous_month = last_previous_month.replace(day=1)
    return PeriodBounds(start=first_previous_month, end=last_previous_month)


def working_days_between(start: Date, end: Date) -> list[Date]:
    """Return Monday-Friday dates in an inclusive date range."""
    if start > end:
        raise ValueError("Start date must be before or equal to end date")

    days: list[Date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def plan_period_logs(
    period: LogPeriod,
    *,
    hours: Decimal,
    project: str,
    task: str,
    notes: str | None = None,
    today: Date | None = None,
) -> list[PlannedLogEntry]:
    """Expand a convenience period into one planned regular-work log per working day."""
    if hours <= 0:
        raise ValueError("Hours must be greater than zero")
    if hours > Decimal("24"):
        raise ValueError("Hours cannot exceed 24 per day")

    bounds = period_bounds(period, today=today)
    return [
        PlannedLogEntry(
            date=entry_date,
            hours=hours,
            project=project,
            task=task,
            notes=notes,
        )
        for entry_date in working_days_between(bounds.start, bounds.end)
    ]
