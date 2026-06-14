# Launch Decision Artifact (Canonical)

- **Owner:** Release Management (Engineering)
- **Last Updated (UTC):** 2026-06-14
- **Scope:** Production launch go/no-go decision package for Value Fabric.
- **Aligned Runbook:** `docs/runbooks/deployment-rollout-and-rollback.md`
- **Primary Readiness Criteria Source:** `docs/readiness/current.md`
- **Current Posture:** **NO GO for Core GA** on `rc-2026-06-13-116815f3`. Repository-owned local gates pass and the local Docker live stack is healthy, but environment-dependent P0 runtime certification (Playwright, rollback, SSO/OIDC) is blocked or deficient, and P1 operational evidence is largely deferred. Pre-existing test-suite failures `R-2026-06-13-01` and `R-2026-06-13-02` remain open.

## 1) Consolidated Evidence Ledger

This table maps each launch criterion in `docs/readiness/current.md` to objective, auditable evidence.

| Launch criterion (`docs/readiness/current.md`) | Objective evidence artifact(s) | Verification command or source | Status owner |
|---|---|---|---|
| 1. `make verify` passes with no failing gate | `artifacts/release/gate-result.json`, CI job log for verify gate | `make verify` | Engineering |
| 1a. Repository-owned `make verify` sub-gates | Local evidence: `make lint` ✅, `make typecheck` ✅, `make security-smoke` ✅, `make verify-structure` ✅, behavior-readiness ✅, docs-harness ✅ | This sweep (2026-06-13) | Engineering |
| 1b. `make verify` blockers remaining | Pre-existing `tests/contract/` static failures (**R-2026-06-13-01**) and `make test` Layer 1 hang / Layer 3 failures (**R-2026-06-13-02**) | `make contract-tests`, `make test` | Engineering |
| 2. Contract lint + tool contract checks pass | `artifacts/release/gate-result.json`, contract-check step logs | `python scripts/ci/platform_contract_lint.py` + `python scripts/ci/check_tool_contracts.py` | Engineering |
| 3. Security smoke/regression checks pass | Security smoke-test CI logs, release summary | `scripts/ops/release-gate.sh` (security checks section); local: `make security-smoke` → 13 passed, 1 xfailed | Security |
| 4. Graph Query module gate passes on PR + release branches | `.github/workflows/graph-module-tests.yml` run summaries and coverage artifacts | GitHub Actions workflow execution on PR + release branch | Engineering |
| 5. Release gate report indicates no P0 blockers | `artifacts/release/gate-result.json`, `artifacts/release/summary.md` | `scripts/ops/release-gate.sh` + `scripts/ops/render-release-summary.sh` | Engineering + Product |
| 6. Launch readiness percentage aligned across canonical docs | `docs/readiness/current.md` and launch docs consistency checks | Docs review + release checklist validation | Product + Operations |
| Tenant isolation regression-free | Tenant isolation test reports and targeted logs | `pytest tests/security -k tenant` (or equivalent service-specific tenant suites) | Security + Engineering |
| L3 Neo4j tenant scoping hardened | 49/49 hostile cross-tenant tests pass (`tests/security/test_benchmarks_cross_tenant_isolation.py`, `test_variables_cross_tenant_isolation.py`, `test_models_cross_tenant_isolation.py`, `test_formula_governance_cross_tenant_isolation.py`); Neo4j schema migration `030_neo4j_tenant_id_constraints_and_indexes.py` created with idempotent NOT NULL constraints + indexes on 7 node labels; migration registry at `services/layer3-knowledge/src/migrations/MIGRATIONS.md` | `pytest tests/security/test_benchmarks_cross_tenant_isolation.py tests/security/test_variables_cross_tenant_isolation.py tests/security/test_models_cross_tenant_isolation.py tests/security/test_formula_governance_cross_tenant_isolation.py --no-mandatory-dep-check -q` → 49 passed | Security + Engineering |
| L3 import topology fixed | 14 previously-blocked test files now collect (55 tests); resolved: 12 git merge conflicts across layer3-knowledge/src, 4 bare `agents.base` imports, 3 bare `config` imports, `config/__init__.py` relative import, `TypedDict` namespace, missing `rdflib`/`neo4j`/`langgraph` deps in pytest venv, `app_monolith.py` shim, `_get_tenant_context` function; `pytest.ini` updated with `testpaths = services/layer3-knowledge`; `services/layer3-knowledge/conftest.py` updated with sys.path guard | `pytest tests/layer3/ tests/ci/test_layer3_settings_import_compat.py tests/performance/test_performance_optimizations.py tests/security/test_layer3_similarity_roi_tenant_isolation.py tests/security/test_neo4j_cross_tenant_write_isolation.py --collect-only --no-mandatory-dep-check -q` → 55 collected, 0 errors | Engineering |
| Live workflow validation passes | E2E critical-path smoke script at `scripts/e2e/critical_path_smoke.py`; artifact at `signoff-evidence/e2e/e2e-critical-path-20260614.json`; Playwright live P0 evidence in progress at `signoff-evidence/e2e/e2e-live-p0-20260613.json` | `python scripts/e2e/critical_path_smoke.py --host` against live stack; **PASS** `overall=pass`, `passed=12`, `failed=0` | Operations |
| Security regression suite stable | Security regression test artifacts | `pytest tests/security` | Security |
| Rollback readiness | Release rollback procedure + DB migration rollback tests | `python scripts/ci/verify_release_rollback.py` → **PASS** 8/8 | SRE + Engineering |

