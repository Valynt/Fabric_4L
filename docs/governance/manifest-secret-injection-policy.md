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
- `make check-manifest-secret-hygiene`

Current denylist checks include:

- `VAULT_DEV_ROOT_TOKEN_ID`
- Inline `postgres:postgres`
- `redis://redis:6379/...` without auth
- Dev auth bypass env vars (`DEV_AUTH_BYPASS`, `ALLOW_DEV_AUTH_BYPASS`, `AUTH_BYPASS_ENABLED`, `ALLOW_INSECURE_DEV_AUTH_BYPASS`)
