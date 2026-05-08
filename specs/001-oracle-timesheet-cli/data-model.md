# Data Model: Oracle Fusion Timesheet CLI

**Phase**: 1 (Design)  
**Status**: Ready for implementation

## Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────┐
│ Session                                              │
│ ├── token (str, encrypted)                           │
│ ├── expiry (datetime)                                │
│ ├── username (str)                                   │
│ └── created_at (datetime)                            │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│ Timesheet (1:N relationship with TimeEntry)          │
│ ├── id (str, Oracle timesheet ID)                    │
│ ├── period_start (date)                              │
│ ├── period_end (date)                                │
│ ├── status (enum: draft|submitted|approved|rejected) │
│ ├── total_hours (float, computed)                    │
│ ├── entries (List[TimeEntry])                        │
│ ├── created_at (datetime)                            │
│ └── updated_at (datetime)                            │
└────────────────────────────────────────────────────────┘
           │
           │ contains many
           ▼
┌──────────────────────────────────────────────────────┐
│ TimeEntry                                            │
│ ├── id (str, Oracle entry ID)                        │
│ ├── date (date)                                      │
│ ├── hours (float, 0.0-24.0)                          │
│ ├── project (Project)                                │
│ ├── task (Task)                                      │
│ ├── notes (str, optional)                            │
│ ├── status (enum: draft|submitted|approved)          │
│ ├── created_at (datetime)                            │
│ └── updated_at (datetime)                            │
└──────────────────────────────────────────────────────┘
      │            │
      │ references │ references
      ▼            ▼
┌──────────────┐  ┌──────────────┐
│ Project      │  │ Task         │
│ ├── code (str) │  │ ├── code (str) │
│ ├── name (str) │  │ ├── name (str) │
│ └── active (bool)│ └── active (bool)
└──────────────┘  └──────────────┘

┌──────────────────────────────────────────────────────┐
│ CacheMetadata                                        │
│ ├── last_fetched (datetime)                          │
│ ├── ttl_hours (int, default 24)                      │
│ ├── version (str, schema version)                    │
│ └── oracle_base_url (str, source URL)                │
└──────────────────────────────────────────────────────┘
```

---

## Pydantic Model Definitions

### Project

```python
from pydantic import BaseModel, Field
from typing import Optional

class Project(BaseModel):
    """Oracle project reference"""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    active: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "PROJ001",
                "name": "Customer Portal Development",
                "active": True
            }
        }
```

**Validation**:
- `code` must be 1-50 chars (alphanumeric, hyphens)
- `name` must be 1-200 chars
- `active` boolean flag

---

### Task

```python
class Task(BaseModel):
    """Oracle task reference"""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    active: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "TASK1",
                "name": "Backend API Implementation",
                "active": True
            }
        }
```

**Validation**: Same as Project

---

### TimeEntry

```python
from datetime import datetime, date
from enum import Enum

class EntryStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"

class TimeEntry(BaseModel):
    """Single time entry in a timesheet"""
    id: Optional[str] = None  # Oracle entry ID (None until submitted)
    date: date = Field(..., description="Entry date (YYYY-MM-DD)")
    hours: float = Field(..., ge=0.0, le=24.0, description="Hours logged (0-24)")
    project: Project
    task: Task
    notes: Optional[str] = Field(None, max_length=500)
    status: EntryStatus = EntryStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "entry_12345",
                "date": "2026-05-08",
                "hours": 8.0,
                "project": {"code": "PROJ001", "name": "Customer Portal", "active": True},
                "task": {"code": "TASK1", "name": "Backend API", "active": True},
                "notes": "Completed authentication module",
                "status": "submitted",
                "created_at": "2026-05-08T09:00:00Z",
                "updated_at": "2026-05-08T09:00:00Z"
            }
        }
```

**Validation**:
- `hours`: 0.0 to 24.0 (no negative, no overday)
- `date`: Must be valid date in YYYY-MM-DD format
- `notes`: Max 500 chars (capture reason, context)
- `status` enum: Only valid states allowed
- Timestamps auto-generated (UTC)

---

### Timesheet

```python
from typing import List

class TimesheetStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"

class Timesheet(BaseModel):
    """Complete timesheet for a user period"""
    id: str = Field(..., min_length=1, description="Oracle timesheet ID")
    period_start: date = Field(..., description="Period start date (YYYY-MM-DD)")
    period_end: date = Field(..., description="Period end date (YYYY-MM-DD)")
    status: TimesheetStatus = TimesheetStatus.DRAFT
    entries: List[TimeEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def total_hours(self) -> float:
        """Computed: sum of all entry hours"""
        return sum(entry.hours for entry in self.entries)
    
    @property
    def total_entries(self) -> int:
        """Computed: count of entries"""
        return len(self.entries)
    
    def get_entries_by_date(self, target_date: date) -> List[TimeEntry]:
        """Query: entries for a specific date"""
        return [e for e in self.entries if e.date == target_date]
    
    def get_entries_by_project(self, project_code: str) -> List[TimeEntry]:
        """Query: entries for a specific project"""
        return [e for e in self.entries if e.project.code == project_code]
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "ts_20260505",
                "period_start": "2026-05-05",
                "period_end": "2026-05-09",
                "status": "submitted",
                "entries": [
                    {
                        "id": "entry_1",
                        "date": "2026-05-08",
                        "hours": 8.0,
                        "project": {"code": "PROJ001", "name": "Customer Portal", "active": True},
                        "task": {"code": "TASK1", "name": "Backend API", "active": True},
                        "notes": "Regular work",
                        "status": "submitted",
                        "created_at": "2026-05-08T09:00:00Z",
                        "updated_at": "2026-05-08T09:00:00Z"
                    }
                ],
                "created_at": "2026-05-05T08:00:00Z",
                "updated_at": "2026-05-08T17:00:00Z"
            }
        }
