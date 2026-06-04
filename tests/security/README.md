# Security Test Suite

Centralized security validation for Fabric 4L. This directory is the canonical
pytest entrypoint for security regression coverage across auth guards, tenant
isolation, secret handling, security headers, dependency policy, and container
policy.

The category files in this directory are intentionally thin. They document the
authoritative coverage for each security area and assert that the referenced
tests still exist and remain pytest-discoverable. The detailed behavioral tests
stay in their existing files to avoid duplicate execution and drift.

## Quick Start

```bash
# Run the centralized suite
pytest tests/security/

# Run through the root package script
pnpm test:security

# Run the first-class tenant isolation gate
pnpm test:isolation

# Run the fast PR smoke gate
make security-smoke
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

## Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `JWT_SECRET` | Yes in CI | `pytest.ini` test value locally | HS256 signing key with at least 32 characters |
| `TEST_DATABASE_URL` | No | `postgresql://localhost:5432/test_value_fabric` | PostgreSQL connection for DB-backed isolation tests |
| `REDIS_HOST` | No | `localhost` | Redis hostname |
| `REDIS_PORT` | No | `6379` | Redis port |
| `NEO4J_URI` | No | `bolt://localhost:7687` | Neo4j Bolt URI |

## CI Configuration

`.github/workflows/security-validation.yml` runs the fast smoke suite for
security-sensitive pull requests and the full centralized suite on scheduled or
manual full runs. Full runs publish:

- `artifacts/security/security-suite-report.xml`
- `artifacts/security/security-suite-summary.md`

## Troubleshooting

### JWT secret failures

Set a test secret with at least 32 characters:

```bash
set JWT_SECRET=test-jwt-secret-must-be-at-least-32-characters-long
```

### Database or Redis connection failures

Start the local infrastructure stack before running DB/cache-backed tests:

```bash
docker compose -f docker-compose.dev.yml up postgres redis neo4j -d
```
