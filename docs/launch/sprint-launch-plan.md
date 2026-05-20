# Value Fabric — 8-Sprint Launch Plan

**Canonical Source:** This document is the authoritative sprint-by-sprint execution plan for the Value Fabric production launch.
**Snapshot Date:** 2026-05-19 (updated from 2026-05-18)
**Current Readiness:** ≥85% assurance score — production-ready threshold met (per `tests/TEST_AUDIT.md`)
**Open P0 Blockers:** 4 (P0-001 through P0-004) — all `REQUIRES_ENVIRONMENT`; no code-level P0s remain
**Open P1 Blockers:** 9 (P1-001 through P1-009) — all `REQUIRES_ENVIRONMENT` or `REQUIRED_PASS` via CI
**Code-level P0/P1 blockers resolved 2026-05-19:** 7 items (see blocker register)

---

## How to Read This Plan

Each sprint maps to one or more open blockers from `docs/launch/launch-blocker-register.md`. Tasks are ordered by dependency: environment-independent work (code, tests, CI wiring) precedes environment-dependent evidence collection. A sprint is **done** when all its exit criteria are met and evidence is attached to the blocker register.

**Sprint pairing rationale:** Sprints 1–4 close code/CI gaps that can be resolved without a live environment. Sprints 5–8 require a staging/production-like environment and collect the evidence that converts `REQUIRES_ENVIRONMENT` blockers to `PASS`.

---

## Sprint 1 — Live Stack CI Promotion + Contract Drift Closure

**Closes:** P1-006, P1-007, P1-008 (CI wiring already done 2026-05-18; evidence attaches on next qualifying run)
**Addresses:** Contract drift Phase 2–3 type generation gap

### Task 1A — Promote live-stack validation from manual to automatic CI

**Context:** `scripts/ci/run_live_workflow_validation.sh` and `.github/workflows/live-workflow-validation.yml` exist. On PR/push the mode defaults to `config-only` — compose syntax and artifact schema only. Full service probing only runs on manual `workflow_dispatch`. This means no CI run has ever automatically validated that all six services start and respond.

**Work items:**
- Add a `smoke` mode to `run_live_workflow_validation.sh` that starts services, waits for health endpoints, runs a minimal probe per layer, then tears down. Keep it under 5 minutes.
- Add a `push` trigger to `live-workflow-validation.yml` on `release/**` and `main` branches with `mode: smoke`.
- Ensure `VITE_USE_MOCKS=false` is enforced in the smoke mode environment block.
- Publish a `live-stack-smoke-evidence-${{ github.sha }}.json` artifact with per-layer health results and timestamps.
- Update `docs/validation/live-workflow-validation.md` to document the new mode.

**Exit criteria:**
- `smoke` mode runs automatically on `release/**` push.
- All six layer health endpoints return 200 in CI output.
- Artifact is retained with release SHA.
- `docs/validation/live-workflow-validation.md` reflects the new mode.

**Files to touch:**
- `scripts/ci/run_live_workflow_validation.sh`
- `.github/workflows/live-workflow-validation.yml`
- `docs/validation/live-workflow-validation.md`

---

### Task 1B — Contract drift Phase 2–3 type generation

**Context:** `contracts/frontend/02-type-synchronization-contract.md` defines three phases. Phase 1 (Signals, Enrichment, Stakeholders, Hypotheses, Drivers, Evidence, Calculator, ValueModel, ValueCase, ValueRealization) is generated. Phase 2–3 domains (Ontology, Workflows, Formulas, ValuePacks, Governance, Settings, Tools, CRM Webhooks) have no generated TypeScript types. The `openapi-typescript` pipeline exists; it just hasn't been run for these domains.

**Work items:**
- Identify which Phase 2–3 domains have OpenAPI specs in `contracts/openapi/`.
- For domains with specs: run `openapi-typescript` and commit generated output to `apps/web/src/api/generated/`.
- For domains without specs: add a stub spec or document the gap in `contracts/drift-allowlist.yaml` with a target sprint.
- Add Phase 2–3 domains to the drift check CI workflow so they are covered going forward.
- Update `contracts/frontend/02-type-synchronization-contract.md` Phase 2–3 status.

**Exit criteria:**
- All Phase 2–3 domains either have generated types or have an explicit allowlist entry with owner and target sprint.
- Drift check CI covers Phase 2–3 domains.
- Type sync contract doc reflects current state.

