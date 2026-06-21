# Value Fabric Test Strategy
## Behavior-First Production Testing Standard

**Version:** 2.0
**Date:** June 5, 2026
**Scope:** Fabric_4L Platform (Layers 1-6 + Frontend)

---

## Executive Summary

This repository uses tests as the **executable contract for intended behavior**.

The standard is not "does the code work locally?" The standard is: **"Does the repo continuously prove that the implementation matches the intended behavior?"**

For every production-critical workflow, the repo must define:

1. **The intended allowed behavior** — encoded as a passing test.
2. **The intended denied behavior** — encoded as a passing test that asserts denial.
3. **The expected failure mode** — explicit error codes, safe defaults, or structured rejections.
4. **The test or gate that proves the behavior before release** — a pytest marker, CI job, or Makefile target.

If behavior is not explicitly intended, it **fails closed by default**.

> **Operating Principle:** No critical behavior exists unless it is tested.  
> **Enforcement Rule:** Intended behavior passes. Unintended behavior fails. Untested behavior is not production-ready.

Troubleshooting should not be the primary mechanism for discovering security, configuration, or runtime gaps. Those gaps should surface as failing tests, failing CI gates, or explicit contract violations before deployment.

For the canonical governance statement, see [`docs/governance/behavior-first-testing.md`](../governance/behavior-first-testing.md).

---

## Behavior Domains

Every major domain must have a clear behavioral contract that encodes both the allowed path and the denied path:

| Domain | What Must Be Proven | Typical Markers |
|---|---|---|
| Auth behavior | Valid auth succeeds; invalid auth fails closed | `security`, `contract_static` |
| Tenant isolation | Cross-tenant access is denied; same-tenant access succeeds | `tenant_boundary`, `security` |
| API access rules | Endpoints enforce auth, authorization, and shape | `contract_static`, `service_required` |
| Configuration validity | Invalid config is rejected at startup or in gates | `contract_static` |
| Environment safety | Dev bypass flags cannot activate in production | `contract_static`, `security` |
| Data boundaries | Data is scoped to tenant, user, and role | `tenant_boundary`, `integration` |
| Failure behavior | Degradation is graceful; errors are safe and structured | `contract_static`, `integration` |
| Frontend user flows | UI states match intended allowed and denied paths | Frontend `*.behavior.test.*` |
| Service-to-service permissions | Internal calls carry and validate tenant context | `integration`, `contract_static` |
| Production readiness gates | Every release proves required invariants before deploy | CI gates, `mandatory` |

---

## Test Pyramid

The pyramid still governs execution economics, but every layer must encode behavior contracts:

```
       /\
      /  \      E2E Tests (10%)
     /    \     Critical User Journeys + End-to-End Behaviors
    /------\
   /        \   Integration Tests (20%)
  /          \  Service Boundaries, APIs, Tenant Isolation
 /------------\
/              \ Unit Tests (70%)
/                \ Fast, Isolated, No I/O, Behavior-Focused
------------------
```

### Pyramid Discipline Rules

1. **Unit Tests: 70%** - Target 100ms execution, no external dependencies, behavior-named
2. **Integration Tests: 20%** - Test service boundaries with real dependencies, include hostile cases
3. **E2E Tests: 10%** - Critical user journeys only, never invert the pyramid
4. **Coverage: ≥80%** - Enforced in CI for all backend layers
5. **Flaky Rate: <1%** - Flaky tests are P0 to fix

---

## Test Categories

### 1. Unit Tests (70%)

| Layer | Location | Focus | Coverage Target |
|-------|----------|-------|-----------------|
| L1 Ingestion | `services/layer1-ingestion/tests/unit/` | Crawler, adapters, models | 80% |
| L2 Extraction | `services/layer2-extraction/tests/` | Chunker, LLM extractor | 80% |
| L3 Knowledge | `services/layer3-knowledge/tests/` | Entity CRUD, search, graph | 80% |
| L4 Agents | `services/layer4-agents/tests/unit/` | Workflow state machine | 80% |
| L5 Ground Truth | `services/layer5-ground-truth/tests/unit/` | Evidence, audit log | 80% |
| L6 Benchmarks | `services/layer6-benchmarks/tests/` | Calculations, metrics | 80% |
| Frontend | `apps/web/src/**/*.test.tsx` | Components, hooks, utils | 70% |

**Behavior-first requirement:** Every unit test that covers a security or boundary decision must assert both the allowed path and a representative denied path (or reference the dedicated hostile/contract test that covers it).

