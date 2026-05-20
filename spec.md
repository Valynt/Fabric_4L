# Spec: 24-Hour Hackathon Sprint — Broad GA / Public Launch
## (Supersedes Sprint 4 / Sprint 5 / Sprint 6 specs)

## Status
Ready for implementation

---

## Problem Statement

Value Fabric is at 97% launch readiness (canonical: `docs/readiness/current.md`) but is blocked from Broad GA by 4 open P0 release blockers, 6 P1 pre-demo items, and a set of frontend UX gaps (Sprint 4 W1–W6) that make the product unsuitable for public users. This sprint closes every blocking item in parallel across security, architecture, infrastructure, frontend, testing, and deployment — targeting a Docker Compose–based public launch within 24 hours.

---

## Current State Summary

| Area | State |
|---|---|
| Launch readiness | 97% (canonical: `docs/readiness/current.md`) |
| Frontend Vitest | 1,515/1,615 passing — 100 failures across 16 files |
| Backend test suite | ~6,349/8,064 passing — majority of failures are infra-dependent (no live services) |
| P0 blockers | 4 open (RLS regression, arch failures, Redis mock bug, staging digest) |
| P1 blockers | 6 open (CI branch protection, unauthenticated route, contract test errors, schemathesis compat, connection-pool tests, security test gaps) |
| Sprint 4 frontend | W1–W6 not yet implemented (Harness Runs UI, AIModel banner, BusinessCase trust row, admin empty states, Playwright/Vitest coverage) |
| Deployment | `docker-compose.live.yml` exists; staging `kustomization.yaml` has placeholder digests blocking CI |

---

## Requirements

### Track 1 — P0 Blockers (all in parallel)

#### P0-1: RLS Enforcement Regression
- `tests/security/test_rls_enforcement.py::TestRLSPolicyStructure::test_remediation_migrations_do_not_reintroduce_null_visibility` must pass.
- Audit all Alembic migrations added after the last known-green baseline to identify which migration reintroduced NULL `tenant_id` visibility.
- Fix the offending migration or add a compensating migration that restores the RLS policy.
- All 12+ tests in `test_rls_enforcement.py` must pass after the fix.

#### P0-2: Architecture Conformance Failures
Five failures in `tests/arch/` block `gate-arch` (a hard gate per `.fabric/prod-gates.policy.yaml`):
- **D-01**: L3 compat path conformance — fix shim or test expectation.
- **D-02**: L5 `TruthObject` missing `tenant_id` field — add field to model and migration.
- **D-03**: Syntax error in `app_monolith` — fix the syntax error.
- **D-11**: L3 shim drift — align shim with canonical service path.
- **D-12**: L3 tenant dependency validation — fix import or dependency resolution.
- All 21 tests in `tests/arch/` must pass after fixes.

#### P0-3: Redis Cache Tenant Isolation (False-Green Gate)
- All 14 tests in `tests/cache/test_redis_tenant_isolation.py` fail with `TypeError: '>=' not supported between instances of 'AsyncMock' and 'int'`.
- Fix: mock `incr` to return `int` (not `AsyncMock`) in the test fixtures.
- All 14 tests must pass after the fix.
- Verify the underlying tenant isolation invariant is actually enforced (not just the mock).

#### P0-4: Staging Kustomization Placeholder Digests
- `k8s/envs/staging/kustomization.yaml` contains placeholder image digests (`sha256:1111...7777`).
- Run `scripts/ci/prepare_kustomize_deploy.sh staging` to replace placeholders with real digests.
- Verify `scripts/check-no-placeholder-digests.sh k8s/envs/staging/kustomization.yaml` exits 0.
- Staging promotion CI must unblock after this fix.

---

### Track 2 — P1 Pre-Demo Blockers (all in parallel)

#### P1-1: Mandatory Security Regression as Required CI Check
- Configure `mandatory-security-regression` job in `.github/workflows/security-gates.yml` as a required status check in GitHub branch protection for `main`.
- Document the configuration step in `docs/runbooks/branch-protection.md` (create if absent).

