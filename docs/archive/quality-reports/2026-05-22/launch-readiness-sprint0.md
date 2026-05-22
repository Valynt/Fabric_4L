# Launch Readiness — Sprint 0 Evidence Report

**Date:** 2026-05-18
**Environment:** Gitpod devcontainer — Python 3.11.15, Node 22.22.3, pnpm 10.18.1
**Infrastructure:** No live services (PostgreSQL, Redis, Neo4j not running in devcontainer)
**Canonical readiness:** [`docs/readiness/current.md`](../docs/readiness/current.md) — **97%**
**Blocker board:** [`docs/readiness/blockers.md`](../docs/readiness/blockers.md)

---

## Sprint 0 Objectives and Outcomes

| Objective | Status | Notes |
|---|---|---|
| Fix Layer 3 `VaultSourceNotSupportedError` (manager.py) | ✅ Done | Class defined; `_load_from_vault()` raises; 7 tests pass |
| Wire digest guard into environment-promotion CI | ✅ Done | Guard added before staging + prod deploy steps |
| Produce this report | ✅ Done | — |
| Create `docs/readiness/blockers.md` | ✅ Done | P0/P1/P2 board populated from audit evidence |
| Reconcile ROADMAP.md canonical-source note | ✅ Done | Note added; no percentage changed |
| Verify `kustomization.yaml` prod placeholder digests removed | ✅ Pre-existing | Confirmed clean by guard script |
| Verify `database.py` 501→422 + DeprecationWarning | ✅ Pre-existing | Confirmed by test suite |

---

## Commands Run

```bash
# R1 — Vault test verification
pytest services/layer3-knowledge/tests/test_vault_config_source.py -v --noconftest

# R2 — Digest guard verification
bash scripts/check-no-placeholder-digests.sh k8s/envs/prod/kustomization.yaml
bash scripts/check-no-placeholder-digests.sh k8s/envs/staging/kustomization.yaml

# make verify subset (available without full service stack)
make check-conflict-markers
make check-no-nul-bytes
make check-migration-heads
make check-readiness-consistency
make check-legacy-debt
make check-deprecations
make verify-structure
make check-workflow-matrix
```

---

## Test Results

### Layer 3 Vault Tests (Sprint 0 target)

```
pytest services/layer3-knowledge/tests/test_vault_config_source.py -v --noconftest
7 passed in 0.25s
```

| Test | Result |
|---|---|
| `test_vault_source_not_supported_error_is_runtime_error` | ✅ PASS |
| `test_vault_source_not_supported_error_message` | ✅ PASS |
| `test_vault_source_raises_not_returns_empty_dict` | ✅ PASS |
| `test_vault_source_error_message_names_source` | ✅ PASS |
| `test_vault_source_error_is_not_silent` | ✅ PASS |
| `test_vault_source_raises_runtime_error` | ✅ PASS |
| `test_env_source_type_still_works` | ✅ PASS |

### Full Suite Summary (from 2026-05-17 baseline — infrastructure unavailable for re-run)

| Suite | Total | Passed | Failed | Skipped | Errors | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| Root `tests/` | 2,810 | 2,009 | 384 | 317 | 95 | — |
| Layer 1 (ingestion) | 757 | 509 | 117 | 32 | 99 | 58.3% |
| Layer 2 (extraction) | 321 | 289 | 31 | 1 | 0 | 61.1% |
| Layer 3 (knowledge) | 439 | 395 | 41 | 1 | 3 | 43.7% |
| Layer 4 (agents) | 1,738 | 1,401 | 231 | 8 | 98 | 59.7% |
| Layer 5 (ground-truth) | 216 | 92 | 21 | 3 | 101 | 59.5% |
| Layer 6 (benchmarks) | 79 | 79 | 0 | 0 | 0 | **83.9%** |
| API service | 89 | 60 | 29 | 0 | 0 | 70.7% |
| Frontend (Vitest) | 1,615 | 1,515 | 100 | 0 | 0 | 39.7% stmts / 80.9% branch |
| **TOTAL** | **8,064** | **6,349** | **954** | **362** | **396** | — |

---

## Failure Classification

### Implementation failures (require code fixes)

| Suite | Count | Representative examples |
|---|---|---|
| Root `tests/` | ~150 | Architecture conformance (5 failures in `tests/arch/`), RLS enforcement regression, Redis cache isolation mock type error |
| Layer 3 | ~20 | Graph alias export missing (`GRAPH_FIELD_ALIAS_REMOVAL_VERSION`), Prometheus registry collision |
| Layer 4 | ~80 | Agent workflow logic, formula governance, tenant model |
| Frontend | ~100 | API contract mismatches, disabled extraction endpoint |

### Environment issues (infrastructure not running in devcontainer)

| Suite | Count | Root cause |
|---|---|---|
| Layer 1 | 99 errors | testcontainers/Docker unavailable — PostgreSQL, Redis not running |
| Layer 4 | 98 errors | testcontainers/Docker unavailable |
| Layer 5 | 101 errors | testcontainers/Docker unavailable |
| Root `tests/` | 95 errors | Same — infrastructure-dependent tests |

