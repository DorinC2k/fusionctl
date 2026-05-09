from __future__ import annotations

import argparse
import gzip
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
APP_DIR = DIST_DIR / "fusionctl"
BUILD_DIR = ROOT / "build" / "packages"
DOCS_DIR = ROOT / "docs"
PACKAGE_NAME = "fusionctl"
MAINTAINER = "Dorin Cobzac"
DESCRIPTION = "Oracle Fusion Timesheet CLI"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Linux .deb and .rpm packages.")
    parser.add_argument(
        "--formats",
        default="deb,rpm",
        help="Comma-separated formats to build: deb, rpm. Defaults to both.",
    )
    args = parser.parse_args()

    formats = {item.strip().lower() for item in args.formats.split(",") if item.strip()}
    unknown_formats = formats - {"deb", "rpm"}
    if unknown_formats:
        raise SystemExit(f"Unknown package format(s): {', '.join(sorted(unknown_formats))}")

    ensure_linux_build()
    version = project_version()

    if "deb" in formats:
        print(build_deb(version))
    if "rpm" in formats:
        print(build_rpm(version))


def ensure_linux_build() -> None:
    executable = APP_DIR / "fusionctl"
    if not executable.exists():
        raise SystemExit(
            "Missing dist/fusionctl/fusionctl. Run `poetry run poe bundle-onedir` on Linux first."
        )


def project_version() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(pyproject["tool"]["poetry"]["version"])


def build_deb(version: str) -> Path:
    deb_root = BUILD_DIR / "deb-root"
    prepare_package_root(deb_root)

    control_dir = deb_root / "DEBIAN"
    control_dir.mkdir(parents=True)
    installed_size = directory_size_kib(deb_root)
    (control_dir / "control").write_text(
        "\n".join(
            [
                f"Package: {PACKAGE_NAME}",
                f"Version: {version}",
                "Section: utils",
                "Priority: optional",
                f"Architecture: {deb_arch()}",
                f"Maintainer: {MAINTAINER}",
                f"Installed-Size: {installed_size}",
                f"Description: {DESCRIPTION}",
                " Local command line tool for Oracle Fusion timecards.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    output = DIST_DIR / f"{PACKAGE_NAME}_{version}_{deb_arch()}.deb"
    output.unlink(missing_ok=True)
    run(["dpkg-deb", "-Znone", "--root-owner-group", "--build", str(deb_root), str(output)])
    return output


def build_rpm(version: str) -> Path:
    rpmbuild = shutil.which("rpmbuild")
    if rpmbuild is None:
        raise SystemExit("rpmbuild is required to create RPM packages.")

    rpm_top = BUILD_DIR / "rpm"
    source_root = rpm_top / "SOURCES" / "root"
    spec_dir = rpm_top / "SPECS"
    for directory in ["BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"]:
        (rpm_top / directory).mkdir(parents=True, exist_ok=True)
    prepare_package_root(source_root)

    spec_path = spec_dir / f"{PACKAGE_NAME}.spec"
    spec_path.write_text(rpm_spec(version), encoding="utf-8")

    run(
        [
            rpmbuild,
            "-bb",
            "--define",
            f"_topdir {rpm_top}",
            "--define",
            "_binary_payload w0.gzdio",
            str(spec_path),
        ]
    )

    rpm_files = sorted((rpm_top / "RPMS").rglob(f"{PACKAGE_NAME}-{version}-*.rpm"))
    if not rpm_files:
        raise SystemExit("rpmbuild completed, but no RPM artifact was found.")

    output = DIST_DIR / rpm_files[-1].name
    output.unlink(missing_ok=True)
    shutil.copy2(rpm_files[-1], output)
    return output


def prepare_package_root(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)

    app_target = root / "opt" / PACKAGE_NAME
    shutil.copytree(APP_DIR, app_target)
    (app_target / "fusionctl").chmod(0o755)

    bin_dir = root / "usr" / "bin"
    bin_dir.mkdir(parents=True)
    os.symlink(f"/opt/{PACKAGE_NAME}/fusionctl", bin_dir / PACKAGE_NAME)

    doc_dir = root / "usr" / "share" / "doc" / PACKAGE_NAME
    doc_dir.mkdir(parents=True)
    for name in ["usage.md", "distribution.md"]:
        source = DOCS_DIR / name
        if source.exists():
            shutil.copy2(source, doc_dir / name)

    man_dir = root / "usr" / "share" / "man" / "man1"
    man_dir.mkdir(parents=True)
    with (DOCS_DIR / "fusionctl.1").open("rb") as source:
        with gzip.open(man_dir / "fusionctl.1.gz", "wb", compresslevel=9) as target:
            shutil.copyfileobj(source, target)


def rpm_spec(version: str) -> str:
    return f"""Name: {PACKAGE_NAME}
Version: {version}
Release: 1%{{?dist}}
Summary: {DESCRIPTION}
License: Proprietary
URL: https://github.com/DorinC2k/fusionctl
AutoReqProv: no

%description
Local command line tool for Oracle Fusion timecards.

%prep

%build

%install
mkdir -p %{{buildroot}}
cp -a %{{_sourcedir}}/root/* %{{buildroot}}/

%files
/opt/{PACKAGE_NAME}
/usr/bin/{PACKAGE_NAME}
%doc /usr/share/doc/{PACKAGE_NAME}/usage.md
%doc /usr/share/doc/{PACKAGE_NAME}/distribution.md
/usr/share/man/man1/{PACKAGE_NAME}.1.gz

%changelog
* Sat May 09 2026 {MAINTAINER} - {version}-1
- Package standalone fusionctl binary.
"""


def deb_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    return machine


def directory_size_kib(path: Path) -> int:
    total = sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    return max(1, total // 1024)


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