#### P1-2: Unauthenticated Route — `GET /workflows/{workflow_id}/state/errors`
- Add `require_authenticated` dependency to the route handler, OR add an explicit allowlist entry in `contracts/route-auth-allowlist.yaml` with a documented rationale if the route is intentionally public.
- Update the route auth inventory test to reflect the change.

#### P1-3: Contract Test Collection Errors (4 L3 files)
Fix import-time drift in:
- `tests/contract/test_entity_contract.py`
- `tests/contract/test_l3_provenance_audit_contract.py`
- `tests/contract/test_l3_route_alias_parity.py`
- `tests/contract/test_layer3_graph_deprecation_contract.py`

All 4 files must collect without errors under `pytest tests/contract`.

#### P1-4: Schemathesis × pytest-xdist Incompatibility
- Pin schemathesis and/or pytest-xdist to compatible versions, OR configure schemathesis tests to run serially (`-p no:xdist`) in `pytest.ini` or a dedicated `conftest.py`.
- `pytest tests/contract` must complete without `WorkerController has no attribute 'workeroutput'` crash.

#### P1-5: Connection-Pooling and ACID Property Tests
- Add tests covering connection pool exhaustion behavior and ACID property guarantees for multi-tenant writes.
- Minimum: one test per service that has a PostgreSQL dependency (L1, L4, L5, API service).
- Tests must be tagged `pytest.mark.connection_pool` and `pytest.mark.acid`.

#### P1-6: Security Test Gaps
Add tests for:
- `GovernanceMiddleware` resolution-order adversarial scenarios (wrong tenant in header vs JWT claim).
- `RequestContext` immutability (mutation attempt raises error).
- Tier-aware isolation (tenant tier does not grant cross-tenant access).
- Audit event emission completeness (every gate decision emits an audit event).

All new tests in `tests/security/` with `pytest.mark.security`.

---

### Track 3 — Frontend Sprint 4 (W1–W6, all in parallel)

#### W1: Harness Runs UI — Close Contract Spec Gaps
- Confirm canonical gate-decision route is `POST /api/v1/agents/harness/gates/{gate_id}/decide`; payload field is `decision`. Fix any mismatch in `harnessApi` or contract spec fixture.
- Confirm `useDecideGate` mutation awaits registry call correctly; fix 422 on invalid transitions.
- Confirm polling: non-terminal runs refetch on `POLL_INTERVALS.workflows`; terminal runs do not. Fix broken `refetchInterval` callback if needed.
- Remove `test.fail()` from `e2e/contracts/harness-runs.spec.ts` only after W1.1–W1.3 are verified stable.
- `e2e/journeys/j25-harness-run-lifecycle.spec.ts` must continue to pass (or remain correctly skipped when `PLAYWRIGHT_BACKEND_URL` is absent).

#### W2: AIModel.tsx — Live Workflow Status Banner
- Add `WorkflowStatusBanner` component at the top of `AIModel.tsx` reading `runId` from URL params or falling back to the most recent harness run for the current account.
- Banner displays: run status, current state/step, last-updated timestamp, gate/validation state.
- Banner has loading, error, and empty states.
- Add annotation below hypothesis list: `"Hypotheses are demo data — backend model generation is not yet wired."`
- Static Meridian/manufacturing hypotheses remain untouched.
- TypeScript must pass for the new component and its props.

#### W3: BusinessCase.tsx — Trust Status Row
- Add compact status row near header/export controls rendering one of: `Degraded`, `Pending Review`, `Validated`, `Export Blocked`, `Export Ready`.
- `Degraded` state: show `Degraded` + `Internal draft only` badges, disable export, tooltip: `"LLM, validation, or evidence enrichment was incomplete. Human review required."`
- `Pending Review` state: show `Pending Review` + `Internal draft only` badges, disable export, tooltip: `"Claims require validation or human approval before export."`
- `Validated` state: show `Validated` badge, enable export if all existing export requirements pass.
- `Export Blocked` state: show `Export Blocked` badge, disable export.
- Existing `isApproved && hasExportDocument` gate logic is preserved; status row is additive.
- No full redesign; existing layout, ROI hero card, and sections unchanged.

