# fusionctl

Oracle Fusion Timesheet CLI for local timesheet viewing, logging, caching, and export.

## MVP Authentication

Oracle Fusion at `eclf.fa.em2.oraclecloud.com` uses Microsoft Azure AD SAML2 SSO with 2FA, so the MVP uses a browser-copied session cookie.

```bash
poetry install --with dev
poetry run fusion auth login --token
poetry run fusion auth status
```

When prompted, paste the `Cookie` header from a successful authenticated Oracle Fusion request.

## Development

```bash
poetry run poe test
poetry run poe lint
poetry run poe typecheck
```
