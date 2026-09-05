# Value Fabric agent entry point

Value Fabric is a contract-first, multi-tenant platform with six backend layers, shared Python packages, and a React frontend.

## Start here

This file is the repository-wide routing layer, not the complete policy manual. Read the nearest nested `AGENTS.md` before changing a package or service, then load only the canonical guidance relevant to the task:

- [Build system](docs/development/BUILD_SYSTEM.md) — command precedence, supported runtimes, setup, and validation.
- [Command inventory](docs/development/COMMANDS.md) — public `make`, `pnpm`, and CI commands.
- [Discovery map](docs/development/DISCOVERY_MAP.md) — source-of-truth paths, drift checks, and focused validation by work type.
- [Platform Contract](packages/platform-contract/CONTRACT.md) — cross-layer context, database, boundary, and UI patterns.
- [Security and tenant isolation](docs/security/) — authentication, authorization, secrets, and tenancy controls.
- [Testing governance](docs/testing/) — test inventory, behavior contracts, and readiness requirements.
- [Governance](docs/governance.md) — architecture, ownership, compatibility, and evidence policy.
- [Release and operations](docs/operations/RELEASE_RUNBOOK.md) and [migration invariants](docs/reference/migration-reproducibility-invariants.md).
- [Frontend design contract](DESIGN.md) — required before changing `apps/web/`.

## Package manager and required gates

- This is a pnpm-only monorepo. Use pnpm `10.18.1` via Corepack; do not use npm or Yarn.
- Use `make` for repository-wide build, test, contract, migration, release, and readiness workflows.
- Use `pnpm` for JavaScript/TypeScript dependencies and workspace scripts.
- Run the narrowest relevant validation first. Before a PR, run `make verify`; for agent, prompt, or skill changes also run `make evals`.
- For contract changes, run `make contract-tests` and the applicable generated-type or breaking-change checks.

## Repository map

- `services/layer1-ingestion/` through `services/layer6-benchmarks/` — maintained backend layers.
- `services/api/` — API gateway and cross-layer auth/routing.
- `packages/shared/` — shared tenant, identity, model, and boundary utilities.
- `packages/platform-contract/` — canonical cross-layer contract types and tests.
- `apps/web/` — React/Vite frontend.
- `contracts/` — API, schema, event, and tool-manifest sources of truth.
- `docs/` — architecture, governance, testing, security, operations, and development references.

## Instruction hierarchy

Nested guidance is authoritative for its scope: `apps/web/AGENTS.md`, `services/*/AGENTS.md`, `packages/*/AGENTS.md`, and `docs/AGENTS.md`. `.windsurf/AGENTS.md` describes fleet coordination only and remains subordinate to this file and the nearest package instructions. Preserve tenant isolation, declared contracts, canonical source paths, and existing tests in every change.
