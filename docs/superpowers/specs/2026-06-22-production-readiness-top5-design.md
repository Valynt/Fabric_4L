# Production Readiness — Top 5 Impactful Tasks

**Date:** 2026-06-22  
**Status:** Design approved by user (`looks good`)  
**Scope:** Bring the Value Fabric repo to production ASAP by unblocking the CI/release gate.

---

## Context & Assumptions

- Target: clean CI + buildable production deploy from `main`, full stack.
- Current environment: Node `v24.17.0` while the repo canon is Node `22.12.0`.
- The working tree has significant uncommitted drift (docker-compose relocations, CI script rewrites, new s2s-auth work). This plan assumes that drift is committed or reverted before remediation work begins.
- Validation run directly on the current tree:
  - `pnpm run verify:frontend` ❌
  - `pnpm run check:contract-compliance` ❌
  - `pnpm run check:api-types` ❌
  - `make verify-structure` ❌

---

## Design / Prioritized Task List

### Approach

Fix the **hard CI/build blockers first**, then clean up residual waivers. This is the fastest path to a green `make verify` and a deployable artifact.

---

### Task 1 — Fix the Frontend TypeScript Build Error

- **File:** `apps/web/src/hooks/usePersistFn.ts:20`
- **Error:** `Type 'unknown' is not assignable to type 'ReturnType<T>'`
- **Fix:** Cast the returned call as `ReturnType<T>`:
  ```ts
  return ((...args: Parameters<T>): ReturnType<T> => fnRef.current(...args) as ReturnType<T>) as T;
  ```
- **Why:** `pnpm run verify:frontend` is red; no production frontend build is possible.
- **Effort:** minutes.
- **Acceptance:** `pnpm run verify:frontend` passes TypeScript step.

---

### Task 2 — Fix Layer 3 OpenAPI Export / Prometheus Duplicate Counter

- **File:** `services/layer3-knowledge/src/services/compat_metrics.py`
- **Error:** `Duplicated timeseries in CollectorRegistry: {'layer3_deprecated_route_hits', 'layer3_deprecated_route_hits_created', 'layer3_deprecated_route_hits_total'}`
- **Fix:** Make `_get_or_create_counter` truly idempotent. Options:
  1. Module-level singleton so the counter is created once.
  2. Unregister any existing counter with the same name before `register()`.
- **Also resolve:** circular-import warning for `value_fabric.shared.security.config` (`is_strict_environment`).
- **Why:** Blocks `pnpm run check:contract-compliance`, a required CI gate and the source of truth for API drift.
- **Effort:** 1 day.
- **Acceptance:** `pnpm run check:contract-compliance` exports Layer 3 successfully.

---

### Task 3 — Restore API Type Generation

- **Root cause:** Local environment is Node `v24.17.0`; repo canon is Node `22.12.0`. `@redocly/openapi-core` fails with `TypeError: Cannot read properties of undefined (reading 'merge')` under Node 24.
- **Fix:** Align the runtime to Node `22.12.0` (recommended), or formally upgrade the repo and adjust pnpm overrides for `@redocly/openapi-core` / `js-yaml`.
- **Why:** `pnpm run check:api-types` fails; frontend types drift from backend contracts.
- **Effort:** 0.5–1 day.
- **Acceptance:** `pnpm run check:api-types` passes.

---

### Task 4 — Fix Structural Preflight

- **Findings:**
  - `hardcoded_db_credentials` in `infra/compose/docker-compose.e2e.yml`, `docker-compose.e2e-local.override.yml`, and `docker-compose.release-smoke.yml`.
  - False-positive `missing_tools_init` for `services/layer4-agents/src/layer4_agents/tools/__init__.py`.
- **Fix:**
  1. Replace hardcoded DB connection strings with `secretKeyRef` / env-file references.
  2. Update `scripts/ci/structural_preflight.py` allowlist or detection logic for the existing `__init__.py`.
- **Why:** `make verify-structure` (part of `make verify` and CI `structural-preflight`) is red.
- **Effort:** 0.5–1 day.
- **Acceptance:** `make verify-structure` passes.

---

### Task 5 — Resolve Behavior-Readiness Waivers Before 2026-09-07

- **File:** `config/ci/behavior_readiness_waivers.yaml`
- **Waivers:** `waiver-l2-import-infra` and `waiver-l3-import-infra`
- **Fix:** Fix L2/L3 test conftest/import chains so `test_cross_tenant_hostile_behavioral.py` tests can execute without pre-existing import-infrastructure issues.
- **Why:** The behavior-readiness audit is YELLOW only because of these waivers. After 2026-09-07 it flips RED.
- **Effort:** 2–4 days.
- **Acceptance:** `make check-behavior-readiness-audit` is GREEN with no active waivers, or with waivers renewed only for truly not-applicable cases.

---

## Quick Wins (Parallel)

- Fix `usePersistFn.ts` cast.
- Correct the `tools/__init__.py` false-positive in structural preflight.
- Commit or revert the unrelated working-tree drift (docker-compose relocations, CI scripts, s2s-auth work) before starting remediation branches.
- If Node 22.12.0 is chosen, pin `.nvmrc` / `package.json` engines.

---

## Decisions Required from User

1. **Frontend refactor intent:** finish the migration to `features/intelligence-workspace/tabs/`, restore deleted pages, or redesign route/tab registration?
2. **Node version:** downgrade runtime to Node 22.12.0 or officially upgrade the repo to Node 24?
3. **Layer 3 compat metrics:** keep and fix the Prometheus counters, or remove deprecation telemetry entirely?
4. **Working-tree drift:** commit the docker-compose relocations and s2s-auth work now, or revert to clean `main`?

---

## Acceptance Criteria for the Design

- `pnpm run verify:frontend` passes.
- `pnpm run check:contract-compliance` passes.
- `pnpm run check:api-types` passes.
- `make verify-structure` passes.
- `make check-behavior-readiness-audit` is GREEN or YELLOW with valid, non-expiring waivers.
- All changes are committed and the working tree is clean.

---

## Risks & Follow-Up

- The working tree is currently a moving target. Gating on an uncommitted state is unreliable; stabilize first.
- Node version mismatch may mask other incompatibilities. After downgrading/upgrading, re-run the full `make verify`.
- Layer 3 counter bug may reappear if exports are run in-process multiple times; prefer module-level singleton with defensive unregister.
