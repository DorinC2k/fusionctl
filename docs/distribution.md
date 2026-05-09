# Standalone Distribution

`fusionctl` can be shipped as a standalone console executable so users do not need to install Python, Poetry, Playwright, or project dependencies.

## Build Targets

Build on the same OS family you want to ship:

- Linux builds produce a Linux executable.
- Windows builds produce a Windows `.exe`.

PyInstaller does not provide general cross-compilation, so release automation should run one build job on Linux and one on Windows.

## Build Command

From a development checkout:

```bash
poetry install --with dev
poetry run poe clean
poetry run poe bundle
```

The build task:

1. Installs Playwright Chromium into the Python package context with `PLAYWRIGHT_BROWSERS_PATH=0`.
2. Runs PyInstaller against `packaging/fusion_entry.py`.
3. Writes the executable to `dist/`.

For a directory-style build that is easier to inspect:

```bash
poetry run poe bundle-onedir
```

Both bundle tasks run `poe clean` first, removing `dist/`, PyInstaller work files, Python bytecode caches, and test/type/lint caches before packaging.

## GitHub Actions

The workflow at `.github/workflows/build-binaries.yml` builds standalone archives for:

- `fusionctl-linux-x64` on `ubuntu-latest`
- `fusionctl-windows-x64` on `windows-latest`

Each job installs dependencies, runs tests, lint, and typecheck, builds with:

```bash
poetry run python scripts/build_standalone.py --onedir --name fusionctl
```

Then it smoke-tests `fusionctl --version` and uploads an archive:

- Linux: `fusionctl-linux-x64.tar.gz`
- Windows: `fusionctl-windows-x64.zip`

## User Install

Users only need the built artifact:

- Linux: `fusionctl`
- Windows: `fusionctl.exe`

They can place it anywhere on `PATH` or run it directly from the extracted release folder.

## Browser Auth

Browser-backed auth uses the bundled Playwright runtime and Chromium. The local browser profile remains outside the executable in the user's app directory:

- Linux/macOS default: `~/.fusion-cli/browser-profile`
- Windows default: `%USERPROFILE%\.fusion-cli\browser-profile`

The first browser login can still require Microsoft 2FA. Reusing the local browser profile avoids repeated 2FA only while Oracle/Azure keep the SSO session valid.
