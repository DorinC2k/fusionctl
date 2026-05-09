from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, time, timezone, timedelta
from decimal import Decimal
from typing import Any

from fusionctl.api.endpoints import OracleEndpoints
from fusionctl.api.oracle_client import OracleClient
from fusionctl.config import Settings, load_settings
from fusionctl.exceptions import AuthenticationError, OracleApiError
from fusionctl.models.timesheet import TimeType
from fusionctl.services.auth_service import AuthService
from fusionctl.services.log_periods import PlannedLogEntry
from fusionctl.storage.secrets import SecretStore

DETAIL_EXPAND = (
    "timeCardLayouts,timeCards,timeCardLayouts.timeCardFields,timeCards.publicHolidays,"
    "timeCards.timeEntries,timeCards.approvalTasks,timeCards.timeEntries.timeCardFieldValues,"
    "timeCards.emptyEntries,timeCards.emptyEntries.timeCardFieldValues,timeCards.messages,"
    "timeCards.timeEntries.messages,timeCards.scheduledHours,timeCards.changeRequests,"
    "timeCards.timeEntries.changeRequests"
)
FUSIONCTL_COMMENT_PREFIX = "created by fusionctl"


@dataclass(frozen=True)
class TimecardExecutionResult:
    written_entries: int
    skipped_dates: int
    processed_cards: int


async def execute_period_logs(entries: Sequence[PlannedLogEntry]) -> TimecardExecutionResult:
    """Write planned period logs to Oracle with replace-style idempotency."""
    settings = load_settings()
    session = AuthService(SecretStore(settings.secrets_file)).require_session()
    endpoints = OracleEndpoints(
        settings.oracle_base_url,
        settings.oracle_resource_version,
        api_version=settings.oracle_api_version,
    )
    client = OracleClient(settings.oracle_base_url, session.token, settings.oracle_timeout)
    person_id = settings.oracle_person_id or session.person_id
    executor = TimecardExecutor(
        client=client,
        endpoints=endpoints,
        settings=settings,
        person_id=person_id,
    )
    return await executor.execute(entries)


