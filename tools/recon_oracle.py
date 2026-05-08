from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import Page, Request, Response, async_playwright

FOCUSED_URL = "https://eclf.fa.em2.oraclecloud.com/fscmUI/redwood/time/existing-timecards/view-summary"
DEFAULT_USERNAME = "dorin.cobzac@endava.com"
OUTPUT_DIR = Path(".fusion-recon")

SECRET_HEADER_NAMES = {"authorization", "cookie", "set-cookie", "x-csrf-token", "x-oracle-apmcs-request-id"}
INTERESTING_HOSTS = ("eclf.fa.em2.oraclecloud.com", "oracle.endava.com")
INTERESTING_PATHS = ("/hcmRestApi/", "/fscmRestApi/", "/fscmUI/", "/resources/", "/describe.openapi")


def redact(value: str) -> str:
    value = re.sub(r"(?i)(JSESSIONID|bm_sv|ORA_[^=;]+|OAMAuthnCookie)=[^;\\s]+", r"\1=<redacted>", value)
    value = re.sub(r"(?i)Bearer\\s+[-._~+/A-Za-z0-9=]+", "Bearer <redacted>", value)
    return value


def clean_headers(headers: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SECRET_HEADER_NAMES:
            cleaned[key] = "<redacted>"
        else:
            cleaned[key] = redact(value)
    return cleaned


def maybe_json(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return redact(text[:4000])


def redact_body(url: str, body: Any) -> Any:
    if isinstance(body, dict):
        return {
            key: "<redacted>" if key.lower() in {"access_token", "id_token", "refresh_token"} else redact_body(url, value)
            for key, value in body.items()
        }
    if isinstance(body, list):
        return [redact_body(url, item) for item in body]
    if isinstance(body, str):
        return redact(body)
    return body


def is_interesting(url: str) -> bool:
    return any(host in url for host in INTERESTING_HOSTS) and any(path in url for path in INTERESTING_PATHS)


async def fill_if_visible(page: Page, selector: str, value: str) -> bool:
    locator = page.locator(selector).first
    try:
        await locator.wait_for(state="visible", timeout=5000)
        await locator.fill(value)
        return True
    except Exception:
        return False


async def click_if_visible(page: Page, selector: str, timeout: int = 5000) -> bool:
    locator = page.locator(selector).first
    try:
        await locator.wait_for(state="visible", timeout=timeout)
        await locator.click()
        return True
    except Exception:
        return False


async def microsoft_login(page: Page, username: str, password: str) -> None:
    if await fill_if_visible(page, "input[type='email'], input[name='loginfmt']", username):
        await click_if_visible(page, "input[type='submit'], button[type='submit']")

    await click_if_visible(page, "text='Work or school account'", timeout=8000)

    if await fill_if_visible(page, "input[type='password'], input[name='passwd']", password):
        await click_if_visible(page, "input[type='submit'], button[type='submit']")

    await click_if_visible(page, "text='Work or school account'", timeout=3000)

    if await fill_if_visible(page, "input[type='password'], input[name='passwd']", password):
        await click_if_visible(page, "input[type='submit'], button[type='submit']")

    await click_if_visible(page, "input[id='idBtn_Back'], button:has-text('No')", timeout=3000)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Capture redacted Oracle Fusion network traffic.")
    parser.add_argument("--url", default=FOCUSED_URL)
    parser.add_argument("--username", default=os.getenv("FUSION_ORACLE_USERNAME", DEFAULT_USERNAME))
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--pause", action="store_true", help="Pause for manual UI exploration after login.")
    args = parser.parse_args()

    password = os.getenv("FUSION_ORACLE_PASSWORD") or getpass.getpass("Oracle/Microsoft password: ")
    events: list[dict[str, Any]] = []
    OUTPUT_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.headed)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        async def on_request(request: Request) -> None:
            if not is_interesting(request.url):
                return
            events.append(
                {
                    "kind": "request",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "method": request.method,
                    "url": request.url,
                    "headers": clean_headers(await request.all_headers()),
                    "post_data": maybe_json(request.post_data),
                }
            )

        async def on_response(response: Response) -> None:
            if not is_interesting(response.url):
                return
            body: Any = None
            content_type = response.headers.get("content-type", "")
            if "json" in content_type or "openapi" in response.url:
                try:
                    body = redact_body(response.url, maybe_json(await response.text()))
                except Exception:
                    body = "<unavailable>"
            events.append(
                {
                    "kind": "response",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "status": response.status,
                    "url": response.url,
                    "headers": clean_headers(response.headers),
                    "body": body,
                }
            )

        page.on("request", on_request)
        page.on("response", on_response)

        await page.goto(args.url, wait_until="domcontentloaded", timeout=90000)
        await microsoft_login(page, args.username, password)

        wait_screenshot = OUTPUT_DIR / "login-wait.png"
        await page.screenshot(path=str(wait_screenshot), full_page=True)
        print(f"If Microsoft Authenticator prompts you, approve it now. Screenshot: {wait_screenshot}")
        try:
            await page.wait_for_url("**eclf.fa.em2.oraclecloud.com**", timeout=120000)
        except Exception:
            pass

        if "login.microsoftonline.com" in page.url:
            await click_if_visible(page, "input[id='idBtn_Back'], button:has-text('No')", timeout=5000)
            try:
                await page.wait_for_url("**eclf.fa.em2.oraclecloud.com**", timeout=60000)
            except Exception:
                pass

        post_wait_screenshot = OUTPUT_DIR / "login-post-wait.png"
        await page.screenshot(path=str(post_wait_screenshot), full_page=True)
        print(f"Post-wait screenshot: {post_wait_screenshot}")

        await page.wait_for_load_state("networkidle", timeout=60000)
        print(f"Current URL: {page.url}")

        metadata_urls = [
            f"{page.url.split('/fscmUI')[0]}/hcmRestApi/rest/describe.openapi?metadataMode=minimal&resources=timeCards,timeChangeAudits,timeCardAttestations",
            f"{page.url.split('/fscmUI')[0]}/hcmRestApi/rest/describe.openapi?partialDescriptionForCatalogOpenAPI=timeCards",
        ]
        for metadata_url in metadata_urls:
            try:
                await page.evaluate(
                    """async (url) => {
                        const response = await fetch(url, { credentials: 'include', headers: { Accept: 'application/json' } });
                        return await response.text();
                    }""",
                    metadata_url,
                )
            except Exception as exc:
                print(f"Metadata fetch failed for {metadata_url}: {exc}")

        if args.pause:
            print("Manual exploration pause. Press Enter here when done.")
            await asyncio.to_thread(input)

        output_path = OUTPUT_DIR / f"oracle-network-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        output_path.write_text(json.dumps(events, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote redacted capture: {output_path}")
        await context.storage_state(path=str(OUTPUT_DIR / "storage-state.redacted-risk.json"))
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