#### W4: Auth/Session — Demo-Path Verification
- Document auth path alignment: `services/api` (`tenant_required`/JWT) and `services/layer4-agents` (`require_authenticated`/`RequestContext`) are both protected.
- Verify frontend `AuthContext` OIDC flow reaches both services correctly in the demo environment.
- No code change required unless a concrete 401/403 failure is found.
- Defer full enterprise auth UX polish (invite flows, role management UI, session expiry UX).

#### W5: Admin Pages — Graceful Empty/Error States
- `BenchmarkPolicies`, `VariableRegistry`, `FormulaGovernance`, and `ValuePacks` must render a visible empty state (using existing `EmptyState` component) when API returns an empty list.
- Each page must render a visible error banner (not a blank screen) when the API call fails, using existing `QueryState`/`ErrorBoundary` pattern.
- If a hook calls a non-existent route (e.g., 404), add `"Data unavailable in this environment"` inline notice — no new backend routes.

#### W6: Playwright and Vitest Coverage
- Remove `test.fail()` from `e2e/contracts/harness-runs.spec.ts` after W1 is confirmed.
- Add Vitest unit tests for `BusinessCase.tsx`: degraded/pending-review/validated/internal-draft-only badge rendering; export disabled when degraded/pending/failed; export enabled only when validated + `document_url` present.
- Add Vitest unit tests for `AIModel.tsx` status banner: all status states, loading, error, empty.
- Add/update Playwright spec: BusinessCase shows correct status row; export blocked for degraded/pending-review; export available for validated.
- `j25-harness-run-lifecycle.spec.ts` must continue to pass or remain correctly skipped.
- Net-new failing test count must not increase.

---

### Track 4 — Test Infrastructure (live services)

- Start `docker-compose.test.yml` (or `docker-compose.dev.yml`) to provide PostgreSQL, Redis, and Neo4j.
- Re-run the full test suite with live services available.
- Fix the 16 failing frontend test files:
  - `src/hooks/useTargets.test.ts` — restore or recreate missing `./queryKeys` module.
  - `src/hooks/useAuth.test.ts` — fix temporal dead zone (TDZ) initialization error.
  - All 14 MSW unmatched-handler failures — add missing MSW request handlers for the routes being tested.
- Target: frontend Vitest suite at 0 failures (1,615/1,615 passing).
- Target: backend suites with live services — resolve all infrastructure-dependent failures; genuine logic failures must be fixed or explicitly documented with a skip rationale.

---

### Track 5 — Deployment (Docker Compose)

- Validate `docker-compose.live.yml` starts all 6 layers + frontend cleanly.
- Ensure all required environment variables are documented in `.env.example` and `.env.dev.example`.
- Run `make verify` (or the closest available subset) against the live stack and confirm no failing gates.
- Perform a full smoke test against the running stack:
  - Layer 1–6 health endpoints return 200.
  - Frontend loads and authenticates via OIDC.
  - At least one end-to-end workflow (ingest → extract → knowledge → agent → ground-truth → benchmark) completes without error.
- Document the launch procedure in `docs/runbooks/docker-compose-launch.md`.

---

### Track 6 — Telemetry and Observability (Sprint 6 carry-over)

#### S6-R4: LLM Cost Telemetry
- Uncomment and wire `LLMCostCalculator` in `services/layer4-agents/src/engine/executor.py`.
- Structured log fields per LLM call: `tenant_id`, `workflow_id`, `model`, `prompt_tokens`, `completion_tokens`, `cost_usd`.
- Add contract test asserting these fields are present for a mocked LLM call.
- Populate `monitoring/grafana/dashboards/llm-costs.json`: total cost by tenant (time series), cost by model (bar), token usage by workflow (table).