### 2. Integration Tests (20%)

| Category | Location | Dependencies | Markers |
|----------|----------|--------------|---------|
| API Integration | `tests/integration/` | PostgreSQL, Neo4j, Redis | `integration` |
| Cross-Layer Flow | `tests/integration/` | Full stack | `integration` |
| Database Tests | `services/layer*/tests/` | PostgreSQL | `requires_postgres` |
| Graph DB Tests | `services/layer3-knowledge/tests/` | Neo4j | `requires_neo4j` |
| Cache Tests | `services/layer*/tests/` | Redis | `requires_redis` |

**Behavior-first requirement:** Integration tests must include hostile cross-tenant cases where applicable. Tenant A must not read Tenant B data, and that must be proven in the test suite.

### 3. Contract Tests (Behavior Contracts)

Contract tests are the primary enforcement mechanism for behavior-first testing.

| Type | Location | Tool | Coverage |
|------|----------|------|----------|
| OpenAPI Schema | `tests/contract/` | schemathesis | All endpoints |
| Response Models | `tests/contract/` | pydantic | All responses |
| Tool Manifests | `tests/contract/` | JSON Schema | All skills |
| Startup Guards | `tests/contract/` | pytest | Dev-bypass safety |
| Auth/Route Inventory | `tests/contract/` | pytest | Unauthenticated route coverage |

#### Contract invocation matrix (CI + local deterministic mode)

| Subset | Marker | Requires live services | Command |
|---|---|---|---|
| Static contract checks | `contract_static` | No | `pytest tests/contract -m contract_static -n 0 -v --tb=short` |
| Service-required contract checks | `service_required` | Yes (or `CONTRACT_TEST_MODE=mock`) | `pytest tests/contract -m service_required -n 0 -v --tb=short` |
| Collection-only static gate | `contract_static` | No | `pytest tests/contract --collect-only -m contract_static -n 0 -q` |
| Collection-only service gate | `service_required` | No (collection only) | `pytest tests/contract --collect-only -m service_required -n 0 -q` |
| Schemathesis OpenAPI property checks | N/A (CLI) | No (spec-driven) | `st check contracts/openapi/layer{1,2,3,4}-*.json --hypothesis-seed 42` |

**Pinned prerequisites**
- `pytest-xdist==3.5.0`
- `schemathesis==3.39.16`

**Service prerequisites for `service_required`**
- `LAYER3_API_URL` (default `http://localhost:8003`)
- `LAYER4_API_URL` (default `http://localhost:8004`)
- `LAYER5_API_URL` (default `http://localhost:8005`)
- Health endpoints must be reachable unless `CONTRACT_TEST_MODE=mock`.

**Behavior-first requirement:** Every contract test must assert a failure mode. A contract test that only validates happy-path shapes is incomplete.

### 4. E2E Tests (10%)

| Journey | Location | Tool | Browsers |
|---------|----------|------|----------|
| Authentication | `apps/web/e2e/journeys/` | Playwright | Chrome, Firefox, Safari |
| Value Pack Workflow | `apps/web/e2e/journeys/` | Playwright | Chrome, Firefox, Safari |
| Agent Workflow | `apps/web/e2e/journeys/` | Playwright | Chrome, Firefox, Safari |
| Knowledge Graph | `apps/web/e2e/journeys/` | Playwright | Chrome, Firefox, Safari |
| Evidence Export | `apps/web/e2e/journeys/` | Playwright | Chrome, Firefox, Safari |

**Behavior-first requirement:** E2E tests must cover critical denied paths (e.g., unauthenticated redirect, insufficient permissions) in addition to golden paths.

### 5. Performance Tests

| Test | Location | SLOs | Markers |
|------|----------|------|---------|
| API Latency | `tests/performance/` | p95 < 200ms | `performance` |
| Search Latency | `tests/performance/` | p95 < 2s | `performance` |
| Load Tests | `tests/performance/` | 50 concurrent | `performance` |
| Frontend LCP | `apps/web/e2e/` | < 2.5s | `performance` |

### 6. Security Tests

