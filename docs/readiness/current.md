# Current Launch Readiness (Canonical)

- **Canonical Source:** This document is the single source of truth for launch readiness criteria and percentage.
- **Generated From CI:** `make verify` (lint, type-check, tests, contract tests, build gates) and release-gate evidence scripts.
- **Snapshot Date (UTC):** 2026-06-15
- **Last Updated:** 2026-06-15
- **Launch Readiness:** **BLOCKED** — launch-gate drift and stale/missing evidence detected on 2026-06-21. The repository cannot currently claim GO or GO WITH ACCEPTED RISKS. Remediation is tracked in `.windsurf/plans/launch-readiness-2026-06-21.md`.

## Current Status

> ❌ **Verified posture is BLOCKED as of 2026-06-21.** Canonical claims of GO WITH ACCEPTED RISKS are not supported by the newest local evidence. See `.windsurf/plans/launch-readiness-2026-06-21.md` for the full assessment.
>
> Verified blockers include:
> 1. **Release gate artifacts are stale or failing** — `artifacts/release/gate-result.json` is dated 2026-05-02 and reports FAIL; `artifacts/release/release-readiness-report.md` (2026-06-21) reports `Release eligible: False`.
> 2. **Tenant-isolation regression** — `artifacts/security/tenant-isolation-summary.md` (2026-06-21) reports cross-layer matrix exit 1.
> 3. **Contract drift** — `artifacts/arch/summary.md` (2026-04-23) reports 1 contract drift violation.
> 4. **Launch-gate drift** — `.github/workflows/smoke-gate.yml` and `scripts/smoke/production_smoke.py` are missing; `.github/workflows/prod-readiness.yml` resolves release-policy artifacts that do not exist locally.
> 5. **Missing/smoke/obs/agent/state artifacts** — `artifacts/smoke/`, `artifacts/obs/`, `artifacts/agent/` are empty; `artifacts/state/` contains only `gate-state.xml`.
>
> The 2026-06-15 claims of `make verify` pass and `make production-readiness-gate` pass are superseded by the newer evidence above and must be re-verified after remediation.

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

**Recommendation:** **BLOCKED** on the current repository state.

**Rationale:**
- ❌ Release gate evidence is stale/failing: `artifacts/release/gate-result.json` (2026-05-02) reports FAIL; `artifacts/release/release-readiness-report.md` (2026-06-21) reports `Release eligible: False`.
- ❌ Tenant-isolation regression: `artifacts/security/tenant-isolation-summary.md` (2026-06-21) reports cross-layer matrix exit 1.
- ❌ Contract drift: `artifacts/arch/summary.md` reports 1 contract drift violation.
- ❌ Launch-gate path drift: missing `smoke-gate.yml`, `scripts/smoke/production_smoke.py`, and required release-policy artifacts.
- ❌ Smoke / obs / agent / state artifact directories are empty or stale.
- ⚠️ P0-001, P0-002, and P0-003 remain environment-dependent; they cannot be accepted as risks until the repository-owned blockers above are resolved.

**Path back to GO / GO WITH ACCEPTED RISKS:**
1. Resolve launch-gate drift (Sprint 1).
2. Fix tenant-isolation regression and contract drift (Sprint 2).
3. Populate obs / agent / smoke / state evidence (Sprint 3).
4. Align P0 Playwright routes and verify L1 hardening (Sprint 4).
5. Run full `make release-gate PROFILE=release-candidate` and collect countersigned waivers for P0/P1 environment-dependent items (Sprint 5).

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
