---
title: "Canonical Build System"
category: "reference"
audience: "contributors"
last-reviewed: "2026-08-31"
freshness: "current"
related: ["./COMMANDS", "../../README", "../../CONTRIBUTING", "../../AGENTS"]
---

# Canonical Build System

Value Fabric uses a layered command hierarchy. The hierarchy is intentional so contributors, CI jobs, and AI agents use the same stable interfaces.

## Command Precedence

Use `make` for repo-wide build, test, migration, contract, release, and readiness workflows. The Makefile is the de facto build system and the canonical local interface for broad platform gates.

Use `pnpm` for JavaScript and TypeScript package management, frontend workspace scripts, root npm-script parity aliases, and local dev commands that need pnpm workspace resolution. This monorepo is pnpm-only; do not use `npm install`, `npm ci`, `yarn install`, or yarn lockfiles in canonical runtime/workspace directories.

Use direct Python CI runners only when debugging or reproducing a CI job that calls that runner directly. The main direct runner is `python scripts/ci/run_root_aggregate_checks.py <gate>`, which backs several root `pnpm` scripts. Direct helper scripts under `scripts/ci/` are implementation details unless they are listed in [COMMANDS.md](./COMMANDS.md), invoked by a documented Makefile target, or called out in workflow documentation.

## DP-3 Transition Policy

[ADR-047](../explanations/adr/ADR-047-task-graph-build-orchestration.md) accepts a strangler migration from the root Makefile to an Nx task graph behind a thin `fabric` facade. Until a task passes shadow parity and changes ownership, its documented Make target remains the compatibility contract and Make remains the current canonical interface.

The transition follows these rules:

- Do not add new orchestration logic to the root Makefile. New service behavior belongs in that service's `project.json`, `pyproject.toml` tooling configuration, or `package.json` script; the root delegates.
- Every task has exactly one implementation owner. An unmigrated task is Make-owned and `fabric` may delegate to Make. A migrated task is graph-owned and its Make compatibility target may delegate to `fabric`. A task must never delegate in both directions.
- Task-graph caching is disabled until inputs, outputs, environment dependencies, and side effects are explicitly classified and parity evidence proves it safe.
- Public Make targets are not considered unused merely because repository search finds no caller. Removal requires an announced deprecation, migration telemetry, and two full quarters of compatibility coverage.
- Required check names, release evidence paths, failure behavior, and GitHub/Depot command parity remain stable throughout the migration.

Phase A introduces no task-runner dependency. It establishes the complete target inventory, consolidates health-ratchet entry points, and adds control-plane drift checks. Phase B adds the facade and representative shadow tasks. Phase C transfers service-owned implementations incrementally. Phase D removes Make only after the sunset gates in ADR-047 have passed.

## Public And Internal Interfaces

Public Makefile targets are targets with `##` help text and appear through `make help`. These targets are documented in [COMMANDS.md](./COMMANDS.md) and may be used by contributors, CI agents, and automation.

Internal implementation details include Makefile recipes without `##` help text, shell/Python helper scripts used inside documented targets, generated artifacts, and workflow-only commands that are not listed in the command map. Internal commands may change without notice.

Root `package.json` scripts are documented public npm-script interfaces. Most root scripts are thin wrappers around Makefile targets, Python CI runners, or package-level pnpm scripts. They do not define a separate build system.


## Runtime Version Matrix

Use the same runtime family across local development, CI, and container images to avoid version-drift failures. The intended matrix is:

| Runtime | Canonical version | Applies to | Source of truth |
|---|---:|---|---|
| Node.js | `22.22.2` | Local frontend tooling, pnpm workspaces, GitHub Actions `setup-node` jobs | Root `package.json` `engines.node` and workflow `node-version` entries |
| pnpm | `10.18.1` | Local installs, CI installs, Corepack activation | Root `package.json` `packageManager` and `corepack prepare pnpm@10.18.1 --activate` commands |
| Python | `3.11` | Local backend tooling, pytest, contract/governance CI jobs | Makefile interpreter selection and GitHub Actions `setup-python` jobs |
| Python container base | `python@sha256:d1e9ca7c4e78d1e8ecadb5d44bfc8e956e7a65b659a9950f569f243d72b326d0` (`python:3.11-slim`) | Maintained service Dockerfiles and full/uv service variants | `FROM python:3.11-slim@sha256:...` (optionally prefixed with `docker.io/`) / `ARG BASE_IMAGE=python@sha256:...` |
| Node container base | `node@sha256:027911463b296bdaf6df82b5ccf2c6b290fee725d5fba6513a037ed019400625` (`node:22.12.0-alpine3.20`) | Frontend Dockerfiles | `FROM node@sha256:...` in `apps/web/Dockerfile*` |

Policy notes:

- CI should pin Node setup jobs to `22.22.2` rather than a moving major alias or Node 24 unless the root engine and local setup docs are intentionally upgraded together.
- Container base images are pinned to cryptographic manifest digests. When refreshing a patch level, update every service Dockerfile together and record the new digest in this matrix.
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

Use `make check-governance` when the change touches import topology, layer/provider boundaries, ownership or canonical-import registries, or shared-package logic. It composes those checks into one deterministic verdict and writes machine-readable evidence to `artifacts/governance/check-governance.json`. Its ratcheted leaves also run under `make check-health-ratchets`.

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

## ARM64 / Apple Silicon Local Development

To avoid QEMU emulation on Apple Silicon hosts, force native `linux/arm64` platforms by layering the opt-in override file on top of the standard dev stack:

```bash
pnpm env:dev  # generates .env.generated
docker compose -f infra/compose/docker-compose.dev.yml \
               -f infra/compose/docker-compose.arm64.yml \
               --env-file .env.generated up -d
```

The override applies `platform: linux/arm64` to every service defined in the partial dev stack (postgres, redis, neo4j, minio, keycloak, pgbouncer, layer2, layer2-worker, layer2-5, layer4, api-gateway, and frontend). The same override can be combined with `docker-compose.full.yml` for the full layer stack.

CI builds application images for both `linux/amd64` and `linux/arm64` and publishes a multi-arch manifest. Use `make docker-build-multi` to reproduce the multi-platform build locally with `docker buildx`.

## Related Documentation

- [Dev Containers and Cloud Workspaces](./DEV_CONTAINERS.md) - Canonical container rebuild, startup, secrets, persistence, ports, and recovery workflows.
- [Command Inventory](./COMMANDS.md) - Stable command map, Makefile target categories, and CI-to-local mappings.
- [Development Discovery Map](./DISCOVERY_MAP.md) - Issue-to-implementation routing by work type, source of truth, drift checks, validation, and evidence.
- [Contributing](../../CONTRIBUTING.md) - Contributor setup and PR process.
- [Agent Entry Point](../../AGENTS.md) - shared package map and links to scoped agent guidance.
