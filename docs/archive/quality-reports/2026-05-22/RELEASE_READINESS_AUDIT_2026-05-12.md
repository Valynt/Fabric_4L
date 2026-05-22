# Release Readiness Audit — Value Fabric

**Date:** 2026-05-12
**Auditor:** Cascade (full-platform audit)
**Scope:** All 6 layers, frontend, contracts, infra, security, tests, CI/CD, observability, docs
**Method:** Static review + CI workflow inspection + live validation on Windows host
**Prior baseline:** `reports/PRODUCTION_READINESS_ASSESSMENT_2026-05-05.md` (Conditional GO, controlled pilot)

---

## 1. Executive Verdict

**Controlled-pilot launch:** � **NO-GO** — **NEW CRITICAL BLOCKER**: Unresolved Git merge conflicts detected in 9 Python files. This was not present in the 2026-05-05 baseline and represents a code hygiene regression that blocks all validation and deployment.

**Broad GA:** 🔴 **NO-GO** — same GA blockers from prior assessment remain (OAuth, Celery sync queue, image digest pinning, full SLO/penetration testing). New evidence below adds merge-conflict resolution to the P0 list.

**Net change since 2026-05-05 (RE-AUDIT FINDINGS):**
- 🔴 **CRITICAL NEW**: **9 files with unresolved merge conflict markers** (`<<<<<<< ours`, `=======`, `>>>>>>> theirs`) — blocks parsing, testing, and deployment.
- 🔴 **CRITICAL NEW**: RLS enforcement test regression — `test_remediation_migrations_do_not_reintroduce_null_visibility` now fails (was 12/12 passing). Suggests a migration may have reintroduced NULL tenant_id visibility pattern.
- 🔴 **CRITICAL NEW**: Architecture test failures increased from 3 → 5. New failures detect merge markers and L3 runtime shim drift.
- ⚠️ Route auth inventory script crashes due to syntax error in `checkpoints.py` (merge conflict).
- ⚠️ Persistent: ~449 active deprecation/contract violations per `reports/CONTRACT_AUDIT_REPORT.md` (canonical compliance ~58%).
- ✅ Frontend remains stable: `apps/web` Vitest suite **118 files / 1,424 tests / 0 failures**.
- 📌 Contract debt concentration is uneven: tenant-context propagation (~200) and UI-state progression (~90) account for ~65% of known violations; prioritize these two tracks first to move compliance efficiently toward the ≥85% target.
- 📌 Contract debt concentration is uneven: tenant-context propagation (~200) and UI-state progression (~90) account for ~65% of known violations; prioritize these two tracks first to move compliance efficiently toward the ≥85% target.
- 📌 Contract debt concentration is uneven: tenant-context propagation (~200) and UI-state progression (~90) account for ~65% of known violations; prioritize these two tracks first to move compliance efficiently toward the ≥85% target.

---

## 2. Dimension Scorecard

