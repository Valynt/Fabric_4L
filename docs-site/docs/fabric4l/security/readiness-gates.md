---
owner: security-team
status: active
last_reviewed: 2026-06-07
---

# Security Readiness Gates

Value Fabric uses a multi-layered readiness system to ensure no unsafe code reaches production. This page documents the production-readiness gate, required CI checks, security-focused gates, `ProductionSafetyValidator`, dev auth bypass detection, contract compliance, and the four-stage behavior-readiness audit ladder.

!!! danger "Ready is a four-stage ladder"
    No stage may be skipped. A passing static contract (Stage 1) does **not** authorize a "ready" claim. Skips/xfails are only tolerated if benign and covered by an active waiver; anything else is **RED**.

## Production-Readiness Gate

The canonical production-readiness gate is enforced by CI and required for all PRs targeting `main`:

```bash
make production-readiness-gate
```

This gate aggregates:
- Structural preflight checks
- Per-layer lint and typecheck
- Security test suite
- Contract compliance checks
- Migration head validation
- Behavior-readiness audit

!!! warning "Blocking for PR merge"
    The `production-readiness-gate` job is required by `.github/workflows/pr-checks.yml`. PRs cannot merge without a green gate.

## Required CI Checks

All PRs targeting `main` must pass the GitHub checks as named in `.github/workflows/pr-checks.yml`:

| Check | Purpose | Security Relevance |
|---|---|---|
| `structural-preflight` | Import topology, Python contract lint, frontend root policy, pnpm enforcement | Prevents supply-chain and dependency attacks |
| Per-layer lint | `ruff` for Python, ESLint for frontend | Catches unsafe patterns, secret leakage, insecure imports |
| Per-layer typecheck | `mypy` for Python, TypeScript for frontend | Prevents type confusion leading to injection or bypass |
| Per-layer tests | `pytest` per layer | Functional correctness including security invariants |
| `contract-checks` | OpenAPI drift detection, schema parity | Prevents silent API changes that could break auth or tenant boundaries |
| `production-readiness-gate` | Canonical readiness gate | Aggregates all security, contract, and behavior checks |

## Security-Focused Gates

### Security Test Suite

```bash
pytest tests/security/
```

This suite includes:
- OWASP Top 10 coverage (`test_owasp_top10.py`, `test_owasp_top10_complete.py`)
- Authentication boundaries (`test_auth_boundaries.py`)
- Tenant isolation matrix (`test_cross_layer_tenant_isolation_matrix.py`)
- Secret handling (`test_secret_handling.py`)
- Rate limiting safety (`test_rate_limit_safety.py`)
- Production bypass guardrails (`test_production_bypass_guardrails.py`)
- Mandatory security regression gate (`test_mandatory_security_regression_gate.py`)

### Frontend Auth Bypass Detection

```bash
pnpm --dir apps/web run test:prod-auth-bypass
```

Scans the production build bundle for:
- Dev auth bypass strings
- Mock auth providers
- Hardcoded credentials or tokens

### Semgrep Security Rules

```bash
semgrep --config .semgrep/ --error
```

Enforces:
- No direct Cypher graph mutations outside `AuditedGraphMutation`
- No dynamic Cypher label/relationship interpolation without allowlists
- No raw `str(e)` in log extras or result dicts

## ProductionSafetyValidator

`ProductionSafetyValidator` (from `value_fabric.shared.security.config`) runs at service startup and validates that the environment is safe for production.

### Validated Conditions

| Condition | Production Requirement | Failure Mode |
|---|---|---|
| `JWT_SECRET` | Must be present and ≥ 48 characters | `RuntimeError` |
| `DATABASE_URL` | Must include `sslmode=require` | `RuntimeError` |
| `CORS_ORIGINS` | Must not be `*` | `RuntimeError` |
| `DEBUG` | Must not be `true` | `RuntimeError` |
| `DEV_AUTH_BYPASS` | Must not be set | `RuntimeError` |
| `ALLOW_DEV_AUTH_BYPASS` | Must not be set | `RuntimeError` |
| `AUTH_BYPASS_ENABLED` | Must not be set | `RuntimeError` |
| `ALLOW_INSECURE_DEV_AUTH_BYPASS` | Must not be set | `RuntimeError` |

### Case-Insensitive Rejection

The validator normalizes values (`.lower().strip()`) and rejects all variants:
- `true`, `TRUE`, `True`
- `1`, `yes`, `Yes`, `YES`
- ` true ` (whitespace-padded)

### Non-Production Behavior

In development, bypass flags are allowed but emit `WARNING` logs:

```python
# Development: allowed with warning
validate_production_safety(environment="development")
# → WARNING: ALLOW_INSECURE_DEV_AUTH_BYPASS is enabled in development
```

### Startup Validation Tests

`tests/security/test_h03_service_startup_validation.py` enforces that misconfigured production environments cause non-zero exit codes.

## Dev Auth Bypass Detection

!!! danger "Bypass flags cause startup failure in production"
    The following flags are for local development only. They are validated by `ProductionSafetyValidator`:

| Flag | Dev Behavior | Production Behavior |
|---|---|---|
| `DEV_AUTH_BYPASS=true` | Skip auth (with warning) | Startup failure |
| `ALLOW_DEV_AUTH_BYPASS=true` | Skip auth (with warning) | Startup failure |
| `AUTH_BYPASS_ENABLED=true` | Skip auth (with warning) | Startup failure |
| `ALLOW_INSECURE_DEV_AUTH_BYPASS=true` | Skip auth (with warning) | Startup failure |

