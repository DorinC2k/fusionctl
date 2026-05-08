from __future__ import annotations

from dataclasses import dataclass

from fusionctl.cli.utils import err_console


@dataclass
class RuntimeState:
    verbosity: int = 0
    config_path: str | None = None
    no_cache: bool = False

    @property
    def label(self) -> str:
        if self.verbosity <= 0:
            return "essential"
        if self.verbosity == 1:
            return "minimal"
        if self.verbosity == 2:
            return "detailed"
        return "maximum"


_state = RuntimeState()


def configure_runtime(
    *,
    verbosity: int,
    config_path: str | None,
    no_cache: bool,
) -> RuntimeState:
    global _state
    _state = RuntimeState(
        verbosity=max(0, verbosity),
        config_path=config_path,
        no_cache=no_cache,
    )
    log(f"Logging: {_state.label}", level=1)
    log(f"Config override: {_state.config_path or '<default>'}", level=2)
    log(f"Cache mode: {'disabled' if _state.no_cache else 'enabled'}", level=2)
    return _state


def runtime_state() -> RuntimeState:
    return _state


def log(message: str, *, level: int = 1) -> None:
    if _state.verbosity >= level:
        err_console.print(f"[dim]{message}[/dim]")
