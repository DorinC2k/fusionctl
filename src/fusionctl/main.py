import typer

from fusionctl import __version__
from fusionctl.cli.commands import auth

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

app = typer.Typer(
    help="Oracle Fusion Timesheet CLI",
    context_settings=CONTEXT_SETTINGS,
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"fusionctl {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output."),
    config: str | None = typer.Option(None, "--config", help="Override config file path."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Ignore cached data."),
) -> None:
    """Manage Oracle Fusion timesheets from the terminal."""
    _ = (verbose, config, no_cache)


app.add_typer(auth.app, name="auth")
