# CLI Command Schema: Oracle Fusion Timesheet CLI

**Version**: 1.0  
**Status**: Contract definition for Typer CLI  
**Framework**: Typer (Click-based) with Rich formatting

---

## Command Structure

```
fusion/                        # Main group (app.callback)
├── auth                       # Authentication commands
│   ├── login                  # Authenticate with Oracle Fusion
│   ├── logout                 # Clear local session
│   └── status                 # Show current auth status
├── timesheet                  # Timesheet management
│   ├── list                   # List available timesheets
│   ├── view                   # View specific timesheet details
│   ├── log                    # Log hours to a timesheet
│   ├── log-week               # Log working days in the current week
│   ├── log-month              # Log working days in the current month
│   ├── log-last-month         # Log working days in the previous calendar month
│   ├── update                 # Update a time entry
│   ├── clear                  # Clear editable user-entered rows
│   ├── delete                 # Delete an editable timecard
│   └── summary                # Show timesheet summary
├── cache                      # Cache management
│   ├── clear                  # Clear all cache
│   └── refresh                # Force refresh from server
└── export                     # Export timesheet data
    └── timesheet              # Export timesheet to CSV/JSON
```

---

## Command Definitions

### GROUP: `fusion` (root)

**Purpose**: Application entry point with global flags

**Global Flags**:
```
--help, -h                      # Show help (available on all commands)
--version, -v                   # Show version
-vv, --verbose                  # Diagnostic logging
-vvv                            # Maximum diagnostic logging
--config <path>                 # Override config file location (default: ~/.fusion-cli/config.yaml)
--no-cache                      # Ignore cached data, fetch fresh
```

**Output Format**:
```
CLI Name: fusion
Description: Oracle Fusion Timesheet CLI - Manage timesheets locally without web UI
Version: 0.1.0
Usage: fusion [OPTIONS] COMMAND [ARGS]...
```

---

### COMMAND: `fusion auth login`

**Purpose**: Authenticate user with Oracle Fusion Cloud (ECLF)

**Signature**:
```
fusion auth login [OPTIONS]
```

**Options**:
```
--token <token>                 # Session cookie token (obtain from browser DevTools Network tab)
                                # Example: bm_sv=<redacted-cookie>~...
--browser                       # Open/reuse persistent local browser profile and extract cookies
--headless                      # Reuse browser profile without showing the browser window
--url <url>                     # Oracle URL to open for browser-backed login
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Session authenticated and stored
1   — Failure: Invalid token
2   — Failure: Token expired or invalid format
3   — Failure: API verification failed
```

**Output on Success (Token Method)**:
```
✓ Authenticated as: user@example.com (Person ID: 100000000000000)
  Session token stored securely in OS keychain
  Token retrieved from: eclf.fa.em2.oraclecloud.com
  Person Number: 0000
```

**Output on Failure**:
```
✗ Authentication failed: Invalid or expired token
  Token must be a valid session cookie from eclf.fa.em2.oraclecloud.com
  To obtain a token:
    1. Go to https://eclf.fa.em2.oraclecloud.com
    2. Log in with your Oracle Fusion credentials
    3. Open DevTools (F12) → Network tab
    4. Look for API requests with 'bm_sv' or 'JSESSIONID' cookies
    5. Copy the full cookie value
    6. Run: fusion auth login --token "bm_sv=..." (or pass interactively)
```

**Browser Mode Example**:
```
$ fusion auth login --browser
[Browser opens; first run may require 2FA]
[CLI extracts session cookies automatically]
✓ Authenticated as: user@example.com
  Session token stored securely in OS keychain
  Browser profile: persistent local profile
```

To refresh cookies later without a visible browser, reuse the same local profile:

```
$ fusion auth login --browser --headless
✓ Authenticated
  Session token stored securely in OS keychain
  Token source: browser-profile
```

**Token Input Method (MVP)**:
```
$ fusion auth login --token
Paste your session token (from browser DevTools):
Enter token: [user pastes bm_sv=... ]
✓ Authenticated as: user@example.com
  Session token stored securely in OS keychain
```

**Acceptance Scenario**:
```
$ fusion auth login --token "bm_sv=<redacted-cookie>~..."
✓ Authenticated as: user@example.com (Person ID: 100000000000000)
  Session token stored securely in OS keychain
  Person Number: 0000
```

**Token Validation**:
- CLI makes test API call to `/employmentInfo` to verify token validity
- If successful, stores token in OS keychain
- If failed, returns 403/401 errors from API

---