## 1b) Runtime Certification Evidence (2026-06-14)

Evidence collected against the local Docker staging surrogate for candidate `rc-2026-06-13-116815f3`.

| Criterion | Evidence artifact | Result | Notes |
|---|---|---|---|
| P0-001 — Playwright backend-integrated journeys | `signoff-evidence/p0-journeys-20260613.json` | **BLOCKED** | Legacy/mock-auth frontend crashes because `AuthContext`, `ClerkAuthBridge`, and `RootRedirect` call Clerk hooks outside `<ClerkProvider>`; seeded case `case-meridian-e2e-001` is missing. |
| P0-002 — Rollback / restore drill | `signoff-evidence/p0-rollback-20260613.json` | **ROLLBACK_PROCEDURE_DEFICIENT** | Image-only rollback of Layer 4 to the previous release-smoke image failed (`ModuleNotFoundError: No module named 'canonical'`); roll-forward recovery restored health and critical-path smoke passed. |
| P0-003 — Enterprise SSO/OIDC | `signoff-evidence/p0-sso-20260613.json` | **BLOCKED** | No IdP configured or deployed; OIDC/Clerk secrets empty. Unauthenticated requests fail closed with 401. |
| P1 operational evidence | `signoff-evidence/p1-operational-20260613.json` | **DEFERRED/PARTIAL** | 2 verified (auth fail-closed, critical-path smoke), 1 partial (metrics endpoints), 4 deferred (alert receivers, billing, live LLM, dashboards/log aggregation). |
| Local live-stack health | `signoff-evidence/e2e/e2e-critical-path-20260614.json` | **PASS** | All six layers `/health` and `/ready` return 200; critical-path smoke passes 12/0. |

## 1c) Final Recommendation

**Decision:** **NO GO for Core GA** on candidate `rc-2026-06-13-116815f3`.

**Evidence summary:**
- ✅ Repository-owned gates (`lint`, `typecheck`, `security-smoke`, `verify-structure`, behavior-readiness, docs-harness) pass.
- ✅ Local Docker live stack is healthy; critical-path smoke passes 12/0.
- ⚠️ Static rollback verifier passes, but runtime image-level rollback is not viable without a coordinated dependency rollback.
- ❌ P0-001 Playwright blocked by auth-provider mismatch and missing seed data.
- ❌ P0-002 Rollback drill shows deficient procedure.
- ❌ P0-003 SSO/OIDC blocked by missing IdP.
- ❌ `R-2026-06-13-01` and `R-2026-06-13-02` pre-existing test-suite failures remain open.
- ⏳ P1 operational evidence largely deferred.

