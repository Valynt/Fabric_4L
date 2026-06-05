# Behavior-First Playwright Tests

This directory contains **behavior-first E2E contracts** for the core user journeys.

## Philosophy

Every spec in this directory encodes:

1. **Intended Allowed Behavior** — What must happen when a valid actor performs a valid action.
2. **Intended Denied Behavior** — What must happen when an invalid actor, invalid action, or out-of-scope request occurs.
3. **Expected Failure Mode** — Explicit error codes, safe defaults, redirects, or structured rejections.
4. **Cross-Layer Proof** — The test proves behavior through the full stack: UI → API → Persistence → UI.

## Operating Principle

> No critical behavior exists unless it is tested.

> Intended behavior passes. Unintended behavior fails. Untested behavior is not production-ready.

## File Mapping

| File | Journey | Layers | Allowed Paths | Denied Paths |
|---|---|---|---|---|
| `j1-ingestion.behavior.spec.ts` | Domain Ingestion → Value Tree | L1 → L2 → L3 → Frontend | Submit domain, track job, explore tree | Invalid domain, empty submission, cross-tenant leakage |
| `j2-intelligence.behavior.spec.ts` | Intelligence Workspace | L3 → L4 → Frontend | View signals/drivers/evidence, agent stream synthesis | Unsupported claims, low-confidence promotion, cross-tenant signals |
| `j3-value-studio.behavior.spec.ts` | Value Studio Deliverables | L4 → L5 → Frontend | Tab navigation, formula recalc, narrative gen, approved export | Export before approval, invalid formula, unauthorized access |
| `j4-governance.behavior.spec.ts` | Governance & Trust | L4 → L5 → Frontend | Decision traces, audit log, health monitor | Cross-tenant audit entries, missing provenance, unauthorized access |

## Naming Convention

```typescript
// Allowed behavior
test('user with <valid context> can <perform valid action> and sees <expected outcome>');

// Denied behavior
test('user without <required context> is <denied action> with <expected failure mode>');
test('<invalid input> is rejected with <expected error state>');
test('cross-tenant <resource> is not visible to <foreign tenant user>');
```

## Running Behavior Tests

```bash
# All behavior tests (mocked, fast)
pnpm exec playwright test e2e/behaviors/

# Specific journey behavior
pnpm exec playwright test e2e/behaviors/j1-ingestion.behavior.spec.ts

# With UI mode for debugging
pnpm exec playwright test e2e/behaviors/ --ui

# Backend-integrated behavior validation
PLAYWRIGHT_LIVE_MODE=true pnpm exec playwright test e2e/behaviors/ --project backend-integrated
```

## Relation to Other Test Suites

- **`e2e/journeys/`** — Chained golden-path journeys. Behavior tests complement journeys by explicitly encoding denied paths and failure modes.
- **`e2e/contracts/`** — Page-level API contract tests. Behavior tests span pages and assert end-to-end state transitions.
- **`e2e/security/`** — Security-focused tests. Behavior tests include security denial cases but frame them as user workflow behavior.
- **`src/**/*.behavior.test.*`** — Vitest component/hook behavior tests. Playwright behavior tests prove the same invariants at the E2E layer.
