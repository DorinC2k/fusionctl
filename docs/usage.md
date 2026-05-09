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
The default Oracle location is `Work from office (employment contract)`.

Current week, from Monday through today:

```bash
fusionctl timesheet log-week --project WORDV266 --task 02 --dry-run
```

Current month, covering every weekly timecard that overlaps the calendar month:

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

Use one location for every planned entry:

```bash
fusionctl timesheet log-week --project WORDV266 --task 02 --location "Work from home" --dry-run
```

Plan a hybrid week with two work-from-home days and the rest from the office:

```bash
fusionctl timesheet log-week --project WORDV266 --task 02 --work-pattern hybrid --work-from-home-days 2 --dry-run
```

The hybrid pattern assigns the first working days in each week to `Work from home`. Remaining working days use `Work from office (employment contract)`.

Apply a holiday calendar for weekend public holidays that Oracle may not prefill:

```bash
fusionctl timesheet log-week --project WORDV266 --task 02 --holiday-calendar moldova --dry-run
```

When a holiday from the calendar falls on a weekend, fusionctl splits the previous working day into `7h Regular` plus `1h Public Holiday`. Holiday data is cached under `./.fusionctl/holiday-calendars` in the directory where you run the command.

Refresh the cache manually:

```bash
fusionctl timesheet refresh-holidays --holiday-calendar moldova --year 2026
```

Logging commands refresh missing or stale cache files automatically. The default staleness window is 30 days; use `--refresh-holidays` to force a refresh or `--holiday-cache-days 0` to always refresh.

For `log-month`, fusionctl plans the full Monday-Sunday timecard weeks that overlap the current calendar month. This means the first planned week can include trailing days from the previous month, and the last planned week can include spillover days from the next month.

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

Linux package artifacts are built with:

```bash
poetry run poe package-linux
```

The APT repository publisher is in `.github/workflows/publish-apt-repo.yml` and is intended for version tags such as `v1.0.0`.
