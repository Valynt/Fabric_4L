# Current Readiness P0 Remediation — 2026-06-01

**Date:** 2026-06-01
**Scope:** Remediate the four active P0 launch blockers identified in `docs/readiness/blockers.md` as of 2026-05-20.
**Outcome:** All four P0 blockers verified passing in the working tree. Readiness docs updated.

---

## Verification Summary

| P0 | Area | Initial State | Verification Command | Final Result |
|---|---|---|---|---|
| **P0-1** | Security / RLS | `blockers.md` listed as open | `pytest tests/security/test_rls_enforcement.py -q --no-mandatory-dep-check` | **26 passed** — already resolved in working tree |
| **P0-2** | Architecture | `blockers.md` listed 5 failures | `pytest tests/arch/ -q --no-mandatory-dep-check` | **35 passed** — required code fixes |
| **P0-3** | Security / Cache | `blockers.md` listed 14 failures | `pytest tests/cache/test_redis_tenant_isolation.py -q --no-mandatory-dep-check` | **16 passed** — required test patch path fixes |
| **P0-4** | Infra / K8s | `blockers.md` listed as open | `scripts/ci/test_placeholder_digest_detection.sh && scripts/ci/check-k8s-image-digests.sh` | **All pass** — already resolved in working tree |

---

## P0-1: Security / RLS — RESOLVED (docs stale)

### Reproduction
```bash
$ python -m pytest tests/security/test_rls_enforcement.py -q --no-mandatory-dep-check
====================================================================================== test session starts =======================================================================================
platform win32 -- Python 3.11.9, pytest-9.0.3, pluggy-1.6.0
collected 26 items

tests\security\test_rls_enforcement.py ..........................                                                                                                                           [100%]

======================================================================================= 26 passed in 1.74s =======================================================================================
```

### Root Cause
No code change required. Remediation migrations (`025`, `026`, `032`, `033`) in `services/layer4-agents/migrations/versions/` already use strict tenant equality in `upgrade()` with no `tenant_id IS NULL OR` clause.

### Files Changed
- `docs/readiness/blockers.md` — marked P0-1 resolved
- `docs/readiness/current.md` — updated status

---

## P0-2: Architecture Conformance — RESOLVED (required fixes)

### Before Fix
```bash
$ python -m pytest tests/arch/ -q --tb=line --no-mandatory-dep-check
FAILED tests/arch/test_canonical_module_sentinels.py::test_layer6_no_production_imports_via_value_fabric_namespace
FAILED tests/arch/test_canonical_module_sentinels.py::test_canonical_sentinel_paths_exist
FAILED tests/arch/test_canonical_module_sentinels.py::test_layer6_canonical_service_files_exist
FAILED tests/arch/test_tenant_architecture.py::test_tenant_scoped_sql_queries_are_guarded
FAILED tests/arch/test_tenant_architecture.py::test_tenant_scoped_models_define_tenant_identifier
FAILED tests/arch/test_async_session_only.py::test_no_sync_create_engine_in_service_runtime
FAILED tests/arch/test_no_merge_markers.py::test_no_merge_conflict_markers[>>>>>>>]
FAILED tests/arch/test_no_merge_markers.py::test_no_merge_conflict_markers[<<<<<<<]
FAILED tests/arch/test_no_non_runtime_imports.py::test_runtime_python_modules_do_not_import_non_runtime_roots
9 failed, 26 passed
```

### After Fix
```bash
$ python -m pytest tests/arch/ -q --tb=line --no-mandatory-dep-check
35 passed in 10.23s
```

### Root Causes & Fixes

| Failure | Root Cause | Fix |
|---|---|---|
| Merge conflict markers | `services/layer4-agents/src/adapters/value_fabric_api.py` and `services/layer4-agents/src/workflows/base.py` contained unresolved Git merge conflict markers | Resolved conflicts, kept canonical implementation |
| Layer 6 sentinel paths | `tests/arch/test_canonical_module_sentinels.py` pointed to pre-package-restructure paths (`src/api/main.py` instead of `src/layer6_benchmarks/api/main.py`) | Updated `SENTINELS` and `test_layer6_canonical_service_files_exist` to use correct paths |
| L4 tenant architecture config | `tests/arch/test_tenant_architecture.py` pointed to compatibility shim paths instead of canonical `layer4_agents` paths | Updated `TENANT_SCOPED_MODELS` and `TENANT_QUERY_GUARD_FILES` to canonical paths |
| Sync `create_engine` | `services/layer1-ingestion/src/shared/database.py` was a stale duplicate of the canonical file; baseline path was also stale | Removed dead duplicate `database.py`; updated baseline path in `config/ci/async_session_legacy_baseline.txt` |
| L6 production imports | `scripts/migrate_l6_test_imports_canonical.py` intentionally references old import paths in regex patterns | Added script to skip list in `test_canonical_module_sentinels.py` |

