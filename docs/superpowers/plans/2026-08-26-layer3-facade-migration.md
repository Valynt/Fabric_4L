# Layer 3 Facade Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove and execute a staged reduction of the retained Layer 3 facade without changing tenant, authorization, provenance, startup, route, Neo4j, or fail-closed behavior.

**Architecture:** Keep `services/layer3-knowledge/src/` as the runtime source of truth. First establish an installable `layer3_knowledge.*` import surface and behavioral equivalence; then migrate callers by execution relevance, retaining explicit compatibility and negative tests until the removal gate is satisfied. No facade or wrapper is deleted as part of the proof phase.

**Tech Stack:** Python 3.11, setuptools/editable installs, FastAPI, Neo4j driver, pytest, Python AST, import-topology CI scripts.

**Spec:** `.jr/tickets/L3-FACADE-WRAPPER-MIGRATION.md`

## Global Constraints

- Preserve tenant-scoped graph access and fail-closed tenant handling.
- Preserve authorization context, provenance metadata, startup behavior, route/alias parity, and Neo4j behavior.
- Do not reintroduce `value_fabric.layer3_knowledge`.
- Do not reintroduce path-redirect behavior in `value_fabric.layer3`.
- Do not bulk-replace imports or patch targets before object-level equivalence is proven.
- Keep shim-contract, deprecated-namespace, compatibility, and negative tests outside the first test-only migration slice.
- Do not weaken CI allowlists or compatibility policy.
- Treat bare `api.*` and `db.*` imports as service-local compatibility dependencies until normalized.
- The first implementation PR must change no production semantics and must be independently revertible.

---

## Current Evidence and Disposition

The AST inventory found no active `value_fabric.layer3.*` or
`value_fabric.layer3_knowledge` import statements in the requested source and
test trees; remaining references are compatibility assertions, CI scanners,
documentation, or migration metadata. It found seven bare `api.*` imports and
two bare `db.*` imports:

| Occurrences | Files | Classification |
|---:|---|---|
| 2 | `services/layer3-knowledge/tests/test_neo4j_integration.py` | Layer 3 integration-test imports: `db.driver` |
| 2 | `tests/integration/test_pack_integration.py` | Cross-service test-only imports: `api.routes.pack_loader` |
| 3 | `tests/contract/test_probe_contract_shared.py`, `services/layer3-knowledge/src/api/__init__.py` | stale/mislocated test imports and service-local compatibility wrapper |

There are 283 relative imports across 103 Layer 3 source files. The service
tree contains `api`, `db`, and other top-level modules under `src`, but no
`layer3_knowledge/` package directory or packaging mapping. Consequently,
`import layer3_knowledge` fails from both repository root and the service
execution context with `ModuleNotFoundError`. This is a package-layout blocker,
not proof that the retained facade is removable.

The retained classifications remain:

| Surface | Disposition |
|---|---|
| Settings mixins | INTENTIONAL / RETAIN |
| Layer 4 database facade | INTENTIONAL / RETAIN |
| Value-flow state module | ARCHITECTURAL DESIGN REQUIRED |
| Layer 3 retained facade seam | REQUIRES MIGRATION PLAN |

## Canonical Target Map

| Retained or legacy path | Canonical target | Equivalence status |
|---|---|---|
| `value_fabric.layer3.*` | `layer3_knowledge.*` backed by `services/layer3-knowledge/src/` | Not proven; canonical package currently cannot import |
| `value_fabric.layer3.config` | `config.settings` (service-local today; future canonical module after package mapping) | Not proven; `config.py` is a compatibility marker |
| `value_fabric.layer3.api.dependencies` | `api.dependencies_secured` or the exact service-local dependency implementation | Not proven; wrapper and tenant behavior require runtime tests |
| `value_fabric.layer3.api.routes.entity_compat` | `api.routes.entities` | Delegation is explicit, but import and route-contract equivalence are not yet proven |
| `value_fabric.layer3.api.routes.compat_aliases` | `api.routes.query_search` and documented alias endpoints | Not a duplicate; deprecated aliases must remain until route parity and caller migration are complete |
| bare `api.*` under Layer 3 `src` and tests | `layer3_knowledge.api.*` after package mapping, or validated service-local `api.*` during transition | Not proven outside the current `src`-on-`sys.path` mode |
| bare `db.*` in Layer 3 tests | `layer3_knowledge.db.*` after package mapping | Not proven; integration collection also depends on optional Neo4j/testcontainers packages |
| `value_fabric.layer3_knowledge` | No replacement; namespace must remain absent | Intentionally forbidden |

