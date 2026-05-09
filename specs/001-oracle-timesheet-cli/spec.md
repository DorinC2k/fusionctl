# Feature Specification: Oracle Fusion Timesheet CLI

**Feature Branch**: `001-oracle-timesheet-cli`  
**Created**: 2026-05-08  
**Status**: Draft  
**Input**: User description: "Build a CLI for Oracle's web app where you log the timesheet and other activities, part of the fusion setup. Python project, using Poetry and Poe, no database, everything should be local"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CLI Authentication with Oracle Fusion Cloud (Priority: P1)

As a developer/user, I need to authenticate with Oracle Fusion Cloud (ECLF) from the CLI so I can access timesheet data securely without storing credentials unsafely.

**Why this priority**: Authentication is the foundational requirement—without it, no other functionality can work. This is a blocking requirement for the MVP.

**Independent Test**: Can be fully tested by running the login command, entering credentials, and verifying that a valid session token is stored locally in a secure manner.

**Acceptance Scenarios**:

1. **Given** the CLI is running without authentication, **When** user runs `fusion auth login --token`, **Then** the CLI prompts for a browser-copied Oracle session cookie string and stores it locally
2. **Given** the CLI has cached credentials, **When** user runs any command, **Then** the CLI reuses the session token without re-prompting
3. **Given** the session token is expired, **When** user runs a command, **Then** the CLI automatically refreshes the token or prompts for re-authentication
4. **Given** the authentication fails, **When** user enters incorrect credentials, **Then** the CLI displays a clear error message and allows retry

---

### User Story 2 - View and Summarize Timesheets (Priority: P1)

As a user, I need to view my existing timesheets and see a summary of logged hours so I can understand my current timesheet status without navigating the web UI.

**Why this priority**: This is the core value proposition of the CLI—viewing timesheets locally. P1 because it's the primary use case.

**Independent Test**: Can be fully tested by running `fusion timesheet list` and `fusion timesheet view` commands, verifying that timesheet data is displayed correctly in terminal format.

**Acceptance Scenarios**:

1. **Given** the CLI is authenticated, **When** user runs `fusion timesheet list`, **Then** the CLI displays all available timesheets with dates, status (draft/submitted/approved), and total hours
2. **Given** a timesheet exists, **When** user runs `fusion timesheet view <timesheet-id>`, **Then** the CLI displays detailed timesheet data including days, hours logged per project/task, and notes
3. **Given** the user requests a summary, **When** user runs `fusion timesheet summary`, **Then** the CLI shows aggregated data (total hours this week/month, hours by project, pending vs submitted)
4. **Given** the web service is unavailable, **When** user runs a view command, **Then** the CLI shows cached data if available with a "cached" indicator

---

### User Story 3 - Log and Update Timesheet Entries (Priority: P1)

As a user, I need to log hours and activities to my timesheet via the CLI so I can quickly add time entries without using the web interface.

**Why this priority**: This is the primary interaction pattern. P1 because it's the core functionality for daily usage.

**Independent Test**: Can be fully tested by running `fusion timesheet log` commands and verifying entries are submitted to Oracle Fusion Cloud and reflected in subsequent `view` commands.

**Acceptance Scenarios**:

1. **Given** the CLI is authenticated, **When** user runs `fusion timesheet log --date <date> --hours <hours> --project <project> --task <task> --notes "<notes>"`, **Then** the CLI submits the entry to Oracle Fusion Cloud
2. **Given** an entry was submitted, **When** the submission succeeds, **Then** the CLI displays a confirmation with entry ID and status
3. **Given** the user wants to update an entry, **When** user runs `fusion timesheet update <entry-id> --hours <new-hours>`, **Then** the CLI updates the entry and shows confirmation
4. **Given** multiple entries need to be logged, **When** user runs `fusion timesheet log` in interactive mode, **Then** the CLI prompts for date/hours/project/task/notes sequentially
5. **Given** a timecard contains a pre-added `Public Holiday` entry for a day, **When** the user logs the preceding working day for 8 hours, **Then** the CLI logs 7 hours as `Regular` and 1 hour as `Public Holiday` on the preceding working day
6. **Given** a timecard contains a pre-filled absence day such as `Annual Leave MD`, **When** the user logs that same date, **Then** the CLI preserves the absence row and does not create a regular work entry for that date
7. **Given** the CLI has already logged entries for a day, **When** the user repeats the same log command for that day, **Then** the CLI detects matching existing entries and does not stack duplicate hours

---

### User Story 4 - Local Caching and Offline Access (Priority: P2)

As a user, I need timesheet data cached locally so I can view previously fetched timesheets even if the network is temporarily unavailable.

**Why this priority**: Enhances reliability and user experience. P2 because P1 features are more critical for MVP but this adds significant UX value.

**Independent Test**: Can be tested by fetching timesheet data, disconnecting from the network, and verifying the CLI still shows cached data with appropriate messaging.

**Acceptance Scenarios**:

