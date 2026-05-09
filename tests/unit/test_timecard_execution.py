from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from fusionctl.api.endpoints import OracleEndpoints
from fusionctl.api.oracle_client import OracleClient
from fusionctl.config import Settings
from fusionctl.models.timesheet import TimeType
from fusionctl.services.log_periods import PlannedLogEntry
from fusionctl.services.timecard_execution import (
    FUSIONCTL_COMMENT_PREFIX,
    TimecardExecutor,
    _build_time_entry,
    _is_approved_card,
    _prefilled_blocked_dates,
    _should_replace_entry,
    _strip_response_metadata,
    _time_entry_payload,
    _time_type_value_map,
)


class RecordingOracleClient(OracleClient):
    def __init__(self) -> None:
        super().__init__("https://example.oraclecloud.com", "JSESSIONID=abc")
        self.posts: list[tuple[str, dict[str, object], str]] = []

    async def refresh_bearer_token(self) -> str:
        return "bearer"

    async def post(
        self,
        url: str,
        payload: dict[str, object],
        *,
        content_type: str = "application/vnd.oracle.adf.action+json",
    ) -> dict[str, object]:
        self.posts.append((url, payload, content_type))
        return {"result": {"items": [], "summary": {"count": 0}}}

    async def get(self, url: str, params: dict[str, str] | None = None) -> dict[str, object]:
        _ = (url, params)
        return {"items": []}

    async def submit_timecard(self, api_root: str, payload: dict[str, Any]) -> dict[str, object]:
        self.posts.append((f"{api_root.rstrip('/')}/timeCards", payload, "submit"))
        return {"ok": True}


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


def test_build_public_holiday_entry_uses_oracle_holiday_field_shape() -> None:
    settings = Settings()
    row = _build_time_entry(
        PlannedLogEntry(
            date=date(2026, 5, 8),
            hours=Decimal("1"),
            time_type=TimeType.PUBLIC_HOLIDAY,
            project="WORDV266",
            task="02",
            location="Work from office (employment contract)",
            notes=None,
        ),
        {"TimeCardId": "300"},
        person_id="100",
        project_value="project-id",
        task_value="task-id",
        time_type_value="holiday-id",
        settings=settings,
    )

    values = {item["TimeCardFieldId"]: item["Value"] for item in row["timeCardFieldValues"]}
    assert values[settings.oracle_field_project] is None
    assert values[settings.oracle_field_task] is None
    assert values[settings.oracle_field_time_type] == "holiday-id"
    assert values[settings.oracle_field_location] is None
    assert values[settings.oracle_field_assignment] == settings.oracle_assignment_value
    assert values[settings.oracle_field_business_unit] is None
    assert values[settings.oracle_field_entry_source] is None
    assert values[settings.oracle_field_entry_context] is None


def test_time_type_value_map_reads_values_from_existing_entries() -> None:
    settings = Settings()

    values = _time_type_value_map(
        [
            {
                "timeCardFieldValues": {
                    "items": [
                        {
                            "TimeCardFieldId": settings.oracle_field_time_type,
                            "Value": "regular-id",
                            "DisplayValue": "Regular",
                        }
                    ]
                }
            },
            {
                "timeCardFieldValues": {
                    "items": [
                        {
                            "TimeCardFieldId": settings.oracle_field_time_type,
                            "Value": "holiday-id",
                            "DisplayValue": "Public Holiday",
                        }
                    ]
                }
            },
        ],
        settings,
    )

    assert values == {
        TimeType.REGULAR: "regular-id",
        TimeType.PUBLIC_HOLIDAY: "holiday-id",
    }


