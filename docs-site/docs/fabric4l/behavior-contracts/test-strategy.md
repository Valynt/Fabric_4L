---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---

# Test Strategy

The ValuePact platform uses a multi-layer test pyramid optimized for a six-layer backend architecture and a React/Vite frontend. Every test type has a specific purpose, marker, and execution context. This page is the authoritative reference for which test to write, which marker to apply, and which command to run.

## Test pyramid

```text
                    ┌─────────────┐
                    │   E2E       │  Playwright, golden-path journeys
                    │  (few)      │  Slowest, highest fidelity
                    ├─────────────┤
                    │  Backend    │  Full live-stack validation
                    │  Integrated │  L1–L6 cross-layer contracts
                    ├─────────────┤
                    │  Contract   │  OpenAPI, schema, cross-layer
                    │  + Security │  Static and service-required
                    ├─────────────┤
                    │  Integration│  Real DB, cache, no containers
                    │  (service)  │  Service boundary tests
                    ├─────────────┤
                    │    Unit     │  Pure logic, no I/O, <100ms
                    │   (many)    │  Fastest, highest volume
                    └─────────────┘
```

The pyramid favors a broad base of fast unit tests, a moderate layer of integration and contract tests, and a narrow apex of expensive E2E and backend-integrated tests.

!!! tip "Run narrow first, then broaden"
    During local development, start with the smallest relevant scope:
    ```bash
    pytest -m unit path/to/relevant/tests
    pytest -m integration path/to/relevant/tests
    pytest tests/contract
    make test-backend-integrated-validation
    ```

## Unit tests

**Purpose:** Verify pure logic, algorithms, and isolated functions without I/O.

**Characteristics:**
- No database, cache, network, or filesystem access
- Execution time under 100ms per test
- Highest volume; target 70–85% coverage per layer

**Marker:** `unit`

**Example locations:**
- `services/layer2-extraction/tests/test_pydantic_extraction.py`
- `tests/unit/l3/test_graph_query_builder.py`
- `tests/unit/l5/test_truth_object_scoring.py`

**Command:**
```bash
pytest -m unit
```

**Coverage gates (per `pyproject.toml` `[tool.coverage.report]`):**

| Layer | Fail-under |
|---|---|
| L1 Ingestion | 70% |
| L2 Extraction | 85% |
| L2.5 Signal Refinery | 80% |
| L3 Knowledge | 75% |
| L4 Agents | 80% |
| L5 Ground Truth | 75% |
| L6 Benchmarks | 70% |
| API Gateway | 75% |

!!! note "Coverage is per-layer opt-in"
    Coverage is not a global gate. Run it locally within a service directory:
    ```bash
    cd services/layer4-agents && pytest --cov=src --cov-report=term-missing --cov-fail-under=80
    ```

## Integration tests

**Purpose:** Verify service boundaries with real dependencies (PostgreSQL, Redis, Neo4j) but without Docker containers or full stack orchestration.

**Characteristics:**
- Real database transactions (rolled back after test)
- Real Redis operations
- Real Neo4j graph queries where applicable
- No live LLM calls (mocked or stubbed)

**Marker:** `integration`

**Additional infrastructure markers:**

| Marker | Dependency |
|---|---|
| `requires_postgres` | Live PostgreSQL instance |
| `postgres_only` | PostgreSQL (SQLite compatibility prohibited) |
| `requires_redis` | Live Redis instance |
| `requires_neo4j` | Live Neo4j instance |

**Example locations:**
- `services/layer3-knowledge/tests/test_hybrid_retrieval.py`
- `tests/integration/test_billing_entitlements.py`

**Command:**
```bash
pytest -m integration
pytest -m "requires_postgres or requires_redis"
```

## Contract tests

Contract tests prove that API schemas, error envelopes, and cross-layer payload shapes remain stable. They are the primary defense against architectural drift.

### Static contract tests

**Purpose:** Validate OpenAPI specs, JSON schemas, import topology, and error envelope shapes without running services.

**Characteristics:**
- Deterministic; no live endpoints required
- Fast; suitable for CI preflight
- Catches drift between specs and code

**Markers:** `contract_static`, `contract_static_no_service`

**Example locations:**
- `tests/contract/test_error_envelope_consistency.py`
- `tests/contract/test_import_topology.py`
- `tests/contract/test_l3_route_contract_regression.py`
- `tests/contract/test_startup_bypass_guard_contract.py`

**Command:**
```bash
pytest -m contract_static
make contract-tests
```

### Service-required contract tests

**Purpose:** Validate runtime API behavior against live endpoints.

**Characteristics:**
- Requires reachable services (L1–L6)
- Validates actual HTTP responses match OpenAPI contracts
- Schemathesis-driven suites fall into this category

**Marker:** `service_required`

**Example locations:**
- `tests/contract/test_api_shape_regression.py`
- `tests/contract/test_health_contract_and_red_metrics.py`

**Command:**
```bash
pytest -m service_required
```

!!! warning "Schemathesis and pytest-xdist incompatibility"
    Schemathesis-driven suites crash under `pytest-xdist` with `INTERNALERROR> AttributeError: 'WorkerController' object has no attribute 'workeroutput'`. These tests are marked `no_parallel` and run serially. CI shards parallelize at the job level instead.

## Tenant-boundary tests

**Purpose:** Prove that tenant isolation is enforced at every layer: API, database, cache, graph, and jobs.

**Characteristics:**
- Hostile: they attempt actions that must be denied
- Assert exact failure modes (401, 403, empty result sets)
- Cross-layer matrix coverage in `tests/security/`