**Files to touch:**
- `apps/web/src/api/generated/` (new generated files)
- `contracts/drift-allowlist.yaml`
- `contracts/frontend/02-type-synchronization-contract.md`
- `.github/workflows/openapi-drift-check.yml` or equivalent

---

## Sprint 2 — Tenant Isolation Hostile-Test Completion + OIDC Route Wiring

**Closes:** Tenant isolation assurance gap (62% → 92%); OIDC route gap in L4

### Task 2A — Complete the 12 P0 tenant isolation gaps

**Context:** `docs/launch/TEST_AUDIT.md` (or equivalent) records 12 P0 gaps. The assurance score is 62% against a 92% target. Five files are outright missing; others need expansion. These are release blockers per the tenant isolation invariant.

**Missing files to create:**
- `tests/security/test_neo4j_tenant_write_enforcement.py` — assert that Neo4j write operations reject cross-tenant node/relationship creation
- `tests/security/test_auth_source_validation.py` — assert that `tenant_id` from request body is rejected when it conflicts with authenticated context
- `tests/security/test_jwt_config_validation.py` — assert that misconfigured JWT (wrong issuer, expired, tampered) fails closed
- `tests/security/test_neo4j_rls_write.py` — assert RLS enforcement on Neo4j write paths
- `tests/security/test_permission_bypass.py` — assert that privilege escalation attempts are rejected

**Expansion work on existing files:**
- Review each existing hostile test file against the gap matrix and add missing assertions.
- Ensure every test covers the "fails closed" case (missing tenant context → 403/401, not 500 or silent pass).

**Exit criteria:**
- All 12 P0 gap files exist and pass `pytest tests/security -v`.
- Assurance score reaches ≥ 92% (re-run the audit script if one exists, or manually verify coverage against the gap matrix).
- No test was removed or weakened to achieve the score.

**Files to touch:**
- `tests/security/test_neo4j_tenant_write_enforcement.py` (new)
- `tests/security/test_auth_source_validation.py` (new)
- `tests/security/test_jwt_config_validation.py` (new)
- `tests/security/test_neo4j_rls_write.py` (new)
- `tests/security/test_permission_bypass.py` (new)
- Existing hostile test files (expansion)

---

### Task 2B — Wire OIDC backend routes in Layer 4

**Context:** `apps/web/src/services/authClient.ts` calls `/auth/oidc/{tenant}/login` and `/auth/oidc/{tenant}/callback`. The OIDC client (`packages/shared/src/value_fabric/shared/identity/oidc.py`) and middleware exist. The `InMemoryOIDCStateStore` / `RedisOIDCStateStore` exist. But no FastAPI route file for these endpoints exists in `services/layer4-agents/src/api/routes/`. The frontend auth flow is broken end-to-end until these routes are wired.

**Work items:**
- Create `services/layer4-agents/src/api/routes/auth.py` with:
  - `GET /auth/oidc/{tenant}/login` — initiates PKCE flow, stores state in `RedisOIDCStateStore` (production) or `InMemoryOIDCStateStore` (dev-guarded), redirects to provider
  - `GET /auth/oidc/{tenant}/callback` — validates state, exchanges code, issues httpOnly cookie, returns to frontend
  - `POST /auth/logout` — clears session cookie, revokes token if provider supports it
- Register the router in the Layer 4 app factory.
- Add the routes to the Layer 4 OpenAPI spec in `contracts/openapi/`.
- Add integration tests in `services/layer4-agents/tests/test_auth_routes.py` covering: successful login flow, state mismatch rejection, expired state rejection, missing tenant rejection.
- Verify `GovernanceMiddleware` correctly handles the new cookie-based auth on subsequent requests.

**Exit criteria:**
- `GET /auth/oidc/{tenant}/login` and `GET /auth/oidc/{tenant}/callback` exist and are registered.
- OpenAPI spec updated.
- Integration tests pass.
- `authClient.ts` flow is end-to-end traceable from frontend call to backend handler.

**Files to touch:**
- `services/layer4-agents/src/api/routes/auth.py` (new)
- `services/layer4-agents/src/api/app.py` or equivalent router registration
- `contracts/openapi/layer4.json`
- `services/layer4-agents/tests/test_auth_routes.py` (new)

---

## Sprint 3 — Model Registry Runtime Enforcement + Ops Closure

**Closes:** Model governance runtime evidence gap; P1-001, P1-002 CI wiring

