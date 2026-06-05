# Workflow Registry

This registry is the ownership and artifact contract for GitHub Actions workflows in this repository. The machine-readable source of truth is `workflow-registry.json`; this document explains the policy and provides a compact inventory view.

## Governance Rules

- Every `.github/workflows/*.yml` or `.yaml` file must have exactly one entry in `workflow-registry.json`.
- S6-6 caps the directory at fewer than 50 workflow YAML files; prefer matrix/profile jobs in an existing canonical workflow over new workflow files.
- `owner` is the accountable team for triage, maintenance, branch-protection impact, and deprecation planning.
- `trigger` must match the workflow `on:` events exactly.
- `blocking` indicates whether the workflow is intended to block a merge, release, deployment, or promotion decision when configured by branch protection or a release gate.
- `required_secrets` must list every `secrets.X` reference used by the workflow, including `GITHUB_TOKEN` when referenced.
- `produced_artifacts` must list every `actions/upload-artifact` path. Workflows that upload no artifacts must use an empty list.
- `runtime_budget_minutes` must be at least the largest workflow job timeout. If jobs do not declare timeouts, use the expected runtime budget.
- `local_validation_command` must point to an existing local command that validates or statically checks the workflow behavior.
- `deprecation_status` must be `active`, `deprecated`, `replaced`, or `candidate-for-consolidation`. Non-active entries require a replacement or resolution path.

## Deprecation Path

Duplicate or overlapping workflows are tracked in `duplicate_groups`. A workflow should move from `active` to `candidate-for-consolidation` only with a named canonical workflow and resolution path. It can move to `deprecated` or `replaced` after required checks, reporting dependencies, and artifact consumers have been updated.

## Validation

Run:

```bash
python scripts/ci/verify_workflow_registry.py
pnpm ci:workflow-registry
```

The verifier fails closed when workflow files, registry entries, triggers, secrets, artifact paths, runtime budgets, owners, local commands, overlap metadata, or the S6-6 workflow count limit drift.

## Inventory

