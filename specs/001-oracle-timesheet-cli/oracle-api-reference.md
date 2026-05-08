# Oracle Fusion Cloud HCM REST API Reference

**Endpoint**: eclf.fa.em2.oraclecloud.com  
**Authentication**: Session cookies (Microsoft Azure AD SAML2)  
**API Version**: 11.13.18.05:9 (may vary)  
**Resource Versioning**: Dynamic (UUID-based, e.g., `rv:ee7b954c-bcc8-4b41-bf6a-3a136a30223e`)

---

## Authentication & Session Management

### Session Establishment

1. User logs in via `https://login.microsoftonline.com/[TENANT_ID]/saml2`
2. User completes 2FA (Microsoft Authenticator)
3. Session cookies are set:
   - `bm_sv`: Akamai bot management token
   - `JSESSIONID`: Oracle session ID
   - Other: CSRF tokens, tracking cookies

### Session Persistence

All API requests require these cookies to be sent in the `Cookie` header:

```http
GET /hcmRestApi/rest/rv:{VERSION}/en/{API_VERSION}/timeCards
Cookie: bm_sv={VALUE}; JSESSIONID={VALUE}
```

### Redwood API Authentication Discovery

The Redwood web app also calls:

```http
GET /fscmRestApi/tokenrelay
```

The response contains a short-lived bearer token. Real `timeCards` calls from the browser include both the browser session cookies and:

```http
Authorization: Bearer <tokenrelay access_token>
Content-Type: application/vnd.oracle.adf.action+json
Accept: application/json
x-xsrf-token: <value from XSRF-TOKEN-* cookie>
```

For CLI implementation, the practical auth flow is:

1. Open Oracle in a persistent local Playwright/Chromium profile.
2. Complete Microsoft 2FA only when Azure/Oracle require it.
3. Extract Oracle cookies from the persistent profile and store the Cookie header in the local secret store.
4. Call `/fscmRestApi/tokenrelay` with those cookies.
5. Use the returned bearer token for HCM REST API calls until it expires.
6. Refresh by calling tokenrelay again; if tokenrelay returns 401, reuse `fusion auth login --browser --headless` to harvest fresh cookies from the local profile.

Live testing showed tokenrelay can return `401` unless the request includes the `x-xsrf-token` header copied from the Oracle `XSRF-TOKEN-*` cookie.

### Session Expiry

- Tokens expire based on server-side session timeout
- CLI should catch 401/403 responses and first try browser-profile refresh before prompting for interactive re-authentication
- Browser profile reuse avoids repeated 2FA only while the SSO session remains valid; it cannot bypass a new server-side MFA challenge
- Implement exponential backoff for rate limiting (429 responses)

---

## Base URL Structure

```
Base: https://eclf.fa.em2.oraclecloud.com/hcmRestApi/rest/rv:{RESOURCE_VERSION}/en/{API_VERSION}/
```

**Example**:
```
https://eclf.fa.em2.oraclecloud.com/hcmRestApi/rest/rv:ee7b954c-bcc8-4b41-bf6a-3a136a30223e/en/11.13.18.05:9/
```

**Resource Version Discovery**:
- Resource version is dynamic and obtained from the first API call
- Capture from response headers or metadata endpoints
- Cache for session duration (10-30 minutes)

---

## API Endpoints

### 1. Get User Employment Info

**Endpoint**:
```
GET /employmentInfo
```

**Query Parameters**:
```
fields=+LegislationCode,+AssignmentName,+DisplayName,+PersonNumber,+LegalEntityId,+LegalEmployerName,+BusinessUnitId,+PersonId,+AssignmentId,+AssignmentNumber
finder=findByPersonId;PersonId={PERSON_ID}
limit=1
onlyData=true
```

**Request Example**:
```bash
GET /hcmRestApi/rest/rv:ee7b954c-bcc8-4b41-bf6a-3a136a30223e/en/11.13.18.05:9/employmentInfo?fields=%2BLegislationCode%2B%2BAssignmentName%2B%2BDisplayName%2B%2BPersonNumber%2B%2BLegalEntityId%2B%2BLegalEmployerName%2B%2BBusinessUnitId%2B%2BPersonId%2B%2BAssignmentId%2B%2BAssignmentNumber&finder=findByPersonId%3BPersonId%3D100000000355154&limit=1&onlyData=true
```

