# Planning Artifact Audit Changelog — 2026-07-18

## Summary

- **Audit date:** 2026-07-18
- **Total archived files:** 169
- **Archived container directories:** 42
- **Files updated in place:** 51 (27 from Group 1, 9 from Group 2, 15 from Group 3)
- **No archived files were modified** — only moved and documented.

### Archived files by source directory

| Source directory | Files archived |
|---|---|
| `docs/` | 129 |
| `.devin/` | 25 |
| `archive/` | 13 |
| `packages/` | 1 |
| `.windsurf/` | 1 |
| **Total** | **169** |

---

## Archived Artifacts

| Original Path | Archived Path | Reason |
|---|---|---|
| `docs/roadmap.md` | `archive/planning-audit-2026-07-18/docs/roadmap.md` | Pure redirect to `../ROADMAP.md`; canonical roadmap lives at repo root. |
| `docs/IMPLEMENTATION_PLAN.md` | `archive/planning-audit-2026-07-18/docs/IMPLEMENTATION_PLAN.md` | Marked `STATUS: ARCHIVED`; references non-existent `frontend/client/` paths and `NAVIGATION_ARCHITECTURE.md`. |
| `docs/WORKFLOW_API_DESIGN.md` | `archive/planning-audit-2026-07-18/docs/WORKFLOW_API_DESIGN.md` | Dated 2026-05-06 "Design Phase"; the endpoints it proposed are now implemented, making the design doc stale. |
| `docs/architecture/ui-component-migration-checklist.md` | `archive/planning-audit-2026-07-18/docs/architecture/ui-component-migration-checklist.md` | References non-existent `frontend/client/src/components/ui/` and `_ui-prototype/` trees. |
| `docs/architecture/ui-component-canonicalization.md` | `archive/planning-audit-2026-07-18/docs/architecture/ui-component-canonicalization.md` | Same as above; canonical UI primitives are under `apps/web/src/components/ui/`. |
| `docs/architecture/legacy-value-fabric-architecture.md` | `archive/planning-audit-2026-07-18/docs/architecture/legacy-value-fabric-architecture.md` | Header says it was migrated during legacy path cleanup; assigns Layer 4 port `8002` (should be `8004`). |
| `docs/contracts/MISSING_ROUTES_IMPLEMENTATION_PLAN.md` | `archive/planning-audit-2026-07-18/docs/contracts/MISSING_ROUTES_IMPLEMENTATION_PLAN.md` | Formula Create/Update/Delete routes are now implemented in L3 and consumed by the frontend. |
| `docs/reference/VERSIONING.md` | `archive/planning-audit-2026-07-18/docs/reference/VERSIONING.md` | 9-line stub/redirect to other policy files. |
| `docs/reference/audit-events-catalog.md` | `archive/planning-audit-2026-07-18/docs/reference/audit-events-catalog.md` | Dated 2024-01; references deleted modules like `services/shared/src/value_fabric/shared/audit_events.py`. |
| `docs/reference/audit-logging-middleware.md` | `archive/planning-audit-2026-07-18/docs/reference/audit-logging-middleware.md` | References non-existent `services/shared/src/value_fabric/shared/audit_middleware.py`. |
| `docs/reference/facade-compatibility-shims.md` | `archive/planning-audit-2026-07-18/docs/reference/facade-compatibility-shims.md` | Claims active `value_fabric/layer*/` shim directories with 253 retained imports; no such directories exist. |
| `docs/operations/data-intelligence-layer-scope.md` | `archive/planning-audit-2026-07-18/docs/operations/data-intelligence-layer-scope.md` | Aspirational 8-week roadmap describing modules (e.g., `CalibrationService`, `OpportunityHypothesis`) not present in code. |
| `docs/governance/frontend-legacy-deprecation-migration.md` | `archive/planning-audit-2026-07-18/docs/governance/frontend-legacy-deprecation-migration.md` | References deleted files (`apps/web/src/api/legacy.ts`, `apps/web/src/components/WfPrimitives.tsx`). |
| `docs/governance/layer3-service-source-inventory.md` | `archive/planning-audit-2026-07-18/docs/governance/layer3-service-source-inventory.md` | Claims canonical runtime under root `value_fabric/layer3/`, which no longer exists. |
| `docs/governance/branch-inventory.md` | `archive/planning-audit-2026-07-18/docs/governance/branch-inventory.md` | Generated branch snapshot from 2026-06-04; branch ages/PR associations are stale. |
| `docs/governance/layer1-alembic-revalidation-2026-05-12.md` | `archive/planning-audit-2026-07-18/docs/governance/layer1-alembic-revalidation-2026-05-12.md` | Lists only migrations `001`–`010`; current Layer 1 has through `021_add_v3_0_source_schema.py`. |
| `docs/governance/layer5-release-gates.md` | `archive/planning-audit-2026-07-18/docs/governance/layer5-release-gates.md` | References missing registers (`layer5-issue-register.md`, `layer5-release-issue-register.md`, `layer5-tenant-exceptions.md`). |
| `docs/governance/graph-storage-encryption-control.md` | `archive/planning-audit-2026-07-18/docs/governance/graph-storage-encryption-control.md` | References missing `k8s/envs/prod/neo4j-aura-patch.yml`. |
| `docs/governance/ai-generated-dependency-review-policy.md` | `archive/planning-audit-2026-07-18/docs/governance/ai-generated-dependency-review-policy.md` | References missing `docs/governance/approved-licenses.md`. |
| `docs/validation/layer1-e2e-validation-2026-04-30-1736.md` | `archive/planning-audit-2026-07-18/docs/validation/layer1-e2e-validation-2026-04-30-1736.md` | Old snapshot with superseded paths (`services/layer1-ingestion/src/crawler/...`, `src/shared/identity/middleware_sync.py`). |
| `docs/validation/layer2-connect-test-debug-2026-04-30.md` | `archive/planning-audit-2026-07-18/docs/validation/layer2-connect-test-debug-2026-04-30.md` | Route inventory does not match current Layer 2 API. |
| `docs/validation/security_regression/i04_mandatory_security_regression_gate_evidence.md` | `archive/planning-audit-2026-07-18/docs/validation/security_regression/i04_mandatory_security_regression_gate_evidence.md` | Wrong workflow file (`test-mandatory.yml`) and wrong test path (`tests/ci/...`). |
| `docs/validation/live-workflow-validation.md` | `archive/planning-audit-2026-07-18/docs/validation/live-workflow-validation.md` | Uses root-level compose paths and claims `.github/workflows/live-workflow-validation.yml` is installed; both are stale. |
| `docs/validation/live_readiness_second_three_sprint_plan.md` | `archive/planning-audit-2026-07-18/docs/validation/live_readiness_second_three_sprint_plan.md` | Historical sprint plan; superseded by current runbook. |
| `docs/validation/live_readiness_third_three_sprint_plan.md` | `archive/planning-audit-2026-07-18/docs/validation/live_readiness_third_three_sprint_plan.md` | Historical sprint plan; superseded by current runbook. |
| `docs/validation/live_readiness_fourth_three_sprint_plan.md` | `archive/planning-audit-2026-07-18/docs/validation/live_readiness_fourth_three_sprint_plan.md` | Historical sprint plan; superseded by current runbook. |
| `docs/validation/live_readiness_three_sprint_plan.md` | `archive/planning-audit-2026-07-18/docs/validation/live_readiness_three_sprint_plan.md` | Historical sprint plan; superseded by current runbook. |
| `docs/validation/sprint-3-completion-summary-2026-05-04.md` | `archive/planning-audit-2026-07-18/docs/validation/sprint-3-completion-summary-2026-05-04.md` | Superseded; references root-level compose files that moved to `infra/compose/`. |
| `docs/validation/backend-startup-issue-2026-05-04.md` | `archive/planning-audit-2026-07-18/docs/validation/backend-startup-issue-2026-05-04.md` | Superseded by later live-stack evidence in `docs/launch/launch-blocker-register.md`. |
| `docs/validation/launch_readiness_final_sign_off_evidence.md` | `archive/planning-audit-2026-07-18/docs/validation/launch_readiness_final_sign_off_evidence.md` | Dated 2026-05-08/11 launch sign-off; superseded by 2026-06-16 launch posture. |
| `docs/validation/architecture-reduction-verification-2026-05-05.md` | `archive/planning-audit-2026-07-18/docs/validation/architecture-reduction-verification-2026-05-05.md` | References mirrored `value_fabric/layer1/` and `value_fabric/layer3/` trees that no longer exist. |
| `packages/feature-flags/src/kill-switch-spec.md` | `archive/planning-audit-2026-07-18/packages/feature-flags/src/kill-switch-spec.md` | Describes a global feature-flag kill-switch framework (endpoints, PagerDuty, `KillSwitch` class) that is not implemented; current code has tenant suspension and standard feature flags only. |
| `.devin/plans/` | `archive/planning-audit-2026-07-18/.devin/plans/` | Transient execution-status checkpoint dumps and obsolete completion summaries; superseded by newer checkpoints or live state. |
| `.windsurf/plans/launch-readiness-2026-06-21.md` | `archive/planning-audit-2026-07-18/.windsurf/plans/launch-readiness-2026-06-21.md` | Superseded by `.windsurf/plans/launch-readiness-2026-06-22.md`. |
| `docs/audit/production-readiness-2026-05-27.md` | `archive/planning-audit-2026-07-18/docs/audit/production-readiness-2026-05-27.md` | Superseded by `docs/audit/engineering-quality-baseline-20260710.md`; claims about L7 billing maturity and duplicate source trees are contradicted by current code. |
| `docs/audit/layer3-graph-execution-inventory.md` | `archive/planning-audit-2026-07-18/docs/audit/layer3-graph-execution-inventory.md` | Every path uses the removed `value_fabric/layer3/` namespace; canonical modules now live under `services/layer3-knowledge/src/`. |
| `docs/audit/l3-neo4j-label-tenant-classification.md` | `archive/planning-audit-2026-07-18/docs/audit/l3-neo4j-label-tenant-classification.md` | 2026-05-05 gap report; tenant scoping, constraints, and indexes it claimed missing now exist in `services/layer3-knowledge/src/schema/constraints.py` and route files. |
| `docs/superpowers/plans/2026-06-07-academy-module.md` | `archive/planning-audit-2026-07-18/docs/superpowers/plans/2026-06-07-academy-module.md` | Implemented; canonical module lives in `services/layer5-ground-truth/docs/academy.md` and `services/layer5-ground-truth/src/layer5_ground_truth/{models/academy.py,api/academy_router.py,services/academy_service.py}`. |
| `docs/superpowers/plans/2026-06-14-remediation-sprint-plan.md` | `archive/planning-audit-2026-07-18/docs/superpowers/plans/2026-06-14-remediation-sprint-plan.md` | Superseded by `docs/superpowers/plans/2026-06-15-remediation-sprint-p0.md`. |
| `docs/superpowers/plans/2026-06-15-shared-auth-webhook-plan.md` | `archive/planning-audit-2026-07-18/docs/superpowers/plans/2026-06-15-shared-auth-webhook-plan.md` | Implemented; `_bypass_flags_are_set` / `_raise_if_bypass_in_nonlocal_env` helpers exist in `packages/shared/src/value_fabric/shared/identity/auth_mode.py`. |
| `docs/superpowers/plans/2026-06-22-fix-usePersistFn-typescript-build.md` | `archive/planning-audit-2026-07-18/docs/superpowers/plans/2026-06-22-fix-usePersistFn-typescript-build.md` | Implemented; `apps/web/src/hooks/usePersistFn.ts` already contains the `as ReturnType<T>` cast. |
| `docs/superpowers/plans/2026-06-22-value-fabric-corrected-remediation.md` | `archive/planning-audit-2026-07-18/docs/superpowers/plans/2026-06-22-value-fabric-corrected-remediation.md` | Catalogued as archived content; large remediation narrative superseded by `2026-06-22-sprint1-code-health-remediation.md` and Phase 0 assessment. |
| `docs/superpowers/plans/launch-readiness-runtime-2026-06-13.md` | `archive/planning-audit-2026-07-18/docs/superpowers/plans/launch-readiness-runtime-2026-06-13.md` | Release-candidate certification plan for `rc-2026-06-13-116815f3`; horizon has passed. |
| `docs/superpowers/specs/2026-06-07-pydantic-deprecation-cleanup-design.md` | `archive/planning-audit-2026-07-18/docs/superpowers/specs/2026-06-07-pydantic-deprecation-cleanup-design.md` | Implemented; no affected files still use `class Config:`. |
| `docs/superpowers/specs/2026-06-22-production-readiness-top5-design.md` | `archive/planning-audit-2026-07-18/docs/superpowers/specs/2026-06-22-production-readiness-top5-design.md` | Marked deprecated/superseded in catalog; overtaken by `engineering-quality-baseline-20260710.md` and later remediation plans. |
| `docs/archive/2026-04-19/` | `archive/planning-audit-2026-07-18/docs/archive/2026-04-19/` | Explicitly ARCHIVED phase-1 reports; superseded/redirected per `docs/archive/INDEX.md`. |
| `docs/archive/2026-04-27/` | `archive/planning-audit-2026-07-18/docs/archive/2026-04-27/` | Explicitly ARCHIVED phase-2 reports; superseded/redirected per `docs/archive/INDEX.md`. |
| `docs/archive/2026-05-28/ROADMAP.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/ROADMAP.md` | 4,649-line completion roadmap superseded by `docs/core-concepts/architecture.md` per `docs/archive/INDEX.md`; contains internal contradictions. |
| `docs/archive/2026-05-28/layer1-fixes-enhancements-roadmap.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer1-fixes-enhancements-roadmap.md` | Duplicate of `docs/architecture/layer1-ingestion-fixes-enhancements-roadmap.md`; references removed `value_fabric/layer1/`. |
| `docs/archive/2026-05-28/tenant-management-phase-1-rls-hardening.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/tenant-management-phase-1-rls-hardening.md` | Superseded by `docs/operations/tenant-management-master-plan.md`; uses old `shared/identity/` and `layer4-agents/src/tenants/` paths. |
| `docs/archive/2026-05-28/tenant-management-phase-1-rls-hardening-rescoped.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/tenant-management-phase-1-rls-hardening-rescoped.md` | Superseded by `docs/operations/tenant-management-master-plan.md`; uses old `shared/identity/` and `layer4-agents/src/tenants/` paths. |
| `docs/archive/2026-05-28/tenant-management-phase-2-provisioning.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/tenant-management-phase-2-provisioning.md` | Superseded by `docs/operations/tenant-management-master-plan.md`; uses old `shared/identity/` and `layer4-agents/src/tenants/` paths. |
| `docs/archive/2026-05-28/tenant-management-phase-3-control-plane.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/tenant-management-phase-3-control-plane.md` | Superseded by `docs/operations/tenant-management-master-plan.md`; uses old `shared/identity/` and `layer4-agents/src/tenants/` paths. |
| `docs/archive/2026-05-28/tenant-management-remediation-plan.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/tenant-management-remediation-plan.md` | Superseded by `docs/operations/tenant-management-master-plan.md`; uses old `shared/identity/` and `layer4-agents/src/tenants/` paths. |
| `docs/archive/2026-05-28/tenant-management-remediation-verification.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/tenant-management-remediation-verification.md` | Superseded by `docs/operations/tenant-management-master-plan.md`; uses old `shared/identity/` and `layer4-agents/src/tenants/` paths. |
| `docs/archive/2026-05-28/DEPRECATIONS.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/DEPRECATIONS.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/deprecated-namespace-migration-tracker.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/deprecated-namespace-migration-tracker.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/deprecated-namespace-support-policy.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/deprecated-namespace-support-policy.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer1-compatibility-deprecation.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer1-compatibility-deprecation.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer3-cypher-security-inventory.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer3-cypher-security-inventory.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer3-graph-field-cutover.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer3-graph-field-cutover.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer3-layer6-wrapper-policy.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer3-layer6-wrapper-policy.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer3-tenant-isolation-audit.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer3-tenant-isolation-audit.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer4-deterministic-replay-spec.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer4-deterministic-replay-spec.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer4-frontend-contract-regeneration.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer4-frontend-contract-regeneration.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer5-api-compatibility-policy.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer5-api-compatibility-policy.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer5-observability-schema.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer5-observability-schema.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/layer6-drift-audit-artifact-index.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/layer6-drift-audit-artifact-index.md` | Redirected by `docs/archive/INDEX.md` to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/UI_UX_AUDIT.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/UI_UX_AUDIT.md` | Redirected by `docs/archive/INDEX.md` to `DESIGN.md`. |
| `docs/archive/2026-05-28/hook-coverage-qa-notes.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/hook-coverage-qa-notes.md` | Redirected by `docs/archive/INDEX.md` to `DESIGN.md`. |
| `docs/archive/2026-05-28/calculator-route-migration.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/calculator-route-migration.md` | Redirected by `docs/archive/INDEX.md` to `DESIGN.md`. |
| `docs/archive/2026-05-28/TEST_FIXES_APPLIED.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/TEST_FIXES_APPLIED.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/assurance-remediation-report.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/assurance-remediation-report.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/pre-existing-failures.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/pre-existing-failures.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/rewrite-queue.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/rewrite-queue.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/test_pass_rate_improvements_2026-05-06.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/test_pass_rate_improvements_2026-05-06.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/autonomous-production-invariants.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/autonomous-production-invariants.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/autonomous-test-assurance-pr-ready.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/autonomous-test-assurance-pr-ready.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/autonomous-test-gap-analysis.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/autonomous-test-gap-analysis.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/autonomous-test-inventory.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/autonomous-test-inventory.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/autonomous-test-validation.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/autonomous-test-validation.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/summary.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/summary.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/triage-notes-2026-04-14.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/triage-notes-2026-04-14.md` | Temporal remediation/governance reports redirected to `docs/reference/testing-strategy.md`. |
| `docs/archive/2026-05-28/auth-tenant-todo-audit-2026-05-12.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/auth-tenant-todo-audit-2026-05-12.md` | Governance temporal reports redirected to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/contract-remediation-queue-by-layer.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/contract-remediation-queue-by-layer.md` | Governance temporal reports redirected to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/production-readiness-status-2026-05-14.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/production-readiness-status-2026-05-14.md` | Governance temporal reports redirected to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/repo-hygiene-report-governance-check.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/repo-hygiene-report-governance-check.md` | Governance temporal reports redirected to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/2026-05-28/repo-hygiene-work-items-2026-05-12.md` | `archive/planning-audit-2026-07-18/docs/archive/2026-05-28/repo-hygiene-work-items-2026-05-12.md` | Governance temporal reports redirected to `docs/governance/compatibility-debt-registry.md`. |
| `docs/archive/CLEANUP_PLAN_DEAD_CODE.md` | `archive/planning-audit-2026-07-18/docs/archive/CLEANUP_PLAN_DEAD_CODE.md` | Partially inaccurate dead-code list (e.g., claims `NarrativeTab.tsx` is unused while file still exists). |
| `docs/archive/quality-reports/` | `archive/planning-audit-2026-07-18/docs/archive/quality-reports/` | Older or duplicate quality reports superseded by the `2026-05-22/` bundle or `docs/reference/testing-strategy.md`. |
| `docs/archive/evidence/reports/2026-06-18/` | `archive/planning-audit-2026-07-18/docs/archive/evidence/reports/2026-06-18/` | Near-duplicates of other 2026-06-18 / 2026-05-28 inventories. |
| `docs/archive/tenant-management-project-plan-original.md` | `archive/planning-audit-2026-07-18/docs/archive/tenant-management-project-plan-original.md` | Original tenant-management plans predating canonical paths. |
| `docs/archive/tenant-management-phase-1-original-schema-per-tenant.md` | `archive/planning-audit-2026-07-18/docs/archive/tenant-management-phase-1-original-schema-per-tenant.md` | Original tenant-management plans predating canonical paths. |
| `archive/fabric-audit/fabric_audit/` | `archive/planning-audit-2026-07-18/archive/fabric-audit/fabric_audit/` | 2025–2026 audits with claims (no PostgreSQL support, 88 raw `HTTPException` sites, Medtronic demo data) contradicted by current code. |
| `archive/specs/specs/` | `archive/planning-audit-2026-07-18/archive/specs/specs/` | Early/mid-2026 specs superseded by implemented code; reference non-existent paths (`frontend/client/src/`, generated modules, old L1/L3 endpoints). |

> **Note on empty directory stubs:** The following archived directories contain no files and are retained only as path stubs: `docs/launch/`, `docs/validation/backend_integrated/`, `ops/incident/runbooks/`, `production-readiness/`, `scripts/ci/`, `scripts/verification/`, `services/`.

---

## Files Updated In Place

A total of **51 active files** received audit notes, path corrections, or status corrections without being moved.

- **Group 1 (27 files):** `ROADMAP.md`; `docs/architecture/system-overview.md`, `data-intelligence-layer.md`, `component-interaction-map.md`, `auth-provider-strategy.md`, `layer1-comprehensive-analysis.md`; `docs/launch/PRODUCTION_SIGNOFF_ISSUE.md`; `docs/contracts/route-mapping-table.md`, `frontend-backend-contract-map.md`, `type-alignment-sprint-10-stabilization-enforcement-evidence.md`, `contract-freshness-gate-evidence.md`; `docs/reference/structured-logging-standard.md`, `performance-characteristics.md`, `layer4-agents-api.md`, `layer3-knowledge-api.md`, `layer5-ground-truth-api.md`, `service-routing-and-api-version-matrix.md`, `faq.md`; `docs/operations/COMMAND_REFERENCE.md`, `salesforce-crm-runbook.md`, `tenant-management-master-plan.md`, `runbook-overview.md`; `docs/governance/compatibility-debt-registry.md`, `audit-remediation-board.md`; `docs/validation/backend_integrated/test_environment_plan.md`; `production-readiness/scorecard.md`; `docs/PRODUCTION_READINESS_CHECKLIST.md`.
- **Group 2 (9 files):** `.kimi/backlog.yaml` (P0-001, P0-002, P0-005 marked completed); `.jr/tickets/DOCKERFILE-LOCKFILE-PATCHING-FIX-PLAN.md`; `.jr/tickets/SHARED-ENV-CONSOLIDATION.md`; `.jr/tickets/L1-CANONICAL-IMPORTS-PACKAGE-FIX.md`; `.jr/tickets/L4-PACKAGE-RESTRUCTURE-PLAN.md`; `.jr/tickets/L6-TEST-DEBT.md`; `.jr/tickets/IMPORT-ARCH-FACADE-RESOLUTION.md`; `.jr/tickets/L3-FACADE-WRAPPER-MIGRATION.md`; `.fabric/gate-engineering/gate-registry.json` (28 stale `TODO-CHECKPOINT-*` entries annotated).
- **Group 3 (15 files):** `docs/superpowers/specs/2026-06-17-api-key-hardening-design.md`; `docs/superpowers/specs/2026-06-15-launch-critical-security-tenancy-remediation.md`; `docs/superpowers/plans/2026-06-15-layer4-security-tenancy-plan.md`; `docs/superpowers/plans/2026-06-15-remediation-sprint-p0.md`; `docs/superpowers/plans/2026-06-15-gate-phase2-completion.md`; `docs/superpowers/plans/2026-06-17-simplify-docker-compose-stack.md`; `docs/superpowers/plans/2026-06-23-phase1b-l4-canonicalization.md`; `docs/audit/tenant-management-readiness-assessment.md`; `docs/audit/engineering-quality-baseline-20260710.md`; `docs/audit/controls-mapping-updated.md`; `docs/audit/evidence-index.md`; `docs/audit/README.md`; `docs/architecture/layer1-ingestion-fixes-enhancements-roadmap.md`; `docs/operations/tenant-management-master-plan.md`; `services/layer5-ground-truth/docs/academy.md`.

---

## Contradictions / Duplicates Resolved

| Topic | Resolution |
|---|---|
| **Duplicate roadmap** | `docs/roadmap.md` redirect archived; note added to root `ROADMAP.md`. |
| **Canonical contract location** | Three-way contradiction between `system-overview.md`, `contract-ratification-memo.md`, and actual `docs/contract.md`; noted in `system-overview.md`. |
| **Layer 4 port** | `legacy-value-fabric-architecture.md` claimed `8002`; `system-overview.md` and `AGENTS.md` confirm `8004`. The stale file was archived. |
| **Layer 5 routing authority** | Contract files described direct `/api/v1/truths` calls; frontend actually uses L4 proxy `/v1/ground-truth/*`. Notes added to both contract files. |
| **Formula CRUD status** | `MISSING_ROUTES_IMPLEMENTATION_PLAN.md` and `frontend-backend-contract-map.md` said missing; `formulas.py` and `useFormulas.ts` implement it. Missing-routes plan archived; contract map updated. |
| **Workflow archive / type query** | `route-mapping-table.md` said not implemented; `workflows.py:955` and `layer4-agents.json` expose both. Note added to route mapping table. |
| **Trust-boundary guard** | Sprint 10 evidence claims files added and passing; files absent but command still wired. Note added. |
| **Severity model** | `runbook-overview.md` uses SEV-0..3 vs `severity-escalation-policy.md` SEV-1..4. Note added. |
| **Salesforce CRM runbook duplication** | `docs/operations/salesforce-crm-runbook.md` had wrong metric prefix; canonical lives at `docs/operations/salesforce-crm/runbook.md`. Note added. |
| **Launch posture** | `audit-remediation-release-readiness-matrix.md` NO-GO, `launch-blocker-register.md` GO WITH ACCEPTED RISKS, `scorecard.md` CONDITIONAL. Reconciliation notes added. |
| **Kill-switch semantics** | Global kill-switch spec archived; existing tenant suspension and feature flags retained. |
| **L4 package restructure status** | Ticket claimed complete but residual flat files remain alongside nested package; status amended to partial/cleanup pending. |
| **L1 package restructure status** | Ticket claimed complete but residual flat directories remain; audit note added. |
| **Backlog vs journal** | `.kimi/backlog.yaml` lagged `.kimi/journal.md`; statuses corrected. |
| **Complete tickets with unchecked criteria** | `DOCKERFILE-LOCKFILE-PATCHING-FIX-PLAN.md` and `SHARED-ENV-CONSOLIDATION.md` criteria checked. |
| **Duplicate launch-readiness plans** | `.windsurf/plans/launch-readiness-2026-06-21.md` archived; 2026-06-22 version retained. |
| **API-key implementation location** | `2026-06-17-api-key-hardening-design.md` points to L4 shim; canonical implementation is in `services/api/app/routers/api_keys.py`. Note added. |
| **Remediation sprint duplication** | `2026-06-14-remediation-sprint-plan.md` archived; `2026-06-15-remediation-sprint-p0.md` retained as canonical. |
| **L4 canonicalization vs baseline** | Plan pushes clean `layer4_agents/` tree but `config/ci/layer4_source_tree_baseline.json` allows 36 non-canonical entries. Note added. |
| **L3 tenant-scoping audits** | 2026-05-05 gap report contradicted by current scoped/allowlisted inventory. Stale report archived. |
| **Production-readiness claims** | 2026-05-27 audit contradicted by current L7 structure and duplicate-tree checks. Archived. |
| **Quality-baseline typecheck** | Baseline reported `make typecheck-layer1` fails; current run passes. Note added. |
| **Duplicate audit snapshots** | `docs/audit/snapshots/audit-snapshot-2026-05-07T114542+0000.json` and `latest.json` are identical and 10+ weeks old. Noted. |
| **Duplicate test inventories / gap analyses** | Multiple dated variants in `docs/archive/` give contradictory counts. Superseded copies archived. |
| **Root archive specs vs code** | e.g., `context-targets-admin.spec.md` requests target routes that do not match current OpenAPI. Archived. |

---

## Sources

- `tmp/planning-audit-2026-07-18/findings-group1.md`
- `tmp/planning-audit-2026-07-18/findings-group2.md`
- `tmp/planning-audit-2026-07-18/findings-group3.md`
- Direct inspection of `archive/planning-audit-2026-07-18/`
