---
owner: security-team
status: active
last_reviewed: 2026-06-07
---

# Secret Management

Value Fabric never commits real secrets to version control. All credentials, API keys, signing secrets, and connection strings are managed through Infisical, injected at runtime via secure channels, and protected by pre-commit hooks and CI scanning.

!!! danger "Never commit secrets"
    Real secrets live in Infisical. `.env.example` is the only committed reference. Pre-commit hooks (`gitleaks`) and CI scanning block any commit that contains secrets. `ProductionSafetyValidator` will cause startup failure if secrets are misconfigured.

## Secret Storage: Infisical

[Infisical](https://infisical.com) is the platform's canonical secret management system.

| Environment | Secret Source | Injection Method |
|---|---|---|
| Local development | Infisical project + personal login | `infisical run` or `.env.generated` |
| CI/CD | Infisical machine identity | GitHub OIDC → Infisical |
| Production Kubernetes | Infisical Kubernetes Operator | Auto-sync to K8s secrets |
| Review apps / staging | Infisical environment branches | Dynamic injection at deploy time |

### Local Development Workflow

```bash
# 1. Install Infisical CLI and log in
infisical login

# 2. Generate local environment file
pnpm env:dev

# 3. Start infrastructure with generated env
docker compose -f docker-compose.dev.yml --env-file .env.generated up -d

# 4. Run migrations and verify
make migrate
make verify
```

The `.env.generated` file is **gitignored** and temporary. It must never be committed.

## Environment Variable Handling

### `.env.example`

`.env.example` is the **committed reference template** for all required environment variables. It contains safe defaults and placeholder values, never real secrets.

Rules for `.env.example`:
- Every new environment variable must be added to `.env.example`
- It must be documented with a comment explaining its purpose
- Safe defaults only — no insecure production defaults
- Tests and Docker Compose files must be aligned with `.env.example`

```bash
# .env.example (committed, safe defaults only)
DATABASE_URL=postgresql://app_user:app_pass@localhost:5432/valuefabric
JWT_SECRET=replace-me-in-production-with-256-bit-secret
CORS_ORIGINS=http://localhost:3001
```

### `.env.generated`

`.env.generated` is a temporary export from Infisical. It is listed in `.gitignore` and must never be committed.

### What NEVER to Commit

| Category | Examples |
|---|---|
| Database connection strings | `postgresql://user:password@host/db` |
| JWT signing secrets | `JWT_SECRET`, `SERVICE_AUTH_SECRET` |
| API key HMAC secrets | `API_KEY_HMAC_SECRET` |
| Encryption keys | `CREDENTIALS_MASTER_KEY` |
| LLM API keys | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` |
| Cloud credentials | AWS access keys, GCP service account JSON |
| Private keys | `-----BEGIN PRIVATE KEY-----` |
| Infisical tokens | `INFISICAL_TOKEN` |

## CI/CD Secret Injection

### GitHub OIDC → Infisical Machine Identity

CI pipelines use GitHub OIDC to authenticate to Infisical without storing long-lived credentials in GitHub secrets.

```yaml
# .github/workflows/pr-checks.yml (simplified)
jobs:
  security-tests:
    steps:
      - uses: actions/checkout@v4
      - name: Fetch secrets from Infisical
        uses: infisical/cli-action@v1
        with:
          method: oidc
          identity-id: ${{ vars.INFISICAL_MACHINE_IDENTITY_ID }}
      - run: make test
```

This pattern:
- Eliminates long-lived GitHub secrets
- Uses short-lived OIDC tokens for authentication
- Supports fine-grained access policies per workflow

## Kubernetes Secret Management

Production deployments use the **Infisical Kubernetes Operator** to sync secrets directly into cluster namespaces.

```yaml
# k8s/ deployment references InfisicalSecret CRD
apiVersion: secrets.infisical.com/v1alpha1
kind: InfisicalSecret
metadata:
  name: value-fabric-secrets
spec:
  authentication:
    universalAuth:
      credentialsRef:
        secretName: infisical-machine-identity
  managedSecretReference:
    secretName: value-fabric-env
    creationPolicy: Owner
```

Benefits:
- Secrets are stored only in Infisical, not in Git
- Automatic rotation propagation to pods
- No manual secret injection during deployments

## Pre-Commit Hooks (gitleaks)

The repository uses `gitleaks` via `.pre-commit-config.yaml` to detect and block committed secrets.

```yaml
# .pre-commit-config.yaml (excerpt)
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

When `pre-commit` is installed (`pre-commit install`), every commit is scanned for:
- Hardcoded passwords and API keys
- Private keys and certificates
- Database connection strings
- Cloud provider credentials

If a false positive occurs, use `gitleaks:allow` comments only after human review.

## Rotating Secrets

### JWT Secrets

1. Generate new secret: `openssl rand -hex 32`
2. Update in Infisical (new version)
3. Deploy services with new secret
4. Allow grace period for old tokens to expire
5. Revoke old secret version in Infisical

### Database Credentials

1. Create new DB user with identical permissions
2. Update `DATABASE_URL` in Infisical
3. Rolling restart of all services
4. Drop old DB user after confirmation

### API Key HMAC Secrets

1. Generate new HMAC secret: `openssl rand -hex 32`
2. Update `API_KEY_HMAC_SECRET` in Infisical
3. Re-issue API keys for active integrations (graceful migration)
4. Deprecate old secret after migration window

### Kubernetes Secret Rotation

When Infisical secrets are updated, the Infisical Kubernetes Operator automatically:
1. Detects the new version
2. Updates the target Kubernetes Secret
3. Triggers a rolling restart if configured with `reloader.stakater.com/auto: "true"`

## Secret Handling in Code

### Secure Patterns

```python
# Load secrets from environment only at startup
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET")

# Validate presence in production
if not JWT_SECRET and ENVIRONMENT == "production":
    raise RuntimeError("JWT_SECRET is required in production")

# Use sanitize_log_error for exceptions — never log raw secrets
logger.error("DB connection failed", extra={
    "error_code": "DB_CONN_FAILED",
    "error": sanitize_log_error(exc),
})
```

### Insecure Patterns (Blocked by CI)

```python
# NEVER hardcode secrets
API_KEY = "sk-live-1234567890abcdef"  # BLOCKED by gitleaks

# NEVER log raw exceptions that may contain secrets
logger.error("Error: %s", str(exc))  # BLOCKED by semgrep

# NEVER expose secrets in error responses
return JSONResponse(content={"error": str(exc)})  # BLOCKED by semgrep

# NEVER include secrets in health check responses
return {"status": "ok", "db_url": DATABASE_URL}  # BLOCKED
```

### Semgrep Secret Leakage Rules

`.semgrep/error-leakage-guard.yml` blocks raw `str(e)` in log extras, result dicts, Celery stages, and health checks:

| Rule | Severity | Blocks |
|---|---|---|
| `error-str-leakage-in-logger-extra` | WARNING | `extra={"error": str(e)}` without `sanitize_log_error` |
| `error-str-leakage-in-result-dict` | ERROR | `{"error": str(e)}` in internal result/error dicts |
| `error-str-leakage-in-celery-stage` | WARNING | `_update_stage(..., "FAILED", str(e))` |
| `error-str-leakage-in-health-check` | WARNING | `JSONResponse(..., content={"error": str(e)})` |

## Startup Validation

Services validate secret configuration at startup via `validate_production_safety()`:

- `JWT_SECRET` must be present and ≥ 48 characters in production
- `DATABASE_URL` must use SSL (`sslmode=require`) in production
- `CORS_ORIGINS` must not include `*` in production
- No dev auth bypass flags may be set

`tests/security/test_h03_service_startup_validation.py` enforces that misconfigured secrets cause non-zero exit codes.

## Secret Handling Tests

| Test File | Coverage |
|---|---|
| `test_secrets_protection.py` | Secret redaction in logs and responses |
| `test_production_bypass_guardrails.py` | Bypass flag rejection in production |
| `test_dev_bypass.py` | Dev bypass behavior and logging |
| `test_startup_bypass_nonzero_exit.py` | Startup failure on misconfiguration |
| `test_h03_service_startup_validation.py` | Service startup secret validation |
| `test_cross_stack_jwt_contract.py` | JWT secret parity across layers |
| `test_jwt_rotation.py` | JWT secret rotation behavior |
| `test_seed_data_no_hardcoded_passwords.py` | No hardcoded passwords in seed data |
| `test_hardcoded_demo_data_removal.py` | Demo data does not contain real secrets |

## Validation Commands

```bash
# Pre-commit hook (includes gitleaks)
pre-commit run --all-files

# Secret handling tests
pytest tests/security/test_secret_handling.py -v
pytest tests/security/test_secrets_protection.py -v

# Production bypass guardrails
pytest tests/security/test_production_bypass_guardrails.py -v
pytest tests/security/test_dev_bypass.py -v

# Startup validation
pytest tests/security/test_h03_service_startup_validation.py -v

# Semgrep secret leakage rules
semgrep --config .semgrep/error-leakage-guard.yml --error

# Full security suite
pytest tests/security/ -v
```
