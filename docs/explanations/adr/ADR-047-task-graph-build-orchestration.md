---
title: "ADR-047: Task-Graph Build Orchestration"
category: "explanations"
audience: "advanced"
last-reviewed: "2026-08-31"
freshness: "current"
related: ["../../development/BUILD_SYSTEM", "../../development/COMMANDS"]
---

# ADR-047: Task-Graph Build Orchestration

**Status:** Accepted

**Date:** 2026-08-31

**Deciders:** Platform Architecture, SRE, and repository maintainers

## Context

The root Makefile is a 76 KB, Bash-bound control plane with 236 named targets, 233 of them public. It supports contributor workflows, CI, release certification, production-readiness gates, and evidence generation. Its size and global `.ONESHELL`/`/bin/bash` assumptions impose onboarding and portability costs, but an abrupt replacement would put required checks and release contracts at unacceptable risk.

At the decision baseline, GitHub and Depot each contain 55 paired workflows. Eight workflow files contain 47 executable direct Make calls spanning 24 target names; the workflow registry records 55 Make validation commands. Release certification adds 27 Make call occurrences across 22 target names, the launch contract declares 13 Make commands, and production policy names 32 unique targets. These are migration contracts, not evidence that the remaining public targets are unused.

The existing `check-health-ratchets` aggregate is a valuable policy boundary. Individual ratchets must remain callable for diagnosis while CI uses the aggregate entry point. Repository references do not prove that a public target is unused; external automation and developer usage require a measured deprecation window.

## Decision

Adopt Nx as the task-graph engine behind a dependency-free, repository-owned `fabric` command. Replace the root Makefile through a strangler migration, while keeping Make as a compatibility bridge until explicit sunset gates pass.

Nx is an execution engine, not the public interface. Contributors and automation use stable `fabric` task names. JavaScript and TypeScript implementations remain owned by workspace `package.json` scripts. Python service task metadata lives beside the service in `project.json`; `pyproject.toml` remains the source for Python tool configuration and installable Python entry points. Root configuration delegates rather than reimplementing service behavior.

### Ownership and delegation

Every task has exactly one implementation owner:

- `make`: the implementation remains in Make; `fabric` may delegate to it.
- `graph`: Nx invokes the service or package-owned implementation; the Make compatibility target may delegate to `fabric`.

The bridge rejects delegation cycles and fails closed on invalid or unknown routing state. There is no period in which Make and the graph maintain independent implementations of the same task.

### Migration phases

| Phase | Scope | Exit condition |
|---|---|---|
| A: inventory and convergence | Inventory every target; correct `.PHONY`; consolidate CI health ratchets; classify task-runner paths; enforce GitHub/Depot task-command parity. | Inventory and command documentation are exact; both PR workflows call `check-health-ratchets`; drift checks pass. |
| B: shadow bridge | Add Nx and the thin `fabric` facade; route representative static, Python, and frontend tasks in shadow mode; keep caching off. | Linux parity evidence and a native Windows job pass without Make, Bash, or WSL for the pilot set. |
| C: distributed ownership | Move service tasks into service/package metadata and migrate task cohorts one at a time; retain compatibility aliases. | Each migrated task has one owner, declared inputs/outputs, parity evidence, and rollback instructions. |
| D: sunset | Observe two full quarters of deprecation, remove direct callers, then remove the bridge and Makefile. | All CI and release paths pass with Make unavailable; telemetry shows no legacy use; release certification remains fail closed. |

The estimated 6-8 engineer weeks covers Phase A, the bridge, and the first 20 migrations. It does not cover complete retirement. Full sunset is a two-quarter elapsed-time outcome and is expected to require additional engineering effort.

### Initial task cohort

The first cohort favors deterministic, read-only leaves: conflict-marker and NUL-byte checks; Layer 1 and Layer 4 lint/typecheck/unit-test leaves; selected layer lint/typecheck leaves; Layer 4 boundary/canonical-path checks; deprecation checks; and package-owned frontend test/build tasks. Aggregates such as `lint` and `typecheck` become graph aliases after their leaves migrate.

Release, signing, evidence, production-readiness, security, migration, live database, Docker, environment bootstrap, generation, baseline-writing, cleanup, and destructive tasks remain Make-owned during the pilot. Frontend build remains shadow-only until CodeQL and workflow parity are proven.

### Cache policy

Nx caching is disabled by default. A task may enable caching only after all inputs, outputs, environment dependencies, secret handling, side effects, working directory, skip behavior, and artifact paths are declared and verified. Security, release, migration, live-environment, and evidence tasks are not cache candidates during the migration.

### Compatibility and validation

- Existing public task names and required-check contexts stay stable.
- GitHub and Depot workflow task commands migrate in lockstep.
- Shadow validation compares exit status, failure behavior, artifacts, environment/argument precedence, dependency order, and skip semantics.
- A Windows claim requires a native Windows CI job that runs the migrated set with legacy fallback disabled and without Make, Bash, or WSL.
- Release-factory migration is a separate P0 workstream. It must atomically preserve launch-contract commands, production policy IDs, release-step provenance, evidence schemas, and rollback behavior.
- A public compatibility command may be removed only after two full quarters of documented deprecation and evidence of no remaining use.

## Consequences

### Positive

- The root orchestration surface stops growing linearly with services.
- Task discovery, dependency ordering, and safe parallel execution become explicit.
- Native Windows execution becomes possible for migrated tasks.
- Service and package owners control their implementations while the root exposes a stable interface.

### Negative

- The bridge temporarily creates two user-visible entry points and requires strict cycle prevention.
- Nx adds a pinned repository dependency and lockfile maintenance.
- Shadow execution increases CI time until parity is established.
- Full migration takes longer than the initial implementation window because deprecation is intentionally bounded by release cycles.

### Neutral

- Make remains the current compatibility interface during Phases A-C.
- Leaf ratchets remain available even though CI uses the aggregate.
- Existing branch-protection check names do not change.

## Alternatives Considered

### Abrupt Makefile replacement

- Pros: shortest path to a single new interface.
- Cons: every developer, workflow, release gate, and hidden caller changes at once.
- Why rejected: late-discovered release and environment semantics would make rollback and parity unreliable.

### Keep and consolidate Make indefinitely

- Pros: lowest immediate migration cost and preserves muscle memory.
- Cons: retains Bash portability limits and lets the root god-object continue to grow.
- Why rejected: the recurring contributor and CI cost is unbounded.

### `just` or Go Task

- Pros: approachable, cross-platform command front ends with low setup cost.
- Cons: provide command organization but less native monorepo project-graph support and affected-task modeling.
- Why rejected: they improve syntax without fully addressing distributed ownership and graph execution.

### Custom task runner

- Pros: exact fit and no framework conventions.
- Cons: creates a scheduler, cache, graph, diagnostics, and portability subsystem the project must maintain.
- Why rejected: the long-term maintenance burden exceeds the thin-facade benefit.

### Turbo

- Pros: mature JavaScript monorepo task graph.
- Cons: the repository is a mixed Python/TypeScript platform and needs explicit non-package project modeling.
- Why rejected: Nx models heterogeneous projects without forcing Python services into JavaScript package semantics.

## Related

- [Canonical Build System](../../development/BUILD_SYSTEM.md)
- [Command Inventory](../../development/COMMANDS.md)
- [Superseded Make/pnpm unification plan](../../superpowers/plans/2026-06-17-unify-makefile-pnpm-entrypoints.md)
- `config/ci/make-task-inventory.json`
- `.github/paths-filters.yml`