class TimecardExecutor:
    def __init__(
        self,
        *,
        client: OracleClient,
        endpoints: OracleEndpoints,
        settings: Settings,
        person_id: str | None,
    ) -> None:
        self.client = client
        self.endpoints = endpoints
        self.settings = settings
        self.person_id = person_id

    async def execute(self, entries: Sequence[PlannedLogEntry]) -> TimecardExecutionResult:
        if not entries:
            return TimecardExecutionResult(written_entries=0, skipped_dates=0, processed_cards=0)

        await self.client.refresh_bearer_token()
        cards = await self._find_cards(min(entry.date for entry in entries), max(entry.date for entry in entries))
        by_week = _group_by_week(entries)
        written_entries = 0
        skipped_dates = 0

        for week, planned_entries in by_week.items():
            card_summary = _find_card_for_week(cards, week)
            if card_summary is None:
                person_id = await self._require_person_id(cards)
                await self.client.create_timecard(
                    self.endpoints.api_root,
                    person_id=person_id,
                    start_date=_start_of_day(week[0]),
                    stop_date=_end_of_day(week[1]),
                )
                cards = await self._find_cards(week[0], week[1])
                card_summary = _find_card_for_week(cards, week)
                if card_summary is None:
                    raise OracleApiError("Oracle created a timecard but did not return it in search")

            detail = await self._fetch_detail(str(card_summary["TimeCardId"]))
            card = _extract_card(detail)
            if self.person_id is None:
                self.person_id = str(detail.get("PersonId") or card.get("PersonId") or "")

            project_value = await self._lookup_project(planned_entries[0], week)
            task_value = await self._lookup_task(planned_entries[0], week, project_value)
            time_type_values = await self._lookup_time_types(planned_entries, week)

            existing_entries = _entries(card)
            blocked_dates = _prefilled_blocked_dates(existing_entries)
            writable_entries = [entry for entry in planned_entries if entry.date not in blocked_dates]
            skipped_dates += len({entry.date for entry in planned_entries if entry.date in blocked_dates})

            filtered_entries = [
                entry
                for entry in existing_entries
                if not _should_replace_entry(
                    entry,
                    writable_entries,
                    project_value=project_value,
                    task_value=task_value,
                    settings=self.settings,
                )
            ]
            if len(filtered_entries) != len(existing_entries):
                await self._save(card, filtered_entries)
                detail = await self._fetch_detail(str(card["TimeCardId"]))
                card = _extract_card(detail)
                filtered_entries = _entries(card)

            for planned_entry in writable_entries:
                new_row = _build_time_entry(
                    planned_entry,
                    card,
                    person_id=await self._require_person_id([detail]),
                    project_value=project_value,
                    task_value=task_value,
                    time_type_value=time_type_values[planned_entry.time_type],
                    settings=self.settings,
                )
                await self._save(card, [*filtered_entries, new_row])
                written_entries += 1
                detail = await self._fetch_detail(str(card["TimeCardId"]))
                card = _extract_card(detail)
                filtered_entries = _entries(card)

        return TimecardExecutionResult(
            written_entries=written_entries,
            skipped_dates=skipped_dates,
            processed_cards=len(by_week),
        )

    async def _find_cards(self, start: Date, end: Date) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timecardDateRangeDetail": {
                "timecardDateFrom": start.isoformat(),
                "timecardDateTo": end.isoformat(),
            },
            "limit": 100,
            "offset": 0,
        }
        data = await self.client.post(self.endpoints.timecards_search(), payload)
        result = data.get("result")
        if isinstance(result, Mapping):
            items = result.get("items", [])
            if isinstance(items, list):
                return [dict(item) for item in items if isinstance(item, Mapping)]
        return []

    async def _fetch_detail(self, timecard_id: str) -> dict[str, Any]:
        data = await self.client.get(
            self.endpoints.timecard_entry_details(),
            params={
                "finder": f"findByTimeCardId;TimeCardId={timecard_id},UserContext=WORKER",
                "expand": DETAIL_EXPAND,
                "limit": "5000",
                "onlyData": "true",
            },
        )
        items = data.get("items")
        if not isinstance(items, list) or not items or not isinstance(items[0], Mapping):
            raise OracleApiError("Oracle timecard detail response did not include a card")
        return dict(items[0])

    async def _save(self, card: Mapping[str, Any], entries: list[dict[str, Any]]) -> None:
        payload: dict[str, Any] = {
            "TimeCardId": card.get("TimeCardId"),
            "TimeCardVersion": card.get("TimeCardVersion"),
            "PersonId": card.get("PersonId") or self.person_id,
            "StartDate": card.get("StartDate"),
            "StopDate": card.get("StopDate"),
            "UserContext": "WORKER",
            "IgnoreWarningsFlag": False,
            "timeEntries": entries,
        }
        await self.client.save_timecard_entries(self.endpoints.api_root, payload)

    async def _lookup_project(self, entry: PlannedLogEntry, week: tuple[Date, Date]) -> str:
        return await self._lookup_code(
            search_term=entry.project,
            field_id=self.settings.oracle_field_project,
            week=week,
        )

    async def _lookup_task(
        self,
        entry: PlannedLogEntry,
        week: tuple[Date, Date],
        project_value: str,
    ) -> str:
        person_id = await self._require_person_id([])
        finder = (
            f"findByWord;SearchTerm={entry.task},TcfId={self.settings.oracle_field_task},"
            f"UserType=WORKER,PersonId={person_id},StartDate={week[0].isoformat()},"
            f"EndDate={week[1].isoformat()},BindTcfId1={self.settings.oracle_field_assignment},"
            f"BindTcfId2={self.settings.oracle_field_project},"
            f"BindTcf1Value={self.settings.oracle_assignment_value},BindTcf2Value={project_value}"
        )
        return await self._lookup_finder_code(finder)

    async def _lookup_time_types(
        self,
        entries: Sequence[PlannedLogEntry],
        week: tuple[Date, Date],
    ) -> dict[TimeType, str]:
        values: dict[TimeType, str] = {}
        for time_type in {entry.time_type for entry in entries}:
            values[time_type] = await self._lookup_code(
                search_term=time_type.value,
                field_id=self.settings.oracle_field_time_type,
                week=week,
            )
        return values

    async def _lookup_code(self, *, search_term: str, field_id: str, week: tuple[Date, Date]) -> str:
        person_id = await self._require_person_id([])
        finder = (
            f"findByWord;SearchTerm={search_term},TcfId={field_id},UserType=WORKER,"
            f"PersonId={person_id},StartDate={week[0].isoformat()},EndDate={week[1].isoformat()}"
        )
        return await self._lookup_finder_code(finder)

    async def _lookup_finder_code(self, finder: str) -> str:
        data = await self.client.get(
            self.endpoints.timecard_field_values(),
            params={
                "finder": finder,
                "limit": "25",
                "offset": "0",
                "onlyData": "true",
            },
        )
        items = data.get("items")
        if not isinstance(items, list):
            raise OracleApiError("Oracle field-value lookup returned an unexpected response")
        for item in items:
            if isinstance(item, Mapping) and item.get("Code"):
                return str(item["Code"])
        raise OracleApiError("Oracle field-value lookup did not return a matching code")

    async def _require_person_id(self, candidate_details: Sequence[Mapping[str, Any]]) -> str:
        if self.person_id:
            return self.person_id
        for detail in candidate_details:
            person_id = detail.get("PersonId")
            if person_id:
                self.person_id = str(person_id)
                return self.person_id
        raise AuthenticationError(
            "Oracle person id is not known. Set FUSION_ORACLE_PERSON_ID in .env and retry."
        )