| Dimension | Status | Rationale |
|---|---|---|
| Security & Tenant Isolation | � | RLS test regression: `test_remediation_migrations_do_not_reintroduce_null_visibility` failing (was passing). Merge conflicts in checkpoint routes block tenant-access validation. |
| CI/CD Enforcement | 🟡 | 51 workflows present; `prod-readiness.yml` profiles wired. `mandatory-security-regression` not yet a required status check; only 2 `continue-on-error: true` instances (1 advisory deprecation scan, 1 kind-cluster retry — acceptable). |
| Infrastructure / K8s | 🟡 | H-08 hardening complete on 10 deployments; **image digest pinning still open** (uses `:latest` w/ `imagePullPolicy: Always`). |
| Testing & Quality | � | Frontend 1,424/1,424 ✅; arch suite **5 failures** (was 3); Redis cache suite **14 failures (fixture bug)**; merge markers in `tests/contract/conftest.py` block contract tests. |
| Contracts | 🟡 | OpenAPI specs valid (7/7); 12 ESLint rules at `error`; canonical contract compliance ~58%; ~449 tracked violations. |
| Testing & Quality | 🟡 | Frontend 1,424/1,424 ✅; arch suite **3 failures**; Redis cache suite **14 failures (fixture bug)**; contract layer tests skip-by-default without live services. |
| Contracts | 🟡 | OpenAPI specs valid (7/7); 12 ESLint rules at `error`; canonical contract compliance ~58%; ~449 tracked violations (highest debt: tenant-context ~200, UI-state ~90, tool-boundary ~46, DB isolation ~43, middleware/auth ~42). |
| Testing & Quality | 🟡 | Frontend 1,424/1,424 ✅; arch suite **3 failures**; Redis cache suite **14 failures (fixture bug)**; contract layer tests skip-by-default without live services. |
| Contracts | 🟡 | OpenAPI specs valid (7/7); 12 ESLint rules at `error`; canonical contract compliance ~58%; ~449 tracked violations (highest debt: tenant-context ~200, UI-state ~90, tool-boundary ~46, DB isolation ~43, middleware/auth ~42). |
| Testing & Quality | 🟡 | Frontend 1,424/1,424 ✅; arch suite **3 failures**; Redis cache suite **14 failures (fixture bug)**; contract layer tests skip-by-default without live services. |
| Contracts | 🟡 | OpenAPI specs valid (7/7); 12 ESLint rules at `error`; canonical contract compliance ~58%; ~449 tracked violations (highest debt: tenant-context ~200, UI-state ~90, tool-boundary ~46, DB isolation ~43, middleware/auth ~42). |
| Frontend Governance | 🟢 | Vitest fully green; design system audit clean; outstanding TODOs are backend-blocked placeholders, not regressions. |
| Observability | 🟡 | Prom/Grafana/Alertmanager configs present; `gate-obs` advisory only; SLO monitoring is GA blocker. |
| Documentation & Runbooks | 🟢 | RUNBOOK, launch checklist, evidence paths complete; 0 broken links per Sprint 4 scan. |
| Packs Ecosystem | 🟢 | 4 packs (ai-technology, energy-utilities, financial-services, life-sciences) carry ontology + formulas + tests; `pack-manifest.json` present. |
| Supply Chain | 🟡 | gitleaks, Trivy, CycloneDX SBOM, ZAP, Bandit all wired; image digests not pinned. |
| **Code Hygiene** | 🔴 | **9 files with unresolved merge conflict markers** — blocks parsing, testing, and deployment. |

---

## 3. Live Validation Evidence (re-audit run)

Host: Windows 11, Python 3.14.4, pnpm 10.18.1, pytest 9.0.3.

| # | Command | Result | Notes |
|---|---|---|---|
| 1 | `python -m pytest tests/arch -q` | **5 failed / 21 passed** | See §4.1 (increased from 3 failures) |
| 2 | `python -m pytest tests/security/test_rls_enforcement.py` | **1 failed / 12 passed** | **REGRESSION**: `test_remediation_migrations_do_not_reintroduce_null_visibility` now failing (was 12/12 passing). |
| 3 | `python -m pytest tests/cache` | **14 failed / 0 passed** | Fixture defect: `AsyncMock` returned where int expected — see §4.2. |
| 4 | `pnpm --dir apps/web exec vitest run` | **1,424 passed / 0 failed (118 files)** | Stable — no change from prior audit. |
| 5 | `python .github/scripts/check_route_auth_inventory.py` | **CRASH — SyntaxError** | `services/layer4-agents/src/api/routes/checkpoints.py:16` has merge conflict marker `<<<<<<< ours`. |

Not run on this host (require Linux CI / live services / Docker stack):

- `make gate-chaos`, `gate-smoke`, `gate-obs`, `gate-agent` — these target dirs that emit "PLACEHOLDER" if absent (`Makefile:471–510`).
- `make gate-security` (full version invokes `bash scripts/ci/mandatory_security_regression_gate.sh` which assumes Bash + venv).
- `pytest tests/backend_integrated` — needs Postgres/Redis/Neo4j stack.

---

## 4. Findings by Severity

### 4.1 P0 — Release blockers for controlled pilot (RE-AUDIT FINDINGS)

**P0-0. Unresolved Git merge conflicts in 9 Python files.** Blocks all validation, parsing, and deployment.

