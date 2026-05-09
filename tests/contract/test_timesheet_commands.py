from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from fusionctl.main import app
from fusionctl.services.holiday_calendar import HolidayCacheResult, PublicHoliday

runner = CliRunner()


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
    assert "Planned" in result.stdout
    assert "WORDV266 / 02" in result.stdout
    assert "Work from office (employment contract)" in result.stdout
    assert "Total:" in result.stdout


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
    assert "Work from home" in result.stdout
    assert "Work from office (employment contract)" in result.stdout


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


def test_log_month_execute_fails_until_oracle_batch_write_is_wired() -> None:
    result = runner.invoke(
        app,
        [
            "timesheet",
            "log-month",
            "--project",
            "WORDV266",
            "--task",
            "02",
            "--execute",
        ],
    )

    assert result.exit_code == 3
    assert "Oracle batch logging is not wired yet" in result.stderr


def test_log_last_month_requires_project_and_task() -> None:
    result = runner.invoke(app, ["timesheet", "log-last-month"])

    assert result.exit_code != 0
    assert "Missing option" in result.stderr