```

**Validation**:
- `period_start` must be before `period_end`
- `status` enum: Only valid states
- `entries` list can be empty (draft timesheet)

**Query Methods**:
- `total_hours`: Computed property (sum of all hours)
- `get_entries_by_date()`: Filter entries by date
- `get_entries_by_project()`: Filter entries by project code

---

### Session

```python
from typing import Optional

class Session(BaseModel):
    """Authentication session with Oracle Fusion Cloud"""
    token: str = Field(..., description="Session token (encrypted)")
    expiry: Optional[datetime] = None  # UTC timestamp
    username: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def is_valid(self) -> bool:
        """Check if session is still valid"""
        if self.expiry is None:
            return True  # No expiry = valid
        return datetime.utcnow() < self.expiry
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "[ENCRYPTED_TOKEN]",
                "expiry": "2026-05-15T10:00:00Z",
                "username": "user@example.com",
                "created_at": "2026-05-08T10:00:00Z"
            }
        }
```

**Validation**:
- `token`: Never logged or printed (security)
- `expiry`: Optional (some APIs don't expire tokens)
- `is_valid`: Helper to check expiration

---

### CacheMetadata

```python
from typing import Optional

class CacheMetadata(BaseModel):
    """Metadata for cached data"""
    last_fetched: datetime = Field(default_factory=datetime.utcnow)
    ttl_hours: int = Field(24, ge=1, le=720)  # 1 hour to 30 days
    version: str = "1.0"  # Schema version for migrations
    oracle_base_url: str = "https://eclf.fa.em2.oraclecloud.com"
    
    def is_expired(self) -> bool:
        """Check if cache is older than TTL"""
        age_hours = (datetime.utcnow() - self.last_fetched).total_seconds() / 3600
        return age_hours > self.ttl_hours
    
    class Config:
        json_schema_extra = {
            "example": {
                "last_fetched": "2026-05-08T10:00:00Z",
                "ttl_hours": 24,
                "version": "1.0",
                "oracle_base_url": "https://eclf.fa.em2.oraclecloud.com"
            }
        }
```

---

## Validation Rules Summary

| Entity | Field | Rule | Error Message |
|--------|-------|------|---------------|
| TimeEntry | hours | 0.0 ≤ hours ≤ 24.0 | "Hours must be between 0 and 24" |
| TimeEntry | date | Valid date, not future | "Date cannot be in the future" |
| Timesheet | period_start | Before period_end | "Period start must be before end" |
| Timesheet | entries | Non-empty for submitted | "Cannot submit timesheet with no entries" |
| Project | code | 1-50 chars, alphanumeric | "Project code must be alphanumeric" |
| Session | token | Non-empty, encrypted | "Session token is missing" |

---

## State Transitions

### TimeEntry Status Flow

```
DRAFT → SUBMITTED → APPROVED
  ↓
  └─→ (stays DRAFT if validation fails)

SUBMITTED → REJECTED → DRAFT (resubmit)
```

### Timesheet Status Flow

```
DRAFT → SUBMITTED → APPROVED
  ↓
  └─→ (stays DRAFT if validation fails)

SUBMITTED → REJECTED → DRAFT (resubmit)
```

**Rules**:
- Only timesheets with all entries SUBMITTED (or APPROVED) can be SUBMITTED
- Individual entries can be updated while timesheet is DRAFT
- Cannot update entries once timesheet is SUBMITTED (must update via Oracle UI or new entry)

---

## Storage Format (JSON)

### Timesheet Cache File: `timesheets.json`

```json
{
  "timesheets": [
    {
      "id": "ts_20260505",
      "period_start": "2026-05-05",
      "period_end": "2026-05-09",
      "status": "submitted",
      "entries": [],
      "created_at": "2026-05-05T08:00:00Z",
      "updated_at": "2026-05-08T17:00:00Z"
    }
  ],
  "metadata": {
    "last_fetched": "2026-05-08T10:00:00Z",
    "ttl_hours": 24,
    "version": "1.0",
    "oracle_base_url": "https://eclf.fa.em2.oraclecloud.com"
  }
}
```

### Entries Cache File: `entries_{ts_id}.json`

```json
{
  "timesheet_id": "ts_20260505",
  "entries": [
    {
      "id": "entry_1",
      "date": "2026-05-08",
      "hours": 8.0,
      "project": {"code": "PROJ001", "name": "Customer Portal", "active": true},
      "task": {"code": "TASK1", "name": "Backend API", "active": true},
      "notes": "Regular work",
      "status": "submitted",
      "created_at": "2026-05-08T09:00:00Z",
      "updated_at": "2026-05-08T09:00:00Z"
    }
  ],
  "metadata": {
    "last_fetched": "2026-05-08T10:00:00Z",
    "ttl_hours": 24,
    "version": "1.0",
    "oracle_base_url": "https://eclf.fa.em2.oraclecloud.com"
  }
}
```

---

## Next Phase: CLI Schema & Quickstart

**Blockers**: None — ready for Phase 1 CLI contract definition and quickstart guide