**Required before next GO review:**
1. Resolve the legacy-auth Clerk hook boundary or run P0 Playwright in a Clerk-configured staging environment and add the missing `case-meridian-e2e-001` seed.
2. Rehearse and document a production-like rollback using immutable, version-pinned images (or a source+dependency rollback) and attach passing recovery evidence.
3. Configure an enterprise IdP and complete SSO/OIDC validation.
4. Close or obtain explicit waivers for `R-2026-06-13-01` and `R-2026-06-13-02`.
5. Exercise P1 operational items in a configured environment with provider credentials.

## 1d) Multi-Function Sign-Off Status

| Function | Owner | Sign-off status | Timestamp (UTC) | Notes |
|---|---|---|---|---|
| Engineering | _TBD_ | Pending | _TBD_ | Pending resolution of P0 runtime blockers. |
| Security | _TBD_ | Pending | _TBD_ | Pending SSO/OIDC and auth fail-closed validation in configured environment. |
| Product | _TBD_ | Pending | _TBD_ | Pending acceptance of launch scope reduction or blocker closure. |
| Operations | _TBD_ | Pending | _TBD_ | Pending rollback drill and observability evidence. |

## 1a) Phase 1 Implementation Evidence (2026-05-21)

### 1.1 L3 Neo4j Tenant Scoping Hardening

| Item | Status | Evidence |
|---|---|---|
| Neo4j schema migration (7 labels) | ✅ Created | `services/layer3-knowledge/src/migrations/030_neo4j_tenant_id_constraints_and_indexes.py` |
| Migration wired into deploy sequence | ✅ Added 2026-05-21 | `docker-compose.live.yml` service `layer3-neo4j-migrate` runs migration 030 before `layer3` starts (`depends_on: service_completed_successfully`); idempotent against repeat runs. |
| Migration registry | ✅ Created | `services/layer3-knowledge/src/migrations/MIGRATIONS.md` |
| Hostile tests — benchmarks | ✅ 13/13 pass | `tests/security/test_benchmarks_cross_tenant_isolation.py` |
| Hostile tests — variables | ✅ 12/12 pass | `tests/security/test_variables_cross_tenant_isolation.py` |
| Hostile tests — models | ✅ 12/12 pass | `tests/security/test_models_cross_tenant_isolation.py` |
| Hostile tests — formula governance | ✅ 12/12 pass | `tests/security/test_formula_governance_cross_tenant_isolation.py` |
| **Total hostile tests** | **✅ 49/49 pass** | `pytest tests/security/test_*_cross_tenant_isolation.py --no-mandatory-dep-check` |

### 1.2 L3 Import Topology Fix

| Item | Status | Evidence |
|---|---|---|
| Merge conflicts resolved | ✅ 17 files | `services/layer3-knowledge/src/` (12 files) + `services/layer5-ground-truth/src/` (5 files) |
| Bare import fixes | ✅ | `agents/*.py` (4 files), `analytics/*.py` (3 files), `api/routes/entities.py` |
| `config/__init__.py` relative import | ✅ Fixed | `from .manager` / `from .settings` |
| `TypedDict` namespace collision | ✅ Fixed | `rate_limiting/types.py` → `typing_extensions.TypedDict` |
| `app_monolith.py` shim | ✅ Created | `services/layer3-knowledge/src/api/app_monolith.py` |
| `_get_tenant_context` function | ✅ Added | `services/layer3-knowledge/src/api/routes/models_router.py` |
| `pytest.ini` testpaths | ✅ Updated | Added `services/layer3-knowledge` |
| `services/layer3-knowledge/conftest.py` | ✅ Updated | sys.path guard + namespace collision comment |
| **Collection result** | **✅ 55 collected, 0 errors** | Previously: 0 collected, 14 errors |
| Tests passing (of collected) | 39/55 pass | 14 pre-existing logic failures (cross-phase burn-down), 2 async fixture errors |

