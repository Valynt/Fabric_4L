# 4-Layer End-User Workflow Test Strategy

This directory contains the implementation of the 4-layer test strategy for the Fabric 4L platform. This strategy ensures that UI behavior aligns with backend contracts, tenant isolation invariants, and production reliability requirements.

## The 4 Layers

### Layer 1: UI Contract Tests (Isolated)

**Location:** `frontend/e2e/contracts/`
**Purpose:** Fast, deterministic verification that the UI renders correctly given a specific API response shape.
**Execution:** `make test-e2e-contracts`
**Characteristics:**

- Fully mocked API responses
- Tests isolated pages and components
- Validates route guards and UI state transitions

### Layer 2: Chained User Journeys (E2E)

**Location:** `frontend/e2e/journeys/`
**Purpose:** Verify that canonical business workflows function end-to-end across multiple pages and state changes.
**Execution:** `make test-e2e-journeys`
**Characteristics:**

- Tests chained actions (e.g., Login → Submit Domain → Wait for Job → Explore Value Tree)
- Can run against live backend (`PLAYWRIGHT_BACKEND_URL`) or in mock mode
- Validates cross-page state persistence and workflow lifecycles

### Layer 3: Backend Contract & Integration Assertions

**Location:** `tests/contract/test_journey_contracts.py`
**Purpose:** Verify that the backend APIs actually fulfill the contracts that the UI expects, and enforce tenant isolation.
**Execution:** `make test-backend-contracts`
**Characteristics:**

- Pairs 1:1 with the canonical user journeys
- Validates API response schemas against OpenAPI specs
- Enforces tenant isolation (Tenant A cannot see Tenant B data)
- Prevents the "UI passes but platform behavior is wrong" failure mode

### Layer 4: Reliability Realism (Load & SLOs)

**Location:** `tests/performance/k6/journey-load-test.js`
**Purpose:** Verify that the canonical journeys perform reliably under load and meet defined SLOs.
**Execution:** `make perf-test-journeys`
**Characteristics:**

- Simulates concurrent users executing the 5 canonical journeys
- Validates p95 latency thresholds and error rates
- Ensures workflow completion SLAs are met under queue pressure

## Canonical Journeys

We have defined 5 canonical user journeys that represent the core business value of the platform. See [CANONICAL_JOURNEYS.md](./CANONICAL_JOURNEYS.md) for detailed definitions.

1. **Domain Ingestion to Value Tree Exploration**
2. **Intelligence Workspace Synthesis**
3. **Value Studio Deliverable Generation**
4. **Governance and Trust Validation**
5. **Tier-Gated Access and Security**

## Temporary Backend Rollout Guards

Journey specs that validate newly introduced backend routes may use a **temporary route-availability guard** to keep CI intent explicit during phased rollouts.

- Current exception: `j25-harness-run-lifecycle.spec.ts` probes `/api/v1/agents/harness/runs` in live mode and skips only on `404` (route not registered yet).
- CI expectation while this guard exists: `j25` remains informative smoke coverage and does **not** hard-fail backend-integrated runs when `/v1/harness/*` is absent.
- Deprecation trigger: once `/v1/harness/*` is promoted into required backend-integrated CI coverage, `j25` must switch to hard-fail gating (matching journeys that use `requireBackendOrThrow`).

## Release Gate

The 4-layer strategy is integrated into the main `Makefile` as the `release-gate` target. This target must pass before any deployment to production.

```bash
make release-gate
```

This sequence runs:

1. Core Quality Gate (Lint, Typecheck, Unit Tests)
2. Agent Behavior Regression (Evals)
3. User-Journey E2E (Playwright + Backend Contracts)
4. Performance & Reliability (k6 Load Tests)
