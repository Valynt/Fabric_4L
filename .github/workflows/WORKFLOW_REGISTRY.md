# Workflow Registry

This registry is the ownership and artifact contract for GitHub Actions workflows in this repository. The machine-readable source of truth is `workflow-registry.json`; this document explains the policy and provides a compact inventory view.

## Governance Rules

- Every `.github/workflows/*.yml` or `.yaml` file must have exactly one entry in `workflow-registry.json`.
- S6-6 caps the directory at 55 workflow YAML files; prefer matrix/profile jobs in an existing canonical workflow over new workflow files.
- `owner` is the accountable team for triage, maintenance, branch-protection impact, and deprecation planning.
- `trigger` must match the workflow `on:` events exactly.
- `blocking` indicates whether the workflow is intended to block a merge, release, deployment, or promotion decision in its owning gate. It does **not** automatically mean every job in that workflow is a branch-protection required status check.
- Branch-protection required status checks are the explicit, curated contexts in `config/ci/required-status-checks.json`; update that file and `.github/workflows/branch-protection-validation.yml` when a workflow/job should become branch-protection enforced.
- `required_secrets` must list every `secrets.X` reference used by the workflow, including `GITHUB_TOKEN` when referenced.
- `produced_artifacts` must list every `actions/upload-artifact` path. Workflows that upload no artifacts must use an empty list.
- `runtime_budget_minutes` must be at least the largest workflow job timeout. If jobs do not declare timeouts, use the expected runtime budget.
- `local_validation_command` must point to a documented public command-map interface from `docs/development/COMMANDS.md`; private helper scripts stay behind those commands.
- `deprecation_status` must be `active`, `deprecated`, `replaced`, or `candidate-for-consolidation`. Non-active entries require a replacement or resolution path.

## Deprecation Path

Duplicate or overlapping workflows are tracked in `duplicate_groups`. A workflow should move from `active` to `candidate-for-consolidation` only with a named canonical workflow and resolution path. It can move to `deprecated` or `replaced` after required checks, reporting dependencies, and artifact consumers have been updated.

## Validation

Run:

```bash
make check-workflow-registry
make check-workflow-references
```

The verifier fails closed when workflow files, registry entries, triggers, secrets, artifact paths, runtime budgets, owners, local commands, overlap metadata, or the S6-6 workflow count limit drift.

## Inventory

The repository currently contains **54** GitHub Actions workflow files.

| Workflow | Owner | Blocking | Triggers | Local validation |
|---|---|---:|---|---|
| `.github/workflows/ai-evals-pipeline.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/api-changelog.yml` | `@value-fabric/sre-leads` | no | `release, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/api-key-rotation.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/audit-evidence.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_call, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/backend-integrated-reproducibility.yml` | `@value-fabric/sre-leads` | no | `workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/branch-protection-validation.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/build-deploy.yml` | `@value-fabric/sre-leads` | no | `push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/bundle-analysis.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/chaos-testing.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_call, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/cleanup-repo.yml` | `@value-fabric/sre-leads` | no | `push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/codeql.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, schedule` | `make check-workflow-references` |
| `.github/workflows/contract-compliance.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/contract-rfc-enforcer.yml` | `@value-fabric/sre-leads` | no | `pull_request` | `make check-workflow-references` |
| `.github/workflows/critical-gates.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/dependency-scan.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/deploy.yml` | `@value-fabric/sre-leads` | no | `workflow_call, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/dr-drill.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/drift-check.yml` | `@value-fabric/sre-leads` | no | `pull_request, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/environment-promotion.yml` | `@value-fabric/sre-leads` | no | `workflow_dispatch, workflow_run` | `make check-workflow-references` |
| `.github/workflows/flakiness-tracker.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/frontend-route-audit-check.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/generated-api-freshness.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/graph-module-tests.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/k8s-readiness.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/l4-frontend-contract-sync.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/layer3-wrapper-drift.yml` | `@value-fabric/sre-leads` | no | `pull_request, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/layer4-route-contract-matrix-check.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/layer6-wrapper-drift.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/monthly-debt-burndown.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/openapi-drift-check.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/penetration-testing.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/performance-load-tests.yml` | `@value-fabric/sre-leads` | no | `push, schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/poc-governance-automation.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/pr-backlog-health.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/pr-checks.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/prod-readiness.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/public-docs.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/publish-ci-tools.yml` | `@value-fabric/sre-leads` | no | `push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/publish-sdk.yml` | `@value-fabric/sre-leads` | no | `push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/release-evidence-bundle.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/repo-hygiene.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/repro-seed-validation.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/runbook-validation.yml` | `@value-fabric/sre-leads` | no | `pull_request, push` | `make check-workflow-references` |
| `.github/workflows/sbom.yml` | `@value-fabric/sre-leads` | no | `push, release, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/sdk-generation.yml` | `@value-fabric/sre-leads` | no | `push, schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/secret-rotation.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/security-gates.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, schedule` | `make check-workflow-references` |
| `.github/workflows/supply-chain.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_call, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/terraform-cd.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/test-reporting.yml` | `@value-fabric/sre-leads` | no | `pull_request, workflow_run` | `make check-workflow-references` |
| `.github/workflows/vault-integration.yml` | `@value-fabric/sre-leads` | no | `workflow_call` | `make check-workflow-references` |
| `.github/workflows/visual-regression.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/weekly-acceptance-gates.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `make check-workflow-references` |
| `.github/workflows/zero-trust-validation.yml` | `@value-fabric/sre-leads` | no | `pull_request, push, schedule, workflow_dispatch` | `make check-workflow-references` |

## Overlap Register

| Canonical workflow | Overlapping workflows | Status | Resolution path |
|---|---|---|---|
| _None_ | _None_ | `active` | No unresolved workflow overlap groups remain after S6-6 consolidation. |