### COMMAND: `fusion auth logout`

**Purpose**: Clear local session and cached credentials

**Signature**:
```
fusion auth logout [OPTIONS]
```

**Options**:
```
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Session cleared
1   — Failure: No active session to clear
```

**Output on Success**:
```
✓ Session cleared
  You are now logged out. Use 'fusion auth login' to authenticate again.
```

---

### COMMAND: `fusion auth status`

**Purpose**: Show current authentication status

**Signature**:
```
fusion auth status [OPTIONS]
```

**Options**:
```
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Authenticated: User session is valid
1   — Not authenticated: No active session
2   — Expired: Session token has expired
```

**Output if Authenticated**:
```
✓ Status: Authenticated
  Username: user@example.com
  Expires: 2026-05-15 10:00:00 UTC (or "Never" if no expiry)
  Cached since: 2026-05-08 10:00:00 UTC
```

**Output if Not Authenticated**:
```
✗ Status: Not authenticated
  Use 'fusion auth login' to authenticate
```

---

### COMMAND: `fusion timesheet list`

**Purpose**: List all available timesheets

**Signature**:
```
fusion timesheet list [OPTIONS]
```

**Options**:
```
--status <status>              # Filter by status: draft|submitted|approved|rejected (optional, all if not specified)
--format <format>              # Output format: table|json (default: table)
--limit <n>                    # Show last N timesheets (default: 10)
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Timesheets listed
1   — Failure: Not authenticated
2   — Failure: Network error
3   — Failure: No timesheets found
```

**Output (table format)**:
```
ID              Period          Status      Total Entries  Total Hours
─────────────────────────────────────────────────────────────────────────
ts_20260505    2026-05-05 to    submitted   5              40.0
               2026-05-09
ts_20260428    2026-04-28 to    approved    5              40.0
               2026-05-02
ts_20260421    2026-04-21 to    draft       3              24.0
               2026-04-25
```

**Output (json format)**:
```json
{
  "timesheets": [
    {
      "id": "ts_20260505",
      "period_start": "2026-05-05",
      "period_end": "2026-05-09",
      "status": "submitted",
      "total_entries": 5,
      "total_hours": 40.0,
      "created_at": "2026-05-05T08:00:00Z",
      "updated_at": "2026-05-08T17:00:00Z"
    }
  ]
}
```

---

### COMMAND: `fusion timesheet view`

**Purpose**: View detailed timesheet with all entries

**Signature**:
```
fusion timesheet view <TIMESHEET_ID> [OPTIONS]
```

**Arguments**:
```
TIMESHEET_ID                    # Oracle timesheet ID (required)
```

**Options**:
```
--format <format>              # Output format: table|json|csv (default: table)
--date <date>                  # Filter entries by date (YYYY-MM-DD, optional)
--project <code>               # Filter entries by project code (optional)
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Timesheet viewed
1   — Failure: Not authenticated
2   — Failure: Timesheet not found
3   — Failure: Network error
```

**Output (table format)**:
```
Timesheet: ts_20260505
Period: 2026-05-05 to 2026-05-09 | Status: submitted | Total Hours: 40.0

Date        Project     Task         Hours  Notes              Status
────────────────────────────────────────────────────────────────────────
2026-05-08  PROJ001     TASK1        8.0    Regular work       submitted
2026-05-07  PROJ001     TASK1        8.0    Regular work       submitted
2026-05-06  PROJ001     TASK2        8.0    Testing & bug fix  submitted
2026-05-05  PROJ001     TASK1        8.0    Regular work       submitted
2026-05-09  PROJ002     TASK3        8.0    Client meeting     submitted
```

---

### COMMAND: `fusion timesheet log`

**Purpose**: Log hours to a timesheet (interactive or one-shot)

**Signature**:
```
fusion timesheet log [OPTIONS]
```

**Options**:
```
--date <date>                  # Entry date (YYYY-MM-DD, required if not interactive)
--hours <hours>                # Hours logged (0.0-24.0, required if not interactive)
--project <code>               # Project code (required if not interactive)
--task <code>                  # Task code (required if not interactive)
--notes <notes>                # Entry notes (optional)
--interactive, -i              # Interactive mode (prompt for each field)
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Entry logged
1   — Failure: Not authenticated
2   — Failure: Validation error (invalid hours, future date, etc.)
3   — Failure: Network error
4   — Failure: Timesheet not found or is read-only
```

