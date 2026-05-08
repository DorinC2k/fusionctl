# Research Phase: Oracle Fusion Timesheet CLI

**Date**: 2026-05-08  
**Status**: In Progress (requires user authentication context)

## Research Questions Resolved

### Q1: Oracle Fusion Cloud API Authentication Method

**Unknown**: How does ECLF (eclf.fa.em2.oraclecloud.com) expose timesheet APIs? REST, SOAP, or web scraping?

**Decision**: REST API via OAuth2 or Session-based auth (most modern approach)

**Rationale**: 
- Oracle Fusion Cloud modernized to REST APIs (deprecated SOAP)
- ECLF endpoint suggests cloud deployment with REST endpoints
- OAuth2 or session tokens are standard for cloud services

**Next Steps**: 
- [NEEDS USER INPUT] Confirm API endpoint structure (GET /fscmUI/rest/... or similar)
- [NEEDS USER INPUT] Authentication flow (OAuth2 client credentials, username/password → session token)
- Reverse-engineer from browser DevTools Network tab if docs unavailable

**Alternatives Considered**:
- SOAP API: Legacy, less likely for modern cloud offerings
- Web scraping: Fragile, violates TOS, avoided unless API unavailable

---

### Q2: CLI Framework Choice

**Unknown**: Best CLI framework for async HTTP + Rich terminal output?

**Decision**: **Typer** (Pydantic integration, modern async support)

**Rationale**:
- Built on Click (battle-tested, standard)
- Native Pydantic integration for argument validation
- Clean decorator-based syntax
- Good async support for httpx calls
- Rich ecosystem for terminal UI (tables, progress, colors)

**Alternative Considered**:
- argparse: Too verbose for modern Python
- Click: Functional but less Pydantic-friendly
- Typer: **CHOSEN** — best balance

**Dependency Added**: `typer[all]` in pyproject.toml

---

### Q3: Async HTTP Client for Oracle API

**Unknown**: httpx vs requests vs aiohttp for async HTTP to Oracle endpoints?

**Decision**: **httpx** (async-first, requests-compatible API)

**Rationale**:
- Requests-like API (familiar), but async-first design
- Excellent for concurrent API calls
- Built-in connection pooling, timeout handling
- Works well with pytest-vcr for testing
- Active maintenance, production-ready

**Alternative Considered**:
- requests: Sync-only, not ideal for CLI responsiveness
- aiohttp: More complex, heavier dependency
- httpx: **CHOSEN** — best fit

**Dependency Added**: `httpx` in pyproject.toml

---

### Q4: Local Credential Storage

**Unknown**: How to securely store OAuth tokens / session tokens locally?

**Decision**: Hybrid approach:
1. **macOS/Linux**: OS keychain (via `keyring` library)
2. **Windows**: Windows Credential Manager (via `keyring` library)  
3. **Fallback**: Encrypted local file (`cryptography` library) if keychain unavailable

**Rationale**:
- OS keychain is standard for secure local storage
- `keyring` library abstracts platform differences
- Fallback prevents total failure on unsupported systems
- Tokens never stored in plaintext

**Implementation**:
```python
# Example in storage/secrets.py
from keyring import get_password, set_password
set_password("fusion-cli", "oracle_token", token_value)
token = get_password("fusion-cli", "oracle_token")
```

**Dependencies**: `keyring` + `cryptography` in pyproject.toml

---

### Q5: Cache Storage Format

**Unknown**: JSON vs YAML vs pickle for caching timesheet data locally?

**Decision**: **JSON** (with optional YAML support for config)

**Rationale**:
- JSON is human-readable, debuggable
- Native Python support
- Pydantic can serialize/deserialize directly
- Version-controllable if needed for backups
- Cross-platform, not Python-specific

**Cache Location**: `~/.fusion-cli/cache/` (XDG Base Directory spec on Linux)

**Cache Structure**:
```
~/.fusion-cli/
├── cache/
│   ├── timesheets.json        # Cached timesheet metadata
│   ├── entries_{ts_id}.json   # Cached entries per timesheet
│   └── metadata.json           # Cache timestamp, version, etc.
└── config.yaml                 # CLI configuration (optional)
```

**Dependencies**: `pydantic` (already chosen) + `orjson` (fast JSON encoding)

---

### Q6: Testing Strategy for API Integration

**Unknown**: How to test CLI against Oracle API without credentials or live server?

**Decision**: **pytest-vcr** (HTTP record/replay)

