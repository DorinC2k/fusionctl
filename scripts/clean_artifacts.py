from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
PATHS_TO_REMOVE = [
    ROOT / "dist",
    ROOT / "build" / "pyinstaller",
    ROOT / "build" / "packages",
    ROOT / "build" / "apt",
    ROOT / ".pytest_cache",
    ROOT / ".mypy_cache",
    ROOT / ".ruff_cache",
]


def main() -> None:
    for path in PATHS_TO_REMOVE:
        remove(path)
    for path in iter_project_files("__pycache__"):
        remove(path)
    for path in iter_project_files("*.pyc"):
        remove(path)


def iter_project_files(pattern: str) -> list[Path]:
    return [
        path
        for path in ROOT.rglob(pattern)
        if not any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts)
    ]


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
        print(f"removed {path.relative_to(ROOT)}")
    elif path.exists():
        path.unlink()
        print(f"removed {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
