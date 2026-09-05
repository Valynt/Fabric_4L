# Contract ESLint plugin guidance

`packages/eslint-plugin-fabric-contracts/` contains ESLint rules that enforce Value Fabric's canonical contract and architecture boundaries.

## Local execution

```bash
pnpm --dir packages/eslint-plugin-fabric-contracts run typecheck
pnpm --dir packages/eslint-plugin-fabric-contracts run lint
pnpm --dir packages/eslint-plugin-fabric-contracts run test
pnpm --dir packages/eslint-plugin-fabric-contracts run build
```

## Conventions

- Keep rules deterministic and focused on declared contract or import-boundary invariants.
- Add or update Jest tests for every rule behavior change.
- Preserve the CommonJS package output and public plugin exports.
- Do not weaken a rule to accommodate an invalid caller; update the canonical source or contract instead.
- Use the root workspace package manager and lockfile; do not create package-local lockfiles.

Read the repository root [`AGENTS.md`](../../AGENTS.md) and [`packages/platform-contract/CONTRACT.md`](../platform-contract/CONTRACT.md) before changing contract enforcement.