**Markers:** `tenant_boundary`, `tenant_isolation`, `tenant_matrix`, `cross_tenant_write`

**Example locations:**
- `tests/security/test_tenant_isolation.py`
- `tests/security/test_cross_tenant_api.py`
- `tests/security/test_cross_layer_tenant_isolation_matrix.py`
- `services/layer2-extraction/tests/test_cross_tenant_hostile_behavioral.py`

**Command:**
```bash
pytest -m tenant_boundary
pytest -m tenant_isolation
```

## Security tests

**Purpose:** Validate OWASP Top 10 mitigations, auth boundaries, rate limiting, injection resistance, and secret handling.

**Characteristics:**
- Includes adversarial and hostile test cases
- Asserts safe failure modes (no stack traces, no secret leakage)
- Required for production readiness

**Marker:** `security`

**Sub-markers for specific security domains:**

| Marker | Focus |
|---|---|
| `auth_boundaries` | Authentication and authorization boundary regression |
| `jwt_config` | JWT configuration safety regression |
| `rate_limit` | Rate-limiting safety regression |
| `context_validation` | Security context validation |
| `rbac` | Role-based access control |

**Example locations:**
- `tests/security/test_owasp_top10.py`
- `tests/security/test_injection.py`
- `tests/security/test_auth_boundaries.py`
- `tests/security/test_csrf_comprehensive.py`

**Command:**
```bash
pytest -m security
```

## E2E tests

**Purpose:** Validate complete user journeys through the frontend, from authentication through business outcomes.

**Characteristics:**
- Playwright-driven browser automation
- Mock API mode (default) or live backend mode
- Golden-path journey coverage

**Markers:** `e2e` (frontend pytest suite), Playwright tags in `apps/web/e2e/`

**Example locations:**
- `apps/web/e2e/behaviors/j1-ingestion.behavior.spec.ts`
- `apps/web/e2e/golden/j11-business-case.journey.spec.ts`

**Commands:**
```bash
# Mocked E2E
pnpm --dir apps/web run test:e2e

# Live backend E2E
pnpm --dir apps/web run test:e2e:live

# Specific golden-path journeys
pnpm --dir apps/web run test:e2e:golden:j1:canonical
pnpm --dir apps/web run test:e2e:golden:j11

# Accessibility (WCAG 2.1 AA)
pnpm --dir apps/web run test:a11y:components
pnpm --dir apps/web run test:a11y:pages
```

## Backend integrated tests

**Purpose:** Validate the full live stack (L1–L6) with durable cross-layer state. These are the most expensive tests and are run only in specific CI profiles and release smoke.

**Characteristics:**
- Requires live services, databases, caches, and graph
- Cross-layer data flow validation
- Chaos resilience and release smoke checks

**Marker:** `backend_integrated`

**Example locations:**
- `tests/backend_integrated/test_cross_layer_data_flow_validation.py`
- `tests/backend_integrated/test_backend_integrated_golden_path.py`
- `tests/backend_integrated/test_chaos_resilience.py`

**Commands:**
```bash
make test-backend-integrated-validation
make test-backend-integrated-release-smoke
```

## Marker reference table

| Marker | Meaning | Speed | Infrastructure |
|---|---|---|---|
| `unit` | Fast, no I/O | <100ms | None |
| `integration` | Real DB/cache | 1–10s | Postgres, Redis, Neo4j |
| `contract_static` | Static OpenAPI/schema | <1s | None |
| `service_required` | Live endpoint contract | 5–30s | L1–L6 running |
| `tenant_boundary` | Cross-tenant hostile | 1–5s | Postgres, Redis, Neo4j |
| `security` | OWASP / auth / rate limit | 1–10s | Varies |
| `e2e` | Playwright journeys | 30–120s | Browser, optional live backend |
| `backend_integrated` | Full live-stack | 60–300s | Full Docker Compose stack |
| `slow` | >1s or heavy deps | Variable | Optional heavy deps (Playwright, etc.) |
| `performance` | SLO benchmarks | Variable | Production-like load |
| `chaos` | Failure injection | Variable | Full stack |

## Production-readiness markers

The following markers are used by `make production-readiness-gate` and its sub-profiles. They are not run on every PR but are required for release candidate promotion.

| Marker | Domain |
|---|---|
| `reliability` | Health, SLO, retry, timeout, degradation |
| `observability` | Logs, traces, metrics, correlation IDs, redaction |
| `recovery` | Backup, restore, disaster recovery |
| `release` | Migration rollback, canary, artifact integrity |
| `tenancy` | Tenant scope and cross-tenant isolation aggregation |
| `billing` | Subscription, webhook, entitlement |
| `abuse` | Quotas, throttling, replay, upload limits |
| `config` | Configuration and environment safety |
| `audit` | Audit logging and tamper resistance |
| `production_safety` | Startup safety and unsafe-default guards |

## Command quick reference

```bash
# All backend layers
make test

# Single layer
make test-layer1   # … through test-layer6

# Unit only
pytest -m unit

# Contract + architecture (no live services)
make contract-tests

# Security suite
pytest -m security

# Tenant isolation
pytest -m tenant_boundary

# Frontend unit/component
pnpm --dir apps/web run test

# Frontend contract tests only
pnpm --dir apps/web run test:contracts

# Full verification gate (required before PR)
make verify
```

## Related documentation

- [Critical Behaviors](critical-behaviors.md) — Layer-by-layer critical behavior examples
- [Gate Registry](gate-registry.md) — Readiness ladder and waiver policy
- `pytest.ini` — Full marker definitions and test paths
- `docs/testing/` — Canonical testing governance and behavior-readiness guidance
