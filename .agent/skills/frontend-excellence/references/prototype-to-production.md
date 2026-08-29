# Prototype → Production Pipeline

**Destination:** A production-quality frontend built from prototype markup/design that matches the v1 visually, is componentized cleanly, and wires to real backend contracts.

## Steps

1. **Inventory the prototype.** List every screen, its data needs, state transitions, error/empty/loading states, and interactions. Note which parts are actually agentic (stream, tool calls, approvals) versus plain CRUD.
2. **Extract design tokens before writing any component.** Pull colors, spacing scale, type scale, radii, shadows, breakpoints from the prototype into the design system (see `DESIGN.md` tokens when present; otherwise create semantic tokens — `bg-primary`, `text-muted-foreground` — never hard-code hex).
3. **Define the component tree.** Separate presentation from state:
   - *Page/route* — fetches data via hooks, owns loading/error/empty states, composes sections.
   - *Domain components* — product behavior, receive typed domain data + callbacks.
   - *UI primitives* — reuse `@/components/ui/*` and Fabric components before creating new ones.
4. **Model the data contract** (see `contract-first-api.md`). Define OpenAPI/JSON Schema *before* UI. Generate types from the spec; do not hand-write DTO types.
5. **Build hooks + adapters.** Every server interaction goes through a typed hook (TanStack Query) with a domain parser at the network boundary. Components never touch raw DTOs.
6. **Componentize the prototype screens.** Convert markup to the tree from step 3. Map each prototype interaction to a state transition (idle → loading → success | error | empty).
7. **Retrofit responsiveness + a11y** (see `checklists/responsive-a11y.md`) without breaking the desktop layout.
8. **Backfill behavior tests.** For every meaningful behavior: a passing test (allowed), a test that asserts denial when security-sensitive (tenant isolation, unauthenticated), and the expected failure mode — encoded as tests, not just code.
9. **Stub the agentic layer.** Where the UI shows agent output, define the tool schemas (see `tool-schema-design.md`) and streaming plumbing (see `streaming-and-realtime.md`) before wiring.

## Common Failure

**Copying prototype styles inline instead of tokenizing first.** Result: pixel drift, no dark mode, `space-y-*` + `bg-blue-500` soup that the design system rejects.

## Verification

```bash
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run lint
pnpm --dir apps/web run test
pnpm --dir apps/web run build
```