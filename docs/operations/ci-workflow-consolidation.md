# CI Workflow Consolidation Record

S6-6 closed the workflow sprawl gate by consolidating duplicate and reporting
workflows into canonical GitHub Actions files. The repository-level invariant is
now at most 55 workflow YAML files in `.github/workflows/`, enforced by
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
| `deploy.yml` | `build-deploy.yml`, `environment-promotion.yml` | `present-blocked`; `blocking=true`; owns workflow-call deployment behavior. | Keep enabled: it owns the unique `workflow_call` trigger, `AWS_DEPLOY_ROLE_ARN` and `INFISICAL_IDENTITY_ID` secrets, `${{ steps.evidence.outputs.file }}` and `deployment-record.json` artifacts, plus `preflight`, `approval-gate`, `deploy`, `smoke-tests`, `rollback-on-failure`, `verify`, `evidence`, and `notify` jobs. | `not safe` |

## Marketplace workflow templates: intentionally not adopted

GitHub's suggested marketplace/starter workflow templates (SLSA Generic
generator, Python application/package, Pylint, Node.js, Webpack, Docker image,
Publish Docker Container, Super Linter, Build projects with Make, publishing
templates, and the various language templates for stacks this monorepo does
not use) are **deliberately not configured**. Do not add them:

- The S6-6 workflow-count cap allows at most 55 workflow files; additions beyond it fail
  `scripts/ci/verify_workflow_registry.py` and
  `tests/ci/test_ci_workflow_consolidation.py`.
- Every applicable template is already covered by canonical workflows using
  free/open-source tooling:

| Template family | Existing coverage |
| --- | --- |
| SLSA Generic generator (OpenSSF) | `supply-chain.yml` (slsa-framework generator, SHA-pinned), `sbom.yml`, `release-evidence-bundle.yml` |
| Python application / package / Pylint | `pr-checks.yml` per-layer ruff, mypy, pytest jobs; black via pre-commit |
| Node.js / Webpack | `pr-checks.yml` frontend jobs (Vite build, Vitest, ESLint); templates would also violate the pnpm-only policy (`scripts/ci/check_package_manager_policy.mjs`) |
| Docker image / Publish Docker Container | `build-deploy.yml`, `deploy.yml` |
| Super Linter | Redundant with ruff/mypy/ESLint/prettier/gitleaks gates in `pr-checks.yml`, `security-gates.yml`, `.pre-commit-config.yaml` |
| CodeQL-adjacent security templates | `codeql.yml`, `dependency-scan.yml`, `security-gates.yml`, `penetration-testing.yml`, `zero-trust-validation.yml` |
| Build projects with Make | `pr-checks.yml` and gates invoke canonical `make verify` / `make production-readiness-gate` targets |
| Package publishing (PyPI/npm/GitHub Packages) | `publish-sdk.yml`, `sdk-generation.yml` — extend these instead |

- Templates for languages/frameworks the monorepo does not use (Django,
  Anaconda, Deno, Java, .NET, Ruby, Rust, Go, Swift, iOS/Xcode, PHP, Elixir,
  Haskell, R, Scala, Dart, Ada, D, Crystal, Clojure, Erlang, CMake, MSBuild,
  Jekyll, Datadog Synthetics, etc.) would create dead workflows and registry
  drift.

If a template's capability is genuinely missing, add it as a job in the
matching canonical workflow above, register it in `workflow-registry.json`,
keep permissions within the `tests/ci/test_workflow_permissions.py`
allowlist, and respect the pnpm-only package-manager policy.

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