| Workflow | Owner | Blocking | Triggers | Local validation |
|---|---|---:|---|---|
| `.github/workflows/ai-evals-pipeline.yml` | `@value-fabric/ai-ml-leads` | yes | `pull_request, push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob ai-evals-pipeline.yml` |
| `.github/workflows/api-key-rotation.yml` | `@value-fabric/security-leads` | no | `schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob api-key-rotation.yml` |
| `.github/workflows/audit-evidence.yml` | `@value-fabric/compliance-team` | no | `schedule, workflow_call, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob audit-evidence.yml` |
| `.github/workflows/backend-integrated-reproducibility.yml` | `@value-fabric/sre-leads` | no | `workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob backend-integrated-reproducibility.yml` |
| `.github/workflows/branch-protection-validation.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob branch-protection-validation.yml` |
| `.github/workflows/build-deploy.yml` | `@value-fabric/sre-leads` | yes | `push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob build-deploy.yml` |
| `.github/workflows/chaos-testing.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_call, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob chaos-testing.yml` |
| `.github/workflows/codeql.yml` | `@value-fabric/security-leads` | yes | `pull_request, push, schedule` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob codeql.yml` |
| `.github/workflows/contract-compliance.yml` | `@value-fabric/compliance-team` | yes | `pull_request, push, schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob contract-compliance.yml` |
| `.github/workflows/contract-rfc-enforcer.yml` | `@value-fabric/architects` | yes | `pull_request` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob contract-rfc-enforcer.yml` |
| `.github/workflows/critical-gates.yml` | `@value-fabric/sre-leads` | yes | `pull_request, push` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob critical-gates.yml` |
| `.github/workflows/deploy.yml` | `@value-fabric/sre-leads` | yes | `workflow_call, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob deploy.yml` |
| `.github/workflows/dr-drill.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob dr-drill.yml` |
| `.github/workflows/drift-check.yml` | `@value-fabric/architects` | yes | `pull_request, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob drift-check.yml` |
| `.github/workflows/environment-promotion.yml` | `@value-fabric/sre-leads` | yes | `workflow_dispatch, workflow_run` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob environment-promotion.yml` |
| `.github/workflows/frontend-route-audit-check.yml` | `@value-fabric/compliance-team` | yes | `pull_request, push` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob frontend-route-audit-check.yml` |
| `.github/workflows/generated-api-freshness.yml` | `@value-fabric/architects` | yes | `pull_request, push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob generated-api-freshness.yml` |
| `.github/workflows/graph-module-tests.yml` | `@value-fabric/qa-leads` | yes | `pull_request, push` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob graph-module-tests.yml` |
| `.github/workflows/k8s-readiness.yml` | `@value-fabric/sre-leads` | yes | `pull_request, push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob k8s-readiness.yml` |
| `.github/workflows/l4-frontend-contract-sync.yml` | `@value-fabric/frontend-leads` | yes | `pull_request, push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob l4-frontend-contract-sync.yml` |
| `.github/workflows/layer3-wrapper-drift.yml` | `@value-fabric/architects` | yes | `pull_request, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob layer3-wrapper-drift.yml` |
| `.github/workflows/layer4-route-contract-matrix-check.yml` | `@value-fabric/architects` | yes | `pull_request, push` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob layer4-route-contract-matrix-check.yml` |
| `.github/workflows/layer6-wrapper-drift.yml` | `@value-fabric/architects` | yes | `pull_request, push` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob layer6-wrapper-drift.yml` |
| `.github/workflows/monthly-debt-burndown.yml` | `@value-fabric/sre-leads` | no | `schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob monthly-debt-burndown.yml` |
| `.github/workflows/openapi-drift-check.yml` | `@value-fabric/architects` | yes | `pull_request, push` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob openapi-drift-check.yml` |
| `.github/workflows/penetration-testing.yml` | `@value-fabric/security-leads` | no | `schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob penetration-testing.yml` |
| `.github/workflows/performance-load-tests.yml` | `@value-fabric/qa-leads` | yes | `push, schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob performance-load-tests.yml` |
| `.github/workflows/pr-checks.yml` | `@value-fabric/sre-leads` | yes | `pull_request, push` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob pr-checks.yml` |
| `.github/workflows/prod-readiness.yml` | `@value-fabric/sre-leads` | yes | `pull_request, push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob prod-readiness.yml` |
| `.github/workflows/publish-sdk.yml` | `@value-fabric/sre-leads` | yes | `push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob publish-sdk.yml` |
| `.github/workflows/release-evidence-bundle.yml` | `@value-fabric/sre-leads` | yes | `pull_request, push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob release-evidence-bundle.yml` |
| `.github/workflows/repo-hygiene.yml` | `@value-fabric/sre-leads` | yes | `pull_request, push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob repo-hygiene.yml` |
| `.github/workflows/repro-seed-validation.yml` | `@value-fabric/sre-leads` | yes | `pull_request, push` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob repro-seed-validation.yml` |
| `.github/workflows/runbook-validation.yml` | `@value-fabric/sre-leads` | yes | `pull_request, push` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob runbook-validation.yml` |
| `.github/workflows/secret-rotation.yml` | `@value-fabric/security-leads` | no | `schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob secret-rotation.yml` |
| `.github/workflows/security-gates.yml` | `@value-fabric/security-leads` | yes | `pull_request, push, schedule` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob security-gates.yml` |
| `.github/workflows/supply-chain.yml` | `@value-fabric/security-leads` | yes | `pull_request, push, workflow_call, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob supply-chain.yml` |
| `.github/workflows/terraform-cd.yml` | `@value-fabric/sre-leads` | yes | `pull_request, push, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob terraform-cd.yml` |
| `.github/workflows/test-reporting.yml` | `@value-fabric/qa-leads` | yes | `pull_request, workflow_run` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob test-reporting.yml` |
| `.github/workflows/vault-integration.yml` | `@value-fabric/sre-leads` | no | `workflow_call` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob vault-integration.yml` |
| `.github/workflows/weekly-acceptance-gates.yml` | `@value-fabric/qa-leads` | no | `schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob weekly-acceptance-gates.yml` |
| `.github/workflows/zero-trust-validation.yml` | `@value-fabric/security-leads` | yes | `pull_request, push, schedule, workflow_dispatch` | `python scripts/ci/check_workflow_targets_and_artifacts.py --workflow-glob zero-trust-validation.yml` |

## Overlap Register

| Canonical workflow | Overlapping workflows | Status | Resolution path |
|---|---|---|---|
| _None_ | _None_ | `active` | No unresolved workflow overlap groups remain after S6-6 consolidation. |
