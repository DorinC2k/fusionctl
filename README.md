# fusionctl

Oracle Fusion Timesheet CLI for local timesheet viewing, logging, caching, and export.

## Install

For development:

```bash
poetry install --with dev
poetry run fusion --version
```

For regular users, download the standalone archive for your OS, extract it, and run:

```bash
fusionctl --version
```

The standalone binary includes Python and project dependencies. No Python install is needed on the user's machine.

## Authentication

Oracle Fusion at `eclf.fa.em2.oraclecloud.com` uses Microsoft Azure AD SAML2 SSO with 2FA. Browser-backed login stores only a local Oracle session for reuse:

```bash
fusionctl auth login --browser
fusionctl auth status
```

For a headless refresh using the existing browser profile:

```bash
fusionctl auth login --browser --headless
```

For development through Poetry:

```bash
poetry run fusion auth login --browser
poetry run fusion auth status
```

The first login can still require Microsoft Authenticator. Reusing the local browser profile avoids repeated 2FA only while Azure/Oracle keep the SSO session valid.

## Common Commands

Preview logging 8h for each working day in the current week:

```bash
fusionctl timesheet log-week --project WORDV266 --task 02 --dry-run
```

Preview the current month up to today:

```bash
fusionctl timesheet log-month --project WORDV266 --task 02 --dry-run
```

Preview the previous calendar month:

```bash
fusionctl timesheet log-last-month --project WORDV266 --task 02 --dry-run
```

Use different daily hours or notes:

```bash
fusionctl timesheet log-week --hours 7.5 --project WORDV266 --task 02 --notes "Delivery work"
```

Current convenience commands expand weekdays and skip weekends. They dry-run by default; `--execute` is reserved for the Oracle batch-write integration.

## Documentation

- [Usage guide](docs/usage.md)
- [Man-style reference](docs/fusionctl.1)
- [Standalone distribution](docs/distribution.md)

## Development

```bash
poetry run poe test
poetry run poe lint
poetry run poe typecheck
```

## Standalone Builds

Build a standalone executable for the current OS:

```bash
poetry run poe bundle
```

The executable is written to `dist/`. Build Linux and Windows artifacts on their matching OS runners. See [Standalone Distribution](docs/distribution.md).

GitHub Actions builds both Linux and Windows standalone archives on every pull request and push to `main`.
