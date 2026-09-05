# Value Studio service guidance

`services/value-studio/` is a private TypeScript service workspace using Node.js, TypeScript, and Vitest.

## Local execution

```bash
pnpm --dir services/value-studio run typecheck
pnpm --dir services/value-studio run test
```

## Conventions

- Target the package's Node.js engine (`>=22.13.0`) and use the root pnpm workspace.
- Keep service tests deterministic and isolated from external systems.
- Preserve the private package boundary unless an explicit workspace integration requires a public package.
- Use typed interfaces at service boundaries and validate external data before use.

Read the repository root [`AGENTS.md`](../../AGENTS.md) and the [discovery map](../../docs/development/DISCOVERY_MAP.md) before cross-package or contract changes.
