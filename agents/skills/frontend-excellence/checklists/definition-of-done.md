# Definition of Done — Frontend Change Checklist

Run this before any frontend change is ready to ship. Every item is a **gate**:
if any box is unchecked, the change is not done.

## Correctness & Type Safety
- [ ] `pnpm --dir apps/web run typecheck` passes with no new errors
- [ ] No `any` casts added (repo rule — DTOs mapped via adapters, not `any`)
- [ ] Components consume domain/view models, not raw API DTOs
- [ ] Network responses validated at the boundary (Zod schema in the hook/adapter)
- [ ] Errors are explicit and contract-aligned (no silent fallbacks for user data)

## Lint & Format
- [ ] `pnpm --dir apps/web run lint` passes
- [ ] Prettier applied (`pnpm --dir apps/web run format`)
- [ ] No new design-token violations (semantic tokens, `gap` not `space-y-*`, no `dark:` overrides)
- [ ] No unused imports / dead code introduced

## Tests
- [ ] Unit/component test added or updated for new behavior
- [ ] Behavior named after intent (`test_user_can_edit_own_widget`), not method, no test removed without a replacement
- [ ] Denied/edge behavior tested (validation rejection, empty state, error state)
- [ ] `pnpm --dir apps/web run test` passes for touched areas

## Accessibility & Responsive
- [ ] Keyboard navigable (Tab order, focus visible, Enter/Space activates)
- [ ] ARIA roles/labels present where semantics are non-obvious
- [ ] No layout break at defined breakpoints (checked against prototype)
- [ ] Contrast and tap-target sizes meet baseline

## Build & Integration
- [ ] `pnpm --dir apps/web run build` (or `build:analyze`) succeeds
- [ ] No contract drift: OpenAPI specs, TS types, TanStack hooks, and consumers agree
- [ ] Query keys registered in the centralized registry (`hooks/queryKeys.ts`) — no ad-hoc key strings
- [ ] No dev-auth bypass flags enabled

## Verification
- [ ] `make verify` (or the relevant subset) passes
- [ ] Change reported with: what changed, validation run, residual risk

If anything is unverifiable locally, report *what*, *why*, and *residual risk* rather than checking the box.