### Task 3A — Enforce model registry as sole runtime selection path

**Context:** `config/production-readiness/model_governance_policy.json` requires `mustResolveFromRegistry: true` and `environmentOverridesAllowed: false`. The `resolve_llm_model` function in `services/layer4-agents/src/registry/service.py` still falls back to `os.getenv('LLM_MODEL', 'gpt-4o')`. This means a misconfigured or missing registry entry silently falls back to a hardcoded model, bypassing governance.

**Work items:**
- Modify `resolve_llm_model` to raise a `ModelRegistryError` (not fall back silently) when the registry has no active deployment for the requested model class and tenant.
- Add a `ALLOW_ENV_MODEL_OVERRIDE` flag (default `False`) that is only settable to `True` in non-production environments, guarded by an environment check.
- Update `services/layer4-agents/src/model_registry_client.py` to log an audit event when fallback is attempted (even if blocked).
- Add a startup check that validates at least one model deployment exists per required model class before the service accepts traffic.
- Update `config/production-readiness/model_governance_policy.json` status to `runtime_enforcement_active`.
- Add regression tests: registry miss → error (not fallback), env override blocked in production mode, audit event emitted on fallback attempt.

**Exit criteria:**
- `resolve_llm_model` raises on registry miss in production mode.
- `ALLOW_ENV_MODEL_OVERRIDE=False` is the production default.
- Audit event is emitted on any fallback attempt.
- Policy JSON status updated.
- Tests pass.

**Files to touch:**
- `services/layer4-agents/src/registry/service.py`
- `services/layer4-agents/src/model_registry_client.py`
- `config/production-readiness/model_governance_policy.json`
- `services/layer4-agents/tests/test_model_registry.py` (expansion)

---

### Task 3B — Ops closure: alert receiver + telemetry CI wiring

**Context:** P1-001 (alert receiver validation) and P1-002 (telemetry dashboard validation) are `REQUIRES_ENVIRONMENT`. The configs exist (`monitoring/alertmanager/alertmanager-production.yml`, `monitoring/prometheus/prometheus.yml`, 24 Grafana dashboards). What's missing is CI-level validation that the configs are syntactically and structurally correct, plus a documented procedure for live delivery proof.

**Work items:**
- Extend `scripts/ci/validate-alertmanager-config.sh` to also validate that all receiver names referenced in routes exist in the receivers block (structural check, not just syntax).
- Add a `scripts/ci/validate-prometheus-rules.sh` that runs `promtool check rules` against all rule files in `monitoring/`.
- Add a `scripts/ci/validate-grafana-dashboards.sh` that validates dashboard JSON schema (no live Grafana required — use `jq` schema check).
- Wire all three validators into a new `.github/workflows/monitoring-validation.yml` job that runs on PR.
- Document the live delivery proof procedure in `docs/runbooks/operational/alerting-deployment-checklist.md` — what command to run, what output to capture, who approves.

**Exit criteria:**
- All three validators pass in CI on PR.
- `monitoring-validation.yml` workflow exists and is green.
- Live delivery proof procedure is documented with owner and acceptance criteria.

**Files to touch:**
- `scripts/ci/validate-alertmanager-config.sh`
- `scripts/ci/validate-prometheus-rules.sh` (new)
- `scripts/ci/validate-grafana-dashboards.sh` (new)
- `.github/workflows/monitoring-validation.yml`
- `docs/runbooks/operational/alerting-deployment-checklist.md`

---

## Sprint 4 — Frontend UX Hardening + Launch Control Room

**Closes:** Frontend production UX gaps; establishes go/no-go governance artifact

### Task 4A — Harden intelligence workspace for production

**Context:** Three deferred tabs (`ontology-match`, `alternatives`, `solution-cost`) are correctly hidden in production via the tab registry. Two remaining issues: (1) `Intelligence.tsx` has a hardcoded `"Meridian Automotive"` string in the subtitle — this must be tenant-driven. (2) The journey SLO gate (P1-008) requires synthetic monitor output; the CI wiring exists but the `nonEmptyRatio` false-pass bug was fixed — evidence attaches on next qualifying run.

**Work items:**
- Replace the hardcoded `"Meridian Automotive"` string in `Intelligence.tsx` with the tenant/account name from the workspace context or API response.
- Audit all other hardcoded customer/tenant strings in `apps/web/src/features/intelligence-workspace/` and replace with context-driven values.
- Verify that all 10 active tabs have non-stub loading, empty, and error states (no `TODO` or placeholder copy in production mode).
- Add a production-mode smoke test that asserts no hardcoded tenant strings appear in rendered output.
- Confirm `workspaceTabRegistry.test.ts` covers the production-visibility rule for all 13 tabs (10 active, 3 deferred).

