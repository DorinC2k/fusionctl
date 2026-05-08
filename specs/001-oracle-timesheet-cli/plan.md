# Implementation Plan: Oracle Fusion Timesheet CLI

**Branch**: `001-oracle-timesheet-cli` | **Date**: 2026-05-08 | **Spec**: [specs/001-oracle-timesheet-cli/spec.md](spec.md)
**Input**: Feature specification from `/specs/001-oracle-timesheet-cli/spec.md`

## Summary

Build a Python CLI tool to log and manage Oracle Fusion Cloud timesheets locally without a database. The CLI will authenticate with ECLF (eclf.fa.em2.oraclecloud.com), fetch existing timesheets, allow users to log hours and activities, cache data locally for offline access, and export to CSV/JSON. Tech stack: Python 3.10+, Poetry for dependency management, Poe for task automation, Typer for CLI framework, local file-based storage with optional encryption for credentials.

## Technical Context

**Language/Version**: Python 3.10+ (latest stable)  
**CLI Framework**: Typer (built on Click, with modern async support)  
**Task Automation**: Poe (Poetry task runner)  
**Dependency Manager**: Poetry (with Poetry export for reproducible builds)  
**Storage**: Local file system (JSON/YAML cache in `~/.fusion-cli/cache/`, credentials in OS keychain or encrypted local file)  
**Testing**: pytest + pytest-asyncio (async HTTP testing) + pytest-vcr (record/replay HTTP interactions)  
**HTTP Client**: httpx (async-capable, similar to requests but modern)  
**Data Serialization**: pydantic (validation) + orjson (fast JSON)  
**Terminal UI**: Rich (tables, panels, progress bars)  
**Target Platform**: Linux/macOS/Windows (cross-platform via Python standard library)  
**Project Type**: CLI tool (single-user local application)  
**Performance Goals**: Commands complete within 5 seconds (network latency acceptable); cached views < 1 second  
**Constraints**: < 50MB runtime memory, offline-capable with cached data, no database dependency  
**Scale/Scope**: Single user, local environment; supports ~100+ timesheet entries in cache

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No constitution defined for this project yet. All architectural decisions are deferred to this plan and design phase. No violations to gate on.

## Project Structure

### Authentication Implementation Notes

**Important Discovery**: Oracle ECLF uses **Microsoft Azure AD (Entra ID) SAML2 SSO**, which requires handling 2FA (Microsoft Authenticator push notifications).

**CLI Authentication Approach**:

Since interactive SAML flows with 2FA cannot be fully automated via simple HTTP requests, we have two options:

**Option A: Headless Browser Automation (Recommended for MVP)**
- Use `playwright-python` or `selenium` to handle SAML login
- Automate credential entry, 2FA approval via browser automation
- Extract session cookies after successful login
- Store cookies in OS keychain

**Option B: Manual Token Copy (Simpler, But Less Convenient)**
- User manually logs in via browser, opens DevTools
- User copies `bm_sv` and `JSESSIONID` cookies
- User runs: `fusion auth login --token <cookie-string>`
- CLI stores token in keychain, reuses for API calls

**Decision for MVP**: Start with **Option B** (simpler to implement), with path to **Option A** (Option A) in future versions.

**Dependencies**: 
- Option B: No additional dependencies (use httpx + keyring)
- Option A: Add `playwright` to pyproject.toml



### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
fusionctl/
├── pyproject.toml              # Poetry config + Poe tasks
├── poetry.lock                 # Locked dependencies
├── README.md                   # Project documentation
├── src/
│   └── fusionctl/
│       ├── __init__.py
│       ├── main.py             # CLI entry point (@app.command())
│       ├── api/
│       │   ├── __init__.py
│       │   ├── oracle_client.py  # HTTP client for ECLF API
│       │   ├── auth.py           # Authentication & token mgmt
│       │   └── endpoints.py      # API endpoint definitions
│       ├── models/
│       │   ├── __init__.py
│       │   ├── timesheet.py      # Timesheet entity (pydantic)
│       │   ├── time_entry.py     # TimeEntry entity
│       │   ├── project.py        # Project entity
│       │   └── session.py        # Session/token entity
│       ├── services/
│       │   ├── __init__.py
│       │   ├── auth_service.py   # Auth logic (login, refresh, logout)
│       │   ├── timesheet_service.py # Timesheet CRUD
│       │   ├── cache_service.py  # Local caching logic
│       │   └── export_service.py # CSV/JSON export
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── commands/
│       │   │   ├── __init__.py
│       │   │   ├── auth.py       # login/logout/status commands
│       │   │   ├── timesheet.py  # list/view/log/update/summary commands
│       │   │   ├── cache.py      # cache clear/refresh commands
│       │   │   └── export.py     # export commands
│       │   └── utils.py          # CLI formatting, tables, etc.
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── cache.py          # File-based cache interface
│       │   └── secrets.py        # Secure credential storage (OS keychain)
│       ├── config.py             # Configuration & environment
│       └── exceptions.py         # Custom exceptions
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures
│   ├── fixtures/
│   │   ├── mock_oracle_responses.py
│   │   └── sample_data.py
│   ├── unit/
│   │   ├── test_auth_service.py
│   │   ├── test_timesheet_service.py
│   │   ├── test_cache_service.py
│   │   └── test_export_service.py
│   ├── integration/
│   │   ├── test_oracle_client_vcr.py  # VCR-recorded HTTP tests
│   │   ├── test_auth_flow.py
│   │   └── test_timesheet_workflow.py
│   └── contract/
│       └── test_cli_commands.py # CLI command contract tests
│
├── .specify/                    # Spec Kit configuration
└── specs/
    └── 001-oracle-timesheet-cli/
        ├── spec.md
        ├── plan.md              # This file
        ├── research.md          # Phase 0 output (TBD)
        ├── data-model.md        # Phase 1 output (TBD)
        ├── quickstart.md        # Phase 1 output (TBD)
        └── contracts/           # Phase 1 output (TBD)
            └── cli-schema.md    # CLI command contract definitions
```

**Structure Decision**: Single-project Python CLI structure (Option 1). Organized by functional layers:
- **api/**: HTTP client and Oracle Fusion integration (one source of external API knowledge)
- **models/**: Data entities (pydantic-validated)
- **services/**: Business logic (auth, caching, export)
- **cli/commands/**: Command-line interface (Typer-based)
- **storage/**: Local persistence (cache files, credential storage)
- **tests/**: Unit, integration (with VCR for recorded HTTP), and contract tests

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
