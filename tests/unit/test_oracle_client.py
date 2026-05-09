from __future__ import annotations

from typing import Any

import pytest

from fusionctl.api.oracle_client import OracleClient


class RecordingOracleClient(OracleClient):
    def __init__(self) -> None:
        super().__init__("https://example.oraclecloud.com", "JSESSIONID=abc")
        self.calls: list[tuple[str, dict[str, object], str | None]] = []

    async def post(
        self,
        url: str,
        payload: dict[str, object],
        *,
        content_type: str = "application/vnd.oracle.adf.action+json",
    ) -> dict[str, object]:
        self.calls.append((url, payload, content_type))
        return {"ok": True}

    async def delete(self, url: str) -> dict[str, object]:
        self.calls.append((url, {}, None))
        return {"ok": True}


@pytest.mark.asyncio
async def test_save_timecard_entries_sets_verified_process_defaults() -> None:
    client = RecordingOracleClient()

    result = await client.save_timecard_entries(
        "https://example.oraclecloud.com/hcmRestApi/rest/rv:id/en/11.13.18.05:9/",
        {"TimeCardId": "300", "timeEntries": []},
    )

    assert result == {"ok": True}
    url, payload, content_type = client.calls[0]
    assert url == "https://example.oraclecloud.com/hcmRestApi/rest/rv:id/en/11.13.18.05:9/timeCards"
    assert content_type == "application/json"
    assert payload["ProcessMode"] == "TIME_SAVE"
    assert payload["UserContext"] == "WORKER"
    assert payload["IgnoreWarningsFlag"] is False


@pytest.mark.asyncio
async def test_create_timecard_uses_plain_json_content_type() -> None:
    client = RecordingOracleClient()

    await client.create_timecard(
        "https://example.oraclecloud.com/api",
        person_id="100",
        start_date="2026-05-11T00:00:00+00:00",
        stop_date="2026-05-17T23:59:59.999+00:00",
    )

    url, payload, content_type = client.calls[0]
    assert url == "https://example.oraclecloud.com/api/timeCards"
    assert content_type == "application/json"
    assert payload["UserContext"] == "WORKER"


@pytest.mark.asyncio
async def test_clear_timecard_entries_saves_only_preserved_rows() -> None:
    client = RecordingOracleClient()
    preserved = [{"TimeEntryId": "holiday"}]

    await client.clear_timecard_entries(
        "https://example.oraclecloud.com/api",
        {"TimeCardId": "300", "timeEntries": [{"TimeEntryId": "regular"}]},
        preserved_time_entries=preserved,
    )

    _, payload, _ = client.calls[0]
    assert payload["ProcessMode"] == "TIME_SAVE"
    assert payload["timeEntries"] == preserved


@pytest.mark.asyncio
async def test_delete_timecard_attempts_parent_timecards_resource() -> None:
    client = RecordingOracleClient()

    await client.delete_timecard("https://example.oraclecloud.com/api/", "300")

    url, _, _ = client.calls[0]
    assert url == "https://example.oraclecloud.com/api/timeCards/300"


@pytest.mark.asyncio
async def test_submit_timecard_sets_verified_submit_process_mode() -> None:
    client = RecordingOracleClient()
    payload: dict[str, Any] = {
        "TimeCardId": "300",
        "UserContext": "WORKER",
        "IgnoreWarningsFlag": True,
        "timeEntries": [],
    }

    await client.submit_timecard("https://example.oraclecloud.com/api", payload)

    _, submitted_payload, _ = client.calls[0]
    assert submitted_payload["ProcessMode"] == "TIME_SUBMIT"
    assert submitted_payload["UserContext"] == "WORKER"
    assert submitted_payload["IgnoreWarningsFlag"] is True


def test_xsrf_token_is_extracted_from_cookie_header() -> None:
    client = OracleClient(
        "https://example.oraclecloud.com",
        "JSESSIONID=abc; XSRF-TOKEN-EM2BLCV_F=token=value; bm_sv=def",
    )

    assert client._xsrf_token() == "token=value"