**Exit criteria:**
- No hardcoded tenant/customer strings in production-rendered paths.
- All 10 active tabs have complete loading/empty/error states.
- Production-mode smoke test passes.
- Tab registry test covers all 13 tabs.

**Files to touch:**
- `apps/web/src/features/intelligence-workspace/Intelligence.tsx`
- Other files in `apps/web/src/features/intelligence-workspace/` as needed
- `apps/web/src/features/intelligence-workspace/__tests__/` (new or expanded tests)

---

### Task 4B — Create launch control room packet

**Context:** `docs/launch/PRODUCTION_SIGNOFF_ISSUE.md` has a 14-phase checklist and a go/no-go formula. `docs/launch/launch-blocker-register.md` has the authoritative blocker register. What's missing is a single operational artifact that a release owner can open on launch day to see: current blocker status, evidence links, owner contacts, rollback trigger criteria, and the go/no-go decision record.

**Work items:**
- Create `docs/launch/launch-control-room.md` with:
  - Go/no-go formula (copied from blocker register, not duplicated — link to source)
  - Live blocker status table (P0 + P1) with evidence link column and owner column
  - Rollback trigger criteria (what conditions trigger immediate rollback)
  - Rollback execution steps (link to `docs/troubleshooting/runbooks/infrastructure/deployment-rollback.md`)
  - Named owners for each gate (identity, SRE, security, frontend, AI platform, billing, build)
  - Decision record section (date, approver, scope, any accepted waivers)
  - Post-launch monitoring window (first 24h, first 7d checkpoints)
- Add a CI check that validates the control room doc exists and has no `TBD` owner fields before a release branch can merge.

**Exit criteria:**
- `docs/launch/launch-control-room.md` exists with all sections populated.
- No `TBD` owner fields.
- CI check validates the doc on release branch merges.

**Files to touch:**
- `docs/launch/launch-control-room.md` (new)
- `.github/workflows/launch-readiness.yml` (add control room validation step)

---

## Sprint 5 — Staging Environment: E2E Journey Evidence (P0-001)

**Closes:** P0-001 (4 of 7 P0 Playwright journeys still require staging evidence)

**Prerequisite:** Staging environment with real backing services, live OIDC provider, and release-candidate SHA deployed.

### Task 5A — Execute remaining 4 P0 Playwright journeys in staging

**Context:** 3 of 7 P0 journeys have staging evidence attached. The remaining 4 must be run against a staging environment with: real login (not mocked), live backing services (PostgreSQL, Neo4j, Redis, all 6 layers), persisted state across steps, and a pinned release-candidate SHA.

**Work items:**
- Identify the 4 remaining journey IDs from `docs/launch/launch-blocker-register.md` P0-001.
- Deploy the release candidate to staging with `VITE_USE_MOCKS=false`.
- Execute each journey via the existing Playwright suite against the staging URL.
- Capture per-journey: JUnit XML, trace file, video, screenshots, and the release SHA.
- Attach artifacts to the blocker register under P0-001 with owner sign-off.
- Update P0-001 status to `PASS` once all 7 journeys have evidence.

**Exit criteria:**
- All 7 P0 journeys have retained JUnit/trace/video/screenshot artifacts.
- Each artifact is tied to the release-candidate SHA.
- P0-001 status updated to `PASS` in `docs/launch/launch-blocker-register.md`.
- Owner sign-off recorded in `docs/launch/launch-control-room.md`.

---

## Sprint 6 — Staging Environment: SSO/OIDC + Rollback Drill (P0-002, P0-003)

**Closes:** P0-002 (rollback drill), P0-003 (SSO/OIDC provider validation)

**Prerequisite:** Staging environment with a configured OIDC provider (Okta, Azure AD, or Google), ArgoCD or equivalent deployment tooling.

### Task 6A — Enterprise SSO/OIDC provider validation

**Context:** The OIDC client, middleware, state store, frontend auth flow, and backend routes (wired in Sprint 2) are all in place. P0-003 requires evidence from a configured provider environment.