**Output on Success**:
```
✓ Time entry logged
  ID: entry_12345
  Date: 2026-05-08
  Hours: 8.0
  Project: PROJ001 (Customer Portal)
  Task: TASK1 (Backend API)
  Status: submitted
```

**Interactive Mode Output**:
```
$ fusion timesheet log --interactive
Date (YYYY-MM-DD) [default: today]: 2026-05-08
Hours (0-24): 8
Project code: PROJ001
Task code: TASK1
Notes (optional): Regular development work
✓ Time entry logged (ID: entry_12345)
```

**One-shot Mode**:
```
$ fusion timesheet log --date 2026-05-08 --hours 8 --project PROJ001 --task TASK1 --notes "Regular work"
✓ Time entry logged (ID: entry_12345)
```

**Public Holiday Adjacent Day Rule**:

If Oracle has pre-added a `Public Holiday` entry for the next day and the requested date is a working day, an 8-hour log is split into two entries for the requested date:

```
$ fusion timesheet log --date 2026-05-07 --hours 8 --project WORDV266 --task 02
✓ Time entries logged
  2026-05-07  7.0h  Regular
  2026-05-07  1.0h  Public Holiday
```

The pre-added public holiday day itself is preserved and not overwritten.

If the same split rows already exist, the command is idempotent and creates no duplicate hours.

**Prefilled Absence Rule**:

If Oracle has pre-filled a date with an absence entry such as `Annual Leave MD`, the CLI preserves that entry and does not create a regular work entry for the same date.

```
$ fusion timesheet log --date 2026-02-23 --hours 8 --project WORDV266 --task 02
✓ Time entry skipped
  2026-02-23  8.0h  Annual Leave MD
```

**Idempotent Re-run**:

Repeating the same log command for an already-logged day skips matching existing date/time-type/hour rows:

```
$ fusion timesheet log --date 2026-05-06 --hours 8 --project WORDV266 --task 02
✓ Time entry skipped
  2026-05-06  8.0h  Regular already exists
```

---

### COMMAND: `fusion timesheet log-week`

**Purpose**: Convenience command to log the same regular work allocation for each working day in the current week, capped at today

**Signature**:
```
fusion timesheet log-week [OPTIONS]
```

**Options**:
```
--hours <hours>                # Hours per working day (default: 8)
--project <code>               # Project code (required)
--task <code>                  # Task code (required)
--location <value>             # Oracle location for every entry (default: Work from office (employment contract))
--work-pattern <pattern>       # Location pattern: office|home|hybrid (default: office)
--work-from-home-days <n>      # WFH days per week for hybrid pattern (default: 2)
--notes <notes>                # Entry notes applied to each day (optional)
--dry-run / --execute          # Preview or write entries (default: dry-run while batch write is being wired)
--help, -h                     # Show help
```

**Behavior**:
- Expands Monday through today for the current week.
- Excludes weekends.
- Defaults location to `Work from office (employment contract)`.
- `--location "Work from home"` applies one location to every planned entry.
- `--work-pattern hybrid --work-from-home-days 2` assigns the first two working days in each week to `Work from home`; remaining working days use `Work from office (employment contract)`.
- Uses the same public-holiday, absence, and idempotency rules as `fusion timesheet log` when execution is wired.

---

### COMMAND: `fusion timesheet log-month`

**Purpose**: Convenience command to log the same regular work allocation for each working day in weekly timecards that overlap the current calendar month

**Signature**:
```
fusion timesheet log-month [OPTIONS]
```

**Options**: same as `fusion timesheet log-week`.

**Behavior**:
- Expands full Monday-Sunday timecard weeks that overlap the current calendar month.
- Includes spillover weekdays from the previous or next month when those days belong to an overlapping weekly timecard.
- Excludes weekends.
- Uses the same public-holiday, absence, and idempotency rules as `fusion timesheet log` when execution is wired.

---

### COMMAND: `fusion timesheet log-last-month`

**Purpose**: Convenience command to log the same regular work allocation for each working day in the previous calendar month

**Signature**:
```
fusion timesheet log-last-month [OPTIONS]
```

**Options**: same as `fusion timesheet log-week`.

**Behavior**:
- Expands the full previous calendar month.
- Excludes weekends.
- Uses the same public-holiday, absence, and idempotency rules as `fusion timesheet log` when execution is wired.

---

### COMMAND: `fusion timesheet update`

**Purpose**: Update an existing time entry

**Signature**:
```
fusion timesheet update <ENTRY_ID> [OPTIONS]
```

**Arguments**:
```
ENTRY_ID                       # Oracle time entry ID (required)
```

