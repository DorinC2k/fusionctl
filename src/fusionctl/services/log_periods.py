from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from decimal import Decimal
from enum import Enum

from fusionctl.models.timesheet import TimeType

LOCATION_WORK_FROM_HOME = "Work from home"
LOCATION_WORK_FROM_OFFICE = "Work from office (employment contract)"
PUBLIC_HOLIDAY_CARRYOVER_HOURS = Decimal("1")


class LogPeriod(str, Enum):
    CURRENT_WEEK = "current-week"
    CURRENT_MONTH = "current-month"
    LAST_MONTH = "last-month"


class WorkPattern(str, Enum):
    OFFICE = "office"
    HOME = "home"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class PeriodBounds:
    start: Date
    end: Date


@dataclass(frozen=True)
class PlannedLogEntry:
    date: Date
    hours: Decimal
    time_type: TimeType
    project: str
    task: str
    location: str
    notes: str | None


def period_bounds(period: LogPeriod, *, today: Date | None = None) -> PeriodBounds:
    """Return the date bounds for a convenience log period."""
    today = today or Date.today()

    if period is LogPeriod.CURRENT_WEEK:
        start = today - timedelta(days=today.weekday())
        return PeriodBounds(start=start, end=today)

    if period is LogPeriod.CURRENT_MONTH:
        first_day = today.replace(day=1)
        next_month = _first_day_of_next_month(first_day)
        last_day = next_month - timedelta(days=1)
        return PeriodBounds(
            start=_week_start(first_day),
            end=_week_end(last_day),
        )

    first_this_month = today.replace(day=1)
    last_previous_month = first_this_month - timedelta(days=1)
    first_previous_month = last_previous_month.replace(day=1)
    return PeriodBounds(start=first_previous_month, end=last_previous_month)


def _first_day_of_next_month(value: Date) -> Date:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1, day=1)
    return value.replace(month=value.month + 1, day=1)


def _week_start(value: Date) -> Date:
    return value - timedelta(days=value.weekday())


def _week_end(value: Date) -> Date:
    return _week_start(value) + timedelta(days=6)


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
    location: str | None = None,
    work_pattern: WorkPattern = WorkPattern.OFFICE,
    work_from_home_days: int = 2,
    holiday_dates: set[Date] | None = None,
    notes: str | None = None,
    today: Date | None = None,
) -> list[PlannedLogEntry]:
    """Expand a convenience period into one planned regular-work log per working day."""
    if hours <= 0:
        raise ValueError("Hours must be greater than zero")
    if hours > Decimal("24"):
        raise ValueError("Hours cannot exceed 24 per day")
    if work_from_home_days < 0 or work_from_home_days > 5:
        raise ValueError("Work-from-home days must be between 0 and 5")

    bounds = period_bounds(period, today=today)
    working_days = working_days_between(bounds.start, bounds.end)
    return [
        entry
        for entry_date in working_days
        for entry in _entries_for_day(
            entry_date,
            hours=hours,
            project=project,
            task=task,
            location=_location_for_day(
                entry_date,
                explicit_location=location,
                work_pattern=work_pattern,
                work_from_home_days=work_from_home_days,
                period_working_days=working_days,
            ),
            holiday_dates=holiday_dates or set(),
            notes=notes,
        )
    ]


def _entries_for_day(
    entry_date: Date,
    *,
    hours: Decimal,
    project: str,
    task: str,
    location: str,
    holiday_dates: set[Date],
    notes: str | None,
) -> list[PlannedLogEntry]:
    carryover_holiday_count = _carryover_holiday_count(entry_date, holiday_dates)
    carryover_hours = PUBLIC_HOLIDAY_CARRYOVER_HOURS * carryover_holiday_count
    if carryover_hours <= 0:
        return [
            PlannedLogEntry(
                date=entry_date,
                hours=hours,
                time_type=TimeType.REGULAR,
                project=project,
                task=task,
                location=location,
                notes=notes,
            )
        ]
    if hours <= carryover_hours:
        raise ValueError("Hours must be greater than public holiday carryover hours")
    return [
        PlannedLogEntry(
            date=entry_date,
            hours=hours - carryover_hours,
            time_type=TimeType.REGULAR,
            project=project,
            task=task,
            location=location,
            notes=notes,
        ),
        PlannedLogEntry(
            date=entry_date,
            hours=carryover_hours,
            time_type=TimeType.PUBLIC_HOLIDAY,
            project=project,
            task=task,
            location=location,
            notes=notes,
        ),
    ]


def _carryover_holiday_count(entry_date: Date, holiday_dates: set[Date]) -> int:
    return sum(
        1
        for holiday_date in holiday_dates
        if holiday_date.weekday() >= 5 and _previous_working_day(holiday_date) == entry_date
    )


def _previous_working_day(value: Date) -> Date:
    previous = value - timedelta(days=1)
    while previous.weekday() >= 5:
        previous -= timedelta(days=1)
    return previous


def _location_for_day(
    entry_date: Date,
    *,
    explicit_location: str | None,
    work_pattern: WorkPattern,
    work_from_home_days: int,
    period_working_days: list[Date],
) -> str:
    if explicit_location:
        return explicit_location
    if work_pattern is WorkPattern.HOME:
        return LOCATION_WORK_FROM_HOME
    if (
        work_pattern is WorkPattern.HYBRID
        and _weekly_workday_index(entry_date, period_working_days) < work_from_home_days
    ):
        return LOCATION_WORK_FROM_HOME
    return LOCATION_WORK_FROM_OFFICE


def _weekly_workday_index(entry_date: Date, period_working_days: list[Date]) -> int:
    week_start = entry_date - timedelta(days=entry_date.weekday())
    days_in_week = [
        day for day in period_working_days if week_start <= day <= week_start + timedelta(days=6)
    ]
    return days_in_week.index(entry_date)
