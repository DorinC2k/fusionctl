# Tasks: Oracle Fusion Timesheet CLI

**Input**: Design documents from `/specs/001-oracle-timesheet-cli/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-schema.md, quickstart.md
**Tests**: Included because the feature specification defines independent tests for every user story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Python CLI project and development workflow.

- [x] T001 Create Poetry project metadata and Poe tasks in pyproject.toml
- [x] T002 [P] Create source package directories under src/fusionctl/
- [x] T003 [P] Create test package directories under tests/
- [x] T004 [P] Add README with MVP cookie-login workflow in README.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, config, storage, HTTP client, and CLI shell required by all user stories.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 [P] Implement settings model and config loading in src/fusionctl/config.py
- [x] T006 [P] Implement custom exception types in src/fusionctl/exceptions.py
- [x] T007 [P] Implement Pydantic Project and Task models in src/fusionctl/models/project.py
- [x] T008 [P] Implement Pydantic TimeEntry and Timesheet models in src/fusionctl/models/timesheet.py
- [x] T009 [P] Implement Pydantic Session and CacheMetadata models in src/fusionctl/models/session.py
- [x] T010 [P] Implement secure session storage abstraction in src/fusionctl/storage/secrets.py
- [x] T011 [P] Implement JSON cache storage in src/fusionctl/storage/cache.py
- [x] T012 Implement Oracle endpoint path builder in src/fusionctl/api/endpoints.py
- [x] T013 Implement httpx Oracle client with cookies, retries, and error mapping in src/fusionctl/api/oracle_client.py
- [x] T014 Implement Typer root app and command registration in src/fusionctl/main.py
- [x] T015 [P] Implement Rich output helpers in src/fusionctl/cli/utils.py
- [x] T016 [P] Add shared pytest fixtures and sample data in tests/conftest.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - CLI Authentication with Oracle Fusion Cloud (Priority: P1) MVP

**Goal**: Store, clear, and report an Oracle Fusion browser session cookie securely.

**Independent Test**: Run `fusion auth login --token`, then `fusion auth status`, then `fusion auth logout`; verify the token is stored, status is authenticated, and logout clears it.

### Tests for User Story 1

- [x] T017 [P] [US1] Add auth command contract tests in tests/contract/test_auth_commands.py
- [x] T018 [P] [US1] Add session storage unit tests in tests/unit/test_auth_service.py

### Implementation for User Story 1

- [x] T019 [US1] Implement auth service login/logout/status in src/fusionctl/services/auth_service.py
- [x] T020 [US1] Implement `fusion auth login|logout|status` commands in src/fusionctl/cli/commands/auth.py
- [x] T021 [US1] Wire auth command group into src/fusionctl/main.py
- [x] T022 [US1] Validate auth flow with `poe test tests/contract/test_auth_commands.py`

**Checkpoint**: Authentication MVP is functional and independently testable.

---

## Phase 4: User Story 2 - View and Summarize Timesheets (Priority: P1)

**Goal**: List, view, and summarize Oracle Fusion timesheets using live API data with cache fallback.

**Independent Test**: Run `fusion timesheet list`, `fusion timesheet view <id>`, and `fusion timesheet summary`; verify terminal and JSON outputs match cached or mocked Oracle data.

### Tests for User Story 2

- [ ] T023 [P] [US2] Add timesheet CLI contract tests in tests/contract/test_timesheet_commands.py
- [ ] T024 [P] [US2] Add Oracle client unit tests for list/detail parsing in tests/unit/test_oracle_client.py
- [ ] T025 [P] [US2] Add timesheet service unit tests in tests/unit/test_timesheet_service.py

### Implementation for User Story 2

- [ ] T026 [US2] Implement Oracle response mapping for timesheets in src/fusionctl/api/oracle_client.py
- [ ] T027 [US2] Implement timesheet list/view/summary logic in src/fusionctl/services/timesheet_service.py
- [ ] T028 [US2] Implement cache reads/writes for fetched timesheets in src/fusionctl/services/cache_service.py
- [ ] T029 [US2] Implement `fusion timesheet list|view|summary` commands in src/fusionctl/cli/commands/timesheet.py
- [ ] T030 [US2] Wire timesheet command group into src/fusionctl/main.py
- [ ] T031 [US2] Validate view workflow with `poe test tests/contract/test_timesheet_commands.py`

**Checkpoint**: Timesheet viewing is functional without logging new entries.

---

## Phase 5: User Story 3 - Log and Update Timesheet Entries (Priority: P1)

**Goal**: Add and update timecard lines from one-shot or interactive CLI input.

**Independent Test**: Run `fusion timesheet log --date <date> --hours <hours> --project <project> --task <task>` and `fusion timesheet update <entry-id> --hours <new-hours>` against mocked Oracle responses.

### Tests for User Story 3

- [ ] T032 [P] [US3] Add log/update command contract tests in tests/contract/test_timesheet_mutation_commands.py
- [ ] T033 [P] [US3] Add mutation service tests in tests/unit/test_timesheet_mutations.py

### Implementation for User Story 3

- [ ] T034 [US3] Implement submit/update entry methods in src/fusionctl/api/oracle_client.py
- [ ] T035 [US3] Implement validation and mutation logic in src/fusionctl/services/timesheet_service.py
- [ ] T036 [US3] Implement `fusion timesheet log|update` commands in src/fusionctl/cli/commands/timesheet.py
- [ ] T037 [US3] Update cache after successful mutations in src/fusionctl/services/cache_service.py
- [ ] T038 [US3] Validate mutation workflow with `poe test tests/contract/test_timesheet_mutation_commands.py`

**Checkpoint**: Core P1 timesheet workflow is complete.

---

## Phase 6: User Story 4 - Local Caching and Offline Access (Priority: P2)

**Goal**: Make cached timesheet data usable when the API is unavailable and allow explicit cache management.

**Independent Test**: Fetch data once, simulate network failure, run view/list commands, and verify cached output includes a cached indicator.

### Tests for User Story 4

- [ ] T039 [P] [US4] Add cache command contract tests in tests/contract/test_cache_commands.py
- [ ] T040 [P] [US4] Add cache service unit tests in tests/unit/test_cache_service.py

### Implementation for User Story 4

- [ ] T041 [US4] Implement cache clear/refresh service operations in src/fusionctl/services/cache_service.py
- [ ] T042 [US4] Implement offline fallback behavior in src/fusionctl/services/timesheet_service.py
- [ ] T043 [US4] Implement `fusion cache clear|refresh` commands in src/fusionctl/cli/commands/cache.py
- [ ] T044 [US4] Wire cache command group into src/fusionctl/main.py
- [ ] T045 [US4] Validate cache workflow with `poe test tests/contract/test_cache_commands.py`

**Checkpoint**: Offline viewing and cache management are complete.

---

## Phase 7: User Story 5 - Export Timesheet Data (Priority: P2)

**Goal**: Export cached or fetched timesheet data as CSV or JSON.

**Independent Test**: Run `fusion export timesheet <id> --format csv` and `--format json`; verify generated files contain the expected entries.

### Tests for User Story 5

- [ ] T046 [P] [US5] Add export command contract tests in tests/contract/test_export_commands.py
- [ ] T047 [P] [US5] Add export service unit tests in tests/unit/test_export_service.py

### Implementation for User Story 5

- [ ] T048 [US5] Implement CSV and JSON export logic in src/fusionctl/services/export_service.py
- [ ] T049 [US5] Implement `fusion export timesheet` command in src/fusionctl/cli/commands/export.py
- [ ] T050 [US5] Wire export command group into src/fusionctl/main.py
- [ ] T051 [US5] Validate export workflow with `poe test tests/contract/test_export_commands.py`

**Checkpoint**: Reporting/export workflow is complete.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Harden the CLI, docs, and developer experience.

- [ ] T052 [P] Add VCR integration test skeleton in tests/integration/test_oracle_client_vcr.py
- [ ] T053 [P] Add developer sample fixtures in tests/fixtures/sample_data.py
- [ ] T054 [P] Update quickstart validation commands in specs/001-oracle-timesheet-cli/quickstart.md
- [ ] T055 Run formatting, linting, type checking, and tests via Poe tasks
- [ ] T056 Review sensitive output paths to ensure cookies are never printed in src/fusionctl/

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies.
- Foundational (Phase 2): Depends on Setup completion and blocks all stories.
- User Stories (Phase 3+): Depend on Foundational completion.
- Polish: Depends on desired user stories being complete.

### User Story Dependencies

- US1 Authentication: First MVP slice and required for live Oracle calls.
- US2 View/Summary: Depends on US1 for live calls but can be tested with fixtures independently.
- US3 Log/Update: Depends on US1 and uses US2 models/client mapping.
- US4 Cache/Offline: Integrates with US2 but can be tested from fixture data.
- US5 Export: Integrates with US2 cache/view data but can be tested from fixture data.

### Parallel Opportunities

- T002-T004 can run in parallel after T001.
- T005-T011 and T015-T016 can run in parallel after setup.
- Contract and unit tests within each user story can be written in parallel.
- US4 and US5 can proceed in parallel after US2 service interfaces are stable.

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 authentication using manual browser-cookie login.
3. Complete US2 list/view/summary against fixtures and then live Oracle once credentials are available.
4. Stop and validate before mutating real timesheets.

### Incremental Delivery

1. Auth-only CLI.
2. Read-only timesheet CLI with cache.
3. Mutating log/update commands.
4. Offline cache controls.
5. CSV/JSON export.
