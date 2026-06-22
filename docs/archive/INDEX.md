# Archived documentation index

This index catalogues historical reports retained for traceability. Each entry
links the original file in place (banner-stamped `STATUS: ARCHIVED`) and points
to the current canonical replacement.

> Files listed here are **not** moved physically — they remain at their original
> paths to avoid breaking external bookmarks and historical commit references.
> A follow-up commit may relocate them under `docs/archive/quality-reports/`
> using `git mv` once link checkers and external references have been audited.

## Audit & analysis reports

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [DOCUMENTATION_AUDIT_REPORT.md](../DOCUMENTATION_AUDIT_REPORT.md) | 2026-05-03 | This documentation refresh pass and the Diátaxis index at [docs/README.md](../README.md) |
| [BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md](../BACKEND_FRONTEND_ALIGNMENT_ANALYSIS.md) | 2026 | [contracts/GOVERNANCE.md](../../contracts/GOVERNANCE.md), [contracts/openapi/](../../contracts/openapi/) |
| [misalignment-report.md](../misalignment-report.md) | 2026-05-02 | [contracts/GOVERNANCE.md](../../contracts/GOVERNANCE.md) |
| [test-quality-audit.md](../test-quality-audit.md) | 2026-05-01 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [test-audit-2026-04-28.md](../test-audit-2026-04-28.md) | 2026-04-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |

## Security reports

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [SECURITY_FIXES_EXECUTION_LOG.md](../SECURITY_FIXES_EXECUTION_LOG.md) | 2026-04-27 | [SECURITY.md](../../SECURITY.md), [security/](../security/), [security-gates.md](../security-gates.md) |
| [SECURITY_FIXES_SUMMARY.md](../SECURITY_FIXES_SUMMARY.md) | 2026-04-27 | [SECURITY.md](../../SECURITY.md), [security/](../security/) |
| [MCP_GATEWAY_SECURITY_ASSESSMENT_2026-04-24.md](../MCP_GATEWAY_SECURITY_ASSESSMENT_2026-04-24.md) | 2026-04-24 | [reference/](../reference/), [security/](../security/) |

## Migration / refactor logs

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) | — | [NAVIGATION_ARCHITECTURE.md](../NAVIGATION_ARCHITECTURE.md), [DESIGN.md](../../DESIGN.md) |
| [CHANGES.md](../CHANGES.md) | 2026-04-21 | [CHANGELOG.md](../../CHANGELOG.md) |
| [migration-note-layer56-canonical-imports.md](../migration-note-layer56-canonical-imports.md) | 2026-05-06 | Direction reversed by [ADR-027](../architecture/ADR-021-layer-3-canonical-runtime-path.md); see [reference/layer-runtime-path-governance.md](../reference/layer-runtime-path-governance.md) |

---

## 2026-06-22 Documentation Cleanup

Archived duplicate environment configuration files:

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [.env.dev.example](../../.env.dev.example) | 2026-06-22 | [.env.example](../../.env.example) with environment profile documentation in [docs/getting-started/environment.md](../getting-started/environment.md) |
| [.env.production-compose.template](../../.env.production-compose.template) | 2026-06-22 | [.env.example](../../.env.example) with environment profile documentation in [docs/getting-started/environment.md](../getting-started/environment.md) |
| [.env.smoke.template](../../.env.smoke.template) | 2026-06-22 | [.env.example](../../.env.example) with environment profile documentation in [docs/getting-started/environment.md](../getting-started/environment.md) |

**Note:** These files were physically moved to `docs/archive/root/` to reduce root-level duplication.

Archived duplicate security documentation:

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [docs/tenant-isolation.md](../tenant-isolation.md) | 2026-06-22 | [docs/security/multi-tenancy.md](../security/multi-tenancy.md) (testing content merged as new section) |
| [docs/SECRETS.md](../SECRETS.md) | 2026-06-22 | [docs/security/secrets-management.md](../security/secrets-management.md) (inventory, rotation procedures, access control merged) |

**Note:** These files were physically moved to `docs/archive/docs/`.

