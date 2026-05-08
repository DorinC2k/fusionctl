from __future__ import annotations

from typing import Any

import pytest

from fusionctl.api.oracle_client import OracleClient


class RecordingOracleClient(OracleClient):
    def __init__(self) -> None:
        super().__init__("https://example.oraclecloud.com", "JSESSIONID=abc")
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def post(self, url: str, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append((url, payload))
        return {"ok": True}


@pytest.mark.asyncio
async def test_save_timecard_entries_sets_verified_process_defaults() -> None:
    client = RecordingOracleClient()

    result = await client.save_timecard_entries(
        "https://example.oraclecloud.com/hcmRestApi/rest/rv:id/en/11.13.18.05:9/",
        {"TimeCardId": "300", "timeEntries": []},
    )

    assert result == {"ok": True}
    url, payload = client.calls[0]
    assert url == "https://example.oraclecloud.com/hcmRestApi/rest/rv:id/en/11.13.18.05:9/timeCards"
    assert payload["ProcessMode"] == "TIME_SAVE"
    assert payload["UserContext"] == "WORKER"
    assert payload["IgnoreWarningsFlag"] is False


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

    _, submitted_payload = client.calls[0]
    assert submitted_payload["ProcessMode"] == "TIME_SUBMIT"
    assert submitted_payload["UserContext"] == "WORKER"
    assert submitted_payload["IgnoreWarningsFlag"] is True


def test_xsrf_token_is_extracted_from_cookie_header() -> None:
    client = OracleClient(
        "https://example.oraclecloud.com",
        "JSESSIONID=abc; XSRF-TOKEN-EM2BLCV_F=token=value; bm_sv=def",
    )

    assert client._xsrf_token() == "token=value"
