# Centralized Security Test Suite

`tests/security/` is the centralized security aggregation suite for Value Fabric.
It documents the production-readiness security categories in one stable pytest
entrypoint while preserving the deeper layer-specific tests in their canonical
service locations.

## Quick Start

```bash
# Centralized security aggregation suite
pytest tests/security/

# pnpm delegate used by CI and contributors
pnpm test:security
```

`pnpm test:security` writes JUnit evidence to
`artifacts/security/pytest-security.xml`.

## Aggregation model

The centralized files are intentionally thin. They either run lightweight shared
checks already present in this directory or validate references to existing
security tests and policy checks. This avoids copying service-level regression
tests while still giving auditors and CI one canonical suite to execute.

Directory-level collection (`pytest tests/security/`) focuses on these central
files:

| Central file | Category | Coverage references |
| --- | --- | --- |
| `test_auth_guards.py` | Authentication, authorization, RBAC, JWT, WebSocket auth, and bypass guardrails | `test_auth_boundaries.py`, `test_auth_default_deny.py`, `test_auth_source_validation.py`, `test_jwt_config_validation.py`, `test_rbac.py`, service API auth tests, Layer 4 fail-closed authz tests |
| `test_tenant_isolation.py` | Tenant context propagation and cross-tenant read/write prevention | Existing root hostile tenant tests plus Layer 1–Layer 6 cross-tenant tests |
| `test_secret_handling.py` | Secret hygiene, production bypass guardrails, and safe secret-backed config | `test_secrets_protection.py`, `test_production_bypass_guardrails.py`, startup bypass checks, Keycloak realm seed and manifest/path hygiene scripts |
| `test_security_headers.py` | HTTP headers, CORS, CSRF, and security middleware posture | Existing header tests, CSRF suite, shared middleware tests, security misconfiguration tests |
| `test_dependency_policy.py` | Package-manager, supply-chain, lockfile, and startup dependency policy | `test_supply_chain.py`, Dockerfile lockfile checks, pnpm-only enforcement, startup dependency verifier tests |
| `test_container_policy.py` | Container, Compose, Kubernetes, and production runtime policy | Startup validation, security misconfiguration, Docker Compose files, and `k8s/` manifests |

The canonical reference map lives in `tests/security/aggregation_manifest.py`.
Add references there when new layer-specific security tests are introduced.

## Running deeper security checks

Explicit file invocation still runs the existing deeper suites. Examples:

```bash
pytest tests/security/test_security_smoke.py -v
pytest tests/security/test_rbac.py -v --tb=short
pytest services/layer4-agents/tests/test_fail_closed_authz_guards.py -v
make security-test-isolation
```

Some deeper suites require infrastructure or optional service dependencies
(PostgreSQL, Redis, Neo4j, Docker, Keycloak, or layer-specific Python packages).
The central directory-level suite is kept lightweight so `pytest tests/security/`
remains a reliable aggregation and documentation gate.

## CI evidence

The security validation workflow publishes the central suite evidence as a
security summary artifact. The artifact includes:

- `artifacts/security/pytest-security.xml` — JUnit test report.
- `artifacts/security/security-test-summary.md` — category coverage summary.

## Environment Variables

| Variable | Required for central suite | Description |
|----------|----------------------------|-------------|
| `JWT_SECRET` | No, test default provided | HS256 signing key for tests that exercise local JWT paths. |
| `TEST_DATABASE_URL` | No, infra tests skip locally if unavailable | PostgreSQL connection for explicit RLS suites. |
| `REDIS_HOST` / `REDIS_PORT` | No, infra tests skip locally if unavailable | Redis connection for explicit cache/rate-limit suites. |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | No, explicit graph tests only | Neo4j connection for explicit graph isolation suites. |