- `services/layer4-agents/src/api/routes/checkpoints.py` — lines 16-25, 202-217, 395-399, 465-473 have conflict markers.
- `value_fabric/layer3/api/routes/compat_aliases.py`
- `tests/contract/conftest.py`
- `specs/value_fabric_api_interfaces.py`
- `specs/value_fabric_extraction_pipeline.py`
- `specs/value_fabric_ontology_schema.py`
- `specs/value_fabric_rdf_serialization.py`
- `specs/value_fabric_reference_models.py`
- `scripts/ci/check_layer3_wrapper_drift.py`

Recommended fix path:

1. Identify the branches involved in the merge conflict.
2. Resolve conflicts manually or with `git mergetool`.
3. Run `git add` for resolved files and complete the merge.
4. Verify no remaining conflict markers with `grep -r "<<<<<<< HEAD"`.

**P0-1. RLS enforcement test regression — remediation migration may have reintroduced NULL tenant_id visibility.** `tests/security/test_rls_enforcement.py::TestRLSPolicyStructure::test_remediation_migrations_do_not_reintroduce_null_visibility` now fails (was 12/12 passing in original audit). Test verifies that migration `026_fix_rls_null_tenant_policy.py` does not reintroduce the unsafe `tenant_id IS NULL OR` pattern. Failure suggests the pattern may have returned in newer migrations or the test itself needs updating.

Recommended fix path:

1. Run test with `-vv` to see which migration file is flagged.
2. Inspect `services/layer4-agents/migrations/versions/` for `tenant_id IS NULL OR` patterns.
3. Remove unsafe patterns or update test baseline if pattern is intentional for admin-only policies.

**P0-2. Architecture conformance suite has 5 failures (increased from 3).** Blocks `gate-arch` (a `blocking` gate per `.fabric/prod-gates.policy.yaml`).

- `tests/arch/test_canonical_module_sentinels.py::test_sentinel_compatibility_modules_are_shims_only` — `services/layer3-knowledge/src/api/models.py` carries implementation logic; canonical path is `value_fabric/layer3/api/models.py`. Violates `canonical-paths.yaml` policy.
- `tests/arch/test_tenant_architecture.py::test_layer5_truth_object_uses_tenant_id` — `services/layer5-ground-truth/src/layer5_ground_truth/models/truth_object.py:TruthObject` is missing `tenant_id` field. **Direct AGENTS.md §6 violation** (tenant-isolation invariant).
- `tests/arch/test_no_non_runtime_imports.py::test_runtime_python_modules_do_not_import_non_runtime_roots` — `value_fabric/layer3/api/app_monolith.py:571` has a syntax error (markdown bullet bleeding into docstring boundary), which cascades into AST scan failure.
- `tests/arch/test_layer3_runtime_shim_drift.py::test_layer3_runtime_shim_drift_script_passes` — **NEW**: L3 runtime shim drift detection failure.
- `tests/arch/test_no_merge_markers.py::test_no_merge_conflict_markers[>>>>>>>]` — **NEW**: Detects merge conflict markers in codebase.
- `tests/arch/test_no_merge_markers.py::test_no_merge_conflict_markers[<<<<<<<]` — **NEW**: Detects merge conflict markers in codebase.
- `tests/arch/test_tenant_architecture.py::test_layer3_required_api_dependencies_reject_missing_and_invalid_tenant` — **NEW**: L3 tenant dependency validation failure.

**P0-3. RLS test pyramid covers structure but Redis cache isolation gate is currently false-green.** `tests/cache/test_redis_tenant_isolation.py` — all 14 tests fail with `TypeError: '>=' not supported between instances of 'AsyncMock' and 'int'` (`packages/shared/src/value_fabric/shared/rate_limiting/tenant_rate_limiter.py:324`). Tenant cache isolation invariant is **untested in practice**. Test mocks must return `int` from `incr` instead of bare `AsyncMock`.

### 4.2 P1 — Pilot-expansion blockers

**P1-1. Mandatory security regression CI job not yet a required status check** (carried from 2026-05-05; still open per `fabric_audit/sprint4_launch_decision_package.md`). Configure in GitHub branch protection before any tenant onboarding.

**P1-2. Unauthenticated route outside allowlist.** `GET /workflows/{workflow_id}/state/errors` is reachable without auth and not present in `contracts/route-auth-allowlist.yaml`. Either add auth dependency or, if intentional for diagnostics, add explicit allowlist entry with rationale.