### Pre-existing unrelated failures (import topology / test infra)

| Count | Root cause |
|---|---|
| 17 collection errors | Import topology errors, missing modules (`layer2_extraction.integration.model_registry_client`), f-string syntax error in test file |
| ~22 tests | L3 tests designed to run from service root; `api.*`/`config.*` not resolvable under repo-root importlib mode |
| Layer 1 subdirs | `tests/contract/`, `tests/domain/`, `tests/security/` — conftest uses `from tests.api.conftest import ...` without `__init__.py` |

---

## make verify Subset Results

| Target | Result | Notes |
|---|---|---|
| `check-conflict-markers` | ✅ PASS | No merge conflict markers in tracked files |
| `check-no-nul-bytes` | ✅ PASS | No NUL bytes in tracked source/config files |
| `check-migration-heads` | ✅ PASS | Exactly one Alembic head per managed service (`alembic` binary missing — entrypoint contract check passed) |
| `check-readiness-consistency` | ✅ PASS | Canonical readiness percentages aligned |
| `check-legacy-debt` | ✅ PASS | Within baseline (86 DEPRECATED markers, 12 OBSOLETE, 1 legacy dir — all pre-existing) |
| `check-deprecations` | ✅ PASS | No overdue deprecation items as of 2026-05-18 |
| `verify-structure` | ❌ FAIL | Pre-existing: 2 pytest collection import errors; k8s secret manifest in `SECRET_INVENTORY.md` flagged by secret-risk pattern (documentation file, not a live secret) |
| `check-workflow-matrix` | ❌ FAIL | Pre-existing: `ModuleNotFoundError: No module named 'jwt'` in root `tests/conftest.py` — environment issue, not a Sprint 0 regression |
| `lint` | ❌ NOT RUN | `ruff` not installed in devcontainer PATH |
| `typecheck` | ❌ NOT RUN | `pyright`/`mypy` not installed in devcontainer PATH |

### Digest guard verification

```
bash scripts/check-no-placeholder-digests.sh k8s/envs/prod/kustomization.yaml
→ No placeholder digests found.  ✅

bash scripts/check-no-placeholder-digests.sh k8s/envs/staging/kustomization.yaml
→ ERROR: placeholder digest(s) found  ❌  (pre-existing — guard is working correctly)
```

The staging kustomization was never cleaned up. The CI guard now blocks staging promotion until `scripts/ci/prepare_kustomize_deploy.sh staging` is run with real digests. This is tracked as **P0-4** in the blocker board.

---

## Release Gate Status

| Gate | Status | Notes |
|---|---|---|
| No merge conflicts | ✅ GREEN | `make check-conflict-markers` passes |
| No placeholder digests (prod) | ✅ GREEN | Guard script confirms clean |
| No placeholder digests (staging) | 🔴 BLOCKED | Staging kustomization has placeholders — P0-4 |
| Readiness consistency | ✅ GREEN | `docs/readiness/current.md` is canonical at 97% |
| Architecture conformance (`gate-arch`) | 🔴 BLOCKED | 5 failures — P0-2 |
| RLS enforcement | 🔴 BLOCKED | NULL tenant_id regression — P0-1 |
| Redis cache isolation | 🔴 BLOCKED | False-green (AsyncMock type error) — P0-3 |
| Deprecation budget | ✅ GREEN | No overdue items |
| Migration heads | ✅ GREEN | One head per service |

**Overall gate verdict: 🔴 NOT READY FOR PILOT LAUNCH** — 4 P0 blockers remain open (P0-1 through P0-4).

---

## Sprint 0 Blockers Snapshot

Canonical board: [`docs/readiness/blockers.md`](../docs/readiness/blockers.md)

| Priority | Open | Closed this sprint |
|---|---|---|
| P0 | 4 | 1 (P0-0 merge conflicts — pre-existing resolution confirmed) |
| P1 | 6 | 0 |
| P2 | 10 | 0 |

**P0 open items:**
- P0-1: RLS enforcement test regression (NULL tenant_id visibility)
- P0-2: Architecture conformance suite (5 failures, blocks `gate-arch`)
- P0-3: Redis cache isolation false-green (AsyncMock type error)
- P0-4: Staging kustomization placeholder digests (CI guard now enforces this)

---

## Residual Risk

| Risk | Severity | Mitigation |
|---|---|---|
| `verify-structure` fails on `SECRET_INVENTORY.md` secret-risk pattern | Low | File is documentation, not a live secret; pre-existing finding |
| `check-workflow-matrix` fails due to missing `jwt` module | Low | Environment issue; not a code regression; install `pyjwt` in devcontainer to resolve |
| Staging placeholder digests block CI promotion | Medium | P0-4 tracked; `prepare_kustomize_deploy.sh staging` must be run before next staging deploy |
| Full `make verify` not runnable without `ruff`/`pyright` in PATH | Medium | CI environment has these tools; devcontainer setup gap, not a code issue |