**Response** (200 OK):
```json
{
  "PersonNumber": "5237",
  "PersonId": "100000000355154",
  "DisplayName": "Dorin Cobzac",
  "AssignmentId": "12345",
  "AssignmentNumber": "E123",
  "LegalEntityId": "1001",
  "LegalEmployerName": "Endava Limited",
  "BusinessUnitId": "2001",
  "LegislationCode": "IE"
}
```

**Purpose**: Get authenticated user's context (PersonId, PersonNumber for subsequent calls)

---

### 2. List Timesheets (Advanced Search)

**Endpoint**:
```
POST /timeCards/action/findByAdvancedSearchQuery
```

**Request Body**:
```json
{
  "displayFields": [
    "TimePeriodStartDate",
    "TimePeriodEndDate",
    "StatusCode",
    "ReportedHours",
    "ScheduledHours",
    "AbsenceHours",
    "TotalHours",
    "SubmissionDate",
    "Exception"
  ],
  "filters": [
    {
      "name": ["TimePeriod"],
      "values": [
        "2026-04-25T00:03:17.380+03:00",
        "2026-05-09T00:03:17.540+03:00"
      ]
    }
  ],
  "limit": 50,
  "offset": 0,
  "query": "",
  "searchFields": ["Status"],
  "sort": [
    {
      "direction": "DESC",
      "name": "TimePeriodStartDate"
    }
  ]
}
```

**Request Example**:
```bash
POST /hcmRestApi/rest/rv:ee7b954c-bcc8-4b41-bf6a-3a136a30223e/en/11.13.18.05:9/timeCards/action/findByAdvancedSearchQuery
Content-Type: application/json

{
  "timecardDateRangeDetail": {
    "timecardDateFrom": "2026-04-20",
    "timecardDateTo": "2026-05-10"
  },
  "limit": 50,
  "offset": 0
}
```

**Response** (200 OK):
```json
{
  "result": {
    "items": [
      {
        "AbsenceHours": null,
        "Exception": null,
        "ReportedHours": "40.00",
        "ScheduledHours": "32.00",
        "StatusCode": "APPROVED",
        "SubmissionDate": "2026-05-04T12:17:04.784+00:00",
        "TimeCardId": "300005105736789",
        "TimePeriodEndDate": "2026-05-03",
        "TimePeriodStartDate": "2026-04-27",
        "TotalHours": "40.00"
      }
    ],
    "summary": {
      "count": 1,
      "hasMore": false,
      "limit": 50,
      "offset": 0
    }
  }
}
```

**Purpose**: Fetch list of timesheets for a date range

**Status Values**: `DRAFT`, `SUBMITTED`, `APPROVED`, `REJECTED`

---

### 3. Get Timecard Details (Verified Redwood Endpoint)

**Endpoint**:
```
GET /timeCardEntryDetails
  ?expand=timeCardLayouts,timeCards,timeCardLayouts.timeCardFields,timeCards.publicHolidays,timeCards.timeEntries,timeCards.approvalTasks,timeCards.timeEntries.timeCardFieldValues,timeCards.emptyEntries,timeCards.emptyEntries.timeCardFieldValues,timeCards.messages,timeCards.timeEntries.messages,timeCards.scheduledHours,timeCards.changeRequests,timeCards.timeEntries.changeRequests
  &finder=findByTimeCardId;TimeCardId={TIMECARD_ID},UserContext=WORKER
  &limit=5000
  &onlyData=true
```

**Request Example**:
```bash
GET /hcmRestApi/rest/rv:ee7b954c-bcc8-4b41-bf6a-3a136a30223e/en/11.13.18.05:9/timeCardEntryDetails?finder=findByTimeCardId%3BTimeCardId%3D300005105736789%2CUserContext%3DWORKER&expand=timeCardLayouts%2CtimeCards%2CtimeCards.timeEntries%2CtimeCards.timeEntries.timeCardFieldValues&limit=5000&onlyData=true
```

