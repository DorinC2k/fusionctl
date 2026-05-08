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
```

For CLI implementation, the practical auth flow is:

1. Store browser cookies from the SSO session.
2. Call `/fscmRestApi/tokenrelay` with those cookies.
3. Use the returned bearer token for HCM REST API calls until it expires.
4. Refresh by calling tokenrelay again; if tokenrelay returns 401, ask the user to re-authenticate.
GET /hcmRestApi/rest/rv:{VERSION}/en/{API_VERSION}/timeCards \
  -H "Cookie: bm_sv={VALUE}; JSESSIONID={VALUE}"
```

### Session Expiry

- Tokens expire based on server-side session timeout
- CLI should catch 401/403 responses and prompt for re-authentication
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

---

### 4. Create or Update Timecard Entries (Discovered, Not Mutated)

Oracle exposes create/update through the `timeCards` resource and child collections. These were discovered from OpenAPI metadata, but no real create/update call was executed during reconnaissance.

**Create top-level timecard**:

```http
POST /timeCards
Content-Type: application/json
```

Top-level writable fields include:

```json
{
  "PersonId": "100000000355154",
  "StartDate": "2026-05-04T00:00:00+00:00",
  "StopDate": "2026-05-10T23:59:59.999+00:00",
  "TimeCardId": "optional if updating existing card",
  "TimeCardVersion": 1,
  "Status": "SAVED",
  "ProcessMode": "SAVE",
  "Source": "ORA_HWM_TIME_ENTRY",
  "UserContext": "WORKER",
  "timeEntries": []
}
```

**Create child time entry**:

```http
POST /timeCards/{timeCards_Id}/child/timeEntries
```

Writable fields:

```json
{
  "TimeEntryId": "optional when creating",
  "TimeEntryVersion": 1,
  "TimeCardId": "300005105736789",
  "UnitOfMeasure": "HR",
  "StartTime": null,
  "StopTime": null,
  "Measure": "8",
  "PersonId": "100000000355154",
  "Comments": null,
  "GroupingSequence": 1,
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
    }
  ]
}
```

**Update child time entry**:

```http
PATCH /timeCards/{timeCards_Id}/child/timeEntries/{timeCards_timeEntries_Id}
```

The patch request accepts the same writable time entry fields. Include `TimeEntryVersion` from the latest detail response to avoid stale writes.

**Submit or process card**:

```http
POST /timeCards/action/processTimeCard
POST /timeCards/action/submitAction
POST /timeCards/action/validateTimeCards
POST /timeCards/action/computeTimeTotals
```

Use metadata from `/describe.openapi?metadataMode=minimal&resources=timeCards` to build action payloads. Treat these as high-risk until tested against a draft/sandbox card.

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

### 5. Submit Timecard for Approval

**Endpoint**:
```
POST /timeCards/{TIMECARD_ID}/action/submit
```

**Request Body**:
```json
{}
```

**Response** (200 OK):
```json
{
  "timecardId": "300005105736789",
  "status": "SUBMITTED",
  "message": "Timecard submitted successfully"
}
```

**Purpose**: Change timecard status from DRAFT to SUBMITTED

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
GET /timeCards/{TIMECARD_ID}
→ Get all entries for the period

# 4. Add a new entry
POST /timeCards
→ Create new line item

# 5. Submit for approval
POST /timeCards/{TIMECARD_ID}/action/submit
→ Change status to SUBMITTED

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
