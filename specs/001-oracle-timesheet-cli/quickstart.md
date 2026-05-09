# Quickstart: Oracle Fusion Timesheet CLI

**Phase**: 1 (Design)  
**Status**: Developer setup guide

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Authentication Setup](#authentication-setup)
4. [First Commands](#first-commands)
5. [Development Workflow](#development-workflow)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Python**: 3.10 or later (check: `python --version`)
- **pip**: Package installer (comes with Python)
- **OS**: Linux, macOS, or Windows with WSL2
- **Network**: Stable internet connection to reach `eclf.fa.em2.oraclecloud.com`

### Oracle Fusion Cloud Access

- Valid Oracle Fusion Cloud account with timesheet access
- Username and password (or OAuth2 credentials if available)
- ECLF endpoint: `https://eclf.fa.em2.oraclecloud.com`

### Development Dependencies (optional)

If you plan to **develop** (not just use) the CLI:

- **Git**: For version control
- **Poetry**: Python dependency manager (install: `curl -sSL https://install.python-poetry.org | python3`)

---

## Installation

### Option 1: Install from PyPI (User)

Once published, install with:

```bash
pip install fusionctl
```

Then verify:

```bash
fusion --version
```

---

### Option 2: Install from Source (Developer)

Clone the repository:

```bash
git clone https://github.com/yourusername/fusionctl.git
cd fusionctl
```

Install Poetry (if not already installed):

```bash
curl -sSL https://install.python-poetry.org | python3
export PATH="$HOME/.local/bin:$PATH"
```

Install dependencies:

```bash
poetry install
```

Activate the virtual environment:

```bash
poetry shell
```

Verify installation:

```bash
fusion --version
# or
poetry run fusion --version
```

---

## Authentication Setup

### First Login

Authenticate with Oracle Fusion Cloud through a persistent local browser profile:

```bash
fusion auth login --browser
```

The first run opens Chromium and may require Microsoft 2FA. After login, `fusionctl` stores Oracle cookies in the local secret store and keeps the browser profile under the app directory so future refreshes can reuse the SSO session:

```bash
fusion auth login --browser --headless
```

Use the manual cookie path only if browser-backed login is unavailable:

```bash
fusion auth login --token
```

On success, the CLI never prints the cookie value:

```
✓ Authenticated as: your-username@endava.com
  Session token stored securely in OS keychain
```

Your session token is stored securely using the OS keychain:
- **macOS**: Keychain.app
- **Linux**: `pass` or `secretservice` (via `keyring` library)
- **Windows**: Windows Credential Manager

The browser profile is local-only and ignored by git. It can avoid repeated 2FA prompts while Azure/Oracle keep the SSO session alive, but it cannot bypass a server-side MFA challenge after the session expires or corporate policy requires re-verification.

### Check Authentication Status

```bash
fusion auth status
```

Output (if authenticated):

```
✓ Status: Authenticated
  Username: your-username@endava.com
  Expires: 2026-05-15 10:00:00 UTC
  Cached since: 2026-05-08 10:00:00 UTC
```

### Logout

```bash
fusion auth logout
```

---

## First Commands

### List Timesheets

```bash
fusion timesheet list
```

Output:

```
ID              Period          Status      Total Entries  Total Hours
─────────────────────────────────────────────────────────────────────
ts_20260505    2026-05-05 to    submitted   5              40.0
               2026-05-09
```

### View a Specific Timesheet

```bash
fusion timesheet view ts_20260505
```

Output:

```
Timesheet: ts_20260505
Period: 2026-05-05 to 2026-05-09 | Status: submitted | Total Hours: 40.0

Date        Project     Task         Hours  Notes              Status
────────────────────────────────────────────────────────────────────
2026-05-08  PROJ001     TASK1        8.0    Regular work       submitted
2026-05-07  PROJ001     TASK1        8.0    Regular work       submitted
```

### Log Hours (Interactive)

```bash
fusion timesheet log --interactive
```

Follow the prompts:

```
Date (YYYY-MM-DD) [default: today]: [Enter or press Enter for today]
Hours (0-24): 8
Project code: PROJ001
Task code: TASK1
Notes (optional): Regular development work
✓ Time entry logged (ID: entry_12345)
```

### Log Hours (One-Shot)

```bash
fusion timesheet log \
  --date 2026-05-08 \
  --hours 8 \
  --project PROJ001 \
  --task TASK1 \
  --notes "Regular development work"
```

### View Summary

```bash
fusion timesheet summary --range week
```

Output:

```
Timesheet Summary: Week of May 5-9, 2026

┌─ Totals ──────────────────┐
│ Total Hours: 40.0         │
│ Submitted: 5              │
│ Draft: 0                  │
└─────────────────────────┘

┌─ By Project ──────────────┐
│ PROJ001: 32.0 hours       │
│ PROJ002: 8.0 hours        │
└─────────────────────────┘
```

### Export to CSV

```bash
fusion export timesheet ts_20260505 --format csv --output my_timesheet.csv
```

Output:

```
✓ Timesheet exported
  Format: CSV
  File: ./my_timesheet.csv
  Entries: 5
  Size: 2.3 KB
```

View the file:

```bash
cat my_timesheet.csv
```

---

## Development Workflow

### Project Structure

```
fusionctl/
├── src/fusionctl/          # Application source code
│   ├── main.py             # CLI entry point
│   ├── api/                # Oracle API client
│   ├── models/             # Data models (pydantic)
│   ├── services/           # Business logic
│   └── cli/                # CLI commands
├── tests/                  # Test suite
├── pyproject.toml          # Poetry config + Poe tasks
└── README.md               # Project documentation
```

### Common Development Tasks

All tasks are defined in `pyproject.toml` and run via Poetry/Poe:

```bash
# List available tasks
poe --help
```

#### Install Development Dependencies

```bash
poetry install --with dev
```

#### Run Tests

```bash
poe test
```

Or run specific tests:

```bash
poe test tests/unit/test_auth_service.py
```

#### Format Code

```bash
poe format
```

#### Lint

```bash
poe lint
```

#### Type Check

```bash
poe typecheck
```

#### Build Documentation

```bash
poe docs
```

### Making Changes

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes** in `src/fusionctl/`

3. **Add tests** in `tests/`

4. **Run full test suite**:

   ```bash
   poe test
   poe lint
   poe typecheck
   ```

5. **Commit**:

   ```bash
   git add .
   git commit -m "feat: add my feature"
   ```

6. **Push and create a pull request**:

   ```bash
   git push origin feature/my-feature
   ```

### Running the CLI Locally (Development Mode)

```bash
poetry run fusion --help
```

Or, if in Poetry shell:

```bash
fusion --help
```

---

## Configuration

### Config File

The CLI stores configuration in `~/.fusion-cli/config.yaml`:

```yaml
oracle:
  base_url: https://eclf.fa.em2.oraclecloud.com
  timeout: 30
cache:
  ttl_hours: 24
  location: ~/.fusion-cli/cache
cli:
  output_format: table  # table or json
  verbose: false
```

You can override by:

1. **Environment variables** (highest priority):

   ```bash
   export FUSION_ORACLE_TIMEOUT=60
   export FUSION_CACHE_TTL_HOURS=48
   ```

2. **Command-line flags**:

   ```bash
   fusion --config ./custom-config.yaml auth login
   ```

3. **Config file** (lowest priority):
   Edit `~/.fusion-cli/config.yaml`

### Cache Management

Cache is stored in `~/.fusion-cli/cache/`:

```
~/.fusion-cli/cache/
├── timesheets.json           # Timesheet metadata
├── entries_ts_20260505.json  # Entries for specific timesheet
└── metadata.json             # Cache metadata (TTL, version)
```

**Clear cache**:

```bash
fusion cache clear
```

**Force refresh from server**:

```bash
fusion cache refresh
```

**Use only cache (offline mode)**:

```bash
fusion timesheet list --no-refresh
```

---

## Troubleshooting

### Issue: "Not authenticated" error

**Problem**: `✗ Not authenticated. Use 'fusion auth login' to begin.`

**Solution**:

```bash
fusion auth login
```

Log in to Oracle Fusion in your browser, copy the `Cookie` header from a successful request to `eclf.fa.em2.oraclecloud.com`, then run:

```bash
fusion auth login --token
```

### Issue: "Network timeout" error

**Problem**: `✗ Network timeout (30s). Check connectivity or try --no-cache for cached data.`

**Solution**:

1. Check internet connection:

   ```bash
   ping eclf.fa.em2.oraclecloud.com
   ```

2. Use cached data (if available):

   ```bash
   fusion timesheet list --no-cache=false
   ```

3. Increase timeout (in config):

   ```yaml
   oracle:
     timeout: 60  # Increase from default 30
   ```

### Issue: "Timesheet not found" error

**Problem**: `✗ Resource not found: Timesheet with ID ts_20260505`

**Solution**:

1. Refresh cache:

   ```bash
   fusion cache refresh
   ```

2. List available timesheets:

   ```bash
   fusion timesheet list
   ```

3. Use the correct timesheet ID from the list.

### Issue: "Validation error: hours must be between 0 and 24"

**Problem**: `✗ Validation error: hours: Hours must be between 0 and 24`

**Solution**:

Provide a valid hour value between 0.0 and 24.0:

```bash
fusion timesheet log --hours 8
```

### Issue: "Permission denied" error

**Problem**: `✗ Permission denied. You don't have access to this timesheet.`

**Solution**:

1. Check that you're using the correct Oracle user account:

   ```bash
   fusion auth status
   ```

2. Log out and log back in with the correct account:

   ```bash
   fusion auth logout
   fusion auth login
   ```

3. Verify Oracle Fusion Cloud permissions for timesheet access.

### Issue: OS Keychain Not Working

**Problem**: `RuntimeError: keyring not available` or credentials not stored

**Solution** (Linux):

Install the required backend:

```bash
# Using systemd
sudo apt-get install python3-secretstorage

# Or use pass
sudo apt-get install pass
```

Then test:

```bash
python -c "import keyring; print(keyring.get_keyring())"
```

**Solution** (macOS):

Keychain is built-in; if it fails, check:

```bash
security dump-keychain
```

**Solution** (Windows):

Windows Credential Manager should work out of the box. If not, fall back to encrypted file storage (less secure).

### Issue: Help or Version Not Working

**Problem**: `fusion --help` or `fusion --version` shows no output

**Solution**:

Reinstall:

```bash
poetry install --force-reinstall
poetry run fusion --help
```

---

## Next Steps

1. **Authenticate**: `fusion auth login`
2. **List timesheets**: `fusion timesheet list`
3. **Log hours**: `fusion timesheet log --interactive`
4. **View summary**: `fusion timesheet summary`
5. **Read full documentation**: See `README.md` and inline help: `fusion --help`

---

## Getting Help

- **CLI help**: `fusion --help` or `fusion <command> --help`
- **Issue tracker**: [GitHub Issues](https://github.com/yourusername/fusionctl/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/fusionctl/discussions)

---

## Need to Reverse-Engineer the Oracle API?

If you don't have API documentation, follow these steps:

1. **Open browser DevTools** in Firefox or Chrome
2. **Go to Oracle Fusion Cloud**: https://eclf.fa.em2.oraclecloud.com
3. **Open Network tab** (Ctrl+Shift+E or Cmd+Option+E)
4. **Log in** and navigate to the timesheet page
5. **Observe HTTP requests** — look for:
   - `GET /fscmUI/rest/...` endpoints
   - Request headers (auth tokens, CSRF tokens)
   - Response body structure (JSON format)
6. **Document** the endpoint, method, headers, and response
7. **Share** findings in [GitHub Discussions](https://github.com/yourusername/fusionctl/discussions)

This will help us implement the Oracle API client accurately.

---

## Project Status

- **Version**: 1.1.2 (Alpha)
- **Status**: In development
- **Last Updated**: 2026-05-08
- **Maintainer**: Your Name

---

## License

[Add license info here]
