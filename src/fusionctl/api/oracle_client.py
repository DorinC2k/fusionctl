from __future__ import annotations

from typing import Any

import httpx

from fusionctl.exceptions import AuthenticationError, OracleApiError


class OracleClient:
    """Thin HTTP client for Oracle Fusion HCM REST calls."""

    def __init__(self, base_url: str, cookie_header: str, timeout: float = 30.0) -> None:
        if not cookie_header.strip():
            raise AuthenticationError("Missing Oracle session cookie")
        self.base_url = base_url.rstrip("/")
        self.cookie_header = cookie_header
        self.timeout = timeout
        self._bearer_token: str | None = None

    async def get(self, url: str, params: dict[str, str] | None = None) -> dict[str, object]:
        async with self._client() as client:
            response = await client.get(url, params=params)
        return self._decode(response)

    async def post(
        self,
        url: str,
        payload: dict[str, object],
        *,
        content_type: str = "application/vnd.oracle.adf.action+json",
    ) -> dict[str, object]:
        async with self._client(content_type=content_type) as client:
            response = await client.post(url, json=payload)
        return self._decode(response)

    async def delete(self, url: str) -> dict[str, object]:
        async with self._client() as client:
            response = await client.delete(url)
        return self._decode(response)

    async def create_timecard(
        self,
        api_root: str,
        *,
        person_id: str,
        start_date: str,
        stop_date: str,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "TimeCardId": 0,
            "TimeCardVersion": 0,
            "PersonId": person_id,
            "StartDate": start_date,
            "StopDate": stop_date,
            "UserContext": "WORKER",
        }
        return await self.post(
            f"{api_root.rstrip('/')}/timeCards",
            payload,
            content_type="application/json",
        )

    async def save_timecard_entries(
        self,
        api_root: str,
        payload: dict[str, Any],
    ) -> dict[str, object]:
        """Save card entries using Oracle Redwood's verified parent-save workflow."""
        return await self._process_timecard(api_root, payload, process_mode="TIME_SAVE")

    async def clear_timecard_entries(
        self,
        api_root: str,
        payload: dict[str, Any],
        *,
        preserved_time_entries: list[dict[str, Any]],
    ) -> dict[str, object]:
        """Clear user-entered rows by saving only the entries Oracle must preserve."""
        clear_payload: dict[str, Any] = {
            **payload,
            "timeEntries": preserved_time_entries,
        }
        return await self._process_timecard(api_root, clear_payload, process_mode="TIME_SAVE")

    async def delete_timecard(
        self,
        api_root: str,
        timecard_id: str,
    ) -> dict[str, object]:
        """Attempt parent-resource deletion; live Oracle may return 404."""
        return await self.delete(f"{api_root.rstrip('/')}/timeCards/{timecard_id}")

    async def submit_timecard(
        self,
        api_root: str,
        payload: dict[str, Any],
    ) -> dict[str, object]:
        """Submit a card using Oracle Redwood's verified parent-submit workflow."""
        return await self._process_timecard(api_root, payload, process_mode="TIME_SUBMIT")

    async def refresh_bearer_token(self) -> str:
        headers = {
            "Accept": "application/json",
            "Cookie": self.cookie_header,
            "User-Agent": "fusionctl/1.1.2",
        }
        if xsrf_token := self._xsrf_token():
            headers["x-xsrf-token"] = xsrf_token
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=headers,
        ) as client:
            response = await client.get(f"{self.base_url}/fscmRestApi/tokenrelay")
        data = self._decode(response)
        token = data.get("access_token")
        if not isinstance(token, str) or not token:
            raise AuthenticationError("Oracle tokenrelay did not return a bearer token")
        self._bearer_token = token
        return token

    def _client(self, *, content_type: str = "application/vnd.oracle.adf.action+json") -> httpx.AsyncClient:
        headers = {
            "Accept": "application/json",
            "Content-Type": content_type,
            "Cookie": self.cookie_header,
            "User-Agent": "fusionctl/1.1.2",
        }
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        if xsrf_token := self._xsrf_token():
            headers["x-xsrf-token"] = xsrf_token
        return httpx.AsyncClient(
            timeout=self.timeout,
            headers=headers,
        )

    def _xsrf_token(self) -> str | None:
        for cookie in self.cookie_header.split(";"):
            name, separator, value = cookie.strip().partition("=")
            if separator and name.startswith("XSRF-TOKEN"):
                return value
        return None

    async def _process_timecard(
        self,
        api_root: str,
        payload: dict[str, Any],
        *,
        process_mode: str,
    ) -> dict[str, object]:
        process_payload: dict[str, Any] = {
            **payload,
            "ProcessMode": process_mode,
            "UserContext": payload.get("UserContext", "WORKER"),
            "IgnoreWarningsFlag": payload.get("IgnoreWarningsFlag", False),
        }
        return await self.post(
            f"{api_root.rstrip('/')}/timeCards",
            process_payload,
            content_type="application/json",
        )

    def _decode(self, response: httpx.Response) -> dict[str, object]:
        if response.status_code in {401, 403}:
            raise AuthenticationError("Oracle session expired or is not authorized")
        if response.is_error:
            raise OracleApiError(
                f"Oracle API error: {response.status_code} {response.text}",
                status_code=response.status_code,
            )
        data = response.json()
        if not isinstance(data, dict):
            raise OracleApiError("Oracle API returned an unexpected response shape")
        return data