### 1.3 Live Cross-Layer E2E

| Item | Status | Evidence |
|---|---|---|
| Smoke script | ✅ Created | `scripts/e2e/critical_path_smoke.py` |
| Dry-run artifact | ✅ Committed | `signoff-evidence/e2e/e2e-critical-path-20260521.json` |
| Live stack run | ⏳ Pending | Requires `docker-compose -f docker-compose.live.yml up -d` + `python scripts/e2e/critical_path_smoke.py` |

### 1.4 Sign-off

| Item | Status |
|---|---|
| 1.1 complete | ✅ |
| 1.2 complete | ✅ |
| 1.3 script ready | ✅ (live run pending) |
| Eng countersignature | ⏳ Pending |
| Sec countersignature | ⏳ Pending |
| Product countersignature | ⏳ Pending |
| Ops countersignature | ⏳ Pending |

---

## 2) Go / No-Go Thresholds

Thresholds below are release-blocking unless explicitly waived by Engineering + Security + Operations.

### Mandatory pass/fail gates

- `make verify` = **PASS**.
- Contract lint and tool contract checks = **PASS**.
- Security smoke/regression checks = **PASS**.
- No unresolved **P0** blockers in release gate output.
- Tenant isolation tests = **PASS** (no cross-tenant read/write leak).
- Live workflow validation = **PASS** for critical launch journeys.

### SLO / burn-rate launch guardrails

During staged rollout and first post-release window:

- Error budget burn-rate must remain within predefined SRE alert thresholds for the release window.
- Any sustained high-severity burn-rate alert or sustained 5xx regression beyond agreed threshold is an automatic rollback trigger.
- Readiness/liveness probe failures that breach rollout SLOs are rollback triggers.

## 3) Rollback Triggers (Aligned to Deployment Runbook)

Rollback triggers are aligned to `docs/runbooks/deployment-rollout-and-rollback.md`.

Immediate rollback (or blue-green traffic switch-back) when any occurs:

1. Smoke checks fail post-deploy for any critical Layer 1–Layer 5 or frontend path.
2. Readiness or liveness probe instability persists after remediation window.
3. Error-rate/SLO dashboards show sustained regression above release threshold.
4. Security regression indicates authz/tenant isolation regression.
5. Contract drift causes client-facing response incompatibility.

Operational steps (runbook-consistent):

1. Freeze rollout.
2. Identify failing component via deployment/pod events and dashboards.
3. Execute rollback (`kubectl rollout undo ...`) or blue-green traffic switch-back.
4. Re-run smoke checks.
5. Escalate incident if issue persists.

## 4) Required Multi-Function Sign-Off

Launch cannot proceed without explicit sign-off from:

- Engineering owner
- Security owner
- Product owner
- Operations owner

| Function | Owner | Sign-off status | Timestamp (UTC) | Notes |
|---|---|---|---|---|
| Engineering | _TBD_ | Pending | _TBD_ | Pending resolution of P0-001, P0-002, and P0-003 runtime blockers. |
| Security | _TBD_ | Pending | _TBD_ | Pending SSO/OIDC and production-like auth fail-closed validation. |
| Product | _TBD_ | Pending | _TBD_ | Pending acceptance of launch scope reduction or blocker closure. |
| Operations | _TBD_ | Pending | _TBD_ | Pending viable rollback drill and observability evidence. |

## 5) Launch Execution Controls

### Branch freeze

- Freeze launch branch before production promotion.
- Permit only release-manager-approved fixes with traceable change control.

### Staged rollout

- Execute canary or blue-green strategy per runbook criteria.
- Validate post-stage health before increasing traffic.
- Keep rollback path pre-validated before each traffic step.

### Post-release monitoring

- Monitor predefined burn-rate/error-budget thresholds for the release watch window.
- Monitor probes, latency, error rate, and security anomaly signals.
- Declare launch complete only after watch window exits without rollback triggers.
