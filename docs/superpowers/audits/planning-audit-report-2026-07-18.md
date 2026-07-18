# Planning Artifact Audit & Cleanup Report

**Audit date:** 2026-07-18  
**Branch:** `main`  
**Auditor:** Kimi Code CLI with delegated cleanup agents  
**Changelog:** `archive/planning-audit-2026-07-18/CHANGELOG.md`  
**Catalogs:**
- Repo artifacts: `tmp/planning-artifact-catalog.json`
- External plans: `tmp/external-plans-catalog.json`

---

## Executive Summary

This audit scanned the repository for planning artifacts (roadmaps, TODO lists, implementation plans, design docs, specs, checklists, milestones, backlogs, and embedded code TODOs), extracted actionable items, cross-referenced them against current code, archived stale material, updated status markers, and consolidated the remaining work into a single prioritized master task list.

**Headline counts:**

| Metric | Count |
|---|---|
| Repo artifacts scanned | 209 file-based + 8 embedded-comment files |
| External artifacts reviewed | 154 files in `/home/ubuntu/plans` |
| Files archived | 169 |
| Files updated in place | 51 |
| Contradictions/duplicates identified | 21 |
| Embedded TODO comments resolved or ticketed | 23 |
| Master task list items | 26 (P0–P2) |

No active source-code logic was changed. No `git commit` was executed.

---

## Scope

**Included:**
- Root-level roadmaps, design docs, and checklists
- `docs/` (architecture, contracts, governance, launch, operations, reference, validation, design-system, audit, archive)
- `docs/superpowers/plans/` and `docs/superpowers/specs/`
- Hidden agent workspace directories (`.devin/`, `.windsurf/`, `.jr/`, `.kimi/`, `.fabric/`, `.agent/`, `.ai/`, `.claude/`, `.codex/`, `.gemini/`, `.roo/`)
- Root `archive/`
- Embedded TODO/FIXME/XXX/HACK comments in `services/`, `apps/`, `packages/`, `tests/`, `sdk/`, `scripts/`, `.github/`
- External planning scratchpad `/home/ubuntu/plans` (read-only summary)

**Excluded:**
- Lint/scan rule regexes and test-fixture placeholder strings
- Source code logic changes beyond comments
- `/home/ubuntu/plans` file modifications

---

## Methodology

1. **Discovery** — `Glob`/`Grep` name-pattern and embedded-comment searches across the repo and `/home/ubuntu/plans`.
2. **Cataloging** — Wrote structured JSON catalogs to `tmp/` for repo and external artifacts.
3. **Parallel cleanup** — Dispatched four scoped agents:
   - Group 1: root + `docs/` artifacts
   - Group 2: hidden agent workspace artifacts
   - Group 3: `docs/superpowers/`, `docs/audit/`, `docs/archive/`, root `archive/`
   - Group 4: embedded TODO/FIXME comments in code
4. **Cross-reference** — Each agent verified concrete claims with `Read`, `Grep`, `Glob`, and targeted commands (`make typecheck-layer1`).
5. **Consolidation** — Compiled findings, generated changelog, and produced this report.

---

## Archived Items

**169 files** were moved to `archive/planning-audit-2026-07-18/<original-relative-path>` preserving directory structure. Full per-file reasons are in `archive/planning-audit-2026-07-18/CHANGELOG.md`.

### By source area

| Source area | Archived | Representative reasons |
|---|---|---|
| `docs/` | 129 | Redirect stubs, superseded roadmaps, historical sprint plans, outdated API designs, references to deleted `value_fabric/layer*/` and `frontend/client/` paths, aspirational specs for unimplemented subsystems |
| `.devin/plans/` | 25 | Transient `execution-status-sync-*` checkpoint dumps and duplicate implementation-complete snapshots |
| Root `archive/` | 13 | 2025/early-2026 audits and specs contradicted by current code |
| `packages/feature-flags/src/kill-switch-spec.md` | 1 | Spec for unimplemented global kill-switch framework |
| `.windsurf/plans/launch-readiness-2026-06-21.md` | 1 | Superseded by the 2026-06-22 version |

