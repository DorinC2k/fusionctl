from datetime import date

import pytest
from pydantic import ValidationError

from fusionctl.models import Project, Task, TimeEntry, Timesheet


def test_timesheet_total_hours() -> None:
    project = Project(code="WORDV266", name="RedHat Helix EU")
    task = Task(code="02", name="Build")
    entry = TimeEntry(date=date(2026, 5, 8), hours=8.0, project=project, task=task)
    timesheet = Timesheet(
        id="300005105736789",
        period_start=date(2026, 5, 4),
        period_end=date(2026, 5, 10),
        entries=[entry],
    )

    assert timesheet.total_hours == 8.0
    assert timesheet.total_entries == 1


def test_time_entry_rejects_future_date() -> None:
    project = Project(code="WORDV266", name="RedHat Helix EU")
    task = Task(code="02", name="Build")

    with pytest.raises(ValidationError):
        TimeEntry(date=date(2999, 1, 1), hours=8.0, project=project, task=task)