**Options**:
```
--hours <hours>                # Update hours (0.0-24.0, optional)
--project <code>               # Update project (optional)
--task <code>                  # Update task (optional)
--notes <notes>                # Update notes (optional)
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Entry updated
1   — Failure: Not authenticated
2   — Failure: Entry not found
3   — Failure: Validation error
4   — Failure: Cannot update submitted entry (read-only)
```

**Output on Success**:
```
✓ Time entry updated
  ID: entry_12345
  Hours: 8.0 → 9.0
  Notes: "Regular work" → "Regular work + standup"
```

---

### COMMAND: `fusion timesheet clear`

**Purpose**: Remove editable user-entered rows from a timecard while preserving Oracle-owned non-working rows

**Signature**:
```
fusion timesheet clear <TIMECARD_ID> [OPTIONS]
```

**Arguments**:
```
TIMECARD_ID                    # Oracle timecard ID (required)
```

**Options**:
```
--yes, -y                      # Skip confirmation prompt
--dry-run                      # Show rows that would be removed/preserved without saving
--help, -h                     # Show help
```

**Exit Codes**:
```
0   — Success: Timecard cleared or no editable rows found
1   — Failure: Not authenticated
2   — Failure: Timecard not found
3   — Failure: Timecard is read-only
4   — Failure: User cancelled confirmation
```

**Output on Success**:
```
✓ Timecard cleared
  Removed: 5 user-entered rows
  Preserved: 1 public holiday row, 0 absence rows
```

**Behavior**:
- Fetch latest timecard details first.
- Preserve rows with `Public Holiday` time type.
- Preserve rows with `AbsenceEntryFlag`, e.g. `Annual Leave MD`.
- Save the card with `ProcessMode=TIME_SAVE` and only preserved rows in `timeEntries`.

---

### COMMAND: `fusion timesheet delete`

**Purpose**: Delete an editable draft/entered timecard after explicit confirmation, when Oracle exposes a working delete action

**Signature**:
```
fusion timesheet delete <TIMECARD_ID> [OPTIONS]
```

**Arguments**:
```
TIMECARD_ID                    # Oracle timecard ID (required)
```

**Options**:
```
--yes, -y                      # Skip confirmation prompt
--dry-run                      # Show target timecard without deleting it
--help, -h                     # Show help
```

**Exit Codes**:
```
0   — Success: Timecard deleted
1   — Failure: Not authenticated
2   — Failure: Timecard not found
3   — Failure: Oracle refused deletion, e.g. submitted/approved card
4   — Failure: User cancelled confirmation
5   — Failure: Delete endpoint/action is not available in this Oracle environment
```

**Output on Success**:
```
✓ Timecard deleted
  ID: 300005124780107
  Period: 2026-05-04 → 2026-05-10
```

**Safety**:
- Must show period, status, reported hours, and entry count before confirmation.
- Must not delete submitted or approved cards unless Oracle explicitly allows it.
- Prefer `clear` when the user only wants to remove logged rows from an existing period.
- Live testing on `2026-05-09` showed `DELETE /timeCards/{TIMECARD_ID}` returns `404` for an editable future card; until a working Redwood delete action is discovered, the CLI should fail with exit code 5 and recommend `fusion timesheet clear`.

---

### COMMAND: `fusion timesheet summary`

**Purpose**: Show aggregated timesheet summary (this week/month, by project)

**Signature**:
```
fusion timesheet summary [OPTIONS]
```

**Options**:
```
--range <range>                # Time range: week|month|custom (default: week)
--start <date>                 # Custom start date (YYYY-MM-DD, required if --range=custom)
--end <date>                   # Custom end date (YYYY-MM-DD, required if --range=custom)
--format <format>              # Output format: table|json (default: table)
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Summary displayed
1   — Failure: Not authenticated
2   — Failure: Invalid date range
```

**Output (table format)**:
```
Timesheet Summary: Week of May 5-9, 2026

┌─ Totals ──────────────────┐
│ Total Hours: 40.0         │
│ Submitted: 5              │
│ Draft: 0                  │
│ Approved: 0               │
└─────────────────────────┘

┌─ By Project ──────────────┐
│ PROJ001: 32.0 hours       │
│ PROJ002: 8.0 hours        │
└─────────────────────────┘

┌─ By Status ───────────────┐
│ Submitted: 5              │
│ Draft: 0                  │
└─────────────────────────┘
```

---

### COMMAND: `fusion cache clear`

**Purpose**: Clear all cached timesheet data

