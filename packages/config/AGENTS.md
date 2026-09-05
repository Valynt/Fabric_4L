# Shared configuration package guidance

`packages/config/` provides the shared TypeScript/Zod environment-validation schemas used by workspace applications.

## Local execution

```bash
pnpm --dir packages/config run typecheck
pnpm --dir packages/config run test
```

## Conventions

- Keep environment schemas typed and fail closed for missing or invalid values.
- Preserve the existing subpath exports (`env/backend`, `env/frontend`, `env/test`, and `env/shared`) when changing public modules.
- Prefer additive schema changes and update consumers when an environment contract changes.
- Use the root workspace package manager and lockfile; do not create package-local lockfiles.

Read the repository root [`AGENTS.md`](../../AGENTS.md) for workspace policy and the [discovery map](../../docs/development/DISCOVERY_MAP.md) before cross-package changes.