1. **Given** the CLI has fetched timesheet data, **When** data is stored in a local cache directory, **Then** subsequent views can use cached data if the network is unavailable
2. **Given** cached data exists, **When** user runs a view command offline, **Then** the CLI displays cached data with a "cached" badge/indicator
3. **Given** cache exists for a timesheet, **When** user explicitly runs `fusion timesheet refresh`, **Then** the CLI forces a fresh fetch from the server
4. **Given** the user wants to manage cache, **When** user runs `fusion cache clear`, **Then** all cached data is removed

---

### User Story 5 - Export Timesheet Data (Priority: P2)

As a user, I need to export timesheet data to CSV/JSON formats so I can use it in other tools or share reports with my manager.

**Why this priority**: Adds value for reporting and integration. P2 because viewing is more critical than exporting for MVP.

**Independent Test**: Can be tested by running export commands and verifying the generated files contain correct data in the specified format.

**Acceptance Scenarios**:

1. **Given** a timesheet is loaded, **When** user runs `fusion timesheet export <timesheet-id> --format csv --output <filename>`, **Then** a CSV file is created with all timesheet entries
2. **Given** multiple timesheets are available, **When** user runs `fusion timesheet export --range <start-date> <end-date> --format json`, **Then** a JSON file contains all timesheets in the date range
3. **Given** data is exported, **When** the file is created, **Then** the CLI confirms the export location and file size

---

### Edge Cases

- What happens when the user's session expires during a long operation?
- How does the system handle network timeouts when fetching large timesheets?
- What occurs if Oracle Fusion Cloud API changes or becomes unavailable?
- How does the CLI behave if local cache becomes corrupted?
- What if the user has multiple active timesheets?
- How does the CLI handle special characters in project names or task descriptions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST authenticate users with Oracle Fusion Cloud (ECLF endpoint: eclf.fa.em2.oraclecloud.com) using browser-copied session cookies for MVP, because the web app uses Microsoft Azure AD SAML2 SSO with 2FA
- **FR-002**: System MUST securely store authentication tokens locally (encrypted or in a secure OS keychain)
- **FR-003**: System MUST fetch existing timesheets from the Oracle Fusion Cloud API
- **FR-004**: System MUST allow users to log hours with associated project, task, and notes
- **FR-005**: System MUST submit timesheet entries to Oracle Fusion Cloud
- **FR-006**: System MUST update existing timesheet entries
- **FR-007**: System MUST display timesheet data in readable terminal format (tables, summaries)
- **FR-008**: System MUST cache timesheet data locally for offline access
- **FR-009**: System MUST export timesheet data to CSV and JSON formats
- **FR-010**: System MUST handle authentication token expiration gracefully by detecting 401/403 API responses and asking the user to re-run cookie login
- **FR-011**: System MUST provide clear error messages for all failures (network, auth, API errors)
- **FR-012**: System MUST support interactive mode for bulk timesheet entry
- **FR-013**: System MUST provide a help command and documentation for all CLI commands
- **FR-014**: System MUST preserve Oracle pre-added `Public Holiday` days and split the preceding working day into 7h `Regular` plus 1h `Public Holiday` when logging a full 8-hour day
- **FR-015**: System MUST preserve Oracle pre-filled absence entries such as `Annual Leave MD` and `Medical Leave MD` and avoid logging regular work on those dates
- **FR-016**: System MUST make repeated log operations idempotent by skipping allocations that already exist for the same date, time type, and hours

### Key Entities

- **Timesheet**: Represents a user's timesheet for a period (contains entries, status, dates)
- **TimeEntry**: Individual time entry (date, hours, project, task, notes, status)
- **Project**: Reference to an Oracle project code
- **Task**: Reference to an Oracle task identifier
- **Session/Token**: Authentication token for Oracle Fusion Cloud API
- **Cache**: Local storage of timesheet data (date-based, with metadata)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can authenticate and access timesheets within 30 seconds of running first command
- **SC-002**: All core commands (list, view, log, summary) return results within 5 seconds (or show cached data if offline)
- **SC-003**: Cached data persists across CLI sessions and can be accessed offline
- **SC-004**: User can log a complete timesheet entry with all required fields in under 1 minute (interactive mode)
- **SC-005**: Export functionality produces valid, importable CSV/JSON files
- **SC-006**: All authentication and sensitive data is handled securely with no credentials visible in logs or config files
- **SC-007**: CLI provides contextual help for every command (--help flag)

## Assumptions

- Users have valid Oracle Fusion Cloud accounts with timesheet access via eclf.fa.em2.oraclecloud.com
- Users have Python 3.10+ installed locally
- Network connectivity is intermittent but generally available
- Oracle Fusion Cloud REST API is accessible and documented (or can be reverse-engineered from web app)
- Users are comfortable with terminal/CLI interfaces
- Local file system storage is acceptable for cache and credentials (security handled via OS permissions or encryption)
- No multi-user support needed (single-user local CLI)
- The Oracle web interface URLs provided (oracle.endava.com and eclf.fa.em2.oraclecloud.com) are the targets for scraping or API integration
