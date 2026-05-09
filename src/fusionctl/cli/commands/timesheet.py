from __future__ import annotations

import asyncio
from datetime import date as Date
from decimal import Decimal, InvalidOperation

import httpx
import typer

from fusionctl.cli.utils import console, exit_with_error, success
from fusionctl.exceptions import AuthenticationError, OracleApiError, StorageError
from fusionctl.services.holiday_calendar import (
    DEFAULT_CACHE_MAX_AGE_DAYS,
    HolidayCalendar,
    load_holidays,
)
from fusionctl.services.timecard_execution import execute_period_logs
from fusionctl.services.log_periods import LogPeriod, PlannedLogEntry, WorkPattern, plan_period_logs
from fusionctl.services.log_periods import period_bounds

app = typer.Typer(help="Timesheet commands")


def _decimal_hours(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation:
        raise typer.BadParameter("Hours must be a number") from None


def _render_plan(period_label: str, entries: list[PlannedLogEntry], *, dry_run: bool) -> None:
    total = sum((entry.hours for entry in entries), Decimal("0"))
    title = "Planned" if dry_run else "Ready"
    success(f"{title} {len(entries)} entries for {period_label}")
    for entry in entries:
        console.print(
            f"  {entry.date.isoformat()}  {entry.hours:g}h  "
            f"{entry.time_type.value}  {entry.project} / {entry.task}  {entry.location}"
        )
    console.print(f"  Total: {total:g}h")


def _log_period(
    period: LogPeriod,
    period_label: str,
    *,
    hours: str,
    project: str,
    task: str,
    location: str | None,
    work_pattern: WorkPattern,
    work_from_home_days: int,
    holiday_calendar: HolidayCalendar | None,
    refresh_holidays: bool,
    holiday_cache_days: int,
    notes: str | None,
    dry_run: bool,
) -> None:
    try:
        holiday_dates = _load_holiday_dates(
            period,
            holiday_calendar=holiday_calendar,
            refresh=refresh_holidays,
            max_age_days=holiday_cache_days,
        )
        entries = plan_period_logs(
            period,
            hours=_decimal_hours(hours),
            project=project,
            task=task,
            location=location,
            work_pattern=work_pattern,
            work_from_home_days=work_from_home_days,
            holiday_dates=holiday_dates,
            notes=notes,
        )
    except (ValueError, httpx.HTTPError) as exc:
        exit_with_error(str(exc), code=2)

    if not entries:
        success(f"No working days to log for {period_label}")
        return

    _render_plan(period_label, entries, dry_run=dry_run)
    if not dry_run:
        try:
            result = asyncio.run(execute_period_logs(entries))
        except (AuthenticationError, OracleApiError, StorageError, httpx.HTTPError) as exc:
            exit_with_error(str(exc), code=3)
        success(
            f"Wrote {result.written_entries} entries across {result.processed_cards} timecards"
        )
        if result.skipped_dates:
            console.print(
                f"  Skipped {result.skipped_dates} dates with Oracle prefilled leave or holidays"
            )


def _load_holiday_dates(
    period: LogPeriod,
    *,
    holiday_calendar: HolidayCalendar | None,
    refresh: bool,
    max_age_days: int,
) -> set[Date]:
    if holiday_calendar is None:
        return set()
    bounds = period_bounds(period)
    years = range(bounds.start.year, bounds.end.year + 1)
    dates: set[Date] = set()
    for year in years:
        result = load_holidays(
            holiday_calendar,
            year,
            refresh=refresh,
            max_age_days=max_age_days,
        )
        dates.update(holiday.date for holiday in result.holidays)
    return dates


@app.command("log-week")
def log_week(
    hours: str = typer.Option("8", "--hours", help="Hours to log for each working day."),
    project: str = typer.Option(..., "--project", help="Oracle project code."),
    task: str = typer.Option(..., "--task", help="Oracle task code."),
    location: str | None = typer.Option(
        None,
        "--location",
        help="Oracle location for every entry. Defaults to Work from office.",
    ),
    work_pattern: WorkPattern = typer.Option(
        WorkPattern.OFFICE,
        "--work-pattern",
        help="Location pattern: office, home, or hybrid.",
    ),
    work_from_home_days: int = typer.Option(
        2,
        "--work-from-home-days",
        min=0,
        max=5,
        help="WFH days per week when --work-pattern hybrid is used.",
    ),
    holiday_calendar: HolidayCalendar | None = typer.Option(
        None,
        "--holiday-calendar",
        help="Holiday calendar for weekend public-holiday carryover, e.g. moldova.",
    ),
    refresh_holidays: bool = typer.Option(
        False,
        "--refresh-holidays",
        help="Refresh the local holiday calendar cache before planning.",
    ),
    holiday_cache_days: int = typer.Option(
        DEFAULT_CACHE_MAX_AGE_DAYS,
        "--holiday-cache-days",
        min=0,
        help="Refresh cached holidays older than this many days. Use 0 to always refresh.",
    ),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes for each entry."),
    dry_run: bool = typer.Option(False, "--dry-run/--execute", help="Preview instead of writing."),
) -> None:
    """Plan regular work logs for this week up to today."""
    _log_period(
        LogPeriod.CURRENT_WEEK,
        "current week",
        hours=hours,
        project=project,
        task=task,
        location=location,
        work_pattern=work_pattern,
        work_from_home_days=work_from_home_days,
        holiday_calendar=holiday_calendar,
        refresh_holidays=refresh_holidays,
        holiday_cache_days=holiday_cache_days,
        notes=notes,
        dry_run=dry_run,
    )


@app.command("log-month")
def log_month(
    hours: str = typer.Option("8", "--hours", help="Hours to log for each working day."),
    project: str = typer.Option(..., "--project", help="Oracle project code."),
    task: str = typer.Option(..., "--task", help="Oracle task code."),
    location: str | None = typer.Option(
        None,
        "--location",
        help="Oracle location for every entry. Defaults to Work from office.",
    ),
    work_pattern: WorkPattern = typer.Option(
        WorkPattern.OFFICE,
        "--work-pattern",
        help="Location pattern: office, home, or hybrid.",
    ),
    work_from_home_days: int = typer.Option(
        2,
        "--work-from-home-days",
        min=0,
        max=5,
        help="WFH days per week when --work-pattern hybrid is used.",
    ),
    holiday_calendar: HolidayCalendar | None = typer.Option(
        None,
        "--holiday-calendar",
        help="Holiday calendar for weekend public-holiday carryover, e.g. moldova.",
    ),
    refresh_holidays: bool = typer.Option(
        False,
        "--refresh-holidays",
        help="Refresh the local holiday calendar cache before planning.",
    ),
    holiday_cache_days: int = typer.Option(
        DEFAULT_CACHE_MAX_AGE_DAYS,
        "--holiday-cache-days",
        min=0,
        help="Refresh cached holidays older than this many days. Use 0 to always refresh.",
    ),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes for each entry."),
    dry_run: bool = typer.Option(False, "--dry-run/--execute", help="Preview instead of writing."),
) -> None:
    """Plan regular work logs for weekly timecards overlapping this month."""
    _log_period(
        LogPeriod.CURRENT_MONTH,
        "current month",
        hours=hours,
        project=project,
        task=task,
        location=location,
        work_pattern=work_pattern,
        work_from_home_days=work_from_home_days,
        holiday_calendar=holiday_calendar,
        refresh_holidays=refresh_holidays,
        holiday_cache_days=holiday_cache_days,
        notes=notes,
        dry_run=dry_run,
    )


@app.command("log-last-month")
def log_last_month(
    hours: str = typer.Option("8", "--hours", help="Hours to log for each working day."),
    project: str = typer.Option(..., "--project", help="Oracle project code."),
    task: str = typer.Option(..., "--task", help="Oracle task code."),
    location: str | None = typer.Option(
        None,
        "--location",
        help="Oracle location for every entry. Defaults to Work from office.",
    ),
    work_pattern: WorkPattern = typer.Option(
        WorkPattern.OFFICE,
        "--work-pattern",
        help="Location pattern: office, home, or hybrid.",
    ),
    work_from_home_days: int = typer.Option(
        2,
        "--work-from-home-days",
        min=0,
        max=5,
        help="WFH days per week when --work-pattern hybrid is used.",
    ),
    holiday_calendar: HolidayCalendar | None = typer.Option(
        None,
        "--holiday-calendar",
        help="Holiday calendar for weekend public-holiday carryover, e.g. moldova.",
    ),
    refresh_holidays: bool = typer.Option(
        False,
        "--refresh-holidays",
        help="Refresh the local holiday calendar cache before planning.",
    ),
    holiday_cache_days: int = typer.Option(
        DEFAULT_CACHE_MAX_AGE_DAYS,
        "--holiday-cache-days",
        min=0,
        help="Refresh cached holidays older than this many days. Use 0 to always refresh.",
    ),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes for each entry."),
    dry_run: bool = typer.Option(False, "--dry-run/--execute", help="Preview instead of writing."),
) -> None:
    """Plan regular work logs for every working day last month."""
    _log_period(
        LogPeriod.LAST_MONTH,
        "last month",
        hours=hours,
        project=project,
        task=task,
        location=location,
        work_pattern=work_pattern,
        work_from_home_days=work_from_home_days,
        holiday_calendar=holiday_calendar,
        refresh_holidays=refresh_holidays,
        holiday_cache_days=holiday_cache_days,
        notes=notes,
        dry_run=dry_run,
    )


@app.command("refresh-holidays")
def refresh_holidays(
    holiday_calendar: HolidayCalendar = typer.Option(
        ...,
        "--holiday-calendar",
        help="Holiday calendar to refresh, e.g. moldova.",
    ),
    year: int = typer.Option(
        Date.today().year,
        "--year",
        min=2000,
        max=2100,
        help="Calendar year to refresh.",
    ),
) -> None:
    """Refresh the working-directory holiday calendar cache."""
    try:
        result = load_holidays(holiday_calendar, year, refresh=True)
    except (ValueError, httpx.HTTPError) as exc:
        exit_with_error(str(exc), code=2)
    success(
        f"Cached {len(result.holidays)} holidays for {holiday_calendar.value} {year} "
        f"at {result.cache_path}"
    )
