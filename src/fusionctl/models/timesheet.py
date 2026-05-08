from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from fusionctl.models.project import Project, Task


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EntryStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"


class TimesheetStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class TimeEntry(BaseModel):
    """Single time entry in a timesheet."""

    id: str | None = None
    date: Date
    hours: float = Field(..., ge=0.0, le=24.0)
    project: Project
    task: Task
    notes: str | None = Field(None, max_length=500)
    status: EntryStatus = EntryStatus.DRAFT
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("date")
    @classmethod
    def date_cannot_be_future(cls, value: Date) -> Date:
        if value > Date.today():
            raise ValueError("Date cannot be in the future")
        return value


class Timesheet(BaseModel):
    """Complete timesheet for a user period."""

    id: str = Field(..., min_length=1)
    period_start: Date
    period_end: Date
    status: TimesheetStatus = TimesheetStatus.DRAFT
    entries: list[TimeEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def period_start_before_end(self) -> "Timesheet":
        if self.period_start > self.period_end:
            raise ValueError("Period start must be before end")
        return self

    @property
    def total_hours(self) -> float:
        return sum(entry.hours for entry in self.entries)

    @property
    def total_entries(self) -> int:
        return len(self.entries)

    def get_entries_by_date(self, target_date: Date) -> list[TimeEntry]:
        return [entry for entry in self.entries if entry.date == target_date]

    def get_entries_by_project(self, project_code: str) -> list[TimeEntry]:
        return [entry for entry in self.entries if entry.project.code == project_code]
