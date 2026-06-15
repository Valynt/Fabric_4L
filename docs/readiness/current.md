# Current Launch Readiness (Canonical)

- **Canonical Source:** This document is the single source of truth for launch readiness criteria and percentage.
- **Generated From CI:** `make verify` (lint, type-check, tests, contract tests, build gates) and release-gate evidence scripts.
- **Snapshot Date (UTC):** 2026-06-14
- **Last Updated:** 2026-06-14
- **Launch Readiness:** **NO GO for Core GA — RE-TESTABLE CANDIDATE** — repository-owned gates pass; runtime P0 evidence is now re-testable (auth crash fixed, rollback doctrine documented, local SSO/OIDC surrogate validated) and P1 operational evidence is largely deferred.

## Current Status

> ❌ **Core GA launch is not approved.** All repository-owned code gates are green, and the environment-dependent P0 runtime certification blockers are now converted into a **re-testable candidate** on the local Docker staging surrogate:
>
> 1. **P0-001 Playwright backend-integrated journeys — RE-TESTABLE.** The legacy-auth Clerk hook boundary crash is fixed and the missing `case-meridian-e2e-001` seed is present. J1 runs end-to-end (1/15 passing locally). The remaining 14 failures are frontend route/UX drift against tenant-scoped routes (e.g., `/settings/data/value-packs` vs `/t/:tenantSlug/settings/value-packs`), not runtime auth blockers.
> 2. **P0-002 Rollback/restore drill — RE-TESTABLE.** The image-only rollback drill failed as expected (`ModuleNotFoundError: canonical`). The rollback runbook now documents that safe rollback requires immutable commit-pinned images or coordinated source+dependency rollback. Layer 4 image is tagged `rc-116815f3` and `rollback-target`.
> 3. **P0-003 Enterprise SSO/OIDC — RE-TESTABLE.** A local Keycloak surrogate is running on port 8080 with the `fabric` realm; token issuance verified for `admin`/`admin` and `analyst`/`analyst` with `realm_access.roles`, `tenant_id`, and `org_id` claims. Real enterprise IdP integration remains environment-dependent.
> 4. Remediation of pre-existing `tests/contract/` static failures and `make test` Layer 1 / Layer 3 issues (see `docs/launch/launch-blocker-register.md` **R-2026-06-13-01** and **R-2026-06-13-02**).
> 5. P1 operational evidence (billing, alert receivers, live LLM, full telemetry dashboards) must be exercised in a configured staging/production-like environment.

| ID | Area | Status | Evidence |
|---|---|---|---|
| P0-001 | Playwright live backend-integrated journeys | ⚠️ RE-TESTABLE | `signoff-evidence/p0-journeys-20260613.json`; auth crash fixed, missing `case-meridian-e2e-001` seeded, remaining failures are frontend route/UX drift |
| P0-002 | Rollback / restore drill | ⚠️ RE-TESTABLE | `signoff-evidence/p0-rollback-20260613.json`; image-only rollback failed, recovery verified, viable rollback doctrine documented |
| P0-003 | Enterprise SSO/OIDC | ⚠️ RE-TESTABLE | `signoff-evidence/p0-sso-20260613.json`; local Keycloak surrogate validated, enterprise IdP integration still required |
| P1 matrix | Operational evidence | ⏳ DEFERRED/PARTIAL | `signoff-evidence/p1-operational-20260613.json`; 2 verified, 1 partial, 4 deferred |
| P0-1 | Security / RLS | ✅ Resolved | `pytest tests/security/test_rls_enforcement.py -q --no-mandatory-dep-check` passes 26/26 |
| P0-2 | Architecture | ✅ Resolved | `pytest tests/arch/ -q --no-mandatory-dep-check` passes 35/35 |
| P0-3 | Security / Cache | ✅ Resolved | `pytest tests/cache/test_redis_tenant_isolation.py -q --no-mandatory-dep-check` passes 16/16 |
| P0-4 | Infra / K8s | ✅ Resolved | `scripts/ci/test_placeholder_digest_detection.sh` passes 9/9; `scripts/ci/check-k8s-image-digests.sh` passes |
| R-2026-06-13-01 | Contract tests / `make contract-tests` | ❌ Open — pre-existing | Multiple `tests/contract/` static contract failures; blocks `make verify`. See register. |
| R-2026-06-13-02 | Unit tests / `make test` | ❌ Open — pre-existing | Layer 1 test hang + Layer 3 collection/runtime failures; blocks `make verify`. See register. |
| Local live-stack smoke | L1–L6 critical path | ✅ Verified | `python scripts/e2e/critical_path_smoke.py --host` with `E2E_SERVICE_AUTH_SECRET` → `overall=pass`, `passed=12`, `failed=0` (artifact: `signoff-evidence/e2e/e2e-critical-path-20260614.json`) |
| Security smoke | Fast PR gating | ✅ Pass | `make security-smoke` → 13 passed, 1 xfailed |
| Rollback readiness | Release rollback procedure (static) | ✅ Pass | `python scripts/ci/verify_release_rollback.py` → 8/8 passed |
>
> **Previously resolved:**
> - ✅ P0-0 — Merge conflict markers resolved
> - ✅ P0-004 — Deploy workflow now uses AWS OIDC auth + server-side dry-run + rollout checks
> - ✅ P0-008 — API gateway Alembic migration structure created
> - ✅ P0-010 — Readiness docs regenerated from live evidence