**Response** (200 OK):
```json
{
  "items": [
    {
      "TimeCardId": "300005105736789",
      "TimeCardVersion": 2,
      "PersonId": "100000000355154",
      "PersonNumber": "5237",
      "timeCards": {
        "items": [
          {
            "TimeCardId": "300005105736789",
            "TimeCardVersion": 2,
            "Status": "APPROVED",
            "StartDate": "2026-04-27T00:00:00+00:00",
            "StopDate": "2026-05-03T23:59:59.999+00:00",
            "timeEntries": {
              "items": [
                {
                  "TimeEntryId": "300005105740582",
                  "TimeEntryVersion": 2,
                  "UnitOfMeasure": "HR",
                  "EntryDate": "2026-04-27T00:00:00+00:00",
                  "Measure": "8",
                  "GroupingSequence": 1,
                  "timeCardFieldValues": {
                    "items": [
                      {
                        "TimeCardFieldId": "300004857566518",
                        "Value": "300004669699898",
                        "DisplayValue": "WORDV266 - RedHat Helix EU"
                      },
                      {
                        "TimeCardFieldId": "300004857566519",
                        "Value": "100002436964151",
                        "DisplayValue": "02 - Build"
                      },
                      {
                        "TimeCardFieldId": "300004857566520",
                        "Value": "300003879160145",
                        "DisplayValue": "Regular"
                      }
                    ]
                  }
                }
              ]
            }
          }
        ]
      }
    }
  ]
}
```

**Purpose**: Get full details of a timesheet including all daily entries

**Important Mapping Notes**:

- Use `timeCardLayouts.items[].timeCardFields.items[]` to map field IDs to labels.
- Observed field labels:
  - `300004857566518`: Project Code
  - `300004857566519`: Task Details
  - `300004857566520`: Time Type
  - `300004857566523`: Location
- Approved timecards can be viewed but not edited (`AllowEditFlag=false`, `AllowSubmitFlag=false` in the layout).
- Some periods contain server-created `Public Holiday` entries before the user logs regular work. These rows are authoritative and must be preserved in the full-card save payload.
- Some periods contain pre-filled absence entries. These rows use `AbsenceEntryFlag` and carry the absence display value in field `300004857566525`; they are also authoritative and must be preserved.

---

### 4. Create or Update Timecard Entries (Verified Live)

Oracle exposes create/update through the top-level `timeCards` resource. Live testing showed that worker-context mutations succeed via `POST /timeCards`; direct child collection writes to `/timeCards/{id}/child/timeEntries` returned 404/403 in this environment.

#### 4.1 Create Current-Period Timecard

```http
POST /timeCards
Content-Type: application/json
```

Verified request:

```json
{
  "TimeCardId": 0,
  "TimeCardVersion": 0,
  "PersonId": "100000000355154",
  "StartDate": "2026-05-04T00:00:00+00:00",
  "StopDate": "2026-05-10T23:59:59.999+00:00",
  "UserContext": "WORKER"
}
```

Verified response:

```http
201 Created
{}
```

**Important**: The Redwood UI attempted `UserContext: "TIME_MANAGER"` on the Add page and Oracle rejected it with `HXT-1665163`. CLI writes should use `UserContext: "WORKER"`.

After creation, fetch details with `timeCardEntryDetails` to obtain `TimeCardId`, `TimeCardVersion`, layout fields, and edit flags.

#### 4.2 Add Time Entry

Create entries by posting the entire card save payload back to `/timeCards` with `ProcessMode: "TIME_SAVE"` and a populated `timeEntries` array:

**Important**: the `timeEntries` array behaves as the desired complete entry set for the card. If the payload contains only one new entry, Oracle replaces the previous entries with that one entry. To add a line without deleting existing lines:

1. Fetch the latest card detail through `timeCardEntryDetails`.
2. Copy every existing `timeEntries.items[]` row with its current `TimeEntryId`, `TimeEntryVersion`, and full `timeCardFieldValues` array.
3. Append one new entry with `TimeEntryId: 0` and `TimeEntryVersion: 0`.
4. Save the full array with `ProcessMode: "TIME_SAVE"`.

Live testing showed that sending multiple new entries with `TimeEntryId: 0` in a single payload can fail with a duplicate primary key error. Add multiple new rows one save at a time, or omit generated IDs only when Oracle accepts that shape for the specific payload.

#### Public Holiday Adjacent Day Rule

When a timecard already contains a pre-added `Public Holiday` entry for a date, preserve that holiday entry exactly as returned by Oracle. If the previous calendar day is a working day and the CLI is logging a full 8-hour day, create two entries on the previous working day:

- `7` hours with time type `Regular`
- `1` hour with time type `Public Holiday`

Use the `Public Holiday` Time Type field value from the pre-added Oracle row or from `timeCardFieldValues` lookup; do not hard-code the underlying Oracle ID because it can vary by environment/layout. The full-card save payload must include both the preserved holiday row and the split previous-day rows.

Verified Republic of Moldova examples:

- Card `300005105736789` contains `MD Labor Day 2026` on `2026-05-01`, with Oracle rows `2026-04-30: 7 Regular + 1 Public Holiday` and `2026-05-01: 8 Public Holiday`.
- Card `300004965689346` contains `MD New Year's Day 2026` on `2026-01-01`, with Oracle rows `2025-12-31: 1 Public Holiday` and `2026-01-01: 8 Public Holiday`.
- Card `300005011389793` contains `MD Orthodox Christmas Day and Holiday 2026` on `2026-01-07` and `2026-01-08`, with Oracle rows including `2026-01-06: 1 Public Holiday`.

#### Prefilled Absence Entries

Oracle absence rows are not normal project/task/time-type rows. Live February 2026 examples showed `timeEntries` with:

- `AbsenceEntryFlag` present
- `Measure: "8"`
- field `300004857566525` containing the absence type display value
- no project/task/time-type/location fields on the absence row

Verified examples:

- Card `300005057958110`, period `2026-02-23` to `2026-03-01`, status `ENTERED`: five 8h rows for `Annual Leave MD`, field value `300000379896443`, with summary `AbsenceHours: "40.00"`, `ReportedHours: "0.00"`, `TotalHours: "40.00"`.
- Card `300005057154971`, period `2026-02-16` to `2026-02-22`, status `APPROVED`: five 8h rows for `Medical Leave MD`, field value `300000369558737`, with summary `AbsenceHours: "40.00"`, `ReportedHours: "0.00"`, `TotalHours: "40.00"`.

When logging regular work, the CLI must treat dates with an existing absence row as already occupied and skip creating regular entries for those dates. In full-card save payloads, preserve absence rows exactly as returned by Oracle, including `TimeEntryId`, `TimeEntryVersion`, `AbsenceEntryFlag`, `EntryType`, and the `timeCardFieldValues` array.

```json
{
  "TimeCardId": "300005124780107",
  "TimeCardVersion": 1,
  "PersonId": "100000000355154",
  "StartDate": "2026-05-04T00:00:00+00:00",
  "StopDate": "2026-05-10T23:59:59.999+00:00",
  "ProcessMode": "TIME_SAVE",
  "UserContext": "WORKER",
  "IgnoreWarningsFlag": false,
  "timeEntries": [
    {
      "TimeEntryId": 0,
      "TimeEntryVersion": 0,
      "TimeCardId": "300005124780107",
      "UnitOfMeasure": "HR",
      "StartTime": null,
      "StopTime": null,
      "Measure": "1",
      "PersonId": "100000000355154",
      "Comments": "created by fusionctl",
      "GroupingSequence": 0,
      "EntryDate": "2026-05-04T00:00:00+00:00",
      "timeCardFieldValues": [
        {
          "TimeCardFieldId": "300004857566518",
          "Value": "300004669699898"
        },
        {
          "TimeCardFieldId": "300004857566519",
          "Value": "100002436964151"
        },
        {
          "TimeCardFieldId": "300004857566520",
          "Value": "300003879160145"
        },
        {
          "TimeCardFieldId": "300004857566523",
          "Value": "Work from home"
        },
        {
          "TimeCardFieldId": "300004857566527",
          "Value": null
        },
        {
          "TimeCardFieldId": "300004857566525",
          "Value": null
        },
        {
          "TimeCardFieldId": "300004857566486",
          "Value": "300000002560077"
        },
        {
          "TimeCardFieldId": "300004857566490",
          "Value": "300000001598197"
        },
        {
          "TimeCardFieldId": "300004857566484",
          "Value": "ST"
        },
        {
          "TimeCardFieldId": "300004857566482",
          "Value": "300000001656097"
        }
      ]
    }
  ]
}
```

Verified response:

```http
201 Created
{}
```

Re-fetching details after save returned a server-created entry:

```json
{
  "TimeEntryId": "300005124722679",
  "TimeEntryVersion": 1,
  "Measure": "1",
  "EntryDate": "2026-05-04T00:00:00+00:00",
  "Comments": "created by fusionctl"
}
```

#### 4.3 Update Time Entry

Update entries with the same top-level `POST /timeCards` save payload. Use the latest `TimeCardVersion` and `TimeEntryVersion` from `timeCardEntryDetails`, and include the full `timeCardFieldValues` array.

Verified update:

