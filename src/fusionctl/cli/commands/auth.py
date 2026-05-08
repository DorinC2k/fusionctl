import typer

from fusionctl.cli.utils import console, exit_with_error, success
from fusionctl.config import load_settings
from fusionctl.exceptions import AuthenticationError, StorageError
from fusionctl.services.auth_service import AuthService
from fusionctl.storage.secrets import SecretStore

app = typer.Typer(help="Authentication commands")


def build_auth_service() -> AuthService:
    settings = load_settings()
    return AuthService(SecretStore(settings.secrets_file))


@app.command()
def login(
    token: str | None = typer.Option(
        None,
        "--token",
        help="Oracle Fusion session cookie header. Omit value to paste securely.",
        prompt=False,
    ),
) -> None:
    """Store an Oracle Fusion browser session cookie."""
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
        exit_with_error("Status: Not authenticated. Use 'fusion auth login --token' to begin.", code=1)
    if not is_valid:
        exit_with_error("Status: Session expired. Use 'fusion auth login --token' to refresh.", code=2)

    assert session is not None
    success("Status: Authenticated")
    console.print(f"  Cached since: {session.created_at.isoformat()}")
    if session.expiry is not None:
        console.print(f"  Expires: {session.expiry.isoformat()}")
    else:
        console.print("  Expires: Unknown; Oracle controls session cookie expiry")
