# Behavior-First Playwright Tests — Strict Edition

This directory contains **strict behavior-first E2E contracts** for the core user journeys. There are no soft assertions, no skip fallbacks, and no catch-and-ignore patterns. Every test either proves the contract or fails.

## Philosophy

Every spec encodes:

1. **Intended Allowed Behavior** — What must happen when a valid actor performs a valid action.
2. **Intended Denied Behavior** — What must happen when an invalid actor, invalid action, or out-of-scope request occurs.
3. **Expected Failure Mode** — Exact `data-testid`, exact status code, or exact redirect target.
4. **Cross-Layer Proof** — UI action → exact API payload → exact response → exact UI state.

## Operating Principle

> No critical behavior exists unless it is tested.

> Intended behavior passes. Unintended behavior fails. Untested behavior is not production-ready.

## Strict Rules

- **No `test.skip` fallbacks.** If the UI does not expose the required element, the behavior is missing and the test fails.
- **No `.catch(() => false)` swallowing.** Visibility assertions must succeed or fail the test.
- **No conditional branches.** `if (isVisible)` is not allowed. The element must be visible.
- **No fuzzy regex matching** when exact text or `data-testid` is available.
- **No `waitForTimeout` guessing.** Use explicit state assertions (`toBeVisible`, `toHaveURL`, `toBeDisabled`).
- **Exact API payload assertions.** Cross-layer tests assert the exact shape of the request payload.

## File Mapping

| File | Journey | Layers | Allowed Paths | Denied Paths |
|---|---|---|---|---|
| `j1-ingestion.behavior.spec.ts` | Domain Ingestion → Value Tree | L1 → L2 → L3 → Frontend | Submit domain, track job, explore tree | Empty input, invalid domain, cross-tenant leakage, unauthenticated |
| `j2-intelligence.behavior.spec.ts` | Intelligence Workspace | L3 → L4 → Frontend | View signals/drivers/evidence, agent synthesis | Unsupported claims, low-confidence flags, cross-tenant signals, unauthenticated |
| `j3-value-studio.behavior.spec.ts` | Value Studio Deliverables | L4 → L5 → Frontend | Tab navigation, formula result, approved export | Export before approval, invalid formula, unauthenticated, cross-tenant |
| `j4-governance.behavior.spec.ts` | Governance & Trust | L4 → L5 → Frontend | Decision traces, audit log, health monitor | Cross-tenant audit, missing provenance, degraded health, unauthenticated |

## Frontend `data-testid` Contract

The behavior tests require the frontend to expose the following stable `data-testid` attributes. If any are missing, the corresponding behavior test will fail closed.

| TestId | Location | Behavior Proven |
|---|---|---|
| `ingestion-submitted` | Command Center | Domain submission succeeded |
| `validation-error` | Forms (ingestion, value model) | Invalid input was rejected |
| `error-state` | Any page after backend failure | Failure mode is safe and visible |
| `agent-chat-input` | Intelligence Workspace | Agent stream input is available |
| `agent-send-button` | Intelligence Workspace | Agent stream can be triggered |
| `agent-refusal` | Intelligence Workspace | Agent refused unsupported claim |
| `low-confidence` | Signals list | Low-confidence signal flagged |
| `value-model-variable-input` | Value Studio → Value Model | Formula variable editable |
| `export-case-{caseId}` | Deliverables → Cases | Export action per case |
| `export-blocked` | Deliverables → Cases (draft) | Export denied for unapproved case |
| `provenance-list` | Governance → Traces detail | Provenance sources visible |
| `incomplete-provenance` | Governance → Traces list | Trace missing provenance is flagged |
| `degraded-state` | Governance → Health | Health degradation surfaced safely |
| `forbidden-state` | Access-denied pages | Forbidden state rendered |
| `not-found-state` | 404 pages | Not-found state rendered |
| `action-disabled` | Disabled primary actions | Action is visibly disabled |

## Naming Convention

```typescript
// Allowed behavior — exact outcome
test('user with <valid context> can <action> and <exact outcome>');

// Denied behavior — exact failure mode
test('user without <context> is denied with <exact testId/status/redirect>');
test('<invalid input> is rejected with 422 and validation-error testId');
test('cross-tenant <resource> is not visible to foreign tenant user');
```

## Running Behavior Tests

```bash
# Behavior tests only — mocked, deterministic, fast (no backend required)
pnpm exec playwright test e2e/behaviors/ --project=behaviors

# All behavior tests across projects
pnpm exec playwright test e2e/behaviors/

# Specific journey behavior
pnpm exec playwright test e2e/behaviors/j1-ingestion.behavior.spec.ts --project=behaviors

# Backend-integrated behavior validation
PLAYWRIGHT_LIVE_MODE=true pnpm exec playwright test e2e/behaviors/ --project=backend-integrated
```

## CI Wiring

Behavior tests run in the `behaviors` Playwright project and are executed by:

- `pnpm run test:e2e:behaviors`
- `make test-e2e-behaviors`
- The `behavior-tests` job in `.github/workflows/pr-checks.yml`

They are required to pass before merge.

## Relation to Other Test Suites

- **`e2e/journeys/`** — Chained golden-path journeys. Behavior tests complement them by proving denied paths and exact failure modes.
- **`e2e/contracts/`** — Page-level API contract tests. Behavior tests span pages and assert end-to-end state transitions.
- **`e2e/security/`** — Security-focused tests. Behavior tests include security denials but frame them as user workflow behavior.
- **`src/**/*.behavior.test.*`** — Vitest component/hook behavior tests. Playwright behavior tests prove the same invariants at the E2E layer.
