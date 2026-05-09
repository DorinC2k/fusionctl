import asyncio

import typer

from fusionctl.cli.utils import console, exit_with_error, success
from fusionctl.config import load_settings
from fusionctl.exceptions import AuthenticationError, StorageError
from fusionctl.services.auth_service import AuthService
from fusionctl.services.browser_auth_service import (
    DEFAULT_ORACLE_TIMECARDS_URL,
    BrowserAuthService,
)
from fusionctl.storage.secrets import SecretStore

app = typer.Typer(help="Authentication commands")


def build_auth_service() -> AuthService:
    settings = load_settings()
    return AuthService(SecretStore(settings.secrets_file))


def build_browser_auth_service() -> BrowserAuthService:
    settings = load_settings()
    return BrowserAuthService(
        SecretStore(settings.secrets_file),
        profile_dir=settings.browser_profile_dir,
        oracle_base_url=settings.oracle_base_url,
    )


@app.command()
def login(
    token: str | None = typer.Option(
        None,
        "--token",
        help="Oracle Fusion session cookie header. Omit value to paste securely.",
        prompt=False,
    ),
    browser: bool = typer.Option(
        False,
        "--browser",
        help="Open a persistent local browser profile and store Oracle cookies after login.",
    ),
    headless: bool = typer.Option(
        False,
        "--headless",
        help="Use the persistent browser profile without showing a browser window.",
    ),
    url: str = typer.Option(
        DEFAULT_ORACLE_TIMECARDS_URL,
        "--url",
        help="Oracle URL to open for browser-backed login.",
    ),
) -> None:
    """Store an Oracle Fusion browser session cookie."""
    if browser:
        try:
            session = asyncio.run(
                build_browser_auth_service().login(
                    url=url,
                    headed=not headless,
                )
            )
        except (AuthenticationError, StorageError) as exc:
            exit_with_error(f"Authentication failed: {exc}", code=1)

        success("Authenticated")
        console.print("  Session token stored locally")
        console.print(f"  Token source: {session.source}")
        console.print("  Browser profile: persistent local profile")
        return

    if token is None:
        token = typer.prompt("Paste Oracle session cookie", hide_input=True)

    try:
        build_auth_service().login_with_cookie(token)
    except (AuthenticationError, StorageError) as exc:
        exit_with_error(f"Authentication failed: {exc}", code=1)

    success("Authenticated")
    console.print("  Session token stored locally")
    console.print("  Token source: eclf.fa.em2.oraclecloud.com")


@app.command()
def logout() -> None:
    """Clear the stored Oracle Fusion session."""
    try:
        removed = build_auth_service().logout()
    except StorageError as exc:
        exit_with_error(f"Logout failed: {exc}", code=1)

    if not removed:
        exit_with_error("No active session to clear", code=1)
    success("Session cleared")


@app.command()
def status() -> None:
    """Show the current authentication status."""
    try:
        is_valid, session = build_auth_service().status()
    except StorageError as exc:
        exit_with_error(f"Could not read auth status: {exc}", code=1)

    if session is None:
        exit_with_error(
            "Status: Not authenticated. Use 'fusionctl auth login --browser' to begin.", code=1
        )
    if not is_valid:
        exit_with_error(
            "Status: Session expired. Use 'fusionctl auth login --browser' to refresh.", code=2
        )

    assert session is not None
    success("Status: Authenticated")
    console.print(f"  Token source: {session.source}")
    console.print(f"  Cached since: {session.created_at.isoformat()}")
    if session.expiry is not None:
        console.print(f"  Expires: {session.expiry.isoformat()}")
    else:
        console.print("  Expires: Unknown; Oracle controls session cookie expiry")
