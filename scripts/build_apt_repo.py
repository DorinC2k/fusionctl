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
BUILD_DIR = ROOT / "build" / "apt"
DOCS_DIR = ROOT / "docs"
PACKAGE_NAME = "fusionctl"
MAINTAINER = "Dorin Cobzac"
DESCRIPTION = "Oracle Fusion Timesheet CLI"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a GitHub Pages compatible APT repo.")
    parser.add_argument(
        "--version",
        default=project_version(),
        help="Package version. Defaults to pyproject.toml.",
    )
    parser.add_argument(
        "--release-url",
        required=True,
        help="URL of the standalone fusionctl-linux-x64.tar.gz release asset.",
    )
    parser.add_argument(
        "--sha256",
        required=True,
        help="Expected SHA256 of the standalone tar.gz release asset.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "dist" / "apt"),
        help="Directory where the apt repository should be written.",
    )
    args = parser.parse_args()

    output = Path(args.output).resolve()
    build_repo(
        output=output,
        version=args.version,
        release_url=args.release_url,
        sha256=args.sha256,
    )
    print(output)


def project_version() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(pyproject["tool"]["poetry"]["version"])


def build_repo(*, output: Path, version: str, release_url: str, sha256: str) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    package = build_bootstrap_deb(version=version, release_url=release_url, sha256=sha256)
    pool_dir = output / "pool" / "main" / "f" / PACKAGE_NAME
    pool_dir.mkdir(parents=True)
    shutil.copy2(package, pool_dir / package.name)

    packages_dir = output / "dists" / "stable" / "main" / f"binary-{deb_arch()}"
    packages_dir.mkdir(parents=True)

    packages_path = packages_dir / "Packages"
    with packages_path.open("w", encoding="utf-8") as target:
        subprocess.run(
            ["dpkg-scanpackages", "--arch", deb_arch(), "pool"],
            cwd=output,
            check=True,
            stdout=target,
        )

    with packages_path.open("rb") as source:
        with gzip.open(packages_dir / "Packages.gz", "wb", compresslevel=9) as target:
            shutil.copyfileobj(source, target)

    release_config = BUILD_DIR / "apt-ftparchive-release.conf"
    release_config.parent.mkdir(parents=True, exist_ok=True)
    release_config.write_text(
        "\n".join(
            [
                'APT::FTPArchive::Release::Origin "fusionctl";',
                'APT::FTPArchive::Release::Label "fusionctl";',
                'APT::FTPArchive::Release::Suite "stable";',
                'APT::FTPArchive::Release::Codename "stable";',
                f'APT::FTPArchive::Release::Architectures "{deb_arch()}";',
                'APT::FTPArchive::Release::Components "main";',
                f'APT::FTPArchive::Release::Description "{DESCRIPTION}";',
                "",
            ]
        ),
        encoding="utf-8",
    )

    release_tmp = BUILD_DIR / "Release"
    with release_tmp.open("w", encoding="utf-8") as target:
        subprocess.run(
            ["apt-ftparchive", "-c", str(release_config), "release", "dists/stable"],
            cwd=output,
            check=True,
            stdout=target,
        )
    shutil.move(release_tmp, output / "dists" / "stable" / "Release")


def build_bootstrap_deb(*, version: str, release_url: str, sha256: str) -> Path:
    package_root = BUILD_DIR / "bootstrap-root"
    if package_root.exists():
        shutil.rmtree(package_root)

    control_dir = package_root / "DEBIAN"
    control_dir.mkdir(parents=True)
    write_control_files(control_dir, version=version, release_url=release_url, sha256=sha256)
    write_payload_files(package_root)

    output = BUILD_DIR / f"{PACKAGE_NAME}_{version}_{deb_arch()}.deb"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    subprocess.run(
        ["dpkg-deb", "-Zgzip", "--root-owner-group", "--build", str(package_root), str(output)],
        check=True,
    )
    return output


def write_control_files(control_dir: Path, *, version: str, release_url: str, sha256: str) -> None:
    (control_dir / "control").write_text(
        "\n".join(
            [
                f"Package: {PACKAGE_NAME}",
                f"Version: {version}",
                "Section: utils",
                "Priority: optional",
                f"Architecture: {deb_arch()}",
                "Depends: ca-certificates, curl, tar",
                f"Maintainer: {MAINTAINER}",
                f"Description: {DESCRIPTION}",
                " Local command line tool for Oracle Fusion timecards.",
                " This APT package downloads the standalone release asset during install.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    postinst = control_dir / "postinst"
    postinst.write_text(postinst_script(release_url=release_url, sha256=sha256), encoding="utf-8")
    postinst.chmod(0o755)

    postrm = control_dir / "postrm"
    postrm.write_text(postrm_script(), encoding="utf-8")
    postrm.chmod(0o755)


def write_payload_files(package_root: Path) -> None:
    bin_dir = package_root / "usr" / "bin"
    bin_dir.mkdir(parents=True)
    os.symlink(f"/opt/{PACKAGE_NAME}/fusionctl", bin_dir / PACKAGE_NAME)

    doc_dir = package_root / "usr" / "share" / "doc" / PACKAGE_NAME
    doc_dir.mkdir(parents=True)
    for name in ["usage.md", "distribution.md"]:
        source = DOCS_DIR / name
        if source.exists():
            shutil.copy2(source, doc_dir / name)

    man_dir = package_root / "usr" / "share" / "man" / "man1"
    man_dir.mkdir(parents=True)
    with (DOCS_DIR / "fusionctl.1").open("rb") as source:
        with gzip.open(man_dir / "fusionctl.1.gz", "wb", compresslevel=9) as target:
            shutil.copyfileobj(source, target)


def postinst_script(*, release_url: str, sha256: str) -> str:
    return f"""#!/bin/sh
set -eu

install_dir="/opt/{PACKAGE_NAME}"
archive_url="{release_url}"
archive_sha256="{sha256}"
tmp_dir="$(mktemp -d)"

cleanup() {{
    rm -rf "$tmp_dir"
}}
trap cleanup EXIT

curl -fsSL "$archive_url" -o "$tmp_dir/{PACKAGE_NAME}-linux-x64.tar.gz"
printf '%s  %s\\n' "$archive_sha256" "$tmp_dir/{PACKAGE_NAME}-linux-x64.tar.gz" | sha256sum -c -

rm -rf "$install_dir"
mkdir -p /opt
tar -xzf "$tmp_dir/{PACKAGE_NAME}-linux-x64.tar.gz" -C /opt
chmod +x "$install_dir/{PACKAGE_NAME}"
"""


def postrm_script() -> str:
    return f"""#!/bin/sh
set -eu

if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    rm -rf "/opt/{PACKAGE_NAME}"
fi
"""


def deb_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    return machine


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