def _group_by_week(entries: Sequence[PlannedLogEntry]) -> dict[tuple[Date, Date], list[PlannedLogEntry]]:
    grouped: dict[tuple[Date, Date], list[PlannedLogEntry]] = defaultdict(list)
    for entry in entries:
        start = entry.date - timedelta(days=entry.date.weekday())
        grouped[(start, start + timedelta(days=6))].append(entry)
    return dict(grouped)


def _find_card_for_week(cards: Sequence[Mapping[str, Any]], week: tuple[Date, Date]) -> Mapping[str, Any] | None:
    for card in cards:
        start = _parse_date(card.get("TimePeriodStartDate"))
        end = _parse_date(card.get("TimePeriodEndDate"))
        if start == week[0] and end == week[1]:
            return card
    return None


def _extract_card(detail: Mapping[str, Any]) -> dict[str, Any]:
    time_cards = detail.get("timeCards")
    if isinstance(time_cards, Mapping):
        items = time_cards.get("items")
        if isinstance(items, list) and items and isinstance(items[0], Mapping):
            card = dict(items[0])
            card.setdefault("PersonId", detail.get("PersonId"))
            return card
    raise OracleApiError("Oracle timecard detail response did not include nested timeCards")


def _entries(card: Mapping[str, Any]) -> list[dict[str, Any]]:
    time_entries = card.get("timeEntries")
    if isinstance(time_entries, Mapping) and isinstance(time_entries.get("items"), list):
        return [dict(entry) for entry in time_entries["items"] if isinstance(entry, Mapping)]
    if isinstance(time_entries, list):
        return [dict(entry) for entry in time_entries if isinstance(entry, Mapping)]
    return []


def _prefilled_blocked_dates(entries: Sequence[Mapping[str, Any]]) -> set[Date]:
    return {
        entry_date
        for entry in entries
        if (entry_date := _parse_date(entry.get("EntryDate"))) is not None
        and (
            entry.get("AbsenceEntryFlag")
            or (
                _time_type_display(entry) == TimeType.PUBLIC_HOLIDAY.value
                and not str(entry.get("Comments", "")).startswith(FUSIONCTL_COMMENT_PREFIX)
            )
        )
    }