Archived duplicate development documentation:

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [docs/DEVELOPMENT.md](../DEVELOPMENT.md) | 2026-06-22 | [docs/getting-started/quickstart.md](../getting-started/quickstart.md), [docs/development/](../development/), and [docs/security/secrets-management.md](../security/secrets-management.md) (Vault dev mode) |

**Note:** This file was physically moved to `docs/archive/docs/`.

---

## 2026-05-28 Documentation Cleanup

Archived temporal reports, redirect-only files, and outdated documentation:

| File | Date | Replaced by |
| ---- | ---- | ----------- |
| [ROADMAP.md](../../ROADMAP.md) | 2026-05-28 | [docs/core-concepts/architecture.md](../core-concepts/architecture.md) |
| [DEPRECATIONS.md](../DEPRECATIONS.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/deprecated-namespace-migration-tracker.md](../reference/deprecated-namespace-migration-tracker.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/deprecated-namespace-support-policy.md](../reference/deprecated-namespace-support-policy.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer1-compatibility-deprecation.md](../reference/layer1-compatibility-deprecation.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [canonical-paths-policy.md](../../canonical-paths-policy.md) | 2026-05-28 | [reference/layer-runtime-path-governance.md](../reference/layer-runtime-path-governance.md) |
| [spec-round2-followup.md](../../spec-round2-followup.md) | 2026-05-28 | Orphaned temporal artifact, no replacement |
| [architecture/ADR-001-fabric-harness-as-the-governed-execution-spine-for-agentic-value-workflows.md](../architecture/ADR-001-fabric-harness-as-the-governed-execution-spine-for-agentic-value-workflows.md) | 2026-05-28 | [explanations/adr/ADR-001-fabric-harness-as-the-governed-execution-spine-for-agentic-value-workflows.md](../explanations/adr/ADR-001-fabric-harness-as-the-governed-execution-spine-for-agentic-value-workflows.md) |
| [architecture/ADR-021-layer-3-canonical-runtime-path.md](../architecture/ADR-021-layer-3-canonical-runtime-path.md) | 2026-05-28 | [explanations/adr/ADR-021-layer-3-canonical-runtime-path.md](../explanations/adr/ADR-021-layer-3-canonical-runtime-path.md) |
| [reference/layer1-fixes-enhancements-roadmap.md](../reference/layer1-fixes-enhancements-roadmap.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer3-cypher-security-inventory.md](../reference/layer3-cypher-security-inventory.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer3-graph-field-cutover.md](../reference/layer3-graph-field-cutover.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer3-layer6-wrapper-policy.md](../reference/layer3-layer6-wrapper-policy.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer3-tenant-isolation-audit.md](../reference/layer3-tenant-isolation-audit.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer4-deterministic-replay-spec.md](../reference/layer4-deterministic-replay-spec.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer4-frontend-contract-regeneration.md](../reference/layer4-frontend-contract-regeneration.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer5-api-compatibility-policy.md](../reference/layer5-api-compatibility-policy.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer5-observability-schema.md](../reference/layer5-observability-schema.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [reference/layer6-drift-audit-artifact-index.md](../reference/layer6-drift-audit-artifact-index.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [governance/auth-tenant-todo-audit-2026-05-12.md](../governance/auth-tenant-todo-audit-2026-05-12.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [governance/contract-remediation-queue-by-layer.md](../governance/contract-remediation-queue-by-layer.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [governance/production-readiness-status-2026-05-14.md](../governance/production-readiness-status-2026-05-14.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [governance/repo-hygiene-report-governance-check.md](../governance/repo-hygiene-report-governance-check.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [governance/repo-hygiene-work-items-2026-05-12.md](../governance/repo-hygiene-work-items-2026-05-12.md) | 2026-05-28 | [governance/compatibility-debt-registry.md](../governance/compatibility-debt-registry.md) |
| [security/triage-notes-2026-04-14.md](../security/triage-notes-2026-04-14.md) | 2026-05-28 | [security/](../security/) |
| [operations/tenant-management-phase-1-rls-hardening-rescoped.md](../operations/tenant-management-phase-1-rls-hardening-rescoped.md) | 2026-05-28 | [operations/tenant-management-master-plan.md](../operations/tenant-management-master-plan.md) |
| [operations/tenant-management-phase-1-rls-hardening.md](../operations/tenant-management-phase-1-rls-hardening.md) | 2026-05-28 | [operations/tenant-management-master-plan.md](../operations/tenant-management-master-plan.md) |
| [operations/tenant-management-phase-2-provisioning.md](../operations/tenant-management-phase-2-provisioning.md) | 2026-05-28 | [operations/tenant-management-master-plan.md](../operations/tenant-management-master-plan.md) |
| [operations/tenant-management-phase-3-control-plane.md](../operations/tenant-management-phase-3-control-plane.md) | 2026-05-28 | [operations/tenant-management-master-plan.md](../operations/tenant-management-master-plan.md) |
| [operations/tenant-management-remediation-plan.md](../operations/tenant-management-remediation-plan.md) | 2026-05-28 | [operations/tenant-management-master-plan.md](../operations/tenant-management-master-plan.md) |
| [operations/tenant-management-remediation-verification.md](../operations/tenant-management-remediation-verification.md) | 2026-05-28 | [operations/tenant-management-master-plan.md](../operations/tenant-management-master-plan.md) |
| [operations/tenant-management-security-audit.json](../operations/tenant-management-security-audit.json) | 2026-05-28 | [operations/tenant-management-master-plan.md](../operations/tenant-management-master-plan.md) |
| [testing/TEST_FIXES_APPLIED.md](../testing/TEST_FIXES_APPLIED.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [testing/assurance-remediation-report.md](../testing/assurance-remediation-report.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [testing/pre-existing-failures.md](../testing/pre-existing-failures.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [testing/rewrite-queue.md](../testing/rewrite-queue.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [testing/test_pass_rate_improvements_2026-05-06.md](../testing/test_pass_rate_improvements_2026-05-06.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [apps/web/docs/UI_UX_AUDIT.md](../../apps/web/docs/UI_UX_AUDIT.md) | 2026-05-28 | [DESIGN.md](../../DESIGN.md) |
| [apps/web/docs/hook-coverage-qa-notes.md](../../apps/web/docs/hook-coverage-qa-notes.md) | 2026-05-28 | [DESIGN.md](../../DESIGN.md) |
| [apps/web/docs/calculator-route-migration.md](../../apps/web/docs/calculator-route-migration.md) | 2026-05-28 | [DESIGN.md](../../DESIGN.md) |
| [reports/autonomous-test-inventory.md](../../reports/autonomous-test-inventory.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [reports/autonomous-production-invariants.md](../../reports/autonomous-production-invariants.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [reports/autonomous-test-gap-analysis.md](../../reports/autonomous-test-gap-analysis.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [reports/autonomous-test-validation.md](../../reports/autonomous-test-validation.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |
| [reports/autonomous-test-assurance-pr-ready.md](../../reports/autonomous-test-assurance-pr-ready.md) | 2026-05-28 | [reference/testing-strategy.md](../reference/testing-strategy.md) |

**Note:** These files were physically moved to `docs/archive/2026-05-28/` to reduce documentation clutter.

---

## Existing archived materials

- [quality-reports/](quality-reports/) — earlier batch of quality reports.
- [archive-registry.md](archive-registry.md) — registry of previously archived items.
- [MIGRATION_REPORT.md](MIGRATION_REPORT.md) — prior migration report.

## Files intentionally **not** archived

These were considered and kept active because they are evergreen references or
rolling baselines, not point-in-time reports:

- [current-failures.md](../current-failures.md) — rolling test baseline; updated continuously.
- [SECURITY_TRIAGE_RUBRIC.md](../SECURITY_TRIAGE_RUBRIC.md) — evergreen classification reference.
- [LAUNCH_RUNBOOK.md](../LAUNCH_RUNBOOK.md) — active production-launch runbook.
