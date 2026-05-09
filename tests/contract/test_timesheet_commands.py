from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from fusionctl.main import app
from fusionctl.services.holiday_calendar import HolidayCacheResult, PublicHoliday
from fusionctl.services.timecard_execution import TimecardExecutionResult

runner = CliRunner()


def normalized_output(value: str) -> str:
    return " ".join(value.split())


def test_log_week_dry_run_lists_planned_entries() -> None:
    result = runner.invoke(
        app,
        [
            "timesheet",
            "log-week",
            "--project",
            "WORDV266",
            "--task",
            "02",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    output = normalized_output(result.stdout)
    assert "Planned" in output
    assert "WORDV266 / 02" in output
    assert "Work from office (employment contract)" in output
    assert "Total:" in output


def test_log_week_hybrid_location_pattern_lists_home_and_office_entries() -> None:
    result = runner.invoke(
        app,
        [
            "timesheet",
            "log-week",
            "--project",
            "WORDV266",
            "--task",
            "02",
            "--work-pattern",
            "hybrid",
            "--work-from-home-days",
            "2",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    output = normalized_output(result.stdout)
    assert "Work from home" in output
    assert "Work from office (employment contract)" in output


def test_log_week_holiday_calendar_lists_public_holiday_carryover(monkeypatch) -> None:
    def load_holidays(*args, **kwargs) -> HolidayCacheResult:
        return HolidayCacheResult(
            holidays=[PublicHoliday(date=date(2026, 5, 9), name="Ziua Europei")],
            cache_path=Path("."),
            refreshed=False,
        )

    monkeypatch.setattr("fusionctl.cli.commands.timesheet.load_holidays", load_holidays)

    result = runner.invoke(
        app,
        [
            "timesheet",
            "log-week",
            "--project",
            "WORDV266",
            "--task",
            "02",
            "--holiday-calendar",
            "moldova",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "2026-05-08  7h  Regular" in result.stdout
    assert "2026-05-08  1h  Public Holiday" in result.stdout


def test_log_month_without_dry_run_writes_planned_entries(monkeypatch) -> None:
    async def execute_period_logs(entries) -> TimecardExecutionResult:
        assert entries
        return TimecardExecutionResult(
            written_entries=len(entries),
            skipped_dates=0,
            processed_cards=1,
            skipped_timecards=0,
        )

    monkeypatch.setattr(
        "fusionctl.cli.commands.timesheet.execute_period_logs",
        execute_period_logs,
    )

    result = runner.invoke(
        app,
        [
            "timesheet",
            "log-month",
            "--project",
            "WORDV266",
            "--task",
            "02",
        ],
    )

    assert result.exit_code == 0
    output = normalized_output(result.stdout)
    assert "Ready" in output
    assert "Wrote" in output


def test_log_last_month_requires_project_and_task() -> None:
    result = runner.invoke(app, ["timesheet", "log-last-month"])

    assert result.exit_code != 0
    assert "Missing option" in result.stderr