**P1-3. Contract test collection errors** in 4 L3 files (`test_entity_contract.py`, `test_l3_provenance_audit_contract.py`, `test_l3_route_alias_parity.py`, `test_layer3_graph_deprecation_contract.py`) prevent local contract-suite execution. Indicates import-time drift between contract test setup and current L3 code paths.

**P1-4. Schemathesis xdist instability.** `tests/contract` run crashed with `WorkerController has no attribute 'workeroutput'` — schemathesis pytest-xdist incompatibility. Either pin schemathesis/xdist versions or run schemathesis tests serially (`-p no:xdist` for that subset). Currently masks real failures.

**P1-5. Connection-pooling and ACID property tests still absent** (per `PRODUCTION_READINESS_ASSESSMENT_2026-05-05.md` §2.4). Required before multi-tenant GA.

**P1-6. P0 security test gaps** carried forward from 2026-05-05: GovernanceMiddleware resolution-order adversarial tests, RequestContext immutability, tier-aware isolation, audit event emission completeness.

### 4.3 P2 — Broad GA blockers

Carried forward from `PRODUCTION_READINESS_ASSESSMENT_2026-05-05.md` §6.3:

1. OAuth authorization flow for CRM integrations.
2. Background sync → Celery/Redis queue (currently `asyncio.create_task`).
3. Comprehensive E2E coverage for critical flows.
4. Dedicated `sync_jobs` history table.
5. Prometheus export for all metrics + full SLO/error-budget monitoring.
6. Disaster recovery rehearsal.
7. Penetration testing.
8. K8s image digest pinning + admission-time validation (Kyverno/OPA Gatekeeper).

### 4.4 P3 — Hygiene / drift

- Canonical contract compliance ~58% (~449 active violations) per `reports/CONTRACT_AUDIT_REPORT.md`. ESLint and CI gates are wired; remaining instances are in-flight migration backlog.
- Layer 4 service compliance score 45% — lowest of all layers; concentrate deprecation-migrator effort here.
- Frontend placeholder backlog (12 items, all backend-blocked) per `reports/FRONTEND_STABILIZATION_REPORT_2026-05-06.md` §1–3.
- 1 advisory `continue-on-error: true` in `contract-compliance.yml:560` on baseline deprecation debt scan — acceptable (warning mode, not on blocking gate).

---

## 5. CI Gate Enforcement Matrix

Cross-reference of `.fabric/prod-gates.policy.yaml` ↔ `Makefile` ↔ `.github/workflows/prod-readiness.yml`.

| Gate | Class | Make target | Workflow job | Local-runnable | Required check? |
|---|---|---|---|---|---|
| policy | blocking | `gates-validate-policy` | `setup` | ✅ | ❓ (verify branch protection) |
| lint | blocking | `lint-release` | (in `pr-checks.yml`) | ✅ | ✅ wired |
| arch | blocking | `gate-arch` → `pytest tests/arch` | `arch-conformance` | ✅ **currently FAIL (5)** | ✅ wired |
| security | blocking | `gate-security` → mandatory regression script | `security-isolation` | bash-only | ⚠️ **NOT yet required-check** |
| security-broad | advisory | `gate-security-broad` | (advisory) | ✅ | n/a |
| chaos | blocking | `gate-chaos` | `dependency-chaos` | needs `tests/chaos/` | ✅ wired |
| smoke | advisory | `gate-smoke` | `cross-domain-smoke` | needs live svc | n/a |
| state | blocking | `gate-state` → `pytest tests/state` | `state-consistency` | ✅ | ✅ wired |
| agent | advisory | `gate-agent` | `agent-provenance` | optional deps | n/a |
| obs | advisory | `gate-obs` | `observability-readiness` | needs k6 | n/a |
| release-policy | blocking | `gate-release-policy` | `release-policy` | needs artifacts | ✅ wired |
| sign-manifest | artifact | `gates-sign-manifest` | `release-policy` | ✅ | ✅ wired |
| summary | artifact | `gates-render-summary` | `prod-readiness-summary` | ✅ | ✅ wired |