```json
{
  "TimeCardId": "300005124780107",
  "TimeCardVersion": 2,
  "PersonId": "100000000355154",
  "StartDate": "2026-05-04T00:00:00+00:00",
  "StopDate": "2026-05-10T23:59:59.999+00:00",
  "ProcessMode": "TIME_SAVE",
  "UserContext": "WORKER",
  "IgnoreWarningsFlag": false,
  "timeEntries": [
    {
      "TimeEntryId": "300005124722679",
      "TimeEntryVersion": 1,
      "TimeCardId": "300005124780107",
      "UnitOfMeasure": "HR",
      "Measure": "2",
      "Comments": "updated by fusionctl",
      "GroupingSequence": 0,
      "EntryDate": "2026-05-04T00:00:00+00:00",
      "timeCardFieldValues": ["same full array as create"]
    }
  ]
}
```

Verified response was `201 {}`. Re-fetching details returned `TimeEntryVersion: 2` and `Measure: "2"`.

#### 4.4 Submit Timecard for Approval (Verified Live)

Submit uses the same top-level parent workflow as save, but with `ProcessMode: "TIME_SUBMIT"`. The submit payload must include the full current card state, including all entries and latest entry versions.

```http
POST /timeCards
Content-Type: application/vnd.oracle.adf.action+json
```

Verified request shape:

```json
{
  "TimeCardId": "300005124780107",
  "TimeCardVersion": 2,
  "PersonId": "100000000355154",
  "StartDate": "2026-05-04T00:00:00+00:00",
  "StopDate": "2026-05-10T23:59:59.999+00:00",
  "ProcessMode": "TIME_SUBMIT",
  "UserContext": "WORKER",
  "IgnoreWarningsFlag": false,
  "timeEntries": [
    {
      "TimeEntryId": "300005124782455",
      "TimeEntryVersion": 1,
      "TimeCardId": "300005124780107",
      "UnitOfMeasure": "HR",
      "Measure": "8",
      "EntryDate": "2026-05-04T00:00:00+00:00",
      "timeCardFieldValues": ["same full field-value array as save"]
    }
  ]
}
```

Verified successful response:

```http
201 Created
{}
```

Re-fetching the card after submit returned:

```json
{
  "Status": "SUBMITTED",
  "TimeCardVersion": 2
}
```

Verified validation failure: submitting a saved card with insufficient weekday hours returned `400 Bad Request` and `o:errorDetails` entries identifying the affected weekday entries. The CLI should surface those messages and leave the card in `SAVED` state.

Older action-style endpoints such as `/timeCards/{id}/action/submit`, `/timeCards/action/submitAction`, and `/timeCards/action/processTimeCard` were not the path used by the Redwood UI in this environment. Treat them as unverified unless future browser traffic proves otherwise.

#### 4.5 Field Value Lookup

Use `timeCardLayouts.items[].timeCardFields.items[].RestURI` and append `SearchTerm` for autocomplete lookup. Example for project:

```http
GET /timeCardFieldValues
  ?onlyData=true
  &offset=0
  &limit=25
  &finder=findByWord;SearchTerm=WORDV266,TcfId=300004857566518,UserType=WORKER,PersonId=100000000355154,StartDate=2026-05-04,EndDate=2026-05-10
```

Verified response:

```json
{
  "items": [
    {
      "Code": "300004669699898",
      "DisplayValue": "WORDV266 - RedHat Helix EU",
      "UnitOfMeasure": "HR"
    }
  ]
}
```

Task lookup depends on project and assignment bindings:

```http
finder=findByWord;SearchTerm=02,TcfId=300004857566519,UserType=WORKER,PersonId=100000000355154,StartDate=2026-05-04,EndDate=2026-05-10,BindTcfId1=300004857566486,BindTcfId2=300004857566518,BindTcf1Value=300000002560077,BindTcf2Value={PROJECT_CODE_ID}
```

### 5. Legacy/Initial Mutation Hypothesis

**Endpoint**:
```
POST /timeCards
```

**Request Body** (Create new entry):
```json
{
  "timecardId": "300005105736789",
  "lines": [
    {
      "timecardDate": "2026-05-08",
      "hours": 8.0,
      "projectCode": "WORDV266",
      "taskCode": "02",
      "timeType": "Regular",
      "location": "Work from office (employment contract)"
    }
  ]
}
```

