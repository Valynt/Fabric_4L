# CI Workflow Consolidation Record

S6-6 closed the workflow sprawl gate by consolidating duplicate and reporting
workflows into canonical GitHub Actions files. The repository-level invariant is
now fewer than 50 workflow YAML files in `.github/workflows/`, enforced by
`scripts/ci/verify_workflow_registry.py`.

## Canonical workflow ownership

| Gate family | Canonical workflow | Consolidated coverage |
| --- | --- | --- |
| Fast PR validation | `pr-checks.yml` | Legacy `test.yml`, mandatory test, verify, and preflight signals now stay under the primary PR gate family. |
| Security scanning | `security-gates.yml` | Secret guardrail and extended security validation coverage stays under the canonical security gate family. |
| Contract enforcement | `contract-compliance.yml` | Contract drift, scorecard, and governance checks remain merge-visible. |
| Release readiness | `prod-readiness.yml` | Launch and production-readiness checklist evidence stays under the production readiness gate. |
| Code scanning | `codeql.yml` | CodeQL has one canonical workflow. |
| Chaos and operational drills | `chaos-testing.yml`, `dr-drill.yml` | Chaos smoke, restore verification, and game-day evidence are represented by canonical operational evidence workflows. |
| Kubernetes readiness | `k8s-readiness.yml` | Kubernetes validation remains under one readiness workflow. |
| Repository hygiene | `repo-hygiene.yml` | Branch cleanup, stale PR, CI backlog, README sync, and KPI reporting are consolidated as repository hygiene/reporting concerns. |
| Supply chain and SDK | `supply-chain.yml`, `publish-sdk.yml` | Package policy, signing, and SDK generation coverage stays with supply-chain and publish workflows. |
| Performance | `performance-load-tests.yml` | Baseline and PR performance gate coverage stays with the load-test workflow family. |

## Retired workflow files

The following workflow files were retired after their coverage was assigned to
the canonical families above:

`audit-snapshot.yml`, `chaos-engineering.yml`, `chaos-smoke.yml`,
`ci-failure-backlog.yml`, `cleanup-branches.yml`, `codeql-analysis.yml`,
`compliance-evidence-integrity.yml`, `game-day-evidence.yml`,
`integration-tests.yml`, `k8s-validation.yml`, `launch-readiness.yml`,
`layer6-dashboard-metric-drift.yml`, `live-workflow-validation.yml`,
`package-manager-policy.yml`, `package-sign.yml`, `performance-baseline.yml`,
`pr-performance-gate.yml`, `preflight.yml`,
`production-readiness-check.yml`, `refresh-testing-kpis.yml`,
`regenerate-sdk.yml`, `restore-verification.yml`, `secret-guardrails.yml`,
`security-validation.yml`, `smoke-gate.yml`, `stale.yml`,
`test-mandatory.yml`, `test.yml`, `verify-gate.yml`,
`workflow-readme-sync-check.yml`.

## Consolidation proof decisions

| Workflow | Replacement owner | Required-check status | Proof summary | Deletion risk |
| --- | --- | --- | --- | --- |
| `codeql-analysis.yml` | `codeql.yml` | `retired-recorded`; both CodeQL workflows were blocking before consolidation. | The current checkout keeps one canonical CodeQL workflow and the retired file is no longer present or registered. Branch protection must no longer require the retired workflow name. | `needs branch-protection update` |
| `chaos-smoke.yml` | `chaos-testing.yml` | `retired-recorded`; historical workflow was PR-triggered and blocking. | The current checkout keeps `chaos-testing.yml` as the operational chaos owner and the retired smoke workflow is no longer present or registered. Branch protection must no longer require `chaos-smoke-informational` or `chaos-smoke-required-ready-marker`. | `needs branch-protection update` |
| `deploy.yml` | `build-deploy.yml`, `environment-promotion.yml` | `present-blocked`; `blocking=true`; owns workflow-call deployment behavior. | Keep enabled: it owns the unique `workflow_call` trigger, `AWS_DEPLOY_ROLE_ARN` secret, `${{ steps.evidence.outputs.file }}` and `deployment-record.json` artifacts, plus `preflight`, `approval-gate`, `deploy`, `smoke-tests`, `verify`, `evidence`, and `notify` jobs. | `not safe` |

## Guardrails

- Keep branch-protected check names aligned with the canonical workflows before
  changing GitHub repository settings.
- Add future workflow behavior as a job/profile in an existing canonical
  workflow unless a separate file has a distinct owner, trigger model, and
  artifact contract.
- Update `workflow-registry.json`, `WORKFLOW_REGISTRY.md`, and `README.md`
  whenever workflow files are added, removed, or renamed.
- Run `python scripts/ci/verify_workflow_registry.py` before marking workflow
  inventory changes complete.

## Deletion risk proof

| Workflow | Status | Risk | Replacement proof |
| --- | --- | --- | --- |
| `codeql-analysis.yml` | retired-recorded | needs branch-protection update | `codeql.yml` remains canonical; both CodeQL workflows were blocking before consolidation. |
| `chaos-smoke.yml` | retired-recorded | needs branch-protection update | `chaos-testing.yml` remains canonical; the retired smoke workflow was PR-triggered and blocking before consolidation. |
| `deploy.yml` | present-blocked | not safe | `deploy.yml` is retained because it still owns workflow-call deployment behavior not covered by `build-deploy.yml` or `environment-promotion.yml`. Unique retained surfaces include trigger `workflow_call`, jobs `preflight`, `approval-gate`, `deploy`, `smoke-tests`, `rollback-on-failure`, `verify`, `evidence`, and `notify`; secrets `AWS_DEPLOY_ROLE_ARN` and `INFISICAL_IDENTITY_ID`; artifacts `${{ steps.evidence.outputs.file }}` and `deployment-record.json`. |
