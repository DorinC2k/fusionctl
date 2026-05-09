from datetime import date
from decimal import Decimal

import pytest

from fusionctl.services.log_periods import LogPeriod, period_bounds, plan_period_logs, working_days_between


def test_current_week_bounds_stop_at_today() -> None:
    bounds = period_bounds(LogPeriod.CURRENT_WEEK, today=date(2026, 5, 9))

    assert bounds.start == date(2026, 5, 4)
    assert bounds.end == date(2026, 5, 9)


def test_current_month_bounds_stop_at_today() -> None:
    bounds = period_bounds(LogPeriod.CURRENT_MONTH, today=date(2026, 5, 9))

    assert bounds.start == date(2026, 5, 1)
    assert bounds.end == date(2026, 5, 9)


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
    assert {entry.project for entry in entries} == {"WORDV266"}
    assert {entry.task for entry in entries} == {"02"}


def test_plan_period_logs_rejects_invalid_hours() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        plan_period_logs(
            LogPeriod.CURRENT_WEEK,
            hours=Decimal("0"),
            project="WORDV266",
            task="02",
        )
