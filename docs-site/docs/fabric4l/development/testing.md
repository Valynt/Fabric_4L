---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Testing

Value Fabric practices **behavior-first testing**. The test suite is the executable contract for intended behavior. Troubleshooting should not be the primary mechanism for discovering security, configuration, or runtime gaps.

## Philosophy

> **No critical behavior exists unless it is tested.**

For every production-critical workflow, encode:

1. **Intended allowed behavior** — a passing test.
2. **Intended denied behavior** — a passing test that asserts denial.
3. **Expected failure mode** — explicit error codes, safe defaults, or structured rejections.
4. **Test or gate that proves behavior before release** — pytest marker, CI job, or Makefile target.

If behavior is not explicitly intended, it **fails closed by default**.

## Test Markers

pytest markers are defined in `pytest.ini` and used to select and categorize tests.

| Marker | Meaning | CI Fate |
|--------|---------|---------|
| `unit` | Fast, no I/O (<100ms) | Required |
| `integration` | Real DB/cache, no containers | Required |
| `contract_static` | OpenAPI contract checks, no live services | Required |
| `service_required` | Contract tests needing live endpoints | Run when infra is available |
| `tenant_boundary` | Cross-tenant isolation regression | Required |
| `security` | OWASP Top 10 and security regression | Required |
| `slow` | >1 s or heavy deps (e.g., Playwright, PyMuPDF) | Optional |
| `backend_integrated` | Full live-stack validation | Run in dedicated jobs |
| `mandatory` | Unit + contract + security; fails if deps missing | Required |
| `requires_postgres` | Needs live PostgreSQL | Optional |
| `requires_neo4j` | Needs live Neo4j | Optional |
| `requires_redis` | Needs live Redis | Optional |
| `requires_docker` | Needs Docker daemon | Optional |
| `flaky` | Known flaky tests being fixed | Skipped in CI |
| `quarantine` | Isolated due to external dependencies | Skipped in CI |

Run tests by marker:

```bash
pytest -m unit
pytest -m "contract_static"
pytest -m tenant_boundary
pytest -m security
```

## Running Tests Per Layer

### Backend

```bash
# All backend layers
make test

# Single layer
make test-layer1
make test-layer2
make test-layer3
make test-layer4
make test-layer5
make test-layer6

# Fast subset (excludes slow and e2e)
make test-fast

# Unit only
make test-unit

# Integration only
make test-integration
```

### Frontend

```bash
# Unit/component tests
pnpm --dir apps/web run test

# Watch mode
pnpm --dir apps/web run test:watch

# Coverage
pnpm --dir apps/web run test:coverage

# Contract tests only
pnpm --dir apps/web run test:contracts

# Security: assert no dev auth bypass in production build
pnpm --dir apps/web run test:prod-auth-bypass
```

## Contract Tests

Contract tests validate that API schemas, OpenAPI specs, JSON schemas, and generated frontend types remain aligned.

```bash
# Cross-layer contract and architecture tests (no live services)
make contract-tests

# OpenAPI drift detection
pnpm run check:contract-compliance

# Regenerate API types and assert no drift
pnpm run generate:api
pnpm run check:api-types

# Breaking change gate
pnpm contract:breaking
```

!!! tip "Run contract tests before pushing API changes"
    `make contract-tests` is fast and does not require a running stack. Run it after any route handler, schema, or DTO change.

## Security Tests

Security tests cover OWASP Top 10, tenant isolation, RBAC, injection prevention, and hostile cross-tenant scenarios.

```bash
# Fast security smoke
make security-smoke

# Full security suite
make security-test

# Tenant isolation only
make security-test-isolation

# RBAC only
make security-test-rbac

# OWASP Top 10
make security-test-owasp

# Injection prevention
make security-test-injection

# Hostile tenant matrix (CI alias)
pnpm test:security:hostile
```

!!! warning "Include hostile tests for security-sensitive changes"
    When touching auth, tenant scoping, or repository filters, add tests that prove:

    - Tenant A cannot read Tenant B data.
    - Tenant A cannot mutate Tenant B data.
    - Missing tenant context fails closed.
    - Invalid contract payload is rejected.
    - Unauthenticated request is rejected with 401.
    - Cross-tenant read fails with 403.

## E2E Tests

E2E tests use Playwright and run against both mocked and live backends.

```bash
# Mocked E2E
pnpm --dir apps/web run test:e2e

# Live backend E2E
pnpm --dir apps/web run test:e2e:live

# Golden-path journeys
pnpm --dir apps/web run test:e2e:golden:j1:canonical
pnpm --dir apps/web run test:e2e:golden:j11

# Full E2E pipeline (seed, run, reset)
make test-e2e-full
```

!!! note "Live E2E requirements"
    Live E2E requires `PLAYWRIGHT_LIVE_MODE=true`, `PLAYWRIGHT_LIVE_FRONTEND_URL`, and `PLAYWRIGHT_BACKEND_URL`.

## Accessibility Tests

```bash
pnpm --dir apps/web run test:a11y:components
pnpm --dir apps/web run test:a11y:pages
```

## Coverage Expectations

Coverage is per-layer opt-in, defined in each service's `pyproject.toml`. The current thresholds are:

| Layer | Fail Under |
|-------|------------|
| L1 — Ingestion | 70% |
| L2 — Extraction | 85% |
| L2.5 — Signal Refinery | 80% |
| L3 — Knowledge | 75% |
| L4 — Agents | 80% |
| L5 — Ground Truth | 75% |
| L6 — Benchmarks | 70% |
| API Gateway | 75% |

Run coverage locally:

```bash
cd services/layer4-agents
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

## Test Naming Conventions

Name tests after the behavior they prove, not the method they call.

| Good | Bad |
|------|-----|
| `test_authenticated_user_can_read_own_data` | `test_get_user_returns_200` |
| `test_cross_tenant_read_fails_closed_with_403` | `test_user_repo_raises_error` |
| `test_agent_checkpoint_resumes_from_saved_state` | `test_checkpoint_workflow` |

## Readiness Ladder

"Ready" is a four-stage ladder; no stage may be skipped:

1. **Static contract resolved** — `make check-behavior-contract`
2. **Behavior tests executed** — `pnpm run test:critical-behaviors`
3. **Readiness audit passed** — `make check-behavior-readiness-audit`
4. **Production ready** — `make production-readiness-gate`

A passing static contract (Stage 1) does **not** authorize a "ready" claim. Skips and xfails are only tolerated if benign or covered by an active waiver in `config/ci/behavior_readiness_waivers.yaml`.

## Maintenance Rules

- Do not remove failing tests unless they are demonstrably obsolete and replaced with better coverage.
- When a critical behavior is discovered to be untested, file a behavior-debt ticket and add a `TODO(behavior-debt)` comment with the ticket link.
- Do not merge additional logic on top of untested behavior until the contract is encoded in tests.

## Validation Commands

Use the narrowest validation first, then broaden:

```bash
# Targeted pytest
pytest services/layer4-agents/tests/test_workflows.py -v

# Layer gate
make test-layer4

# Contract gate
make contract-tests

# Full PR gate
make verify
```