| OWASP Category | Location | Coverage | Behavior-First Requirement |
|----------------|----------|----------|---------------------------|
| A01: Broken Access Control | `tests/security/` | ✓ IDOR, authz | Denied paths must fail with correct status |
| A02: Cryptographic Failures | `tests/security/` | ✓ TLS, password policy | Invalid crypto is rejected |
| A03: Injection | `tests/security/` | ✓ SQL, NoSQL, command | Malicious input is sanitized/rejected |
| A04: Insecure Design | `tests/security/` | ✓ Rate limiting | Excess requests are throttled |
| A05: Security Misconfiguration | `tests/security/` | ✓ Headers, debug mode | Unsafe config fails startup gates |
| A06: Vulnerable Components | `tests/security/` | ✓ Dependency scanning | CVEs block CI |
| A07: Auth Failures | `tests/security/` | ✓ Brute force, MFA | Invalid credentials fail closed |
| A08: Integrity Failures | `tests/security/` | ✓ CSRF, webhooks | Forged requests are rejected |
| A09: Logging Failures | `tests/security/` | ✓ Audit, alerts | Sensitive events are logged |
| A10: SSRF | `tests/security/` | ✓ URL validation | Unauthorized outbound requests are blocked |

### 7. Accessibility Tests

| Test | Location | Standard | Tool |
|------|----------|----------|------|
| WCAG 2.1 AA Audit | `apps/web/scripts/a11y/` (axe scan) | WCAG 2.1 AA | axe-core |
| Keyboard Navigation | `apps/web/e2e/` | WCAG 2.1.1 | Playwright |
| Screen Reader | `apps/web/e2e/` | WCAG 4.1.2 | Playwright |
| Component A11y | `apps/web/src/**/*.a11y.spec.tsx` | WCAG 2.1 | jest-axe |

---

## Test Infrastructure

### Python Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "pytest-xdist>=3.6.0",        # Parallel execution
    "pytest-timeout>=2.3.0",       # Prevent hanging
    "pytest-randomly>=3.16.0",     # Randomize order
    "factory-boy>=3.3.0",          # Test data factories
    "faker>=33.0.0",               # Fake data
    "testcontainers>=4.8.0",       # Docker for tests
    "schemathesis>=3.38.0",        # API contract testing
    "hypothesis>=6.122.0",         # Property-based testing
    "httpx>=0.27.0",               # Async HTTP client
    "respx>=0.21.0",               # HTTPX mocking
]
```

### Frontend Dependencies

```json
{
  "devDependencies": {
    "vitest": "^2.0.0",
    "@vitest/coverage-v8": "^2.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "jsdom": "^24.0.0",
    "msw": "^2.0.0",              # Mock Service Worker
    "@playwright/test": "^1.49.0",
    "@axe-core/playwright": "^4.10.0"  # Accessibility testing
  }
}
```

### Test Data Factories

All test data created via Factory Boy patterns in `tests/factories.py`:

- `EntityFactory` - Capabilities, use cases, personas, value drivers
- `ValuePackFactory` - Value packs with formulas
- `UserFactory` - Users with roles and tiers
- `FormulaFactory` - Formulas with expressions
- `BusinessCaseFactory` - Business cases with financials
- `ExtractionJobFactory` - Ingestion jobs
- `AgentWorkflowStateFactory` - Workflow states
- `AuditLogEntryFactory` - Audit log entries

### Test Markers

> The canonical, authoritative marker list lives in [`pytest.ini`](../../pytest.ini)
> (55 markers). The subset below is the most commonly used; do not treat it as
> exhaustive. Security/isolation markers such as `tenant_boundary`,
> `cross_tenant_write`, `auth_boundaries`, `production_safety`, and
> `contract_static` are also enforced by CI gates.

```ini
markers =
    unit: Fast unit tests (no I/O, <100ms)
    integration: Integration tests with real dependencies
    e2e: End-to-end tests
    contract: API contract tests (OpenAPI schema validation)
    contract_static: Static contract checks with no live services
    service_required: Contract tests requiring live endpoints
    tenant_boundary: Cross-tenant isolation regression tests
    performance: Performance benchmarks and SLO validation
    security: Security tests (OWASP Top 10)
    accessibility: WCAG 2.1 AA compliance tests
    slow: Tests that take > 1 second
    flaky: Known flaky tests being fixed - skip in CI
    requires_postgres: Tests requiring PostgreSQL
    requires_redis: Tests requiring Redis
    requires_neo4j: Tests requiring Neo4j
    mandatory: Required for PR merge; behavior-critical gates
