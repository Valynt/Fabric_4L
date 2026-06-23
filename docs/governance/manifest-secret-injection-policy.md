# Manifest Secret Injection Policy

This policy defines approved secret injection paths for Kubernetes manifests and production-like compose definitions.

## Approved Secret Injection Paths

- **Infisical runtime injection** for local/dev and CI secret materialization (env-file and process injection).
- **Kubernetes Secret references** using `valueFrom.secretKeyRef` in workload manifests.
- **ExternalSecret / ESO-managed Secrets** as the production source that syncs secret data from the secret manager into Kubernetes Secrets.

## Prohibited Patterns in Non-Dev Manifests

- Inline passwords, tokens, or root-token identifiers.
- Inline database credentials such as `postgres:postgres`.
- Redis URLs without authentication credentials.
- Dev-only auth bypass variables in production overlays/manifests.

## Automated Enforcement

CI enforces these controls via:

- `scripts/ci/check_manifest_secret_hygiene.py`
- `scripts/ci/check_path_and_env_hygiene.py`
- `make check-manifest-secret-hygiene`
- `make check-path-env-hygiene`

Current denylist checks include:

- `VAULT_DEV_ROOT_TOKEN_ID`
- Inline `postgres:postgres`
- `redis://redis:6379/...` without auth
- Dev auth bypass env vars (`DEV_AUTH_BYPASS`, `ALLOW_DEV_AUTH_BYPASS`, `AUTH_BYPASS_ENABLED`, `ALLOW_INSECURE_DEV_AUTH_BYPASS`)

## Repository Path and Env-Template Tracking Policy

To prevent secret leakage and non-portable filesystem artifacts, the repository blocks:

- Drive-letter-like path prefixes (for example `C:\...`) in tracked filenames.
- Escaped/non-portable path-prefix artifacts (for example shell-escaped Windows-path fragments that become literal filenames).
- Tracked `.env`-style files that are not approved templates.

### Allowed tracked env-template patterns

Only template files are allowed to be tracked:

- `.env.example`
- `.env.dev.example`
- `.env.production-compose.template`
- `*.env.example`
- `*.env.template`

Any other `.env`-style tracked filename is forbidden and must be untracked or renamed to an approved template pattern.