The map distinguishes actual aliases from compatibility surfaces. In
particular, `compat_aliases.py` carries tenant-aware authorization, telemetry,
and route deprecation behavior; it must not be treated as dead duplication.

## Complete Caller Inventory

| Caller | Occurrence | Execution relevance | Migration treatment |
|---|---|---|---|
| `services/layer3-knowledge/src/api/__init__.py` | `api.dependencies`, `api.main`, `api.models` | Service-local compatibility wrapper | Retain until canonical package and startup proof |
| `services/layer3-knowledge/src/api/dependencies.py` | wrapper to dependency surface | Service-local compatibility wrapper | Retain; prove tenant and authorization parity first |
| `services/layer3-knowledge/src/api/routes/entity_compat.py` | re-export of `api.routes.entities` | Compatibility route wrapper | Retain; verify route-contract and import parity |
| `services/layer3-knowledge/src/api/routes/compat_aliases.py` | deprecated alias routes | Production runtime compatibility | Retain; not removable by namespace cleanup |
| `services/layer3-knowledge/tests/test_neo4j_integration.py:102,132` | `from db.driver ...` | Test-only, optional live integration | Candidate for first migration after canonical proof |
| `tests/integration/test_pack_integration.py:261,278` | `from api.routes.pack_loader ...` | Test-only, cross-service integration | Candidate only after proving this is Layer 3's pack loader and not a stale service import |
| `tests/contract/test_probe_contract_shared.py` | `api.routes.system` | Test-only but stale/mislocated Layer-6 reference | Exclude from first slice; resolve ownership separately |
| `scripts/ci/check_layer3_imports.py` | regexes, allowlists, dead-namespace rules | CI/tooling and generated/patch-target policy | Change only after caller migrations and removal-gate evidence |
| `tests/ci/test_shim_divergence.py` | public symbol parity checks | Compatibility contract test | Keep outside first slice |
| `tests/ci/test_deprecated_namespace_imports.py` | forbidden namespace assertions | Negative compatibility test | Keep outside first slice |
| `tests/contract/conftest.py` | Neo4j import shim and live-service gates | Test infrastructure | Keep until canonical import proof separates static and live requirements |
| `tests/security/conftest.py` and security suites | path setup and canonical/legacy patch targets | Security and patch-target compatibility | Migrate only after object-level target equivalence |
| source comments, docs, and migration metadata | legacy-path explanations | Documentation/governance | Update only with the corresponding migration batch |

No active production runtime import of `value_fabric.layer3.*` was found by
the AST inventory. That does not authorize deletion: the service-local
wrappers and bare imports remain reachable under the supported `src` path
execution mode.

## Blockers

1. **Package layout:** `services/layer3-knowledge/src` is a flat source root,
   not an importable `layer3_knowledge` package. Both required canonical import
   proofs fail with `ModuleNotFoundError`.
2. **Import mode:** bare `api.*` and `db.*` imports require the service `src`
   directory on `sys.path`; pytest importlib mode and repository-root
   execution do not guarantee that context.
3. **Optional dependencies:** Neo4j, testcontainers, embedding, Redis, and
   related dependencies can fail collection independently of import topology.
   Static contract collection currently installs a Neo4j shim and gates live
   tests.
4. **Circular re-exports:** compatibility modules re-export canonical
   service-local modules. Replacing them with absolute legacy imports can
   recreate cycles; `entity_compat.py` and `compat_aliases.py` require direct
   dependency-graph review.
5. **Patch-target identity:** changing a patch string is unsafe unless the
   patched object is the object looked up by the production module at runtime.
6. **Hidden startup reliance:** service startup may rely on `src` path
   manipulation and historical bare imports. Startup must be proven in a
   clean process before wrapper removal.

## Migration Dependency Order

1. **Canonical package proof:** add or validate packaging metadata and a
   canonical import smoke test without changing runtime behavior. If the
   package must be restructured, stop and create a separate package-restructure
   design before any caller migration.