## Final Launch Decision

**Recommendation:** **NO GO for Core GA** on candidate `rc-2026-06-13-116815f3`.

**Rationale:**
- Repository-owned gates are green and the local Docker live stack is healthy.
- P0 runtime certification is now **re-testable**: the legacy-auth Clerk hook boundary crash is fixed, the missing `case-meridian-e2e-001` seed is present, the Playwright auth fixture seeds backend sessions correctly, the rollback runbook documents a viable rollback doctrine with version-pinned images, and a local Keycloak SSO/OIDC surrogate is validated.
- The remaining P0-001 gap is frontend test-route drift (not a runtime auth blocker); full closure requires either aligning J1 tests with the tenant-scoped UI or collecting staging evidence in a Clerk-configured environment.
- P1 operational evidence is incomplete (billing, alert receivers, live LLM, telemetry dashboards deferred).
- Pre-existing test-suite blockers `R-2026-06-13-01` and `R-2026-06-13-02` remain open.

**Path to approval:**
1. Align J1 test routes/selectors with the current tenant-scoped UI, or run P0 Playwright in a Clerk-configured staging environment, and collect retained JUnit/trace evidence.
2. Rehearse a coordinated image+dependency rollback (or version-pinned immutable-image rollback) in a production-like environment and attach passing evidence.
3. Configure an enterprise IdP (Keycloak/Clerk) and complete SSO/OIDC login/logout/tenant-mapping validation.
4. Close `R-2026-06-13-01` and `R-2026-06-13-02` or obtain explicit waivers.
5. Exercise P1 operational items in a configured environment with provider credentials.

## CI Evidence Inputs

- `make verify`
- `scripts/ops/release-gate.sh`
- `scripts/ops/render-release-summary.sh`
- `artifacts/release/gate-result.json`
- `artifacts/release/summary.md`
- `scripts/ci/platform_contract_lint.py`
- `scripts/ci/check_tool_contracts.py`
- `.github/workflows/graph-module-tests.yml` (Graph Query module quality gates on PR + release branches)

## Sprint Roadmap Progress (as of 2026-05-17)

| Sprint | Status | Key outcomes |
|---|---|---|
| S1 — Foundations | ✅ Complete | `PYTEST` var fixed to use pipx binary; `make setup` installs into pytest venv; root `pytest.ini` `addopts` scoped (removed `--timeout`/`--randomly-seed`); `CONTRIBUTING.md` updated |
| S2 — Core fixes | ✅ Complete | `get_openai_provider` mock → `get_llm_provider`; `Layer3KnowledgeClient` → `Layer3Client` import fixed (0-signal regression resolved); `HarnessRunRepository.list()` tuple handling verified; `CoreferenceResolver` verified implemented; `platform-contract` verified Pydantic v2 |
| S3 — Integration | ✅ Complete | Formula category filter verified implemented; k8s Kustomize overlay verified correct; Layer 4 secret names verified (`llm-provider-secret` + `TOGETHER_API_KEY`) |
| S4 — Release prep | ✅ Complete | Layer 3 Neo4j tenant isolation audit verified (see `docs/reference/layer3-tenant-isolation-audit.md`); `SqlTelemetryEmitter.get_events()` verified intentional `NotImplementedError`; readiness doc updated |
| S5 — Broad GA sprint | ✅ Complete (2026-05-19) | All 12 P0 + 11 P1 code blockers resolved; frontend 1773/1773 ✅; backend arch/cache/contract/unit 677/677 ✅; security P0/P1 suites 78/78 ✅; LLM cost telemetry 66/66 ✅; staging digests fixed; state inspector auth wired; assurance score ≥85% |

## Launch Criteria

The platform is launch-ready when all of the following are true:

1. `make verify` passes with no failing gate.
2. Contract lint + tool contract checks pass.
3. Security smoke tests pass.
4. Graph Query module gate passes on PR and release branches (coverage: lines ≥90%, branches ≥80%, functions ≥90%; flaky rate ≤1.0%; contract and performance jobs green).
5. Release gate report indicates no P0 blockers.
6. Launch readiness percentage remains aligned across canonical docs.

## Historical Snapshot Tagging

Any archived readiness note that includes percentages must include at least one of:

- `Historical Snapshot`
- `Snapshot Date:`
- Filename prefix `ARCHIVED_`

This allows automated checks to distinguish historical records from canonical readiness state.

## Decision Artifact

- Canonical launch decision package: `docs/readiness/launch-decision-artifact.md`