### Files Changed
- `services/layer4-agents/src/adapters/value_fabric_api.py` — resolved merge conflict
- `services/layer4-agents/src/workflows/base.py` — resolved merge conflict, removed stray markers
- `tests/arch/test_no_merge_markers.py` — added `.jr` and `reports` to exclusion list
- `tests/arch/test_canonical_module_sentinels.py` — updated Layer 6 canonical paths, added L6 migration script skip
- `tests/arch/test_tenant_architecture.py` — updated TENANT_SCOPED_MODELS and TENANT_QUERY_GUARD_FILES to canonical paths
- `services/layer1-ingestion/src/shared/database.py` — removed stale duplicate
- `config/ci/async_session_legacy_baseline.txt` — updated baseline path to match canonical file location

---

## P0-3: Redis Cache Tenant Isolation — RESOLVED (required fixes)

### Before Fix
```bash
$ python -m pytest tests/cache/test_redis_tenant_isolation.py -q --tb=line --no-mandatory-dep-check
FAILED tests/cache/test_redis_tenant_isolation.py::TestCacheKeyIsolation::test_entity_cache_keys_include_tenant_id
FAILED tests/cache/test_redis_tenant_isolation.py::TestCacheKeyIsolation::test_query_result_cache_is_tenant_scoped
FAILED tests/cache/test_redis_tenant_isolation.py::TestCacheKeyIsolation::test_cache_invalidation_is_tenant_scoped
FAILED tests/cache/test_redis_tenant_isolation.py::TestCachePoisoningPrevention::test_cache_key_injection_is_prevented
FAILED tests/cache/test_redis_tenant_isolation.py::TestCachePoisoningPrevention::test_wildcard_cache_invalidation_is_tenant_scoped
FAILED tests/cache/test_redis_tenant_isolation.py::TestCachePoisoningPrevention::test_tenant_cannot_poison_another_tenants_cache
FAILED tests/cache/test_redis_tenant_isolation.py::TestDegradedModeIsolation::test_cache_miss_does_not_leak_data
FAILED tests/cache/test_redis_tenant_isolation.py::TestDegradedModeIsolation::test_redis_connection_pool_does_not_leak_tenant_context
8 failed, 8 passed
```

### After Fix
```bash
$ python -m pytest tests/cache/test_redis_tenant_isolation.py -q --tb=line --no-mandatory-dep-check
16 passed in 0.90s
```

### Root Cause
The original `TypeError: '>=' not supported between instances of 'AsyncMock' and 'int'` was already fixed by `tests/cache/conftest.py::make_redis_mock()`. The remaining failures were caused by tests patching a non-existent module path (`value_fabric.layer3.api.cache.get_redis_client`). The actual cache module is imported as `src.api.cache` during test execution.

### Fix
Replaced all 8 occurrences of `"value_fabric.layer3.api.cache.get_redis_client"` with `"src.api.cache.get_redis_client"` in the test file.

### Files Changed
- `tests/cache/test_redis_tenant_isolation.py` — fixed patch paths

### Tenant Isolation Evidence Verified
All 16 passing tests assert the following security properties:
- Rate limit keys include `tenant_id` and are distinct per tenant
- Tenant A cannot exhaust tenant B's quota
- Counter state remains isolated when requests interleave
- Cache keys include `tenant_id`
- Cross-tenant cache read/write/invalidation is blocked
- Degraded mode (Redis unavailable) raises `RuntimeError` (fail-safe)

---

## P0-4: Staging Kustomize Digests — RESOLVED (docs stale)