**Non-default-blocking workflows still on watch list:** `mandatory-security-regression` (in `security-gates.yml`), `branch-protection-validation`, `openapi-drift-check`, `package-manager-policy`. None confirmed as enforced required checks from the workspace files alone — needs GitHub branch-protection settings inspection (out of scope locally).

---

## 6. Drift Register

| ID | Type | Item | Source |
|---|---|---|---|
| D-00 | **Code hygiene** | **9 files with unresolved merge conflict markers** | Re-audit grep scan |
| D-01 | Code/path | L3 models in compatibility path | `tests/arch/test_canonical_module_sentinels.py` |
| D-02 | Schema | L5 `TruthObject` missing `tenant_id` | `tests/arch/test_tenant_architecture.py` |
| D-03 | Code | Syntax error in `value_fabric/layer3/api/app_monolith.py:571` | arch suite |
| D-04 | Auth | Unauthenticated route not allowlisted | `route-auth-inventory` script |
| D-05 | Test infra | Schemathesis × pytest-xdist incompat | `tests/contract` run |
| D-06 | Test infra | AsyncMock fixture leak in cache tests | `tests/cache/test_redis_tenant_isolation.py` |
| D-07 | **Security** | RLS remediation test regression — NULL pattern may have returned | `tests/security/test_rls_enforcement.py` |
| D-08 | Contract backlog | ~449 deprecation instances | `DEPRECATIONS.md` / `CONTRACT_AUDIT_REPORT.md` |
| D-09 | Frontend↔backend | Extraction endpoint disabled (`L2-42`) | `apps/web/src/api/protocol/extraction.ts:66` |
| D-10 | Frontend↔backend | Entity creation not exposed by L3 | `apps/web/src/hooks/useEntities.ts:251` |
| D-11 | Arch | L3 runtime shim drift detection failure | `tests/arch/test_layer3_runtime_shim_drift.py` |
| D-12 | Arch | L3 tenant dependency validation failure | `tests/arch/test_tenant_architecture.py::test_layer3_required_api_dependencies_reject_missing_and_invalid_tenant` |

---

## 7. Accepted Risks (carry-forward)

- Pytest regression tests require project venv in CI (standard Python practice).
- `gate-chaos`/`gate-smoke`/`gate-obs` need live services or Litmus/k6 — exercised only in CI environments, advisory locally.
- Pilot launch limited to single-tenant or controlled cohort with elevated on-call until P1 list closes.

---

## 8. Remediation Plan

### M0 — Immediate (blocks all launches - merge conflicts must be resolved first)

| # | Task | Owner | Exit criteria | Validation command |
|---|---|---|---|---|
| M0-0 | **Resolve Git merge conflicts in 9 Python files** | All | `grep -r "<<<<<<< HEAD"` returns 0 matches | `grep -r "<<<<<<< HEAD" .` |
| M0-1 | Investigate and fix RLS remediation test regression | Layer 4 | `test_remediation_migrations_do_not_reintroduce_null_visibility` passes | `python -m pytest tests/security/test_rls_enforcement.py::TestRLSPolicyStructure::test_remediation_migrations_do_not_reintroduce_null_visibility -vv` |

### M1 — Pre-pilot (after merge conflicts resolved)

| # | Task | Owner | Exit criteria | Validation command |
|---|---|---|---|---|
| M1-1 | Fix arch failure: move L3 models to canonical path; add shim | Layer 3 | `pytest tests/arch/test_canonical_module_sentinels.py` green | `python -m pytest tests/arch/test_canonical_module_sentinels.py` |
| M1-2 | Add `tenant_id` to L5 `TruthObject` (model + Alembic migration + repo updates) | Layer 5 | `pytest tests/arch/test_tenant_architecture.py::test_layer5_truth_object_uses_tenant_id` green; existing L5 tests still pass | `python -m pytest tests/arch services/layer5-ground-truth/tests` |
| M1-3 | Repair `value_fabric/layer3/api/app_monolith.py:571` docstring/syntax | Layer 3 | AST scan passes | `python -m pytest tests/arch/test_no_non_runtime_imports.py` |
| M1-4 | Fix Redis cache tenant-isolation test fixtures (use real fakeredis or proper `AsyncMock(return_value=...)`) | Platform | 14/14 pass | `python -m pytest tests/cache/test_redis_tenant_isolation.py` |
| M1-5 | Add auth dep or allowlist entry for `GET /workflows/{id}/state/errors` | Layer 4 | Inventory script reports 0 unallowlisted | `python .github/scripts/check_route_auth_inventory.py` |
| M1-6 | Configure `mandatory-security-regression` as required status check on `main` and `release/*` | Release Mgr | Branch protection screenshot in `fabric_audit/` | n/a (GitHub UI) |