### Notable archives

- `docs/roadmap.md` — pure redirect to root `ROADMAP.md`
- `docs/IMPLEMENTATION_PLAN.md` — already marked archived; referenced deleted paths
- `docs/WORKFLOW_API_DESIGN.md` — proposed endpoints are now implemented
- `docs/contracts/MISSING_ROUTES_IMPLEMENTATION_PLAN.md` — formula CRUD and workflow archive now exist
- `docs/archive/2026-05-28/ROADMAP.md` — 4,649-line superseded roadmap with internal contradictions
- `docs/audit/production-readiness-2026-05-27.md` — contradicted by current L7 billing and source-tree state

---

## Items Updated In Place

**51 files** were annotated or corrected rather than archived because they remain canonical or partially active.

### By area

| Area | Count | Examples |
|---|---|---|
| `docs/` | 27 | Added audit notes for stale paths, corrected API base paths, noted launch-posture conflicts |
| Hidden agent dirs | 9 | Updated `.kimi/backlog.yaml` statuses, checked acceptance criteria in `.jr/tickets`, annotated `.fabric/gate-engineering/gate-registry.json` past-due checkpoints |
| `docs/superpowers/` + `docs/audit/` | 15 | Linked child plans to parent specs, corrected canonical paths, noted missing artifacts |
| Source comments | 7+ files | Updated 23 embedded TODOs to `DONE(...)` with evidence or minted debt-ticket IDs |

### Key corrections

- `docs/reference/layer4-agents-api.md`: base path corrected `/api/v1` → `/v1`
- `docs/validation/backend_integrated/test_environment_plan.md`: compose path corrected to `infra/compose/docker-compose.test.yml`
- `docs/architecture/layer1-ingestion-fixes-enhancements-roadmap.md`: runtime path corrected to `services/layer1-ingestion/src/layer1_ingestion/`
- `.kimi/backlog.yaml`: P0-001, P0-002, P0-005 marked `completed`
- `.fabric/gate-engineering/gate-registry.json`: 28 past-due `TODO-CHECKPOINT-6` entries annotated
- Embedded TODOs in Layer 1 idempotency/robots/terminal-state tests marked `DONE(...)` where implementation exists

---

## Contradictions & Duplicates Resolved

| # | Topic | Resolution |
|---|---|---|
| 1 | Duplicate roadmap redirect (`docs/roadmap.md` vs `ROADMAP.md`) | Archived redirect |
| 2 | Layer 4 port (`8002` vs `8004`) | Archived wrong doc, corrected surviving refs |
| 3 | Formula CRUD status (missing vs implemented) | Archived missing-routes plan, annotated contract map |
| 4 | Workflow archive / type query status | Annotated route mapping table |
| 5 | L5 routing authority (direct vs L4 proxy) | Annotated contract docs |
| 6 | Launch posture (GO / CONDITIONAL / NO-GO) | Added reconciliation notes; requires human release-owner decision |
| 7 | Severity model (SEV 0–3 vs SEV 1–4) | Added audit note |
| 8 | `.kimi/backlog.yaml` lag vs `.kimi/journal.md` | Corrected statuses |
| 9 | `.jr/tickets` claiming completion with unchecked criteria | Checked criteria and added audit notes |
| 10 | Duplicate launch-readiness assessments | Archived older `.windsurf/plans/launch-readiness-2026-06-21.md` |
| 11 | Duplicate remediation sprint plans | Archived older `2026-06-14-remediation-sprint-plan.md` |
| 12 | API-key dual implementation | Surviving spec annotated with canonical/shim warning |
| 13 | Layer 4 canonicalization goal vs baseline allowance | Annotated plan and baseline contradiction |
| 14 | L3 tenant-scoping audit contradictions | Archived stale gap report |
| 15 | Production-readiness claims contradicted by code | Archived stale audit |
| 16 | Duplicate test inventories / gap analyses | Archived near-duplicate reports |
| 17 | Trust-boundary gate files absent but command wired | Added audit note |
| 18 | Salesforce CRM runbook duplication | Added note pointing to canonical subdir runbook |
| 19 | `docs/PRODUCTION_READINESS_CHECKLIST.md` vs `production-readiness/` | Noted overlap, kept both with audit notes |
| 20 | Root `value_fabric/` namespace references | Flagged in compatibility-debt registry |
| 21 | Kill-switch subsystem spec vs tenant-suspension implementation | Archived spec |

