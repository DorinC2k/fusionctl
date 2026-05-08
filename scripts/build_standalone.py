from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "packaging" / "fusion_entry.py"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "pyinstaller"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a standalone fusionctl executable.")
    parser.add_argument(
        "--name",
        default=default_binary_name(),
        help="Output executable name. Defaults to fusionctl/fusionctl.exe.",
    )
    parser.add_argument(
        "--skip-browser-install",
        action="store_true",
        help="Skip Playwright Chromium installation before packaging.",
    )
    parser.add_argument(
        "--onedir",
        action="store_true",
        help="Build a dist directory instead of a single executable.",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = "0"

    if not args.skip_browser_install:
        run([sys.executable, "-m", "playwright", "install", "chromium"], env=env)

    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        args.name,
        "--clean",
        "--noconfirm",
        "--console",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(BUILD_DIR),
    ]
    if args.onedir:
        pyinstaller_args.append("--onedir")
    else:
        pyinstaller_args.append("--onefile")
    pyinstaller_args.append(str(ENTRYPOINT))

    run(pyinstaller_args, env=env)


def default_binary_name() -> str:
    if platform.system().lower().startswith("win"):
        return "fusionctl.exe"
    return "fusionctl"


def run(command: list[str], *, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