```

---

## CI/CD Integration

### GitHub Actions Workflow

**File:** `.github/workflows/pr-checks.yml`

**Jobs:**
1. **backend-tests** - Unit, integration, contract, security tests
2. **frontend-tests** - Unit tests, lint, type check, behavior tests
3. **e2e-tests** - Playwright E2E tests (depends on backend/frontend)
4. **performance-tests** - Benchmarks (main branch only)
5. **contract-checks** - Cross-layer contract, OpenAPI drift, tool contracts
6. **production-readiness-gate** - `make production-readiness-gate`

**Services:**
- PostgreSQL 16
- Redis 7
- Neo4j 5 (Enterprise)

**Coverage Gates:**
- Backend: ≥80% line coverage
- Frontend: ≥70% line coverage
- Security: All OWASP tests pass
- Accessibility: WCAG 2.1 AA compliance

**Behavior-first gates:**
- Every PR must pass `contract_static` tests.
- Every PR must pass `tenant_boundary` tests.
- Every PR must pass `mandatory` markers.
- Missing tests for new critical behavior may be blocked in review.

### Parallel Execution

All tests run in parallel:
- Python: `pytest -n auto` (pytest-xdist)
- Frontend: `vitest --pool=threads`
- E2E: Playwright workers = 3 in CI

---

## Test Execution Commands

### Run All Tests

```bash
# Backend (all layers)
pytest -m unit -n auto --timeout=60
pytest -m integration --timeout=120
pytest -m contract --timeout=60
pytest -m security --timeout=60

# Frontend (apps/web)
pnpm run test -- --coverage

# E2E
pnpm exec playwright test

# Accessibility
pnpm exec playwright test e2e/accessibility/

# Performance
pytest -m performance --timeout=300 -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit -n auto

# Integration tests with services
pytest -m integration --timeout=120

# Security tests
pytest -m security

# Contract tests
pytest -m contract

# Tenant boundary (behavior-first isolation)
pytest -m tenant_boundary

# Mandatory gates (behavior-critical)
pytest -m mandatory

# Single layer
pytest services/layer3-knowledge/tests/ -m unit

# Single test file
pytest services/layer4-agents/tests/unit/test_workflow_state_machine.py -v
```

---

## Quality Gates

### Pre-Commit

```bash
# Run via pre-commit hook
make verify  # Runs: lint → type-check → unit tests → contract tests
```

### Pre-PR

```bash
# Full verification
make verify && make evals