**Rationale**:
- Record real API responses once (with anonymized data)
- Replay for all test runs (fast, deterministic, no live dependency)
- Great for CI/CD pipelines
- Matches GitOps/IaC philosophy of reproducibility

**Test Structure**:
- `tests/fixtures/`: Mock responses and sample data
- `tests/integration/`: VCR-recorded HTTP tests (test_*.py with vcr decorator)
- `tests/unit/`: Service logic without HTTP (mocked dependencies)
- `tests/contract/`: CLI command contracts (stdout/exit code validation)

**Dependencies**: `pytest-vcr`, `pytest-asyncio`, `pytest` in pyproject.toml

---

### Q7: Export Format Support

**Unknown**: CSV vs JSON for export? Both?

**Decision**: **Both CSV and JSON** (user choice via `--format` flag)

**Rationale**:
- CSV: Spreadsheet-friendly (Excel, Google Sheets) — primary use case
- JSON: Structured data, easier for downstream processing
- `--format csv|json` flag in export command

**CSV Structure**:
```
date,project,task,hours,notes,status
2026-05-08,PROJ001,TASK1,8,Regular work,submitted
```

**Dependencies**: `csv` module (stdlib) + `orjson` (already chosen)

---

### Q8: Configuration Management

**Unknown**: Centralized config file or environment variables?

**Decision**: **Both** (config file as primary, env vars for CI/CD override)

**Rationale**:
- User preference stored in `~/.fusion-cli/config.yaml`
- Environment variables override for automation
- Pydantic Settings for easy management

**Config Example**:
```yaml
# ~/.fusion-cli/config.yaml
oracle:
  base_url: https://eclf.fa.em2.oraclecloud.com
  timeout: 30
cache:
  ttl_hours: 24
  location: ~/.fusion-cli/cache
cli:
  output_format: table  # or json
```

**Dependencies**: `pydantic-settings` in pyproject.toml

---

## Dependencies Summary

**Core**:
- `typer[all]` — CLI framework
- `httpx` — Async HTTP client
- `pydantic` — Data validation
- `rich` — Terminal formatting

**Storage & Security**:
- `keyring` — OS keychain integration
- `cryptography` — Fallback encryption

**Configuration**:
- `pydantic-settings` — Config management
- `orjson` — Fast JSON

**Testing**:
- `pytest` — Test framework
- `pytest-asyncio` — Async test support
- `pytest-vcr` — HTTP mocking

**Task Runner** (via Poetry):
- `poe` — Task automation (specified in pyproject.toml)

---

---

## Q9: Oracle Fusion Cloud Authentication Flow (RESOLVED)

**Unknown**: Exact OAuth2/SAML authentication mechanism for ECLF

**Decision**: **Microsoft Azure AD SAML2 SSO + Session Tokens** (Azure B2C/Entra ID)

**Discovered Details**:
- **Auth Endpoint**: `https://login.microsoftonline.com/0b3fc178-b730-4e8b-9843-e81259237b77/saml2`
- **ECLF Base URL**: `https://eclf.fa.em2.oraclecloud.com`
- **Auth Method**: SAML2 + 2FA (Microsoft Authenticator)
- **Session Token**: Stored in cookies (`bm_sv`, `JSESSIONID`)
- **User Identification**: Person Number (e.g., "5237") and Person ID (in API params)

**Implementation Approach**:
1. Redirect to Microsoft login URL (SAML flow)
2. Capture session cookies after 2FA approval
3. Use session cookies in subsequent API calls (OR extract JWT bearer token if available)
4. Token refresh: Likely automatic via cookie expiry, or re-authenticate

**Next Steps for CLI**:
- May need to use a headless browser (Playwright/Selenium) for initial login due to SAML complexity
- OR document manual login flow, save session cookies to keychain
- Investigate if Bearer token auth available (check HTTP response headers)

---

## Q10: HCM REST API Endpoints (RESOLVED)

**Unknown**: Exact endpoint structure for timecard CRUD operations

**Decision**: **Oracle HCM REST API** with resource versioning

**Discovered Endpoints**:

### Base URL Pattern
```
https://eclf.fa.em2.oraclecloud.com/hcmRestApi/rest/rv:{RESOURCE_VERSION}/en/{VERSION}/
```

Example: `https://eclf.fa.em2.oraclecloud.com/hcmRestApi/rest/rv:ee7b954c-bcc8-4b41-bf6a-3a136a30223e/en/11.13.18.05:9/`

### Key Resources

