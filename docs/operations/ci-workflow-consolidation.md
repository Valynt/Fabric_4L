# CI Workflow Consolidation Plan

This inventory defines the current cleanup path for overlapping GitHub Actions workflows. It is intentionally non-destructive: workflows stay enabled until branch protection and replacement proof are confirmed.

## Current inventory

The repository currently carries more than 50 workflow files in `.github/workflows/`. This phase records ownership and replacement rules only; it does not delete or disable required gates.

| Category | Canonical owner | Consolidation action |
| --- | --- | --- |
| PR validation | `pr-checks.yml` | Keep required job names stable; move only proven duplicate tests out of legacy workflows after remote proof. |
| Security | `security-gates.yml`, `security-validation.yml`, `zero-trust-validation.yml` | Preserve visible security results; consolidate only overlapping scheduled/manual checks. |
| Contracts | `contract-compliance.yml`, `openapi-drift-check.yml` | Keep contract failures merge-visible; do not bury contract drift in optional workflows. |
| Launch/readiness | `launch-readiness.yml`, `production-readiness-check.yml`, `release-evidence-bundle.yml` | Require artifact-path and branch-protection proof before disabling older readiness workflows. |
| Operational drills | `restore-verification.yml`, `dr-drill.yml`, `chaos-testing.yml` | Keep scheduled evidence workflows enabled until a canonical operational evidence workflow owns the drill. |

## Canonical workflow ownership

| Gate family | Canonical workflow | Notes |
| --- | --- | --- |
| Fast PR validation | `pr-checks.yml` | Primary PR build, test, type, and coverage signal. Keep focused on fast merge-blocking feedback. |
| Security scanning | `security-gates.yml` | Owns SAST and dependency audit coverage such as Bandit and pip-audit. |
| Contract enforcement | `contract-compliance.yml` | Owns OpenAPI drift, platform contract linting, and contract scorecard evidence. |
| Launch evidence | `launch-readiness.yml` | Owns staged launch-readiness evidence once remote execution is proven. |

## Deprecation candidates

| Workflow | Current status | Replacement | Required before disabling |
| --- | --- | --- | --- |
| `test.yml` | Legacy monolithic test workflow. | `pr-checks.yml` plus targeted integration workflows. | Confirm branch protection does not require `Test Suite`; confirm per-layer PR checks cover required tests. |
| `critical-gates.yml` | Overlaps auth coverage, tenant isolation, OpenAPI drift, and config gates. | `security-gates.yml`, `contract-compliance.yml`, and `pr-checks.yml`. | Confirm each matrix gate has an active canonical owner and artifact path. |
| `prod-readiness.yml` | Older production-readiness gate. | `launch-readiness.yml`. | Confirm launch-readiness Stage 1-4 remote execution and artifact upload. |
| `chaos-smoke.yml` | Overlaps broader chaos and smoke validation. | `chaos-testing.yml` plus `smoke-gate.yml`. | Confirm both replacement workflows publish the same evidence artifacts and are not required branch-protection checks. |
| `codeql-analysis.yml` | Potential duplicate of `codeql.yml`. | `codeql.yml`. | Confirm only one CodeQL workflow is required and both use equivalent languages, schedules, and upload behavior. |
| `deploy.yml` | Potential duplicate deployment surface. | `build-deploy.yml` plus `environment-promotion.yml`. | Confirm deployment job names, environments, and rollback hooks are preserved. |

## Cleanup rules

- Do not delete or disable a workflow in the same PR that only introduces the replacement.
- Do not rename required workflow or job names until branch protection has been updated.
- Remove duplicated checks only from the non-canonical workflow after the canonical workflow has a passing remote run.
- Keep security and contract gates visible; do not hide failures by moving them to optional workflows.
- Before deleting a workflow, record its replacement in `workflow-registry.json` or this document with branch-protection impact, required job names, and artifact ownership.