#### S6-R5: Harness Trace and Validation Outcome Telemetry
- Harness trace events must emit: `tenant_id`, `run_id`, `workflow_type`, `stage`, `trace_id`.
- Validation outcome events must emit: `tenant_id`, `run_id`, `gate_id`, `outcome`, `decision_by`.
- Failed/degraded workflow events must emit: `tenant_id`, `run_id`, `error_class`, `error_code`, `stage`.
- Add contract tests for each structured log schema.

#### S6-R6: Release Gate Report
- Create `reports/RELEASE_GATE_SPRINT7.md` (this sprint) stating: no P0 blockers, deployment path (Docker Compose), GitOps status, digest guard passes, rollback procedure reference.

---

### Track 7 — Documentation and Launch Prep

- Update `docs/readiness/current.md` with fresh `make verify` evidence after all fixes.
- Update `docs/readiness/blockers.md` — mark all resolved P0/P1 items as closed with evidence.
- Update `docs/readiness/launch-decision-artifact.md` — fill in Engineering/Security/Product/Operations sign-off table.
- Create `docs/runbooks/docker-compose-launch.md` with step-by-step launch, smoke test, and rollback instructions.
- Ensure `README.md` reflects the current setup commands (pnpm, docker-compose, make verify).
- Create `docs/runbooks/hotfix-process.md` documenting the post-launch hotfix and rollback procedure.

---

## Acceptance Criteria

| # | Criterion | Verification |
|---|---|---|
| AC-1 | All 4 P0 blockers resolved | `make verify` passes; `test_rls_enforcement.py` all pass; `tests/arch/` all pass; `test_redis_tenant_isolation.py` all pass; staging digest guard exits 0 |
| AC-2 | All 6 P1 items resolved | `mandatory-security-regression` is a required CI check; unauthenticated route fixed; contract tests collect cleanly; schemathesis runs without crash; connection-pool + ACID tests added; security test gaps filled |
| AC-3 | Frontend Sprint 4 W1–W6 complete | Harness Runs UI contract spec has no `test.fail()`; AIModel has live status banner; BusinessCase has trust status row; admin pages have empty/error states; Vitest 0 failures; Playwright specs pass |
| AC-4 | Frontend Vitest at 0 failures | `pnpm --dir apps/web exec vitest run` exits 0 with 1,615 tests passing |
| AC-5 | Backend tests pass with live services | `docker-compose.test.yml` up; infrastructure-dependent failures resolved; genuine logic failures fixed or documented |
| AC-6 | `make verify` passes | All gates green (lint, typecheck, tests, contract-tests, security-smoke, deprecations, tool-contracts, platform-contract-lint, etc.) |
| AC-7 | Docker Compose launch succeeds | `docker-compose.live.yml up` starts cleanly; all health endpoints return 200; OIDC auth works; one full L1→L6 workflow completes |
| AC-8 | LLM cost telemetry wired | `LLMCostCalculator` active in executor; structured log fields present; Grafana dashboard populated |
| AC-9 | Harness/validation telemetry contract tests pass | All 3 structured log schema contract tests pass |
| AC-10 | Release gate report created | `reports/RELEASE_GATE_SPRINT7.md` exists with no P0 blockers |
| AC-11 | Readiness docs updated | `docs/readiness/current.md` updated; `blockers.md` all P0/P1 closed; launch-decision-artifact sign-off table filled |
| AC-12 | Launch runbooks complete | `docs/runbooks/docker-compose-launch.md` and `docs/runbooks/hotfix-process.md` exist and are accurate |

---

## Implementation Approach

The following tracks run in parallel. Within each track, steps are sequential.

### Track 1 — P0 Blockers
1. Audit Alembic migration history to find the NULL `tenant_id` RLS regression (P0-1).
2. Write a compensating migration or fix the offending migration; run `test_rls_enforcement.py`.
3. Fix `tests/arch/` D-01, D-02, D-03, D-11, D-12 failures (P0-2).
4. Fix `tests/cache/test_redis_tenant_isolation.py` AsyncMock → int mock (P0-3).
5. Run `scripts/ci/prepare_kustomize_deploy.sh staging`; verify digest guard (P0-4).