Tests in `tests/security/test_dev_bypass.py` and `test_production_bypass_guardrails.py` verify rejection across all production-like environments (`production`, `prod`, `staging`, `stage`, `preprod`).

## Contract Compliance Gates

### OpenAPI Drift Detection

```bash
pnpm run check:contract-compliance
```

Fails if:
- Route handlers diverge from OpenAPI specs
- Response shapes change without schema updates
- Frontend-generated types drift from backend contracts

### API Types Regeneration Check

```bash
pnpm run check:api-types
```

Regenerates TypeScript types from OpenAPI and fails if any diff is produced. This prevents silent API contract drift.

### Conflict Marker Check

```bash
make check-conflict-markers
```

Blocks unresolved Git merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) from being merged.

### Pytest Skip Governance

```bash
make check-pytest-skip-governance
```

Enforces discipline around `pytest.skip`, `pytest.mark.skip`, and `pytest.mark.xfail`. Unauthorized skips in security tests are blocked.

## Behavior-Readiness Audit Stages

"Ready" is a four-stage ladder. No stage may be skipped.

### Stage 1: Static Contract Resolved

```bash
make check-behavior-contract
```

- Capabilities map to allowed + denied tests
- Static analysis only; tests are not executed
- Identifies gaps in the test matrix

### Stage 2: Behavior Tests Executed

```bash
pnpm run test:critical-behaviors
```

- The tests actually run and pass
- Covers allowed behavior, denied behavior, and expected failure modes
- Security tests run here

### Stage 3: Readiness Audit Passed

```bash
make check-behavior-readiness-audit
```

- Executes the suites
- Enforces skip discipline (no unauthorized skips in security tests)
- Emits `GREEN`/`YELLOW`/`RED` to `artifacts/readiness/behavior-readiness-audit.json`
- Skips/xfails only tolerated if benign + not-applicable or covered by an active, time-boxed waiver in `config/ci/behavior_readiness_waivers.yaml`

### Stage 4: Production Ready

```bash
make production-readiness-gate
```

- Canonical gate
- The `behavior-readiness` gate is wired into:
  - `mainline-full`
  - `release-candidate`
  - `production-core`
  - `tier0-production-safety`

!!! note "Stage 1 is not enough"
    A passing static contract (Stage 1) does **not** authorize a "ready" claim. You must progress through all four stages.

## What Blocks Production Deployment

The following conditions will block a PR from merging or a deployment from proceeding:

| Blocker | Gate / Check | Why |
|---|---|---|
| Failing security test | `pytest tests/security/` | Untested or broken security behavior |
| Dev auth bypass flag set | `ProductionSafetyValidator` | Production would be insecure |
| `DEBUG=true` in production | `ProductionSafetyValidator` | Verbose errors expose internals |
| OpenAPI drift | `contract-checks` | Frontend/backend contract mismatch |
| Unauthorized pytest skip | `check-pytest-skip-governance` | Security test may be hidden |
| Missing migration head | `check-migration-heads` | Database state undefined |
| Conflict markers in source | `check-conflict-markers` | Incomplete merge |
| Semgrep security rule violation | `semgrep --config .semgrep/ --error` | Blocked pattern (direct mutation, dynamic Cypher, secret leakage) |
| RED behavior-readiness audit | `check-behavior-readiness-audit` | Critical behavior untested or failing |
| Failing `production-readiness-gate` | `production-readiness-gate` | Aggregate gate failure |
| Container policy violation | `test_container_policy.py` | Missing `runAsNonRoot`, `readOnlyRootFilesystem`, etc. |

## Kubernetes Deployment SecurityContext

All rendered deployment bundles under `k8s/deployments/*` enforce baseline Kubernetes hardening:

| Setting | Value | Rationale |
|---|---|---|
| `securityContext.runAsNonRoot` | `true` | Prevents root container execution |
| `securityContext.seccompProfile.type` | `RuntimeDefault` | Restricts available syscalls |
| `securityContext.allowPrivilegeEscalation` | `false` | Prevents privilege escalation |
| `securityContext.readOnlyRootFilesystem` | `true` | Prevents runtime binary modification |
| `securityContext.capabilities.drop` | `ALL` | Removes all Linux capabilities |

CI enforcement: `python scripts/ci/k8s_routing_check.py` fails when rendered deployment manifests violate this baseline.

## Validation Commands

```bash
# Full production-readiness gate
make production-readiness-gate

# Behavior-readiness stages
make check-behavior-contract
pnpm run test:critical-behaviors
make check-behavior-readiness-audit

# Security-focused subsets
pytest tests/security/ -v
pytest tests/security/test_mandatory_security_regression_gate.py -v
pytest tests/security/test_production_bypass_guardrails.py -v
pytest tests/security/test_dev_bypass.py -v

# Contract and structural
pnpm run check:contract-compliance
pnpm run check:api-types
make check-conflict-markers
make check-pytest-skip-governance

# Frontend production auth bypass scan
pnpm --dir apps/web run test:prod-auth-bypass

# Semgrep security rules
semgrep --config .semgrep/ --error

# Container policy
pytest tests/security/test_container_policy.py -v

# Kubernetes hardening
python scripts/ci/k8s_routing_check.py
```
