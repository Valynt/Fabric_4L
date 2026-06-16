# Current Launch Readiness (Canonical)

- **Canonical Source:** This document is the single source of truth for launch readiness criteria and percentage.
- **Generated From CI:** `make verify` (lint, type-check, tests, contract tests, build gates) and release-gate evidence scripts.
- **Snapshot Date (UTC):** 2026-06-15
- **Last Updated:** 2026-06-15
- **Launch Readiness:** **GO WITH ACCEPTED RISKS for Core GA** — all repository-owned code gates pass; the remaining P0/P1 items are environment-dependent and are formally tracked as accepted risks pending owner countersignature.

## Current Status

> ✅ **Repository-owned gates are green.** The platform is a defensible **Core GA candidate** with accepted-risk waivers required for the environment-dependent P0/P1 items below.
>
> 1. **`make verify` passes** — lint, typecheck, per-layer tests, contract tests (420 passed / 33 skipped / 1 xfailed), security smoke (13 passed / 1 xfailed), behavior-readiness YELLOW (0 blocking skips), structural preflight (0 findings), docs-harness, and frontend checks all pass.
> 2. **`make production-readiness-gate` passes** — billing 17/17, abuse 8/8, config 206/206, audit 6/6.
> 3. **Pre-existing test-suite blockers `R-2026-06-13-01` and `R-2026-06-13-02` are closed.** The contract-static failures and Layer 1/3 collection issues were fixed in the 2026-06-15 sweep.
> 4. **Environment-dependent P0 items (P0-001 Playwright journeys, P0-002 rollback rehearsal, P0-003 enterprise SSO/OIDC) are re-testable on the local surrogate** but require a configured staging/production-like environment for full closure. They are formally accepted risks pending signed waivers.
> 5. **P1 operational evidence** (billing provider integration, alert receivers, live LLM validation, full telemetry dashboards/SLO reports) remains deferred/partial and is also covered by accepted-risk waivers.

| ID | Area | Status | Evidence |
|---|---|---|---|
| `make verify` | Repository-owned canonical gate | ✅ PASS | `artifacts/readiness/make-verify-2026-06-15.log` |
| `make production-readiness-gate` | Production-readiness gate | ✅ PASS | `artifacts/readiness/make-production-readiness-gate-2026-06-15.log` |
| P0-001 | Playwright live backend-integrated journeys | ⚠️ ACCEPTED RISK — pending sign-off | Legacy-auth Clerk hook boundary fixed; `case-meridian-e2e-001` seed made deterministic; new behavior tests pass; staging execution still required for full evidence |
| P0-002 | Rollback / restore drill | ⚠️ ACCEPTED RISK — pending sign-off | `signoff-evidence/p0-rollback-20260613.json` refreshed; immutable-image rollback doctrine added to runbook; static verifier 8/8; runtime rehearsal requires environment |
| P0-003 | Enterprise SSO/OIDC | ⚠️ ACCEPTED RISK — pending sign-off | `signoff-evidence/p0-sso-20260613.json` refreshed; local Keycloak surrogate committed to `docker-compose.live.yml` under the `sso` profile; realm import validated; real IdP integration required |
| P1 matrix | Operational evidence | ⏳ DEFERRED / ACCEPTED RISK | `signoff-evidence/p1-operational-20260613.json`; local checks pass; provider-dependent items deferred |
| R-2026-06-13-01 | Contract tests / `make contract-tests` | ✅ Closed | Fixed in 2026-06-15 sweep; `make verify` passes |
| R-2026-06-13-02 | Unit tests / `make test` | ✅ Closed | Fixed in 2026-06-15 sweep; `make verify` passes |
| Local live-stack smoke | L1–L6 critical path | ✅ Verified (2026-06-14) | `signoff-evidence/e2e/e2e-critical-path-20260614.json` — `overall=pass`, `passed=12`, `failed=0` |
| End-to-end value workflow (mock scenario) | Full intake → analysis → value hypothesis → evidence → output | **BLOCKED** | `docs/evidence/fabric4l-e2e-mock-workflow-20260616.md` — services not running and no LLM credentials in this environment; reproducible probe script and blocker evidence attached |
| Security smoke | Fast PR gating | ✅ Pass | `make security-smoke` → 13 passed, 1 xfailed |
| Rollback readiness | Release rollback procedure (static) | ✅ Pass | `python scripts/ci/verify_release_rollback.py` → 8/8 passed |
| DR backup/restore | Backup verify + restore dry-run | ✅ Pass | `pnpm ops:backup:verify` → 13 passed; `pnpm ops:restore:dry-run` ✅ |
| Release safety | Release dry-run / rollback verify | ✅ Pass | `pnpm release:dry-run` ✅; `pnpm release:rollback:verify` → 8/8 |

