# UI Design Readiness

**Owner:** Frontend Platform  
**Status:** release gate evidence  
**Last updated:** June 16, 2026

## Readiness Definition

The frontend is design-ready when P0 and P1 workflows render with coherent shared layout, accessible controls, intentional loading/empty/error/restricted/success states, and responsive behavior across desktop, tablet, and mobile widths. Design readiness does not mean every future workflow is productized. It means release-significant paths do not hide broken states, fake success, weaken auth, or rely on placeholder copy.

This document complements `frontend-workflow-coverage-matrix.md`, Playwright journeys, Vitest coverage, accessibility scans, and the `test:ui-readiness` gate.

## P0 And P1 Expectations

| Area | Release expectation |
|---|---|
| Route shell | Uses the established sidebar, horizontal tabs where applicable, right rail where applicable, and shared page/header primitives. |
| Loading state | Uses an intentional status region with operation-specific copy and no infinite silent skeletons. |
| Empty state | Explains why no data is visible and gives the next useful action or states that the surface is not release-enabled. |
| Success state | Shows a truthful completed, saved, approved, or synced state backed by product data or deterministic mocks in test-only contexts. |
| Validation error state | Keeps user input, associates field errors with controls, and blocks invalid mutation before submission. |
| API failure and retry | Shows a recoverable error state with retry or navigation guidance without exposing raw secrets, stack traces, or cross-tenant data. |
| Unauthorized or restricted state | Explains access limits without bypassing route guards or displaying protected data. |
| Long-running job state | Shows queued/running/completed/failed semantics and does not present progress as complete until the workflow is complete. |
| Unsaved or partial state | Preserves recoverable user input and communicates incomplete workflow status. |
| Responsiveness | Keeps navigation, action bars, tables, dialogs, forms, and right rails usable at desktop, tablet, and mobile widths. |
| Accessibility | Primary CTAs, forms, tabs, dialogs, alerts, status badges, and route navigation are keyboard reachable and labeled. |

## Checklist

- P0 rows in `frontend-workflow-coverage-matrix.md` retain route, test evidence, persona, resilience, and accessibility proof.
- P1 rows retain route-family coverage and risk notes for design-sensitive workflows.
- Shared primitives exist for page shell, page header, empty state, loading state, error state, status badges, data tables, tabs, and dialogs.
- Critical E2E journeys do not use `test.skip`, `test.fixme`, backend skip valves, or placeholder-only assertions.
- Release-significant source paths do not include UI debt markers or broad "coming soon" copy.
- Accessibility checks remain wired through `test:a11y:components`, `test:a11y:pages`, and keyboard-flow coverage.
- `test:ui-readiness` passes before release sign-off.

## Commands

```bash
corepack pnpm --dir apps/web run check
corepack pnpm --dir apps/web run test:ui-readiness
corepack pnpm --dir apps/web run test:a11y:components
corepack pnpm --dir apps/web run test:e2e:guard
corepack pnpm --dir apps/web run verify:frontend
```

## What Blocks Release

- Fake success states, hidden backend failures, or silent redirects that mask incomplete workflows.
- Auth, tenant, or entitlement bypasses added to make a route appear ready.
- New P0/P1 `test.skip`, `test.fixme`, backend skip valves, or mock-only release gates.
- Undocumented placeholder markers in release-significant UI source, including `TODO_UI`, `FIXME_UI`, `PLACEHOLDER_UI`, lorem ipsum copy, or broad "coming soon" route copy.
- Missing loading, empty, error, restricted, or success-state expectations for a P0 workflow.
- Broken mobile navigation, clipped primary actions, horizontal page overflow, or dialogs that exceed the viewport.

## Acceptable Follow-up

- Non-release P2 surfaces may remain unproductized when they render an intentional empty or restricted state and are documented in the workflow matrix watchlist.
- Deep visual refinements may be deferred when the shared primitive is accessible, responsive, and covered by route/workflow tests.
- Live backend validation may be deferred when the local mock-mode gate is deterministic and live-mode validation is tracked separately.
- Product copy can be refined after release when it does not misrepresent workflow status or hide failure.

## Known Gaps

- Some academy detail surfaces are intentionally not release-enabled; they render explicit follow-up states and are not P0/P1 workflow owners.
- The UI-readiness gate is static and deterministic. It does not replace Playwright screenshot review for touched routes.
- P2 watchlist items in `frontend-workflow-coverage-matrix.md` still need expanded proof before they can become release-significant workflows.

## Ownership

Frontend Platform owns this gate and the shared primitives it checks. Domain teams own user-facing quality for their P0/P1 workflow rows. Any new release-significant route must update this document, the workflow coverage matrix, and the corresponding tests before it is treated as design-ready.