2. **Behavioral equivalence fixtures:** prove startup, tenant context,
   authorization, provenance, route aliases, Neo4j access, and fail-closed
   behavior through canonical imports.
3. **Test-only import migration:** migrate only the smallest proven cluster;
   leave compatibility and negative tests unchanged.
4. **CI/tooling and patch-target migration:** update scanners and patch targets
   only after canonical object identity is demonstrated.
5. **Service-local wrapper migration:** replace `config.py`,
   `api/dependencies.py`, and other documented wrappers one at a time.
6. **Production runtime normalization:** migrate any newly proven production
   callers while preserving route and authorization contracts.
7. **Facade removal:** delete only after every removal-gate condition is green
   and an owner-approved removal decision is recorded.

## First Focused PR Proposal

There is no safe implementation PR yet because the canonical import prerequisite
is currently false. The smallest proposed first migration slice, once Task 1
below passes, is the Layer 3 integration-test import cluster:

- `services/layer3-knowledge/tests/test_neo4j_integration.py:102,132`
  - change `from db.driver import get_driver, reset_driver` to the proven
    canonical target;
  - preserve the real Neo4j container, driver reset, schema, loader, vector,
    and GraphRAG assertions;
  - run only when the existing integration dependencies are available.

This slice changes no production semantics, removes two bare compatibility
imports, has direct Neo4j behavior coverage, and is independently revertible.
`tests/integration/test_pack_integration.py` is deliberately not included:
its `api.routes.pack_loader` imports are cross-service and their ownership and
canonical target are not yet proven. Shim-contract, deprecated-namespace,
compatibility, security, contract, and negative tests remain outside this PR.

## Removal Gate

No retained facade or wrapper may be deleted until all conditions below are
true:

- zero production callers of the retained path;
- zero compatibility callers, except explicitly owner-approved retained aliases;
- zero CI/tooling references and zero legacy patch targets;
- canonical imports succeed from repository root and the supported Layer 3
  service execution context in a clean process;
- startup succeeds without facade path bootstrapping or unrecorded `sys.path`
  manipulation;
- canonical and compatibility objects have verified identity or behavioral
  equivalence where identity cannot be preserved;
- tenant-scoped graph reads and writes remain isolated;
- missing or invalid tenant context remains fail-closed;
- authorization context and provenance metadata remain present;
- route and deprecated-alias contracts remain green;
- Neo4j static and live validation is green under the appropriate dependency
  profile;
- security, contract, import-topology, shim-divergence, and deprecated-namespace
  checks are green;
- the CI allowlist is narrowed only after the corresponding callers are gone;
- an owner-approved removal decision and rollback path are recorded.

## Invariants and Validation Matrix

| Invariant | Evidence required before the next batch |
|---|---|
| Tenant-scoped graph access | Layer 3 tenant-query and hostile cross-tenant tests pass through canonical imports |
| Fail-closed behavior | Missing tenant/auth context tests reject access; no fallback-to-global behavior |
| Startup/import behavior | Clean repository-root and service-context import probes plus service startup smoke |
| Route/alias parity | Route-contract tests and deprecated alias tests pass without changing status, auth, telemetry, or response shape |
| Neo4j behavior | Static collection with shim and live integration profile both pass where dependencies exist |
| Architecture/import topology | `check_layer3_imports.py --strict` and import-topology tests remain green |
| Security coverage | Layer 3 tenant isolation, authorization, and graph write/read security tests remain green |
| Provenance | Existing provenance assertions continue to observe the same metadata through canonical modules |

## Planned Tasks

### Task 1: Establish canonical package import proof

**Files:**
- Inspect/Modify only after design approval: `services/layer3-knowledge/pyproject.toml`, `services/layer3-knowledge/setup.cfg`, or the repository's existing package metadata
- Test: `tests/arch/` or the existing Layer 3 import/startup test location selected by repository convention

**Interfaces:**
- Produces a clean-process proof that `import layer3_knowledge` and the
  canonical submodules resolve from repository root and service execution
  context.
- Produces an explicit dependency report distinguishing package-layout,
  optional-dependency, and circular-import failures.

- [ ] Run the two import probes before editing packaging:
  `python -c "import layer3_knowledge"` from repository root and from
  `services/layer3-knowledge`.
- [ ] Record the exact `ModuleNotFoundError` and confirm the failure is not
  caused by Neo4j or another optional dependency.