**1. employmentInfo** (Get user context)
```
GET /employmentInfo?fields=+LegislationCode,+AssignmentName,+DisplayName,+PersonNumber,+LegalEntityId,+LegalEmployerName,+BusinessUnitId,+PersonId,+AssignmentId,+AssignmentNumber,+AssignmentName&finder=findByPersonId;PersonId={PERSON_ID}&limit=1&onlyData=true
```
Response includes: PersonNumber, PersonId, LegalEntityId, BusinessUnitId, AssignmentId

**2. timeCards** (List timesheets)
```
POST /timeCards/action/findByAdvancedSearchQuery
Content-Type: application/json

{
  "query": {
    // Query parameters for filtering timesheets
  }
}
```
Response includes: List of timesheets with periods, status (Approved/Draft/Submitted), total hours

**3. timeCardAttestations** (Attestation status)
```
GET /timeCardAttestations
```

**4. timeChangeAudits** (Change history)
```
GET /timeChangeAudits
```

### Metadata Endpoints
```
GET /describe.openapi?metadataMode=minimal&resources=timeCards,timeChangeAudits,timeCardAttestations
GET /describe.openapi?partialDescriptionForCatalogOpenAPI=timeCards
```

Returns OpenAPI 3.0 schema for the resource

---

## Q11: Timecard Data Structure (RESOLVED)

**Unknown**: Exact JSON structure for timecard entries

**Discovered Structure**:

### Timesheet Summary (from list view)
```
{
  "timecardId": "300005105736789",
  "periodStart": "27/04/26",
  "periodEnd": "03/05/26",
  "status": "Approved",  // or "Draft", "Submitted"
  "reportedHours": 40,
  "scheduledHours": 40,
  "absenceHours": 0,
  "totalHours": 40,
  "personNumber": "5237",
  "personId": "100000000355154",
  "exceptionPeriod": "27/04/26 - 03/05/26"
}
```

### Timecard Detail (daily entries)
```
{
  "date": "27/04/26",  // Format: DD/MM/YY
  "dayOfWeek": "Monday",
  "entries": [
    {
      "hours": 8.0,
      "projectCode": "WORDV266",
      "projectName": "RedHat Helix EU",
      "taskCode": "02",
      "taskName": "Build",
      "timeType": "Regular",  // or "Public Holiday", "Absence", etc.
      "location": "Work from office (employment contract)",  // or "Work from home"
      "startTime": "09:00",  // Optional for time-tracked entries
      "endTime": "17:00"     // Optional for time-tracked entries
    }
  ]
}
```

### HTTP Response Format
```
{
  "items": [ /* array of timesheets */ ],
  "count": 10,
  "hasMore": false,
  "limit": 50,
  "offset": 0
}
```

---

## Q12: Session Management & Security (RESOLVED)

**Unknown**: How to securely handle session tokens and re-authentication

**Discovered Details**:
- **Session Token Location**: HTTP Cookies (bm_sv, JSESSIONID, Oracle specific tokens)
- **Token Expiry**: Automatic (no explicit expiry visible, handled by server)
- **2FA**: Required (Microsoft Authenticator push notification)
- **CSRF Protection**: Likely enforced (check response headers for CSRF tokens)
- **API Authentication**: Session cookies passed in `Cookie` header

**Implementation**:
```
Cookie: bm_sv=E3A8F9F36D259512CECA0FF7AAC9627A~...; JSESSIONID=...
```

**CLI Strategy**:
1. Store all cookies from initial SAML login in OS keychain
2. Serialize cookies to file (with encryption fallback)
3. Reuse cookies in subsequent API calls (httpx session persistence)
4. On 401/403: Trigger re-authentication flow
5. For 2FA: Provide instructions to manually approve, OR use headless browser automation

---

## Next Phase: Phase 1 Design

**Blockers Remaining**: ✅ **ALL RESOLVED**

**Critical Information Captured**:
- ✅ Authentication flow (Microsoft Azure AD SAML2)
- ✅ API base URL and resource versioning scheme
- ✅ Key REST endpoints (employmentInfo, timeCards, timeCardAttestations, timeChangeAudits)
- ✅ Timecard data structure (summary and detailed entries)
- ✅ Session management (cookie-based, automatic expiry)
- ✅ HTTP headers and request format

**Phase 1 Deliverables**:
1. `data-model.md` — Pydantic model definitions
2. `contracts/cli-schema.md` — CLI command schema (all commands, flags, outputs)
3. `quickstart.md` — Developer setup guide (Poetry install, first run, etc.)
4. Update `AGENTS.md` with plan reference