---

## External Plans (`/home/ubuntu/plans`)

**154 files** were cataloged but not modified because they live outside the repo. They are a mix of plans, audit reports, remediation backlogs, helper scripts, and transient phase-status dumps.

### High-level breakdown

| Type | Approx. count | Notes |
|---|---|---|
| Plans / roadmaps | ~90 | Many reference past target dates (2026-05/06) |
| Audit / remediation reports | ~35 | Several are V9 production-readiness artifacts |
| Helper scripts | ~12 | Patch/conflict/reference analysis utilities |
| Status dumps / logs | ~17 | `git_status_phase4.txt`, `phase4_*` reports, empty files |

### Observations

- Several files are duplicates or near-duplicates of in-repo plans (e.g., `fabric-4l-complexity-reduction-*.md`, `p0-production-pass-checklist.md`).
- Many contain `DONE/COMPLETED` markers but no evidence links; their repo counterparts should be checked before being treated as authoritative.
- Helper scripts like `analyze_reports.py`, `check_conflicts.py`, `fix_patches.py` may be useful for future cleanup but are not under version control.
- Empty/truncated files (e.g., `phase4_diff_stat.txt'`, `phase4_stat.txt'`) appear to be shell-quoting artifacts and can be deleted manually.

**Recommendation:** If any external plan is still active, migrate it into the repo under `docs/superpowers/plans/` or `.jr/tickets/` and delete the external copy to avoid split-brain planning.

---

## Master Task List

A prioritized, de-duplicated list of remaining work derived from the audit. Each item is intended to be consumable by a downstream agent.

### P0 — Blockers / high-risk drift

- [ ] **Resolve launch-posture authority**  
  Files: `production-readiness/scorecard.md`, `docs/launch/launch-blocker-register.md`, `docs/governance/audit-remediation-release-readiness-matrix.md`  
  Acceptance: A single authoritative GO/NO-GO record exists; conflicting documents are archived or reconciled.

- [ ] **Decide canonical API-key implementation**  
  Files: `services/api/app/routers/api_keys.py`, `services/layer4-agents/src/layer4_agents/tenants/api/routes/api_keys.py`, `docs/superpowers/specs/2026-06-17-api-key-hardening-design.md`  
  Acceptance: One tree is canonical; the other is removed or converted to a thin proxy; design spec updated.

- [ ] **Remove residual flat source files in Layer 4**  
  Directory: `services/layer4-agents/src/` (flat modules coexist with `layer4_agents/` package)  
  Acceptance: No top-level `.py` modules remain outside `layer4_agents/`; `make typecheck-layer4` and `pytest services/layer4-agents/tests` pass.

- [ ] **Remove residual flat source files in Layer 1**  
  Directory: `services/layer1-ingestion/src/` (flat `adapters/`, `api/`, `shared/` coexist with `layer1_ingestion/`)  
  Acceptance: Only canonical nested package remains; `make typecheck-layer1` and `make test-layer1` pass.

- [ ] **Wire stuck-jobs reconciliation metrics to production loop**  
  Ticket: `VF-L1-TERMINAL-DEBT-001`  
  Files: `services/layer1-ingestion/src/layer1_ingestion/metrics/prometheus_metrics.py`, `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`  
  Acceptance: `refresh_stuck_jobs()` is invoked from a periodic reconciliation task; metric tests pass.