# Or individual layers
make test-layer1
make test-layer2
make test-layer3
make test-layer4
make test-frontend
```

### CI Gates

| Gate | Requirement | Blocking | Behavior-First Note |
|------|-------------|----------|---------------------|
| Unit Tests | ≥80% coverage | Yes | Must include boundary assertions |
| Integration Tests | All pass | Yes | Must include hostile cross-tenant cases |
| Contract Tests | All pass | Yes | Must assert failure modes |
| Security Tests | All pass | Yes | Must cover denied paths |
| Tenant Boundary | All pass | Yes | Cross-tenant isolation is non-negotiable |
| E2E Tests | All pass | Yes | Must cover denied paths |
| Accessibility | WCAG 2.1 AA | Yes | |
| Performance | SLOs met | Yes (main only) | |
| Flaky Rate | <1% | Yes | |

---

## Test Maintenance

### Flaky Test Protocol

1. **Detection** - CI flags test as flaky (non-deterministic failures)
2. **Quarantine** - Mark with `@pytest.mark.flaky` and skip in CI
3. **Investigation** - Root cause analysis within 24 hours
4. **Fix** - Stabilize or rewrite test
5. **Re-enable** - Remove flaky marker after 5 consecutive passes

### Behavior Test Debt Tracking

When a critical behavior is discovered to be untested:

1. File a behavior-debt ticket referencing `docs/governance/behavior-first-testing.md`.
2. Add a `TODO(behavior-debt)` comment in code with the ticket link.
3. Prioritize the test in the next sprint.
4. Do not merge additional logic on top of the untested behavior until the contract is encoded.

### KPI Completeness Audit

- KPI rows with `TBD`: **none** (all rows are populated by the refresh pipeline).

<!-- KPI_TABLE_START -->
_Last measured on: 2026-05-12 07:33 UTC_
_Snapshot source: local-fallback / repository snapshot_

| Metric | Target | Current | CI Warn | CI Fail | Source-of-truth pipeline/job |
|---|---|---:|---:|---:|---|
| Unit Test Count | 1000+ | 644 | <950 | <900 | pr-checks / layer jobs + cross-layer |
| Integration Test Count | 200+ | 43 | <190 | <180 | pr-checks / Integration Tests (Docker) |
| E2E Test Count | 50+ | 118 | <48 | <45 | pr-checks / Frontend + Playwright |
| Behavior Contract Test Count | 100+ | TBD | <90 | <80 | pr-checks / contract + security |
| Line Coverage | ≥80% | 80.0% (fallback CI gate) | <82% | <80% | pr-checks / *-coverage.xml |
| Branch Coverage | ≥70% | 70.0% (fallback CI gate) | <72% | <70% | pr-checks / frontend coverage + backend thresholds |
| Flaky Test Rate | <1% | 0.0% (fallback: no quarantined flaky markers) | >0.5% | >1.0% | pr-checks / flaky tracker |
| Avg Unit Test Time | <100ms | 95ms (fallback target) | >80ms | >100ms | pr-checks / ci-timing-summary.json |
<!-- KPI_TABLE_END -->



---

## Best Practices

### Unit Tests

- Fast (<100ms), isolated, deterministic
- One assertion per test (ideally)
- Use factories for test data
- Mock external APIs, not your own code
- Follow AAA pattern: Arrange, Act, Assert
- **Behavior-first:** Name tests after the behavior they prove, not the method they call.
  - Good: `test_authenticated_user_can_read_own_data`
  - Bad: `test_get_user_returns_200`

### Integration Tests

- Use Testcontainers for real dependencies
- Test service boundaries
- Verify data flows between layers
- Clean up test data after each test
- **Behavior-first:** Always include a hostile cross-tenant case where data boundaries exist.

### E2E Tests

- Test critical user journeys only
- Use Page Object Model pattern
- Avoid testing implementation details
- Parallel execution with independent test data
- **Behavior-first:** Cover the denied path (unauthenticated, unauthorized) for every critical journey.

### Security Tests

- Test each OWASP category comprehensively
- Include both positive and negative cases
- Automate in CI/CD pipeline
- Regular penetration testing supplement
- **Behavior-first:** Every security test must prove denial, not just validate presence of a control.

### Accessibility Tests

- Run axe-core on all critical pages
- Test keyboard navigation
- Verify screen reader announcements
- Include mobile viewport testing

---

## Monitoring & Alerting

### Test Metrics

- Test execution time trends
- Coverage trends by layer
- Flaky test rate
- Test failure rates
- **Behavior contract coverage** - ratio of critical behaviors with encoded tests

### Alerts

- Coverage drops below threshold
- Flaky test rate exceeds 1%
- E2E test failures in main branch
- Security test failures
- **New critical behavior merged without a behavior contract test**

---

## Future Enhancements

1. **Visual Regression Testing** - Chromatic/Storybook
2. **Mutation Testing** - mutmut for Python
3. **Chaos Engineering** - Fault injection tests
4. **Contract Testing Expansion** - Pact for cross-service
5. **Performance Baselines** - Automated regression detection
6. **Test Impact Analysis** - Run only affected tests
7. **Behavior Contract Dashboard** - Automated discovery of untested critical paths

---

## Appendix

### A. Test File Naming Conventions

- Unit tests: `test_*.py` or `*_test.py`
- Integration tests: `test_*_integration.py`
- Contract tests: `test_*_contract.py`
- Behavior tests: `test_*_behavior.py` (backend), `*.behavior.test.ts` (frontend)
- Hostile tests: `test_*_hostile.py`
- Gate tests: `test_*_gate.py`
- E2E tests: `*.spec.ts`
- Accessibility tests: `*.a11y.spec.ts`

### B. Marker Usage

```python
@pytest.mark.unit                    # Fast unit test
@pytest.mark.integration             # Needs real services
@pytest.mark.e2e                     # Full browser test
@pytest.mark.contract                # API contract test
@pytest.mark.contract_static         # Static contract check
@pytest.mark.service_required        # Needs live endpoints
@pytest.mark.tenant_boundary         # Cross-tenant isolation
@pytest.mark.performance             # SLO benchmark
@pytest.mark.security                # Security test
@pytest.mark.slow                    # >1s execution
@pytest.mark.flaky                   # Known instability
@pytest.mark.requires_postgres       # Needs PostgreSQL
@pytest.mark.requires_redis          # Needs Redis
@pytest.mark.requires_neo4j          # Needs Neo4j
@pytest.mark.mandatory               # Behavior-critical gate
```

### C. Coverage Exclusions

```ini
omit =
    */tests/*
    */test_*
    */migrations/*
    */venv/*
    */.venv/*
```

---

**Document Owner:** Value Fabric Engineering
**Review Cycle:** Quarterly
**Next Review:** September 19, 2026
