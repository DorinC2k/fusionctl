from __future__ import annotations

from decimal import Decimal, InvalidOperation

import typer

from fusionctl.cli.utils import console, exit_with_error, success
from fusionctl.services.log_periods import LogPeriod, PlannedLogEntry, plan_period_logs

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
        console.print(f"  {entry.date.isoformat()}  {entry.hours:g}h  {entry.project} / {entry.task}")
    console.print(f"  Total: {total:g}h")


def _log_period(
    period: LogPeriod,
    period_label: str,
    *,
    hours: str,
    project: str,
    task: str,
    notes: str | None,
    dry_run: bool,
) -> None:
    try:
        entries = plan_period_logs(
            period,
            hours=_decimal_hours(hours),
            project=project,
            task=task,
            notes=notes,
        )
    except ValueError as exc:
        exit_with_error(str(exc), code=2)

    if not entries:
        success(f"No working days to log for {period_label}")
        return

    _render_plan(period_label, entries, dry_run=dry_run)
    if not dry_run:
        exit_with_error(
            "Oracle batch logging is not wired yet. Re-run with --dry-run to preview entries.",
            code=3,
        )


@app.command("log-week")
def log_week(
    hours: str = typer.Option("8", "--hours", help="Hours to log for each working day."),
    project: str = typer.Option(..., "--project", help="Oracle project code."),
    task: str = typer.Option(..., "--task", help="Oracle task code."),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes for each entry."),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Preview instead of writing."),
) -> None:
    """Plan regular work logs for this week up to today."""
    _log_period(
        LogPeriod.CURRENT_WEEK,
        "current week",
        hours=hours,
        project=project,
        task=task,
        notes=notes,
        dry_run=dry_run,
    )


@app.command("log-month")
def log_month(
    hours: str = typer.Option("8", "--hours", help="Hours to log for each working day."),
    project: str = typer.Option(..., "--project", help="Oracle project code."),
    task: str = typer.Option(..., "--task", help="Oracle task code."),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes for each entry."),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Preview instead of writing."),
) -> None:
    """Plan regular work logs for this month up to today."""
    _log_period(
        LogPeriod.CURRENT_MONTH,
        "current month",
        hours=hours,
        project=project,
        task=task,
        notes=notes,
        dry_run=dry_run,
    )


@app.command("log-last-month")
def log_last_month(
    hours: str = typer.Option("8", "--hours", help="Hours to log for each working day."),
    project: str = typer.Option(..., "--project", help="Oracle project code."),
    task: str = typer.Option(..., "--task", help="Oracle task code."),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes for each entry."),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Preview instead of writing."),
) -> None:
    """Plan regular work logs for every working day last month."""
    _log_period(
        LogPeriod.LAST_MONTH,
        "last month",
        hours=hours,
        project=project,
        task=task,
        notes=notes,
        dry_run=dry_run,
    )