### P1 operational evidence classification (2026-06-15)

| ID | Area | Classification | Repository evidence | External dependency |
|---|---|---|---|---|
| P1-001 | Notification and alert receivers | **EXTERNAL** | Alertmanager rules, routing, templates committed | Receiver secrets + deployed Alertmanager |
| P1-002 | Telemetry dashboards and alert validation | **EXTERNAL** | Grafana dashboards, SLO rules, tracing/Sentry code committed | Deployed observability stack + Sentry DSN |
| P1-003 | Billing and metering provider validation | **EXTERNAL** | Billing service, Stripe SDK integration, 17/17 local tests pass | Stripe/provider sandbox credentials |
| P1-004 | Performance and reliability smoke test | **VERIFIED** | Critical-path smoke 12/0 | None |
| P1-005 | Dependency automation coverage | **REQUIRED_PASS** | `check_dependabot_coverage.py` passes | None |
| P1-006 | Frontend test report artifact retention | **REQUIRED_PASS** | CI wiring in place | Next qualifying CI run |
| P1-007 | Broad security suite report | **REQUIRED_PASS** | Local suite 26/26 pass; CI wiring in place | Next qualifying CI run |
| P1-008 | Journey SLO report | **OPEN** | CI wiring in place | Next qualifying CI run |
| P1-009 | Live LLM provider validation | **EXTERNAL** | Provider adapters, safety tests, evidence generator committed | Provider API keys/sandbox |

See `docs/launch/runtime-dependency-report-2026-06-15.md` for the full environment request and risk acceptance statement.

> **Previously resolved:**
> - ✅ P0-0 — Merge conflict markers resolved
> - ✅ P0-004 — Deploy workflow now uses AWS OIDC auth + server-side dry-run + rollout checks
> - ✅ P0-008 — API gateway Alembic migration structure created
> - ✅ P0-010 — Readiness docs regenerated from live evidence
> - ✅ 2026-06-15 — All repository-owned `make verify` blockers closed

## Final Launch Decision

**Recommendation:** **GO WITH ACCEPTED RISKS for Core GA** on the current repository state.

**Rationale:**
- ✅ All repository-owned gates pass: `make verify`, `make production-readiness-gate`, security smoke, contract-static tests, architecture tests, behavior-readiness audit, structural preflight, and docs-harness.
- ✅ Pre-existing test-suite blockers `R-2026-06-13-01` and `R-2026-06-13-02` are closed.
- ✅ Local Docker live stack is healthy; critical-path smoke passes 12/0.
- ✅ Static DR and release-safety evidence passes (backup verify 13/13, restore dry-run, release dry-run, rollback verifier 8/8).
- ⚠️ P0-001, P0-002, and P0-003 are environment-dependent; local surrogate evidence is attached, but full staging/production evidence is missing. These are formally accepted risks pending owner countersignature.
- ⚠️ P1 operational evidence is incomplete; accepted-risk waivers are required for billing provider integration, alert receivers, live LLM validation, and full telemetry dashboards/SLO reports.

**Required before removing accepted-risk status (path to unconditional GO):**
1. Execute P0 Playwright launch journeys in a Clerk-configured staging environment and attach retained JUnit/trace evidence (or sign a scope-reduction waiver).
2. Rehearse a coordinated image+dependency rollback (or version-pinned immutable-image rollback) in a production-like environment and attach passing evidence (or sign a waiver).
3. Configure an enterprise IdP and complete SSO/OIDC login/logout/tenant-mapping validation (or sign a waiver).
4. Obtain countersigned waivers for all accepted P0/P1 risks recorded in `production-readiness/risk_register.md` and `docs/launch/launch-blocker-register.md`.
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
