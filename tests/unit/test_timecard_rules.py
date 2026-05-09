from datetime import date
from decimal import Decimal

import pytest

from fusionctl.models import Project, Task, TimeEntry, TimeType
from fusionctl.services.timecard_rules import allocate_regular_day


def project() -> Project:
    return Project(code="WORDV266", name="RedHat Helix EU")


def task() -> Task:
    return Task(code="02", name="Build")


def public_holiday(day: date) -> TimeEntry:
    return TimeEntry(
        date=day,
        hours=Decimal("8"),
        time_type=TimeType.PUBLIC_HOLIDAY,
        project=project(),
        task=task(),
    )


def annual_leave(day: date) -> TimeEntry:
    return TimeEntry(
        date=day,
        hours=Decimal("8"),
        absence_type="Annual Leave MD",
        project=project(),
        task=task(),
    )


def regular_entry(day: date, hours: str = "8") -> TimeEntry:
    return TimeEntry(
        date=day,
        hours=Decimal(hours),
        time_type=TimeType.REGULAR,
        project=project(),
        task=task(),
    )


def public_holiday_carryover(day: date) -> TimeEntry:
    return TimeEntry(
        date=day,
        hours=Decimal("1"),
        time_type=TimeType.PUBLIC_HOLIDAY,
        project=project(),
        task=task(),
    )


def test_working_day_before_public_holiday_splits_one_hour_to_public_holiday() -> None:
    allocations = allocate_regular_day(
        date(2026, 5, 7),
        Decimal("8"),
        [public_holiday(date(2026, 5, 8))],
    )

    assert [(item.hours, item.time_type) for item in allocations] == [
        (Decimal("7"), TimeType.REGULAR),
        (Decimal("1"), TimeType.PUBLIC_HOLIDAY),
    ]


def test_regular_day_without_next_day_public_holiday_stays_regular() -> None:
    allocations = allocate_regular_day(date(2026, 5, 6), Decimal("8"), [])

    assert [(item.hours, item.time_type) for item in allocations] == [
        (Decimal("8"), TimeType.REGULAR)
    ]


def test_existing_regular_day_is_idempotent() -> None:
    allocations = allocate_regular_day(
        date(2026, 5, 6),
        Decimal("8"),
        [regular_entry(date(2026, 5, 6))],
    )

    assert allocations == []


def test_existing_public_holiday_split_is_idempotent() -> None:
    allocations = allocate_regular_day(
        date(2026, 5, 7),
        Decimal("8"),
        [
            public_holiday(date(2026, 5, 8)),
            regular_entry(date(2026, 5, 7), "7"),
            public_holiday_carryover(date(2026, 5, 7)),
        ],
    )

    assert allocations == []


def test_partial_public_holiday_split_only_plans_missing_row() -> None:
    allocations = allocate_regular_day(
        date(2026, 5, 7),
        Decimal("8"),
        [
            public_holiday(date(2026, 5, 8)),
            regular_entry(date(2026, 5, 7), "7"),
        ],
    )

    assert [(item.hours, item.time_type) for item in allocations] == [
        (Decimal("1"), TimeType.PUBLIC_HOLIDAY)
    ]


def test_preadded_public_holiday_day_is_left_alone() -> None:
    allocations = allocate_regular_day(
        date(2026, 5, 8),
        Decimal("8"),
        [public_holiday(date(2026, 5, 8))],
    )

    assert allocations == []


def test_preadded_annual_leave_day_is_left_alone() -> None:
    allocations = allocate_regular_day(
        date(2026, 2, 23),
        Decimal("8"),
        [annual_leave(date(2026, 2, 23))],
    )

    assert allocations == []


def test_working_day_before_annual_leave_does_not_split() -> None:
    allocations = allocate_regular_day(
        date(2026, 2, 20),
        Decimal("8"),
        [annual_leave(date(2026, 2, 23))],
    )

    assert [(item.hours, item.time_type) for item in allocations] == [
        (Decimal("8"), TimeType.REGULAR)
    ]


def test_weekend_before_public_holiday_does_not_split() -> None:
    allocations = allocate_regular_day(
        date(2026, 5, 2),
        Decimal("8"),
        [public_holiday(date(2026, 5, 3))],
    )

    assert [(item.hours, item.time_type) for item in allocations] == [
        (Decimal("8"), TimeType.REGULAR)
    ]


def test_day_before_public_holiday_requires_more_than_carryover_hour() -> None:
    with pytest.raises(ValueError, match="greater than 1"):
        allocate_regular_day(
            date(2026, 5, 7),
            Decimal("1"),
            [public_holiday(date(2026, 5, 8))],
        )