### Track 2 — P1 Blockers
1. Add `require_authenticated` to `GET /workflows/{workflow_id}/state/errors` (P1-2).
2. Fix import-time drift in 4 L3 contract test files (P1-3).
3. Pin schemathesis/xdist or configure serial execution (P1-4).
4. Add connection-pool and ACID tests per service (P1-5).
5. Add GovernanceMiddleware, RequestContext, tier-aware, and audit-event security tests (P1-6).
6. Configure `mandatory-security-regression` as required CI check (P1-1) — requires GitHub branch protection settings.

### Track 3 — Frontend Sprint 4
1. Fix W1: confirm route/payload, fix polling, remove `test.fail()` guards.
2. Implement W2: `WorkflowStatusBanner` in `AIModel.tsx`.
3. Implement W3: trust status row in `BusinessCase.tsx`.
4. Verify W4: auth path alignment; document findings.
5. Implement W5: empty/error states for 4 admin pages.
6. Implement W6: Vitest unit tests + Playwright spec updates.

### Track 4 — Test Infrastructure
1. Start `docker-compose.test.yml` (or `docker-compose.dev.yml`).
2. Restore/recreate `./queryKeys` module for `useTargets.test.ts`.
3. Fix TDZ initialization error in `useAuth.test.ts`.
4. Add missing MSW request handlers for all 14 unmatched-handler failures.
5. Re-run full Vitest suite; confirm 0 failures.
6. Re-run backend suites with live services; fix or document remaining failures.

### Track 5 — Deployment
1. Validate `docker-compose.live.yml` configuration; fix any missing env vars.
2. Update `.env.example` and `.env.dev.example` with all required variables.
3. Run `make verify` against live stack.
4. Execute smoke test (health endpoints, OIDC, L1→L6 workflow).
5. Write `docs/runbooks/docker-compose-launch.md`.

### Track 6 — Telemetry
1. Uncomment `LLMCostCalculator` in `executor.py`; add structured log fields.
2. Add contract test for LLM cost log schema.
3. Populate `monitoring/grafana/dashboards/llm-costs.json`.
4. Verify harness trace and validation outcome log fields; add contract tests.
5. Create `reports/RELEASE_GATE_SPRINT7.md`.

### Track 7 — Documentation
1. Update `docs/readiness/current.md` with fresh evidence.
2. Close all resolved P0/P1 items in `docs/readiness/blockers.md`.
3. Fill sign-off table in `docs/readiness/launch-decision-artifact.md`.
4. Write `docs/runbooks/hotfix-process.md`.
5. Verify `README.md` setup commands are current.

---

## Out of Scope (Deferred to Post-Launch)

- OAuth authorization flow for CRM integrations (P2-1)
- Celery/Redis queue for background sync (P2-2)
- Full SLO/error-budget monitoring (P2-5)
- Disaster recovery rehearsal (P2-6)
- Penetration testing (P2-7)
- K8s admission-time image digest validation via Kyverno/OPA (P2-8)
- Canonical contract compliance from ~58% to ≥85% (P2-9 — 449 violations)
- 12 frontend placeholder items blocked on missing backend endpoints (P2-10)
- Full enterprise auth UX (invite flows, role management, session expiry)
- APQC/BIAN/FIBO reference model integration (L2)
- Proxy rotation for L1 crawler

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| RLS migration fix introduces new regression | Medium | High | Run full `test_rls_enforcement.py` + tenant isolation suite after fix |
| Arch D-02 (L5 TruthObject `tenant_id`) requires a migration | Medium | High | Write additive migration; test with L5 suite before merging |
| MSW handler gaps are larger than 14 files | Low | Medium | Audit all `useXxx.test.ts` files for unregistered routes before fixing |
| Docker Compose live stack fails to start | Low | High | Test each service independently; check `.env` completeness first |
| `mandatory-security-regression` CI config requires GitHub admin access | Medium | Low | Document as manual step; proceed with code fixes in parallel |
| 24-hour window insufficient for all tracks | Medium | High | Prioritize P0 → P1 → Track 5 (deploy) → Track 3 (frontend) → Track 6 (telemetry) |