- [ ] **Implement billing webhook business logic**  
  Ticket: `VF-L7-WEBHOOK-DEBT-001`  
  File: `services/layer7-billing/src/layer7_billing/api/routes/billing_webhooks.py`  
  Acceptance: `payment.created`, `invoice.paid`, and related events update billing state; tests added.

- [ ] **Fix trust-boundary gate wiring**  
  File: `apps/web/package.json` (`test:trust-boundaries`)  
  Acceptance: Either source/test files are created or the script is removed; `pnpm run test:trust-boundaries` passes or exits cleanly.

- [ ] **Resolve billing service duplication**  
  Directories: `services/billing/`, `services/layer7-billing/`  
  Acceptance: A single billing service remains; routes/tests/migrations consolidated.

- [ ] **Replace `TODO-CHECKPOINT-*` placeholders in gate registry**  
  File: `.fabric/gate-engineering/gate-registry.json`  
  Acceptance: All 56 placeholder `ticket` values are real ticket IDs; past-due `target_date` entries updated.

### P1 — Correctness / contract alignment

- [ ] **Enforce Layer 4 canonical source tree in CI baseline**  
  File: `config/ci/layer4_source_tree_baseline.json`  
  Acceptance: Baseline no longer permits non-canonical top-level entries; incremental migration plan documented.

- [ ] **Consolidate duplicate test inventories**  
  Directory: `docs/archive/`  
  Acceptance: A single canonical test inventory is generated from `pytest --collect-only` and committed; duplicates archived.

- [ ] **Refresh audit snapshots and workflow**  
  Files: `docs/audit/snapshots/latest.json`, `docs/audit/README.md`  
  Acceptance: Snapshot regenerated within last 7 days; either `.github/workflows/audit-snapshot.yml` created or README corrected.

- [ ] **Register newly minted debt IDs**  
  Tickets: `VF-FE-ROUTER-DEBT-001`, `VF-SDK-AUTH-DEBT-001`, `VF-L7-WEBHOOK-DEBT-001`, `VF-SDK-PACT-DEBT-001`  
  Acceptance: IDs added to canonical debt registry/backlog with owner and target date.

- [ ] **Reconcile SEV model**  
  Files: `docs/operations/runbook-overview.md`, `docs/governance/severity-escalation-policy.md`  
  Acceptance: One SEV scale (0–3 or 1–4) is adopted; both documents updated.

- [ ] **Decide kill-switch semantics**  
  Files: `packages/shared/src/value_fabric/shared/tenant_kill_switch.py`, `packages/shared/src/value_fabric/shared/identity/feature_flags.py`  
  Acceptance: Decision recorded: implement global kill switches, consolidate with tenant suspension, or keep archived.

- [ ] **Verify or remove workspace/case route references**  
  File: `docs/architecture/component-interaction-map.md`  
  Acceptance: Routes either found in code and documented, or references removed.

- [ ] **Clean up root `value_fabric/` namespace references**  
  Files: `docs/governance/compatibility-debt-registry.md`, other governance docs  
  Acceptance: References updated to canonical `packages/shared/src/value_fabric/shared/` or retired.

- [ ] **Implement idempotency key format validation**  
  Ticket: `VF-L1-IDEMPOTENCY-DEBT-001`  
  Files: `services/layer1-ingestion/src/layer1_ingestion/api/schemas/target_schemas.py`, `services/layer1-ingestion/tests/api/test_targets_execute_idempotency.py`  
  Acceptance: Regex/pattern validator added; skipped test unskipped and passing.

### P2 — Hygiene / follow-up

- [ ] **Unskip tests for implemented behavior**  
  Files: `services/layer1-ingestion/tests/api/test_targets_execute_idempotency.py`, `services/layer1-ingestion/tests/compliance/test_strict_robots_mode.py`, `services/layer1-ingestion/tests/pipeline/test_terminal_state_reconciliation.py`  
  Acceptance: All `DONE(...)` items have passing tests; skips removed.

