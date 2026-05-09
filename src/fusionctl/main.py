import typer

from fusionctl import __version__
from fusionctl.cli.commands import auth, timesheet
from fusionctl.cli.runtime import configure_runtime

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
    verbose: bool = typer.Option(
        False,
        "-vv",
        "--verbose",
        help="Enable diagnostic logging.",
    ),
    very_verbose: bool = typer.Option(
        False,
        "-vvv",
        "--very-verbose",
        help="Enable maximum diagnostic logging.",
    ),
    config: str | None = typer.Option(None, "--config", help="Override config file path."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Ignore cached data."),
) -> None:
    """Manage Oracle Fusion timesheets from the terminal."""
    verbosity = 3 if very_verbose else 2 if verbose else 0
    configure_runtime(verbosity=verbosity, config_path=config, no_cache=no_cache)


app.add_typer(auth.app, name="auth")
app.add_typer(timesheet.app, name="timesheet")
