from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from fusionctl.exceptions import AuthenticationError
from fusionctl.models.session import Session
from fusionctl.storage.secrets import SecretStore

DEFAULT_ORACLE_TIMECARDS_URL = (
    "https://eclf.fa.em2.oraclecloud.com/fscmUI/redwood/time/existing-timecards/view-summary"
)
COOKIE_DOMAINS = ("oraclecloud.com", "oracle.endava.com")
STAY_SIGNED_IN_BUTTONS = ("Yes", "Da")
SESSION_COOKIE_NAMES = ("JSESSIONID", "OAMAuthnCookie", "ORA_FUSION_PREFS")


class BrowserAuthService:
    """Capture Oracle session cookies from a persistent local browser profile."""

    def __init__(
        self,
        secret_store: SecretStore,
        *,
        profile_dir: Path,
        oracle_base_url: str,
    ) -> None:
        self.secret_store = secret_store
        self.profile_dir = profile_dir
        self.oracle_base_url = oracle_base_url.rstrip("/")

    async def login(
        self,
        *,
        url: str = DEFAULT_ORACLE_TIMECARDS_URL,
        headed: bool = True,
        timeout_seconds: int = 180,
    ) -> Session:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise AuthenticationError(
                "Browser login requires Playwright. Run 'poetry install' and "
                "'poetry run playwright install chromium'."
            ) from exc

        self.profile_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                headless=not headed,
                ignore_https_errors=True,
            )
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)
                await self._wait_for_oracle_session(page, timeout_seconds=timeout_seconds)
                cookies = await context.cookies()
            except Exception as exc:
                if _is_target_closed_error(exc):
                    raise AuthenticationError(
                        "Browser login was closed before the Oracle session was captured. "
                        "Run 'fusionctl auth login --browser' again and leave the window open "
                        "until fusionctl closes it."
                    ) from exc
                raise
            finally:
                await context.close()

        cookie_header = cookie_header_from_playwright(cookies)
        if not cookie_header:
            raise AuthenticationError(
                "Could not find Oracle cookies in the browser profile. Complete the login "
                "in the opened browser and try again."
            )

        session = Session(token=cookie_header, source="browser-profile")
        self.secret_store.save_session(session)
        return session

    async def _wait_for_oracle_session(self, page: Any, *, timeout_seconds: int) -> None:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            await self._accept_stay_signed_in_prompt(page)
            if "oraclecloud.com" in page.url:
                if await self._tokenrelay_is_available(page) or await self._session_cookie_is_available(page):
                    return
            try:
                await page.wait_for_timeout(1000)
            except Exception as exc:
                if _is_target_closed_error(exc):
                    raise AuthenticationError(
                        "Browser login was closed before the Oracle session was captured."
                    ) from exc
                raise
        raise AuthenticationError("Timed out waiting for Oracle login to finish")

    async def _accept_stay_signed_in_prompt(self, page: Any) -> None:
        for label in STAY_SIGNED_IN_BUTTONS:
            try:
                button = page.get_by_role("button", name=label, exact=True)
                if await button.count():
                    await button.first.click(timeout=1000)
                    return
            except Exception:
                continue

    async def _tokenrelay_is_available(self, page: Any) -> bool:
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        try:
            return bool(
                await page.evaluate(
                    """async () => {
                        const xsrf = document.cookie
                            .split('; ')
                            .find((row) => row.startsWith('XSRF-TOKEN'))
                            ?.split('=')
                            .slice(1)
                            .join('=');
                        const response = await fetch('/fscmRestApi/tokenrelay', {
                            credentials: 'include',
                            headers: {
                                Accept: 'application/json',
                                ...(xsrf ? { 'x-xsrf-token': xsrf } : {}),
                            },
                        });
                        return response.ok;
                    }"""
                )
            )
        except Exception:
            return False

    async def _session_cookie_is_available(self, page: Any) -> bool:
        try:
            cookies = await page.context.cookies()
        except Exception:
            return False
        return has_oracle_session_cookie(cookies)


def _is_target_closed_error(exc: Exception) -> bool:
    return "Target page, context or browser has been closed" in str(exc)


def has_oracle_session_cookie(cookies: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        any(domain in str(cookie.get("domain", "")) for domain in COOKIE_DOMAINS)
        and str(cookie.get("name", "")).startswith(SESSION_COOKIE_NAMES)
        and bool(cookie.get("value"))
        for cookie in cookies
    )


def cookie_header_from_playwright(cookies: Sequence[Mapping[str, Any]]) -> str:
    oracle_cookies = [
        cookie
        for cookie in cookies
        if any(domain in str(cookie.get("domain", "")) for domain in COOKIE_DOMAINS)
        and cookie.get("name")
        and cookie.get("value")
    ]
    oracle_cookies.sort(key=lambda cookie: (str(cookie.get("domain", "")), str(cookie["name"])))
    return "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in oracle_cookies)