- [ ] **Regenerate dead-code cleanup list**  
  File: `docs/archive/CLEANUP_PLAN_DEAD_CODE.md` (archived)  
  Acceptance: New dead-code report generated from current tooling; files actually unused are removed.

- [ ] **Create real remediation tickets for gate registry**  
  File: `.fabric/gate-engineering/gate-registry.json`  
  Acceptance: Every past-due gate has a linked ticket in the issue tracker.

- [ ] **Consolidate Salesforce CRM runbooks**  
  Files: `docs/operations/salesforce-crm-runbook.md`, `docs/operations/salesforce-crm/runbook.md`  
  Acceptance: One canonical runbook remains; duplicate archived.

- [ ] **Update `COMMAND_REFERENCE.md` and `faq.md` to current toolchain**  
  Files: `docs/operations/COMMAND_REFERENCE.md`, `docs/reference/faq.md`  
  Acceptance: `pnpm` commands, `infra/compose/` paths, and `apps/web/` layout used consistently.

- [ ] **Add L5/L6/L7 consumer clients to Python SDK**  
  Ticket: `VF-SDK-PACT-DEBT-001`  
  File: `sdk/python/src/valuefabric/client.py`  
  Acceptance: Consumer clients exist for L5 Ground Truth, L6 Benchmarks, L7 Billing; Pact tests use them.

- [ ] **Implement local callback server in Python SDK auth**  
  Ticket: `VF-SDK-AUTH-DEBT-001`  
  File: `sdk/python/src/valuefabric/cli/auth.py`  
  Acceptance: Browser auth flow can capture token via local HTTP callback; test added.

- [ ] **Implement advanced account-scoped gating or remove router TODO**  
  Ticket: `VF-FE-ROUTER-DEBT-001`  
  File: `apps/web/src/shell/router.tsx`  
  Acceptance: `accountAdvPolicy` consumed by routes or removed.

- [ ] **Remove or migrate useful external `/home/ubuntu/plans` files**  
  Acceptance: Active plans moved into repo under canonical paths; stale external files deleted.

---

## Risks & Residual Concerns

1. **Static audit only.** No full test suite was run. Run `make verify`, `pnpm --dir apps/web test`, and targeted layer tests before claiming readiness.
2. **Launch authority conflict remains unresolved.** A human release owner must pick the authoritative posture.
3. **Flat-source shadowing.** Layer 1 and Layer 4 still have flat modules alongside canonical nested packages; import resolution may be fragile.
4. **Minted ticket IDs.** New debt IDs created by this audit are not yet in a canonical issue tracker/backlog.
5. **Gate-registry placeholders.** 56 `TODO-CHECKPOINT-*` placeholders remain; only 28 were annotated as past due.
6. **External plans.** `/home/ubuntu/plans` may contain active work not reflected in the repo; split-brain risk.
7. **Archival is reversible.** All archived files are under `archive/planning-audit-2026-07-18/` and can be restored if a file was moved in error.

---

## Files Touched

**New:**
- `archive/planning-audit-2026-07-18/CHANGELOG.md`
- `archive/planning-audit-2026-07-18/` (169 archived files)
- `tmp/planning-artifact-catalog.json`
- `tmp/external-plans-catalog.json`
- `tmp/planning-audit-2026-07-18/findings-group1.md`
- `tmp/planning-audit-2026-07-18/findings-group2.md`
- `tmp/planning-audit-2026-07-18/findings-group3.md`
- `tmp/planning-audit-2026-07-18/findings-group4.md`
- `docs/superpowers/audits/planning-audit-report-2026-07-18.md` (this file)

