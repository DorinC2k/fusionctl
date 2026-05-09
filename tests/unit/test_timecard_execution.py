from datetime import date
from decimal import Decimal

from fusionctl.config import Settings
from fusionctl.models.timesheet import TimeType
from fusionctl.services.log_periods import PlannedLogEntry
from fusionctl.services.timecard_execution import (
    FUSIONCTL_COMMENT_PREFIX,
    _build_time_entry,
    _prefilled_blocked_dates,
    _should_replace_entry,
)


def test_prefilled_blocked_dates_keep_leave_and_oracle_holidays_only() -> None:
    blocked = _prefilled_blocked_dates(
        [
            {"EntryDate": "2026-05-06T00:00:00+00:00", "AbsenceEntryFlag": True},
            {
                "EntryDate": "2026-05-08T00:00:00+00:00",
                "Comments": FUSIONCTL_COMMENT_PREFIX,
                "timeCardFieldValues": {
                    "items": [{"DisplayValue": "Public Holiday"}],
                },
            },
            {
                "EntryDate": "2026-05-01T00:00:00+00:00",
                "timeCardFieldValues": {
                    "items": [{"DisplayValue": "Public Holiday"}],
                },
            },
        ]
    )

    assert blocked == {date(2026, 5, 1), date(2026, 5, 6)}


def test_should_replace_matching_project_task_rows_for_planned_dates() -> None:
    settings = Settings()
    planned = [
        PlannedLogEntry(
            date=date(2026, 5, 4),
            hours=Decimal("8"),
            time_type=TimeType.REGULAR,
            project="WORDV266",
            task="02",
            location="Work from home",
            notes=None,
        )
    ]
    existing = {
        "EntryDate": "2026-05-04T00:00:00+00:00",
        "timeCardFieldValues": {
            "items": [
                {"TimeCardFieldId": settings.oracle_field_project, "Value": "project-id"},
                {"TimeCardFieldId": settings.oracle_field_task, "Value": "task-id"},
                {"TimeCardFieldId": settings.oracle_field_time_type, "DisplayValue": "Regular"},
            ]
        },
    }

    assert _should_replace_entry(
        existing,
        planned,
        project_value="project-id",
        task_value="task-id",
        settings=settings,
    )


def test_build_time_entry_includes_location_and_oracle_field_values() -> None:
    settings = Settings()
    row = _build_time_entry(
        PlannedLogEntry(
            date=date(2026, 5, 4),
            hours=Decimal("7"),
            time_type=TimeType.REGULAR,
            project="WORDV266",
            task="02",
            location="Work from office (employment contract)",
            notes=None,
        ),
        {"TimeCardId": "300"},
        person_id="100",
        project_value="project-id",
        task_value="task-id",
        time_type_value="regular-id",
        settings=settings,
    )

    values = {item["TimeCardFieldId"]: item["Value"] for item in row["timeCardFieldValues"]}
    assert row["Measure"] == "7"
    assert values[settings.oracle_field_project] == "project-id"
    assert values[settings.oracle_field_task] == "task-id"
    assert values[settings.oracle_field_time_type] == "regular-id"
    assert values[settings.oracle_field_location] == "Work from office (employment contract)"
