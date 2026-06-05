---
title: "Canonical Build System"
category: "reference"
audience: "contributors"
last-reviewed: "2026-06-05"
freshness: "current"
related: ["./COMMANDS", "../../README", "../../CONTRIBUTING", "../../AGENTS"]
---

# Canonical Build System

Value Fabric uses a layered command hierarchy. The hierarchy is intentional so contributors, CI jobs, and AI agents use the same stable interfaces.

## Command Precedence

Use `make` for repo-wide build, test, migration, contract, release, and readiness workflows. The Makefile is the de facto build system and the canonical local interface for broad platform gates.

Use `pnpm` for JavaScript and TypeScript package management, frontend workspace scripts, root npm-script parity aliases, and local dev commands that need pnpm workspace resolution. This monorepo is pnpm-only; do not use `npm install`, `npm ci`, `yarn install`, or yarn lockfiles in canonical runtime/workspace directories.

Use direct Python CI runners only when debugging or reproducing a CI job that calls that runner directly. The main direct runner is `python scripts/ci/run_root_aggregate_checks.py <gate>`, which backs several root `pnpm` scripts. Direct helper scripts under `scripts/ci/` are implementation details unless they are listed in [COMMANDS.md](./COMMANDS.md), invoked by a documented Makefile target, or called out in workflow documentation.

## Public And Internal Interfaces

Public Makefile targets are targets with `##` help text and appear through `make help`. These targets are documented in [COMMANDS.md](./COMMANDS.md) and may be used by contributors, CI agents, and automation.

Internal implementation details include Makefile recipes without `##` help text, shell/Python helper scripts used inside documented targets, generated artifacts, and workflow-only commands that are not listed in the command map. Internal commands may change without notice.

Root `package.json` scripts are documented public npm-script interfaces. Most root scripts are thin wrappers around Makefile targets, Python CI runners, or package-level pnpm scripts. They do not define a separate build system.


## Runtime Version Matrix

Use the same runtime family across local development, CI, and container images to avoid version-drift failures. The intended matrix is:

| Runtime | Canonical version | Applies to | Source of truth |
|---|---:|---|---|
| Node.js | `22.12.0` or newer within the Node 22 LTS line | Local frontend tooling, pnpm workspaces, GitHub Actions `setup-node` jobs | Root `package.json` `engines.node` and workflow `node-version` entries |
| pnpm | `10.18.1` | Local installs, CI installs, Corepack activation | Root `package.json` `packageManager` and `corepack prepare pnpm@10.18.1 --activate` commands |
| Python | `3.11` | Local backend tooling, pytest, contract/governance CI jobs | Makefile interpreter selection and GitHub Actions `setup-python` jobs |
| Python container base | `python:3.11.13-slim-bookworm` | Maintained service Dockerfiles and full/uv service variants | `FROM python:3.11.13-slim-bookworm` in service Dockerfiles |

Policy notes:

- CI should pin Node setup jobs to `22.12.0` rather than a moving major alias or Node 24 unless the root engine and local setup docs are intentionally upgraded together.
- CI should run Python governance, contract, and backend checks on Python 3.11 to match the supported service runtime family.
- Service Dockerfiles should use the shared Python 3.11 patch image above; update all service Dockerfiles together when refreshing the patch level.
- If a workflow needs a newer runtime for a one-off tool, document the exception in that workflow and in this matrix before merging the drift.

## Canonical Setup Flow

For first-time local setup, use one flow:

```bash
corepack enable
corepack prepare pnpm@10.18.1 --activate
pnpm install --frozen-lockfile
make setup
make migrate
make verify
```

Use `make bootstrap` only when you want the repo's one-command setup path, including Infisical-assisted environment export where configured.

## Canonical Validation Flow

For a normal PR, run the narrowest relevant target first and finish with `make verify` when feasible. Examples:

```bash
make test-layer4
make contract-tests
pnpm --dir apps/web run test
make verify
```

For docs-only command-map changes, run:

```bash
pnpm docs:check
python -m pytest tests/docs/
```

For CI parity debugging, use the exact command from [COMMANDS.md](./COMMANDS.md) or the workflow job. Examples:

```bash
python scripts/ci/run_root_aggregate_checks.py --list
python scripts/ci/run_root_aggregate_checks.py schema
pnpm test:isolation
```

## Related Documentation

- [Command Inventory](./COMMANDS.md) - Stable command map, Makefile target categories, and CI-to-local mappings.
- [Development Discovery Map](./DISCOVERY_MAP.md) - Issue-to-implementation routing by work type, source of truth, drift checks, validation, and evidence.
- [Contributing](../../CONTRIBUTING.md) - Contributor setup and PR process.
- [Agent Reference](../../AGENTS.md) - AI agent command and governance reference.