**Work items:**
- Configure a staging OIDC provider (Okta dev tenant or Azure AD app registration).
- Execute: successful login → token issuance → authenticated API call → logout.
- Execute: failed login (wrong credentials) → correct error, no token issued.
- Execute: group/role mapping → correct RBAC applied.
- Capture: redacted provider config evidence, login/logout trace, failed-login handling, audit event sample.
- Attach to P0-003 with identity owner sign-off.

**Exit criteria:**
- Successful login/logout evidenced with trace.
- Failed login fails closed (no token, correct error).
- Role mapping verified.
- Audit event captured.
- P0-003 status updated to `PASS`.

---

### Task 6B — Rollback and restore drill

**Context:** P0-002 requires a rollback drill executed in the launch environment. `docs/troubleshooting/runbooks/infrastructure/deployment-rollback.md` documents the steps. ArgoCD steps are documented but ArgoCD is noted as not installed — this must be resolved or the runbook updated to reflect the actual rollback mechanism.

**Work items:**
- Confirm the actual rollback mechanism (ArgoCD, Helm rollback, kubectl rollout undo, or manual).
- Update `docs/troubleshooting/runbooks/infrastructure/deployment-rollback.md` to reflect the actual mechanism.
- Execute a rollback drill in staging: deploy release candidate → trigger rollback → verify previous version is serving → verify data integrity.
- Capture: redacted rollback transcript, restore proof, data-integrity check output, timing notes.
- Attach to P0-002 with SRE owner sign-off.

**Exit criteria:**
- Rollback mechanism is documented and matches reality.
- Drill executed and timed.
- Data integrity verified post-rollback.
- P0-002 status updated to `PASS`.

**Files to touch:**
- `docs/troubleshooting/runbooks/infrastructure/deployment-rollback.md`

---

## Sprint 7 — Live Provider Evidence: LLM + Alerting + Telemetry (P1-001, P1-002, P1-009)

**Closes:** P1-001 (alert receiver), P1-002 (telemetry), P1-009 (live LLM provider)

**Prerequisite:** Production-like environment with live LLM provider credentials, PagerDuty/Slack receivers configured, Prometheus/Grafana stack running.

### Task 7A — Live LLM provider validation

**Context:** P1-009 requires evidence that live LLM workflows produce grounded citations, correct fact/assumption labeling, refusal behavior, prompt-injection resistance, cost tracking, and traceability. The model registry enforcement (Sprint 3) must be active.

**Work items:**
- Execute a live agent workflow (Layer 4) against the configured LLM provider (not a mock).
- Verify: citations are grounded (traceable to source documents), fact/assumption labels are present, a prompt-injection attempt is refused, cost is tracked in the model registry, the workflow trace is retained.
- Capture a redacted evidence bundle (no raw API keys, no customer data).
- Attach to P1-009 with AI platform owner sign-off.

**Exit criteria:**
- Live workflow executed against real provider.
- All six evidence dimensions captured.
- P1-009 status updated to `PASS`.

---

### Task 7B — Alert receiver and telemetry validation

**Context:** P1-001 requires proof that alert receivers (PagerDuty, Slack, email) actually deliver. P1-002 requires proof that metrics/logs/traces flow to dashboards and alert rules fire correctly.

**Work items:**
- Send a test alert through Alertmanager and capture delivery confirmation from each receiver (PagerDuty incident ID, Slack message, email header).
- Verify at least one alert rule fires and routes correctly through the inhibition rules.
- Capture a Grafana dashboard screenshot showing live metric data.
- Capture a log/trace sample from the observability stack.
- Attach to P1-001 and P1-002 with SRE and observability owner sign-off.

**Exit criteria:**
- All configured receivers have delivery proof.
- At least one alert rule fires and routes correctly.
- Dashboard shows live data.
- P1-001 and P1-002 updated to `PASS`.

---

## Sprint 8 — Go/No-Go Decision + Cutover

**Closes:** All remaining P1 items; executes go/no-go; governs cutover

**Prerequisite:** All P0 blockers `PASS`. P1 blockers either `PASS` or have accepted waivers with owner sign-off.

### Task 8A — Final blocker sweep and waiver decisions

**Work items:**
- Review all P1 items not yet closed: P1-003 (billing), P1-004 (performance smoke), P1-005 (dependency coverage).
- For each: either attach evidence (if environment is available) or execute the waiver process defined in `docs/launch/launch-blocker-register.md` (approving owner, expiration date, customer impact statement, rollback plan, monitoring plan, scope reduction if needed).
- Confirm P1-005 (`check_dependabot_coverage.py`) passes — this is `REQUIRED_PASS` and has no environment dependency.
- Confirm P1-006, P1-007, P1-008 have CI artifacts attached from a qualifying run against the release SHA.

