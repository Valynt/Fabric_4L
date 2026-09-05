# Platform contract package guidance

`packages/platform-contract/` is the canonical source for cross-layer Python and TypeScript contract types, schemas, and contract tests. Read [`CONTRACT.md`](CONTRACT.md) before changing boundary behavior.

## Rules

- Keep tenant context, database-session, middleware, tool-boundary, agent-output, and frontend-state patterns aligned with `CONTRACT.md`.
- Prefer additive, compatibility-preserving contract changes. Do not silently change response shapes or generated types.
- Update the corresponding contract tests and generated artifacts through the documented generation workflow; do not hand-edit generated OpenAPI or TypeScript output.
- Check all affected service consumers and `contracts/` sources before changing a public symbol.
- Keep this package provider-agnostic and independent of `services/*`.

## Validation

```bash
make contract-tests
pnpm run check:api-types
make verify
```

The repository-wide routing and command guidance lives in [`../../AGENTS.md`](../../AGENTS.md), [`../../docs/development/DISCOVERY_MAP.md`](../../docs/development/DISCOVERY_MAP.md), and [`../../docs/development/COMMANDS.md`](../../docs/development/COMMANDS.md).