### Reproduction
```bash
$ bash scripts/ci/test_placeholder_digest_detection.sh
--- Placeholder digest detection ---
  PASS: detects sha256:1111111111111111111111111111111111111111111111111111111111111111
  PASS: detects sha256:2222222222222222222222222222222222222222222222222222222222222222
  PASS: detects sha256:7777777777777777777777777777777777777777777777777777777777777777
  PASS: detects sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
  PASS: detects sha256:0000000000000000000000000000000000000000000000000000000000000000
  PASS: passes sha256:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
  PASS: passes sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef
  PASS: passes sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

--- Grep pattern test against prod kustomization.yaml ---
  PASS: prod kustomization has no placeholder digests

Results: 9 passed, 0 failed

$ bash scripts/ci/check-k8s-image-digests.sh
Checking for mutable image tags in production overlays...
  Checking k8s/overlays/production...
  Checking k8s/overlays/staging...
PASS: No mutable tags in production overlays
```

### Root Cause
No code change required. Both `k8s/envs/staging/kustomization.yaml` and `k8s/overlays/staging/kustomization.yaml` already contained real immutable SHA256 digests. `blockers.md` was stale.

### Files Changed
- `docs/readiness/blockers.md` — marked P0-4 resolved
- `docs/readiness/current.md` — updated status

---

## Readiness Docs Update

- `docs/readiness/blockers.md` — all P0 items marked resolved with evidence; last updated 2026-06-01
- `docs/readiness/current.md` — launch readiness updated to **CONDITIONALLY UNBLOCKED — service-backed skipped-test evidence pending**; all P0 local evidence captured; snapshot date 2026-06-01

The docs do **not** claim "fully production ready" or "final launch approved." Final sign-off is gated on service-backed validation of the 9 skipped tests.

---

## Final Gate Validation (End-to-End)

### Canonical Gate Command Run
```bash
$ make gate-arch
→ Gate: Architecture Conformance
35 passed in 11.35s
✅  gate-arch passed
```

### Targeted P0 Evidence Commands (Re-run Confirmation)
```bash
$ python -m pytest tests/security/test_rls_enforcement.py tests/arch/ tests/cache/test_redis_tenant_isolation.py -q --no-mandatory-dep-check --tb=line
77 passed in 12.53s

$ bash scripts/ci/test_placeholder_digest_detection.sh
Results: 9 passed, 0 failed

$ bash scripts/ci/check-k8s-image-digests.sh
PASS: No mutable tags in production overlays
```

### Bonus Fix: Migration Head Check
```bash
$ python scripts/ci/check_migration_entrypoints.py
[PASS] Migration entrypoint contract passed for all maintained layer services.
```

---

## Risk Assessment: Test-Only Fix Check

| Question | Answer |
|---|---|
| Were architecture fixes achieved only by weakening tests? | **No.** We resolved actual merge conflicts in 2 Python files, fixed stale canonical paths in sentinel config, updated tenant architecture test config to point to canonical implementations, and removed a dead duplicate `database.py`. Tests now validate real invariants. |
| Do Redis isolation fixes still validate real tenant boundaries? | **Yes.** The fix changed the patch target from a non-existent module (`value_fabric.layer3.api.cache`) to the actual module (`src.api.cache`). Tests still assert: tenant-scoped keys, cross-tenant read/write blocking, cache poisoning prevention, wildcard invalidation scoping, and degraded-mode fail-safe. |
| Does the merge-marker exclusion hide real source-code markers? | **No.** The `.jr` and `reports` exclusions only cover documentation/artifact directories. Runtime source files in `services/`, `tests/`, `scripts/` are still scanned. The test still caught markers in `services/layer4-agents/src/adapters/value_fabric_api.py` and `services/layer4-agents/src/workflows/base.py` before we fixed them. |
| Does the staging digest check validate all relevant paths? | **Yes.** `test_placeholder_digest_detection.sh` checks `k8s/envs/prod/kustomization.yaml`. `check-k8s-image-digests.sh` checks both `k8s/overlays/production/` and `k8s/overlays/staging/`. All paths verified. |
| Were any mutable tags introduced? | **No.** `check-k8s-image-digests.sh` found zero mutable tags (`:latest`, `:main`, `:dev`, `:master`, `:develop`) in production or staging overlays. |

---