def test_strip_response_metadata_removes_oracle_context_and_links() -> None:
    assert _strip_response_metadata(
        {
            "TimeEntryId": "entry",
            "@context": {"key": "entry"},
            "links": [{"href": "ignored"}],
            "ReadOnlyFlag": True,
            "timeCardFieldValues": {
                "items": [
                    {
                        "TimeCardFieldId": "field",
                        "Value": "value",
                        "@context": {"key": "field"},
                        "ReadOnlyFlag": False,
                    }
                ]
            },
        }
    ) == {
        "TimeEntryId": "entry",
        "timeCardFieldValues": {
            "items": [
                {
                    "TimeCardFieldId": "field",
                    "Value": "value",
                }
            ]
        },
    }


def test_time_entry_payload_keeps_only_saveable_fields() -> None:
    assert _time_entry_payload(
        {
            "TimeEntryId": "entry",
            "TimeEntryVersion": 1,
            "EntryDate": "2026-05-04T00:00:00+00:00",
            "Measure": "8",
            "AbsenceEntryFlag": False,
            "ActualDate": "2026-05-04",
            "timeCardFieldValues": {
                "items": [
                    {
                        "TimeCardFieldId": "field",
                        "TimeEntryId": "entry",
                        "Value": "value",
                        "DisplayValue": "Regular",
                        "@context": {"key": "field"},
                    }
                ]
            },
        }
    ) == {
        "TimeEntryId": "entry",
        "TimeEntryVersion": 1,
        "EntryDate": "2026-05-04T00:00:00+00:00",
        "Measure": "8",
        "timeCardFieldValues": [{"TimeCardFieldId": "field", "Value": "value"}],
    }


def test_is_approved_card_checks_detail_and_summary_status() -> None:
    assert _is_approved_card({"Status": "APPROVED"}, {"StatusCode": "SUBMITTED"})
    assert _is_approved_card({"Status": "SUBMITTED"}, {"StatusCode": "APPROVED"})
    assert not _is_approved_card({"Status": "SUBMITTED"}, {"StatusCode": "SUBMITTED"})


@pytest.mark.asyncio
async def test_submit_uses_latest_card_state_and_sanitized_entries() -> None:
    client = RecordingOracleClient()
    executor = TimecardExecutor(
        client=client,
        endpoints=OracleEndpoints("https://example.oraclecloud.com", "resource"),
        settings=Settings(),
        person_id="100",
    )

    await executor._submit(
        {
            "TimeCardId": "300",
            "TimeCardVersion": 2,
            "PersonId": "100",
            "StartDate": "2026-05-04T00:00:00+00:00",
            "StopDate": "2026-05-10T23:59:59.999+00:00",
        },
        [
            {
                "TimeEntryId": "entry",
                "TimeEntryVersion": 1,
                "EntryDate": "2026-05-04T00:00:00+00:00",
                "Measure": "8",
                "AbsenceEntryFlag": False,
                "timeCardFieldValues": {
                    "items": [{"TimeCardFieldId": "field", "Value": "value"}]
                },
            }
        ],
    )

    _, payload, marker = client.posts[0]
    assert marker == "submit"
    assert payload["TimeCardVersion"] == 2
    assert payload["timeEntries"] == [
        {
            "TimeEntryId": "entry",
            "TimeEntryVersion": 1,
            "EntryDate": "2026-05-04T00:00:00+00:00",
            "Measure": "8",
            "timeCardFieldValues": [{"TimeCardFieldId": "field", "Value": "value"}],
        }
    ]


@pytest.mark.asyncio
async def test_find_cards_uses_advanced_search_action_payload() -> None:
    client = RecordingOracleClient()
    executor = TimecardExecutor(
        client=client,
        endpoints=OracleEndpoints("https://example.oraclecloud.com", "resource"),
        settings=Settings(),
        person_id="100",
    )

    cards = await executor._find_cards(date(2026, 5, 4), date(2026, 5, 10))

    assert cards == []
    _, payload, content_type = client.posts[0]
    assert content_type == "application/vnd.oracle.adf.action+json"
    assert payload["filters"] == [
        {
            "name": ["TimePeriod"],
            "values": ["2026-05-04T00:00:00+00:00", "2026-05-10T23:59:59.999+00:00"],
        }
    ]