**Exit criteria:**
- All P0 blockers: `PASS`.
- All P1 blockers: `PASS` or `WAIVED` with documented owner and expiration.
- P1-005 passes in CI.
- P1-006, P1-007, P1-008 have retained CI artifacts.

---

### Task 8B — Go/no-go decision record

**Context:** The go/no-go formula from `docs/launch/launch-blocker-register.md`:
> `clean build + clean migrations + clean security gate + clean contract gate + clean live P0 Playwright evidence + clean observability gate + documented rollback + named owners = production candidate`

**Work items:**
- Populate the decision record section of `docs/launch/launch-control-room.md`:
  - Date and time of decision
  - Approving owner(s)
  - Launch scope (Core GA, paid GA, or scoped subset)
  - Any accepted waivers with expiration dates
  - Rollback trigger criteria confirmed
  - Post-launch monitoring window confirmed (first 24h, first 7d)
- Tag the release SHA in git: `git tag -a v1.0.0-ga -m "Core GA launch — go/no-go approved <date> by <owner>"`
- Execute cutover per the release checklist in `docs/launch-checklists/platform-launch.md`.

**Exit criteria:**
- Decision record populated in `docs/launch/launch-control-room.md`.
- Release SHA tagged.
- Cutover executed per checklist.
- Post-launch monitoring window active.

---

## Blocker-to-Sprint Mapping

| Blocker | Sprint | Type | Current Status |
|---|---|---|---|
| P0-001 — 4 of 7 P0 journeys need staging evidence | 5 | REQUIRES_ENVIRONMENT | Open |
| P0-002 — Rollback drill | 6 | REQUIRES_ENVIRONMENT | Open |
| P0-003 — SSO/OIDC provider validation | 6 | REQUIRES_ENVIRONMENT | Open |
| P0-004 — Secret hygiene gate | 1 (CI) | REQUIRED_PASS | Automated |
| P1-001 — Alert receiver validation | 7 | REQUIRES_ENVIRONMENT | Open |
| P1-002 — Telemetry dashboard validation | 7 | REQUIRES_ENVIRONMENT | Open |
| P1-003 — Billing/metering validation | 8 | REQUIRES_ENVIRONMENT | Open |
| P1-004 — Performance smoke test | 8 | REQUIRES_ENVIRONMENT | Open |
| P1-005 — Dependabot coverage | 8 | REQUIRED_PASS | Automated |
| P1-006 — Frontend test report artifact | 1 (CI wired) | REQUIRED_PASS | CI wired, evidence pending |
| P1-007 — Security suite report artifact | 1 (CI wired) | REQUIRED_PASS | CI wired, evidence pending |
| P1-008 — Journey SLO report artifact | 1 (CI wired) | REQUIRED_PASS | CI wired, evidence pending |
| P1-009 — Live LLM provider validation | 7 | REQUIRES_ENVIRONMENT | Open |
| Tenant isolation 62% → 92% | 2 | CODE | Open |
| OIDC routes not wired in L4 | 2 | CODE | Open |
| Model registry env-var fallback | 3 | CODE | Open |
| Contract drift Phase 2–3 | 1 | CODE | Open |
| Live stack CI config-only mode | 1 | CODE | Open |
| Hardcoded tenant string in Intelligence.tsx | 4 | CODE | Open |
| Launch control room doc missing | 4 | DOC | Open |

---

## Sprint Summary

| Sprint | Theme | Blocker type | Environment needed |
|---|---|---|---|
| 1 | Live stack CI promotion + contract drift | CODE + CI | No |
| 2 | Tenant isolation + OIDC route wiring | CODE + TEST | No |
| 3 | Model governance enforcement + ops CI | CODE + CI | No |
| 4 | Frontend UX hardening + launch control room | CODE + DOC | No |
| 5 | Staging E2E journey evidence | EVIDENCE | Yes — staging |
| 6 | SSO/OIDC + rollback drill | EVIDENCE | Yes — staging + OIDC provider |
| 7 | Live LLM + alerting + telemetry | EVIDENCE | Yes — production-like |
| 8 | Go/no-go decision + cutover | GOVERNANCE | Yes — production |