**Signature**:
```
fusion cache clear [OPTIONS]
```

**Options**:
```
--confirm, -c                  # Skip confirmation prompt
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Cache cleared
1   — Failure: Cache not found or already empty
```

**Output**:
```
Warning: This will delete all cached timesheet data locally.
Are you sure? (y/N): y
✓ Cache cleared
  Deleted: 12 cached timesheets, 87 entries
```

---

### COMMAND: `fusion cache refresh`

**Purpose**: Force refresh of cached data from server

**Signature**:
```
fusion cache refresh [OPTIONS]
```

**Options**:
```
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Cache refreshed
1   — Failure: Not authenticated
2   — Failure: Network error
```

**Output**:
```
⟳ Refreshing timesheet data from Oracle Fusion...
✓ Cache refreshed
  Fetched: 5 timesheets, 23 entries
  Last updated: 2026-05-08 14:30:00 UTC
```

---

### COMMAND: `fusion export timesheet`

**Purpose**: Export timesheet data to CSV or JSON

**Signature**:
```
fusion export timesheet <TIMESHEET_ID> [OPTIONS]
```

**Arguments**:
```
TIMESHEET_ID                   # Oracle timesheet ID to export (required)
```

**Options**:
```
--format <format>              # Export format: csv|json (default: csv)
--output <path>                # Output file path (default: timesheet_<id>.<format>)
--help, -h                      # Show help
```

**Exit Codes**:
```
0   — Success: Timesheet exported
1   — Failure: Not authenticated
2   — Failure: Timesheet not found
3   — Failure: Cannot write to output path
```

**Output**:
```
✓ Timesheet exported
  Format: CSV
  File: ./timesheet_ts_20260505.csv
  Entries: 5
  Size: 2.3 KB
```

**CSV Output** (`timesheet_ts_20260505.csv`):
```
date,project_code,project_name,task_code,task_name,hours,notes,status
2026-05-08,PROJ001,Customer Portal,TASK1,Backend API,8.0,Regular work,submitted
2026-05-07,PROJ001,Customer Portal,TASK1,Backend API,8.0,Regular work,submitted
2026-05-06,PROJ001,Customer Portal,TASK2,Testing,8.0,Testing & bug fix,submitted
```

**JSON Output** (`timesheet_ts_20260505.json`):
```json
{
  "timesheet": {
    "id": "ts_20260505",
    "period_start": "2026-05-05",
    "period_end": "2026-05-09",
    "status": "submitted",
    "entries": [
      {
        "date": "2026-05-08",
        "project": "PROJ001",
        "task": "TASK1",
        "hours": 8.0,
        "notes": "Regular work"
      }
    ]
  }
}
```

---

## Error Handling Contract

**All Commands** must handle and display these errors appropriately:

| Error | Exit Code | Message Pattern |
|-------|-----------|-----------------|
| Not authenticated | 1 | `✗ Not authenticated. Use 'fusion auth login' to begin.` |
| Network timeout | 2 | `✗ Network timeout (30s). Check connectivity or try --no-cache for cached data.` |
| API error | 3 | `✗ Oracle API error: [status code] [error message from server]` |
| Validation error | 4 | `✗ Validation error: [field]: [specific rule violation]` |
| Not found | 5 | `✗ Resource not found: [type] with ID [id]` |
| Permission denied | 6 | `✗ Permission denied. You don't have access to this timesheet.` |

**All errors** must:
- Start with `✗` symbol (failure indicator)
- Include a clear, actionable message
- Suggest next steps (e.g., "Use 'fusion auth login' to authenticate")
- Be written to `stderr` (not stdout)

---

## Global Behavior Contract

**Help System**:
```
Every command supports --help / -h
Displays: description, usage pattern, all options with defaults
Example: fusion timesheet view --help
```

**Verbose Mode**:
```
No verbosity flag: only essential command output, confirmations, and errors.
-v: version shortcut, not logging.
-vv: diagnostic logging, such as config/cache mode.
-vvv: maximum diagnostics for API/cache troubleshooting.

Sensitive values are never logged:
- cookies
- bearer/access/refresh/id tokens
- passwords
```

**Config Override**:
```
--config <path> overrides ~/.fusion-cli/config.yaml
Useful for testing with different configurations
```

**Cache Behavior**:
```
By default: Uses cache if available and fresh (TTL: 24 hours)
--no-cache: Fetches fresh from server, updates cache
```

---

## Next Phase: Implementation

**Ready for**: Task generation and development
**Blockers**: None — contract fully specified
