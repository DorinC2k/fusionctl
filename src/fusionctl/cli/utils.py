import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def failure(message: str) -> None:
    err_console.print(f"[red]✗[/red] {message}")


def exit_with_error(message: str, code: int = 1) -> None:
    failure(message)
    raise typer.Exit(code)