**Exit criteria for M1:** all `blocking` gates in `.fabric/prod-gates.policy.yaml` pass on a clean Linux CI run; no unallowlisted unauthenticated routes; required-check enforcement confirmed.

### M1 — Pilot expansion

| # | Task | Exit criteria |
|---|---|---|
| M1-1 | Resolve schemathesis × xdist crash (pin or `-p no:xdist` for schema tests) | `pytest tests/contract` runs to completion in CI |
| M1-2 | Repair 4 L3 contract collection errors | 0 collection errors in `tests/contract` |
| M1-3 | Land P0 security test gaps (GovernanceMiddleware order, RequestContext immutability, tier-aware isolation, audit emission completeness) | New test files green in CI |
| M1-4 | Resolve `docker-compose.backend-integrated.yml` build failure | `tests/backend_integrated` runs in CI |
| M1-5 | Add connection-pool exhaustion + ACID property tests | New tests green; documented in evidence bundle |
| M1-6 | Layer 4 deprecation migration sprint (lowest compliance: 45%) | L4 score ≥ 65%; tools throwing exceptions ≤ 5 |

### M2 — Broad GA

| # | Task | Exit criteria |
|---|---|---|
| M2-1 | Implement OAuth authorization flow for CRM integrations | E2E auth flows green; manual-token paths removed |
| M2-2 | Migrate background sync to Celery/Redis | `sync_jobs` history table populated; pod restart durability test |
| M2-3 | Image digest pinning + Kyverno/Gatekeeper admission policy | All deployments use `@sha256:` digests; admission denial test |
| M2-4 | Full SLO monitoring + error-budget alerting | Prom rules + Grafana dashboards committed; alert dry-run evidence |
| M2-5 | Disaster recovery rehearsal | RTO/RPO measured and documented |
| M2-6 | External penetration test | Report in `reports/security/` with remediation log |

### M3 — Post-GA hygiene

- Drive canonical contract compliance from 58% → ≥ 85%.
- Resolve frontend backend-blocked placeholders (12 items) once corresponding backends ship.
- Reduce `tests/contract` skipped-by-default count by adding contract-only fixtures that don't require full service stacks.

---

## 9. Evidence Index

- This audit: `reports/RELEASE_READINESS_AUDIT_2026-05-12.md`
- Prior assessment: `reports/PRODUCTION_READINESS_ASSESSMENT_2026-05-05.md`
- Sprint 4 launch package: `fabric_audit/sprint4_launch_decision_package.md`
- I-04 mandatory regression gate: `fabric_audit/i04_mandatory_security_regression_gate_evidence.md`
- Contract audit: `reports/CONTRACT_AUDIT_REPORT.md`
- Frontend stabilization: `reports/FRONTEND_STABILIZATION_REPORT_2026-05-06.md`
- Test assurance: `reports/ASSURANCE_REMEDIATION_REPORT.md`
- Gate infrastructure: `reports/GATES_INFRASTRUCTURE_AUDIT_2026-05-02.md`, `reports/GATE_GRADUATION_REPORT_2026-05-02.md`
- RLS NULL fix evidence: `services/layer4-agents/migrations/versions/018_add_rls_to_billing_tables.py:40` + `tests/security/test_rls_enforcement.py` (12/12)

---

*Audit generated 2026-05-12. Methodology: combined static review of `contracts/`, `apps/web/`, `services/`, `value_fabric/`, `.github/workflows/`, `Makefile`, `.fabric/prod-gates.policy.yaml`; live execution of arch / contract / cache / RLS pytest suites and full Vitest run on Windows host; CI workflow inspection for `continue-on-error` and gate wiring.*