def _should_replace_entry(
    existing_entry: Mapping[str, Any],
    planned_entries: Sequence[PlannedLogEntry],
    *,
    project_value: str,
    task_value: str,
    settings: Settings,
) -> bool:
    entry_date = _parse_date(existing_entry.get("EntryDate"))
    if entry_date not in {entry.date for entry in planned_entries}:
        return False
    if existing_entry.get("AbsenceEntryFlag"):
        return False
    if _time_type_display(existing_entry) == TimeType.PUBLIC_HOLIDAY.value and entry_date.weekday() >= 5:
        return False
    values = _field_value_map(existing_entry)
    return (
        values.get(settings.oracle_field_project) == project_value
        and values.get(settings.oracle_field_task) == task_value
    ) or str(existing_entry.get("Comments", "")).startswith(FUSIONCTL_COMMENT_PREFIX)


def _build_time_entry(
    entry: PlannedLogEntry,
    card: Mapping[str, Any],
    *,
    person_id: str,
    project_value: str,
    task_value: str,
    time_type_value: str,
    settings: Settings,
) -> dict[str, Any]:
    return {
        "TimeEntryId": 0,
        "TimeEntryVersion": 0,
        "TimeCardId": card.get("TimeCardId"),
        "UnitOfMeasure": "HR",
        "StartTime": None,
        "StopTime": None,
        "Measure": _format_decimal(entry.hours),
        "PersonId": person_id,
        "Comments": entry.notes or FUSIONCTL_COMMENT_PREFIX,
        "GroupingSequence": 0,
        "EntryDate": _start_of_day(entry.date),
        "timeCardFieldValues": [
            {"TimeCardFieldId": settings.oracle_field_project, "Value": project_value},
            {"TimeCardFieldId": settings.oracle_field_task, "Value": task_value},
            {"TimeCardFieldId": settings.oracle_field_time_type, "Value": time_type_value},
            {"TimeCardFieldId": settings.oracle_field_location, "Value": entry.location},
            {"TimeCardFieldId": settings.oracle_field_payroll_time_type, "Value": None},
            {"TimeCardFieldId": settings.oracle_field_absence, "Value": None},
            {"TimeCardFieldId": settings.oracle_field_assignment, "Value": settings.oracle_assignment_value},
            {"TimeCardFieldId": settings.oracle_field_business_unit, "Value": settings.oracle_business_unit_value},
            {"TimeCardFieldId": settings.oracle_field_entry_source, "Value": settings.oracle_entry_source_value},
            {"TimeCardFieldId": settings.oracle_field_entry_context, "Value": settings.oracle_entry_context_value},
        ],
    }


def _field_value_map(entry: Mapping[str, Any]) -> dict[str, str | None]:
    values = entry.get("timeCardFieldValues")
    items: list[Any] = []
    if isinstance(values, Mapping) and isinstance(values.get("items"), list):
        items = values["items"]
    elif isinstance(values, list):
        items = values
    mapped: dict[str, str | None] = {}
    for item in items:
        if isinstance(item, Mapping) and item.get("TimeCardFieldId"):
            value = item.get("Value")
            mapped[str(item["TimeCardFieldId"])] = None if value is None else str(value)
    return mapped


def _time_type_display(entry: Mapping[str, Any]) -> str | None:
    values = entry.get("timeCardFieldValues")
    items: list[Any] = []
    if isinstance(values, Mapping) and isinstance(values.get("items"), list):
        items = values["items"]
    elif isinstance(values, list):
        items = values
    for item in items:
        if isinstance(item, Mapping):
            display = item.get("DisplayValue") or item.get("Value")
            if display in {TimeType.REGULAR.value, TimeType.PUBLIC_HOLIDAY.value}:
                return str(display)
    return None


def _parse_date(value: Any) -> Date | None:
    if value is None:
        return None
    if isinstance(value, Date) and not isinstance(value, datetime):
        return value
    text = str(value)
    try:
        return Date.fromisoformat(text[:10])
    except ValueError:
        return None


def _start_of_day(value: Date) -> str:
    return datetime.combine(value, time.min, tzinfo=timezone.utc).isoformat()


def _end_of_day(value: Date) -> str:
    return f"{value.isoformat()}T23:59:59.999+00:00"


def _format_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f").rstrip("0").rstrip(".") or "0"