**Request Body** (Update existing entry):
```json
{
  "timecardId": "300005105736789",
  "lines": [
    {
      "lineId": "300005105736790",
      "timecardDate": "2026-04-27",
      "hours": 9.0,
      "projectCode": "WORDV266",
      "taskCode": "02",
      "timeType": "Regular",
      "location": "Work from home"
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "timecardId": "300005105736789",
  "status": "DRAFT",
  "lines": [
    {
      "lineId": "300005105736790",
      "timecardDate": "2026-04-27",
      "hours": 9.0,
      "status": "DRAFT"
    }
  ],
  "reportedHours": 41.0
}
```

**Error Responses**:
- `400 Bad Request`: Invalid data format or business rule violation
- `403 Forbidden`: Cannot edit submitted/approved timecard
- `404 Not Found`: Timecard or entry not found

---

### 6. Get Timecard Attestations

**Endpoint**:
```
GET /timeCardAttestations
```

**Query Parameters**:
```
finder=findByPersonId;PersonId={PERSON_ID}
limit=50
```

**Response** (200 OK):
```json
{
  "items": [
    {
      "attestationId": "500001",
      "timecardId": "300005105736789",
      "personId": "100000000355154",
      "attestationStatus": "APPROVED",
      "attestationDate": "2026-05-08"
    }
  ],
  "count": 1
}
```

**Purpose**: Get attestation status for timesheets

---

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Log error details, display to user |
| 401 | Unauthorized | Token expired, prompt re-auth |
| 403 | Forbidden | Permission denied, display error |
| 404 | Not Found | Resource doesn't exist, display error |
| 429 | Too Many Requests | Implement exponential backoff, retry |
| 500 | Server Error | Retry with backoff, inform user |
| 503 | Service Unavailable | Retry with backoff, suggest checking status |

### Error Response Format

```json
{
  "errorCode": "VALIDATION_ERROR",
  "errorMessage": "Hours cannot exceed 24",
  "details": {
    "field": "hours",
    "value": 25.0,
    "constraint": "max=24"
  }
}
```

---

## Pagination

List endpoints support pagination via `limit` and `offset`:

```bash
GET /timeCards/action/findByAdvancedSearchQuery \
  -d '{"limit": 10, "offset": 0}'
```

Response includes:
```json
{
  "items": [...],
  "count": 10,
  "hasMore": true,
  "limit": 10,
  "offset": 0
}
```

---

## Rate Limiting

- Monitor response headers for `X-RateLimit-*` headers
- On 429 response, implement exponential backoff:
  - 1st retry: 1 second
  - 2nd retry: 2 seconds
  - 3rd retry: 4 seconds
  - Max: 10 retries (stop after ~17 seconds)

---

## Request Headers

All requests should include:

```
Content-Type: application/json
Accept: application/json
Cookie: [session cookies from authentication]
User-Agent: fusionctl/0.1.0
```

---

## Implementation Notes

1. **Resource Version Caching**: Cache the resource version UUID for 30 minutes to avoid discovering it on every request
2. **Session Persistence**: Reuse httpx.Client with cookies across requests
3. **Date Formats**: Oracle uses ISO 8601 (YYYY-MM-DD) in API but displays DD/MM/YY in UI
4. **Timezone**: All times are UTC/Server timezone, adjust for user's local timezone in CLI output
5. **Retries**: Implement 3-5 retries for transient failures (500, 503, timeouts)

---

## Example: Complete Workflow

```python
# 1. Get user context
GET /employmentInfo?finder=findByPersonId;PersonId={PERSON_ID}
→ Get PersonNumber, AssignmentId, LegalEntityId

# 2. List timesheets for date range
POST /timeCards/action/findByAdvancedSearchQuery
→ Get list of timecards

# 3. Get details of one timecard
GET /timeCardEntryDetails?finder=findByTimeCardId;TimeCardId={TIMECARD_ID},UserContext=WORKER
→ Get all entries for the period

# 4. Add a new entry or update an existing entry
POST /timeCards
→ Save the full desired entry set with ProcessMode=TIME_SAVE

# 5. Submit for approval
POST /timeCards
→ Submit the full current entry set with ProcessMode=TIME_SUBMIT

# 6. Check attestation
GET /timeCardAttestations?finder=findByPersonId;PersonId={PERSON_ID}
→ Verify attestation status
```

---

## Debugging Tips

1. **Enable verbose logging** in CLI to see all HTTP requests/responses
2. **Use browser DevTools** to inspect actual API calls made by the web UI
3. **Record API responses** with pytest-vcr for testing
4. **Validate session cookies** with test API call on login
5. **Check response headers** for rate-limit and server errors