## Final Gate Results

| Gate | Command | Result |
|---|---|---|
| **Canonical Architecture** | `make gate-arch` | **35 passed** |
| RLS Security | `pytest tests/security/test_rls_enforcement.py -q --no-mandatory-dep-check` | 26 passed |
| Architecture | `pytest tests/arch/ -q --no-mandatory-dep-check` | 35 passed |
| Redis Cache Isolation | `pytest tests/cache/test_redis_tenant_isolation.py -q --no-mandatory-dep-check` | 16 passed |
| Staging Digest Guard | `bash scripts/ci/test_placeholder_digest_detection.sh` | 9 passed |
| Mutable Tag Guard | `bash scripts/ci/check-k8s-image-digests.sh` | PASS |
| Migration Heads | `python scripts/ci/check_migration_entrypoints.py` | PASS |
| DB Bootstrap Conformance | `python scripts/ci/check_db_bootstrap_conformance.py` | PASS |
| DB Production Readiness Split | `python scripts/ci/check_db_production_readiness_split.py` | PASS |
| Tenant Isolation Middleware | `pytest tests/security/test_tenant_isolation.py -q --no-mandatory-dep-check --timeout=60` | 4 passed, 9 skipped |
| Neo4j Tenant Write Enforcement | `pytest tests/security/test_neo4j_tenant_write_enforcement.py -q --no-mandatory-dep-check --timeout=60` | 17 passed |
| Rate Limit Middleware Regression | `pytest tests/test_tenant_rate_limiting.py::TestTenantRateLimitMiddleware -q --no-mandatory-dep-check --timeout=60` | 1 passed |

---

## Service-Backed Validation Required Before Final Sign-Off

The following tests were **skipped** because local PostgreSQL and Redis services are not available in the bare development environment used for this session. They **must** be run in a service-backed CI or staging environment before final production readiness sign-off:

| Test File | Skipped Tests | Reason | Required Environment |
|---|---|---|---|
| `tests/security/test_tenant_isolation.py` | Cache isolation tests (3) | Redis unavailable locally | `docker compose up redis` |
| `tests/security/test_tenant_isolation.py` | RLS enforcement tests (3) | PostgreSQL unavailable locally | `docker compose up postgres` |
| `tests/security/test_tenant_isolation.py` | Endpoint-dependent tests (3) | Full app routes not mounted | Complete app with routes |

**Required outcome:** Run these tests in CI/staging with PostgreSQL, Redis, and app services available. All skipped tests must either pass or be explicitly justified with environment evidence.

---

## Status

**All documented P0 blockers have passing local evidence or have been verified resolved in the current working tree.**

**Launch Readiness: CONDITIONALLY UNBLOCKED — service-backed skipped-test evidence pending.**

### What is resolved
- **P0-1 RLS**: `make gate-arch` component + `pytest tests/security/test_rls_enforcement.py` pass (26/26).
- **P0-2 Architecture**: `make gate-arch` passes (35/35). Merge conflicts resolved, canonical paths corrected, dead code removed.
- **P0-3 Redis Cache**: `pytest tests/cache/test_redis_tenant_isolation.py` passes (16/16). Patch paths corrected to actual module.
- **P0-4 Staging K8s**: Digest guard and mutable-tag guard both pass.
- **Bonus**: Layer 5 migration multi-head fixed; `check-migration-heads` passes.

### What remains outside P0 scope
The following gates fail for **pre-existing reasons unrelated to the P0 remediation**:
- `make gate-security` → `gate-mandatory-security-regression` fails because required security suites contain pre-existing `skip`/`xfail` markers (tracked as P1-6 in `blockers.md`).
- `make gate-database` → `tests/integration/test_cross_store_consistency.py` fails because it requires live Neo4j (integration test, not a P0 blocker).
- `make gate-security-broad` → Collection errors in security tests due to missing live service infrastructure.

These failures are **not caused by the P0 fixes** and are documented as P1/P2 backlog items.

### Required before final launch sign-off
Run the 9 skipped service-backed tenant isolation tests in CI/staging with PostgreSQL and Redis available. All skipped tests must either pass or be explicitly justified with environment evidence.

Do not mark as "fully production ready" or "final launch approved" until the skipped tests pass in a service-backed environment.
