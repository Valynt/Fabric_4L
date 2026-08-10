# AGENTS — apps/web (Frontend)

Scoped instructions for agents working in `apps/web/`. The root `AGENTS.md`
holds universal invariants and prohibited actions; this file adds only
frontend-specific rules. Read `DESIGN.md` (repo root) before any change here —
it is the frontend governance contract.

## Stack (do not add alternatives)

React, Vite, TypeScript, Tailwind, shadcn/ui, TanStack Query, Zustand (only
where existing state patterns require it). pnpm only — never npm or yarn.

## Rules

- Reuse existing shell/layout patterns: `PageShell`, `PageHeader`, shared card
  primitives, existing loading/empty/error states.
- Horizontal tabs inside major workspaces; right rail for detail panels and
  agent streams; drilldowns via overlays/drawers/right-side panels.
- Consume domain/view models, not raw API DTOs; keep DTO-to-domain mapping in
  adapters; validate network responses; avoid `any`.
- Use TanStack Query patterns for all server data.
- No new component libraries, icon systems, one-off colors, custom card
  wrappers, or vertical navigation.
- Organization switching must invalidate unsafe cached tenant state.

## Validation

```bash
pnpm --dir apps/web run lint
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run test
pnpm --dir apps/web run build
pnpm --dir apps/web run test:e2e        # mocked Playwright
pnpm --dir apps/web run test:prod-auth-bypass
```

Test behavior, not implementation details. Golden-path journeys live under the
`test:e2e:golden:*` scripts (see `release/v1/tasks/V1-GOLDEN-002.yaml`).
