from datetime import date
from decimal import Decimal

import pytest

from fusionctl.services.log_periods import (
    LogPeriod,
    period_bounds,
    plan_period_logs,
    working_days_between,
)
from fusionctl.services.log_periods import (
    LOCATION_WORK_FROM_HOME,
    LOCATION_WORK_FROM_OFFICE,
    WorkPattern,
)
from fusionctl.models.timesheet import TimeType


def test_current_week_bounds_stop_at_today() -> None:
    bounds = period_bounds(LogPeriod.CURRENT_WEEK, today=date(2026, 5, 9))

    assert bounds.start == date(2026, 5, 4)
    assert bounds.end == date(2026, 5, 9)


def test_current_month_bounds_cover_full_overlapping_timecard_weeks() -> None:
    bounds = period_bounds(LogPeriod.CURRENT_MONTH, today=date(2026, 5, 9))

    assert bounds.start == date(2026, 4, 27)
    assert bounds.end == date(2026, 5, 31)


def test_current_month_bounds_include_next_month_spillover_weekdays() -> None:
    bounds = period_bounds(LogPeriod.CURRENT_MONTH, today=date(2026, 4, 15))

    assert bounds.start == date(2026, 3, 30)
    assert bounds.end == date(2026, 5, 3)


def test_last_month_bounds_cover_full_previous_calendar_month() -> None:
    bounds = period_bounds(LogPeriod.LAST_MONTH, today=date(2026, 5, 9))

    assert bounds.start == date(2026, 4, 1)
    assert bounds.end == date(2026, 4, 30)


def test_working_days_between_excludes_weekends() -> None:
    days = working_days_between(date(2026, 5, 1), date(2026, 5, 5))

    assert days == [
        date(2026, 5, 1),
        date(2026, 5, 4),
        date(2026, 5, 5),
    ]


def test_plan_period_logs_creates_one_entry_per_working_day() -> None:
    entries = plan_period_logs(
        LogPeriod.CURRENT_WEEK,
        hours=Decimal("8"),
        project="WORDV266",
        task="02",
        notes="Regular work",
        today=date(2026, 5, 9),
    )

    assert [entry.date for entry in entries] == [
        date(2026, 5, 4),
        date(2026, 5, 5),
        date(2026, 5, 6),
        date(2026, 5, 7),
        date(2026, 5, 8),
    ]
    assert {entry.hours for entry in entries} == {Decimal("8")}
    assert {entry.time_type for entry in entries} == {TimeType.REGULAR}
    assert {entry.project for entry in entries} == {"WORDV266"}
    assert {entry.task for entry in entries} == {"02"}
    assert {entry.location for entry in entries} == {LOCATION_WORK_FROM_OFFICE}


def test_plan_current_month_logs_full_overlapping_timecard_weeks() -> None:
    entries = plan_period_logs(
        LogPeriod.CURRENT_MONTH,
        hours=Decimal("8"),
        project="WORDV266",
        task="02",
        today=date(2026, 4, 15),
    )

    assert entries[0].date == date(2026, 3, 30)
    assert entries[-1].date == date(2026, 5, 1)
    assert date(2026, 5, 1) in {entry.date for entry in entries}


def test_plan_period_logs_uses_explicit_location_for_every_entry() -> None:
    entries = plan_period_logs(
        LogPeriod.CURRENT_WEEK,
        hours=Decimal("8"),
        project="WORDV266",
        task="02",
        location=LOCATION_WORK_FROM_HOME,
        today=date(2026, 5, 9),
    )

    assert {entry.location for entry in entries} == {LOCATION_WORK_FROM_HOME}


def test_hybrid_work_pattern_assigns_first_n_working_days_to_home_each_week() -> None:
    entries = plan_period_logs(
        LogPeriod.CURRENT_WEEK,
        hours=Decimal("8"),
        project="WORDV266",
        task="02",
        work_pattern=WorkPattern.HYBRID,
        work_from_home_days=2,
        today=date(2026, 5, 9),
    )

    assert [(entry.date, entry.location) for entry in entries] == [
        (date(2026, 5, 4), LOCATION_WORK_FROM_HOME),
        (date(2026, 5, 5), LOCATION_WORK_FROM_HOME),
        (date(2026, 5, 6), LOCATION_WORK_FROM_OFFICE),
        (date(2026, 5, 7), LOCATION_WORK_FROM_OFFICE),
        (date(2026, 5, 8), LOCATION_WORK_FROM_OFFICE),
    ]


def test_home_work_pattern_assigns_all_entries_to_home() -> None:
    entries = plan_period_logs(
        LogPeriod.CURRENT_WEEK,
        hours=Decimal("8"),
        project="WORDV266",
        task="02",
        work_pattern=WorkPattern.HOME,
        today=date(2026, 5, 9),
    )

    assert {entry.location for entry in entries} == {LOCATION_WORK_FROM_HOME}


def test_weekend_holiday_calendar_splits_previous_working_day() -> None:
    entries = plan_period_logs(
        LogPeriod.CURRENT_WEEK,
        hours=Decimal("8"),
        project="WORDV266",
        task="02",
        holiday_dates={date(2026, 5, 9)},
        today=date(2026, 5, 9),
    )

    assert [(entry.date, entry.hours, entry.time_type) for entry in entries][-2:] == [
        (date(2026, 5, 8), Decimal("7"), TimeType.REGULAR),
        (date(2026, 5, 8), Decimal("1"), TimeType.PUBLIC_HOLIDAY),
    ]


def test_sunday_holiday_calendar_splits_previous_friday() -> None:
    entries = plan_period_logs(
        LogPeriod.CURRENT_WEEK,
        hours=Decimal("8"),
        project="WORDV266",
        task="02",
        holiday_dates={date(2026, 3, 8)},
        today=date(2026, 3, 8),
    )

    assert [(entry.date, entry.hours, entry.time_type) for entry in entries][-2:] == [
        (date(2026, 3, 6), Decimal("7"), TimeType.REGULAR),
        (date(2026, 3, 6), Decimal("1"), TimeType.PUBLIC_HOLIDAY),
    ]


def test_plan_period_logs_rejects_invalid_hours() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        plan_period_logs(
            LogPeriod.CURRENT_WEEK,
            hours=Decimal("0"),
            project="WORDV266",
            task="02",
        )


def test_plan_period_logs_rejects_invalid_hybrid_home_days() -> None:
    with pytest.raises(ValueError, match="between 0 and 5"):
        plan_period_logs(
            LogPeriod.CURRENT_WEEK,
            hours=Decimal("8"),
            project="WORDV266",
            task="02",
            work_pattern=WorkPattern.HYBRID,
            work_from_home_days=6,
        )
