# fusionctl Usage Guide

`fusionctl` is a local CLI for Oracle Fusion timecards. It is designed to run without a database and to keep authentication state on the user's machine.

## Quick Start

Check the binary:

```bash
fusionctl --version
```

Authenticate with Oracle:

```bash
fusionctl auth login --browser
fusionctl auth status
```

Preview this week's entries:

```bash
fusionctl timesheet log-week --project WORDV266 --task 02 --dry-run
```

## Authentication Commands

Open a visible browser and complete Microsoft Authenticator if prompted:

```bash
fusionctl auth login --browser
```

Reuse the existing browser profile without showing the browser:

```bash
fusionctl auth login --browser --headless
```

Check whether a local session is present:

```bash
fusionctl auth status
```

Remove the stored local session:

```bash
fusionctl auth logout
```

## Timesheet Convenience Commands

The convenience commands expand a period into one planned entry per working day. Weekends are skipped.

Current week, from Monday through today:

```bash
fusionctl timesheet log-week --project WORDV266 --task 02 --dry-run
```

Current month, from the first day of the month through today:

```bash
fusionctl timesheet log-month --project WORDV266 --task 02 --dry-run
```

Previous calendar month:

```bash
fusionctl timesheet log-last-month --project WORDV266 --task 02 --dry-run
```

Change daily hours:

```bash
fusionctl timesheet log-week --hours 6 --project WORDV266 --task 02 --dry-run
```

Add notes to every planned entry:

```bash
fusionctl timesheet log-month --project WORDV266 --task 02 --notes "Regular project work" --dry-run
```

`--dry-run` is the current default. `--execute` exists as the future write switch and currently fails clearly until the Oracle batch-write integration is wired into the CLI command path.

## Verbosity

Default output shows only essentials:

```bash
fusionctl auth status
```

Diagnostic logging:

```bash
fusionctl -vv auth status
```

Maximum logging:

```bash
fusionctl -vvv --no-cache auth status
```

`-v` is reserved for version output:

```bash
fusionctl -v
```

## Local Files

Runtime state lives under `~/.fusion-cli` by default:

- `browser-profile/`: persistent browser profile for Oracle/Azure SSO reuse
- `session.json`: fallback local session file if OS keyring storage is unavailable
- `cache/`: local cache directory for read workflows

Secrets should stay in `.env` or the local OS keyring/session store. `.env` is ignored by git.

## Builds

Build for the current OS:

```bash
poetry run poe bundle
```

Build an inspectable directory:

```bash
poetry run poe bundle-onedir
```

Linux and Windows binaries must be built on matching OS runners. The GitHub Actions workflow in `.github/workflows/build-binaries.yml` builds both standalone archives.