- [ ] Inspect existing package metadata and compare it with the flat `src`
  tree; do not create a namespace alias that relies on `value_fabric.layer3`.
- [ ] Add the smallest repository-native import smoke test only if an existing
  test does not already cover both contexts.
- [ ] Run the smoke test in both contexts and stop if package restructuring
  changes runtime import semantics.

### Task 2: Prove canonical behavioral equivalence

**Files:**
- Test: existing Layer 3 startup/import, tenant, route-contract, security, and Neo4j test files
- Inspect: `services/layer3-knowledge/src/api/dependencies.py`,
  `services/layer3-knowledge/src/api/routes/entity_compat.py`,
  `services/layer3-knowledge/src/api/routes/compat_aliases.py`

**Interfaces:**
- Produces fixtures that exercise canonical imports while retaining the
  existing tenant, authorization, provenance, route, and fail-closed assertions.

- [ ] Add or reuse a canonical import fixture that supplies authenticated
  tenant context and rejects missing context.
- [ ] Assert canonical graph reads/writes preserve tenant predicates and
  authorization checks.
- [ ] Assert provenance fields and route alias response/deprecation behavior
  are unchanged.
- [ ] Run the focused Layer 3 contract, security, startup, and Neo4j tests;
  document optional-dependency skips separately from regressions.

### Task 3: Migrate the first test-only cluster

**Files:**
- Modify: `services/layer3-knowledge/tests/test_neo4j_integration.py:102,132`
- Test: the same file, with its existing integration marker and skip behavior

**Interfaces:**
- Consumes the canonical package proof and equivalence fixtures from Tasks 1
  and 2.
- Produces two canonical test imports with no production-file changes.

- [ ] Change only the two `db.driver` imports to the exact canonical target
  proven in Task 1.
- [ ] Preserve the existing driver reset, container, schema, loader, vector,
  and GraphRAG assertions.
- [ ] Run the focused integration test with the existing dependency-aware
  marker; a dependency skip is acceptable only when it is the existing
  documented skip mode.
- [ ] Run the Layer 3 import-topology and relevant contract checks.
- [ ] Revert the slice independently if canonical target identity or startup
  behavior differs.

### Task 4: Migrate later caller batches

**Files:**
- Modify only the files enumerated by a fresh AST inventory after each prior batch
- Update: `scripts/ci/check_layer3_imports.py` only when references are proven obsolete

**Interfaces:**
- Each batch consumes the prior batch's green evidence and produces a
  separately reviewable reduction in compatibility debt.

- [ ] Migrate cross-service test imports only after ownership of
  `api.routes.pack_loader` is proven.
- [ ] Migrate CI/tooling references and patch targets only after canonical
  object identity is tested.
- [ ] Migrate service-local wrappers one at a time, preserving explicit
  compatibility tests.
- [ ] Migrate production imports last, with route, security, tenant, and
  provenance validation in the same PR.

### Task 5: Apply the removal gate

**Files:**
- Modify/delete only the retained facade and wrapper files named by the
  completed caller inventory
- Update: `.jr/tickets/L3-FACADE-WRAPPER-MIGRATION.md` and import-topology checks

**Interfaces:**
- Consumes all batch inventories and validation artifacts.
- Produces a narrowly scoped facade-removal change with an explicit rollback.

- [ ] Re-run the AST inventory and require zero unapproved callers, patch
  targets, and CI references.
- [ ] Run startup, contract, security, tenant-isolation, provenance, Neo4j,
  shim-divergence, deprecated-namespace, and import-topology checks.
- [ ] Narrow the CI allowlist only for references proven removed.
- [ ] Delete only the facade surface covered by the gate; do not remove active
  route aliases or intentional compatibility wrappers.

## Risks Explicitly Deferred

- Package restructuring required to expose `layer3_knowledge.*`.
- Ownership and migration of cross-service `api.routes.pack_loader` imports.
- Normalization of all 283 relative imports and all service-local bare imports.
- Security-suite patch-target migration.
- Removal of `config.py`, `api/dependencies.py`, `entity_compat.py`, or
  `compat_aliases.py`.
- Any change to Neo4j dependency installation or static import shims.
- Changes to CI allowlists, generated contracts, or compatibility policy.
- The value-flow state redesign and Layer 4 database facade disposition.

