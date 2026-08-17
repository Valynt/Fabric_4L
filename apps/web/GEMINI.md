# Frontend Rules (apps/web)

This directory houses the React / Vite / TypeScript web application for Value Fabric.

## Requirements
- Always follow `DESIGN.md` located at the repository root.
- Use Tailwind CSS and shadcn/ui primitives.
- Strict TypeScript: No `any`. Explicit typing for props, state, and API responses.
- React components must consume domain/view models, NOT raw API DTOs.
- Map DTOs to view models in API adapter layers.
- Preserve the layout hierarchy: `PageShell` -> `PageHeader` -> Tabs / Right Rail.
- Verify changes with:
  ```bash
  pnpm --dir apps/web run typecheck
  pnpm --dir apps/web run lint
  pnpm --dir apps/web run test
  ```
