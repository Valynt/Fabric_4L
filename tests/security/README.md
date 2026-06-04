# Security Test Suite

## What This Suite Validates

Centralized security validation for Fabric 4L. This directory is the canonical pytest entrypoint for security regression coverage across auth guards, tenant isolation, secret handling, security headers, dependency policy, and container policy.

The category files in this directory are intentionally thin. They document the authoritative coverage for each security area and assert that the referenced tests still exist and remain pytest-discoverable. The detailed behavioral tests stay in their existing files to avoid duplicate execution and drift.

## Production Risks Covered

- Missing authentication or authorization guards.
- Cross-tenant reads, writes, cache access, graph access, or worker leakage.
- Secrets, dev bypass flags, or provider credentials exposed in unsafe contexts.
- Missing security headers, container hardening, or dependency policy enforcement.

## Existing Coverage Aggregated

The category manifests aggregate the detailed security coverage listed in the matrix below while preserving the original behavioral tests in their existing files.

## Quick Start

```bash
pytest tests/security/
pnpm test:security
pnpm test:isolation
```

## Coverage Matrix

| Category | Aggregation file | Referenced coverage |
| --- | --- | --- |
| Auth guards | `test_auth_guards.py` | Auth boundaries, default deny, auth source validation, JWT validation/config, API key rejection, RBAC, WebSocket auth, MCP gateway auth, API impersonation |
| Tenant isolation | `test_tenant_isolation.py` and `pnpm test:isolation` | Tenant boundary fail-closed behavior, cross-tenant API/write/JWT checks, cross-layer tenant matrix, graph hostile regressions, RLS, background jobs, cache isolation |
| Secret handling | `test_secret_handling.py` | Secret redaction, production/dev bypass guardrails, startup validation, JWT rotation, environment contract checks, bcrypt security |
| Security headers | `test_security_headers.py` | HTTP security headers, CORS posture, middleware misconfiguration, shared security middleware, startup validation |
| Dependency policy | `test_dependency_policy.py` | Supply chain policy, frozen lockfile enforcement, provider billing posture, deprecated dependency boundaries, frontend coverage thresholds |
| Container policy | `test_container_policy.py` | Dockerfile lockfile policy, supply-chain image/SBOM policy, Kubernetes security policies, Bunnyshell deployment contract |

## Known Gaps

- LIVE_PENETRATION_TESTING: external penetration tests and dynamic scans remain scheduled/manual workflow responsibilities.
- LIVE_TENANT_INFRA_RLS: live RLS validation requires provisioned PostgreSQL/Neo4j infrastructure and is covered by integrated gates.

## How To Run

```bash
pytest tests/security/
pnpm test:security
pnpm test:isolation
```

## CI Artifact

CI should publish `artifacts/production-readiness/security/junit.xml` and `artifacts/production-readiness/security/summary.md`. Existing full security runs also publish:

- `artifacts/security/security-suite-report.xml`
- `artifacts/security/security-suite-summary.md`

## Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `JWT_SECRET` | Yes in CI | `pytest.ini` test value locally | HS256 signing key with at least 32 characters |
| `TEST_DATABASE_URL` | No | `postgresql://localhost:5432/test_value_fabric` | PostgreSQL connection for DB-backed isolation tests |
| `REDIS_HOST` | No | `localhost` | Redis hostname |
| `REDIS_PORT` | No | `6379` | Redis port |
| `NEO4J_URI` | No | `bolt://localhost:7687` | Neo4j Bolt URI |

