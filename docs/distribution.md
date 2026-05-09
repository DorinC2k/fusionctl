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

The Linux job also builds native packages:

- Debian/Ubuntu: `fusionctl_<version>_amd64.deb`
- RPM-based distributions: `fusionctl-<version>-1.x86_64.rpm`

Those packages install the PyInstaller directory under `/opt/fusionctl` and expose
`/usr/bin/fusionctl` on the system `PATH`.

## Linux Packages

Build a Linux onedir artifact first:

```bash
poetry run poe bundle-onedir
```

Then build both Linux package formats:

```bash
poetry run poe package-linux
```

The package task writes artifacts to `dist/`. It requires:

- `dpkg-deb` for `.deb`
- `rpmbuild` for `.rpm`

On Ubuntu, install RPM tooling with:

```bash
sudo apt-get install rpm
```

Install the Debian package locally with:

```bash
sudo apt install ./dist/fusionctl_1.1.5_amd64.deb
fusionctl --version
```

Install the RPM package on Fedora/RHEL-compatible systems with:

```bash
sudo dnf install ./dist/fusionctl-1.1.5-1.x86_64.rpm
fusionctl --version
```

## GitHub-Hosted APT Repository

Yes, this project can also host an APT repository in GitHub. The workflow at
`.github/workflows/publish-apt-repo.yml` publishes a static APT repository to
GitHub Pages.

The standalone Linux bundle is large because it includes the Playwright browser
runtime. GitHub Pages should not be used to store that large archive directly.
Instead, the APT repository contains a small `fusionctl` bootstrap package. With
the recommended signing secrets configured, that package is delivered from a
signed APT repository. During install, it downloads
`fusionctl-linux-x64.tar.gz` from GitHub Releases during install, verifies its
SHA256 checksum, and extracts it to `/opt/fusionctl`.

The publishing flow is:

1. Keep source code and build workflows on `main`.
2. Build the Linux standalone archive.
3. Upload `fusionctl-linux-x64.tar.gz` and its `.sha256` file to a GitHub Release.
4. Build the APT repository under `public/apt`.
5. Publish the static repository with GitHub Pages.

The workflow runs automatically for version tags such as:

```bash
git tag v1.1.5
git push origin v1.1.5
```

It can also be run manually from GitHub Actions with the `Publish APT repository`
workflow.

Enable GitHub Pages for the repository and set the source to GitHub Actions.

### Signed APT Repo

Recommended: add these GitHub Actions secrets before publishing:

- `APT_GPG_PRIVATE_KEY`: armored private GPG key used to sign the APT repository
- `APT_GPG_PASSPHRASE`: passphrase for that private key, if it has one

With signing enabled, users install from GitHub Pages with:

```bash
curl -fsSL https://dorinc2k.github.io/fusionctl/apt/fusionctl.gpg \
  | sudo gpg --dearmor -o /usr/share/keyrings/fusionctl.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/fusionctl.gpg] https://dorinc2k.github.io/fusionctl/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/fusionctl.list

sudo apt update
sudo apt install fusionctl
```

### Unsigned Test Repo

If the signing secrets are not configured, the workflow still publishes an
unsigned repository for testing. Users must explicitly mark it trusted:

```bash
echo "deb [arch=amd64 trusted=yes] https://dorinc2k.github.io/fusionctl/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/fusionctl.list

sudo apt update
sudo apt install fusionctl
```

Then normal upgrades work through APT:

```bash
sudo apt update
sudo apt upgrade fusionctl
```

Do not commit generated repository metadata or package files to `main`; publish
them from release automation.

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