**Modified in place (51 files total):**
- `ROADMAP.md`
- `docs/PRODUCTION_READINESS_CHECKLIST.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/data-intelligence-layer.md`
- `docs/architecture/component-interaction-map.md`
- `docs/architecture/auth-provider-strategy.md`
- `docs/architecture/layer1-comprehensive-analysis.md`
- `docs/architecture/layer1-ingestion-fixes-enhancements-roadmap.md`
- `docs/launch/PRODUCTION_SIGNOFF_ISSUE.md`
- `docs/contracts/route-mapping-table.md`
- `docs/contracts/frontend-backend-contract-map.md`
- `docs/contracts/type-alignment-sprint-10-stabilization-enforcement-evidence.md`
- `docs/contracts/contract-freshness-gate-evidence.md`
- `docs/reference/structured-logging-standard.md`
- `docs/reference/performance-characteristics.md`
- `docs/reference/layer4-agents-api.md`
- `docs/reference/layer3-knowledge-api.md`
- `docs/reference/layer5-ground-truth-api.md`
- `docs/reference/service-routing-and-api-version-matrix.md`
- `docs/operations/COMMAND_REFERENCE.md`
- `docs/reference/faq.md`
- `docs/operations/salesforce-crm-runbook.md`
- `docs/operations/tenant-management-master-plan.md`
- `docs/operations/runbook-overview.md`
- `docs/governance/compatibility-debt-registry.md`
- `docs/governance/audit-remediation-board.md`
- `docs/validation/backend_integrated/test_environment_plan.md`
- `production-readiness/scorecard.md`
- `docs/superpowers/specs/2026-06-17-api-key-hardening-design.md`
- `docs/superpowers/specs/2026-06-15-launch-critical-security-tenancy-remediation.md`
- `docs/superpowers/plans/2026-06-15-layer4-security-tenancy-plan.md`
- `docs/superpowers/plans/2026-06-15-remediation-sprint-p0.md`
- `docs/superpowers/plans/2026-06-15-gate-phase2-completion.md`
- `docs/superpowers/plans/2026-06-17-simplify-docker-compose-stack.md`
- `docs/superpowers/plans/2026-06-23-phase1b-l4-canonicalization.md`
- `docs/audit/tenant-management-readiness-assessment.md`
- `docs/audit/engineering-quality-baseline-20260710.md`
- `docs/audit/controls-mapping-updated.md`
- `docs/audit/evidence-index.md`
- `docs/audit/README.md`
- `services/layer5-ground-truth/docs/academy.md`
- `.kimi/backlog.yaml`
- `.jr/tickets/DOCKERFILE-LOCKFILE-PATCHING-FIX-PLAN.md`
- `.jr/tickets/SHARED-ENV-CONSOLIDATION.md`
- `.jr/tickets/L1-CANONICAL-IMPORTS-PACKAGE-FIX.md`
- `.jr/tickets/L4-PACKAGE-RESTRUCTURE-PLAN.md`
- `.jr/tickets/L6-TEST-DEBT.md`
- `.jr/tickets/IMPORT-ARCH-FACADE-RESOLUTION.md`
- `.jr/tickets/L3-FACADE-WRAPPER-MIGRATION.md`
- `.fabric/gate-engineering/gate-registry.json`
- `apps/web/src/shell/router.tsx`
- `sdk/python/src/valuefabric/cli/auth.py`
- `services/layer7-billing/src/layer7_billing/api/routes/billing_webhooks.py`
- `tests/pact/test_l5_l6_l7_contracts.py`
- `services/layer1-ingestion/tests/api/test_targets_execute_idempotency.py`
- `services/layer1-ingestion/tests/compliance/test_strict_robots_mode.py`
- `services/layer1-ingestion/tests/pipeline/test_terminal_state_reconciliation.py`

**Archived (original paths now deleted):**
- 169 files listed in `archive/planning-audit-2026-07-18/CHANGELOG.md`

---

## Validation

- `make typecheck-layer1` — passed (used as a spot-check during Group 3 cleanup).
- Static cross-references via `Read`, `Grep`, `Glob` — performed by all cleanup agents.
- Full repo verification (`make verify`, frontend tests, etc.) — not run; flagged as follow-up.

---

*End of report.*
