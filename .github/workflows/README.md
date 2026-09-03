# GitHub Actions Workflows

## Overview

This directory currently contains **55** GitHub Actions workflow files.

The authoritative ownership, trigger, secret, artifact, runtime, local-command,
and deprecation inventory lives in:

- `workflow-registry.json`
- `WORKFLOW_REGISTRY.md`

S6-6 caps this directory at 55 workflow YAML files. New workflow files
must be justified in the registry and should prefer adding a profile or matrix job
to an existing canonical workflow.

## Workflow Tiers

### Required / Blocking Gates

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `pr-checks.yml` | Multi-layer lint/typecheck/tests/policy checks | `pull_request`, `push` |
| `critical-gates.yml` | Merge-blocking auth/tenant/OpenAPI/config critical gates | `pull_request`, `push` |
| `contract-compliance.yml` | Contract lint, drift, and compliance checks | `pull_request`, `push`, `schedule`, `workflow_dispatch` |
| `security-gates.yml` | SAST/container/dependency security scans | `pull_request`, `push`, `schedule` |
| `k8s-readiness.yml` | Kubernetes manifest validation and policy checks | `pull_request`, `push`, `workflow_dispatch` |
| `prod-readiness.yml` | Release-readiness evidence and policy gates | `pull_request`, `push`, `workflow_dispatch` |

### Scheduled / Continuous Assurance

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `audit-evidence.yml` | Audit evidence collection | `schedule`, `workflow_call`, `workflow_dispatch` |
| `backend-integrated-reproducibility.yml` | Backend-integrated reproducibility evidence | `workflow_dispatch` |
| `chaos-testing.yml` | Chaos engineering experiments | `schedule`, `workflow_call`, `workflow_dispatch` |
| `dr-drill.yml` | Disaster recovery drill orchestration | `schedule`, `workflow_dispatch` |
| `performance-load-tests.yml` | K6 critical-path load testing | `push`, `schedule`, `workflow_dispatch` |
| `weekly-acceptance-gates.yml` | Weekly acceptance-gate evidence | `schedule`, `workflow_dispatch` |

### Active Optional / Manual / Reusable

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `build-deploy.yml` | Build and deploy pipeline | `push`, `workflow_dispatch` |
| `cleanup-repo.yml` | Repository cleanup automation | `push`, `workflow_dispatch` |
| `deploy.yml` | Deployment workflow | `workflow_call`, `workflow_dispatch` |
| `environment-promotion.yml` | Environment promotion gates | `workflow_dispatch`, `workflow_run` |
| `vault-integration.yml` | Reusable Vault/OIDC secret injection workflow | `workflow_call` |
| `penetration-testing.yml` | Penetration test workflow | `schedule`, `workflow_dispatch` |
| `zero-trust-validation.yml` | Zero-trust/security policy checks | `pull_request`, `push`, `schedule`, `workflow_dispatch` |
| `supply-chain-integrity.yml` | Supply-chain integrity and provenance checks | `pull_request`, `push`, `workflow_call`, `workflow_dispatch` |
| `test-reporting.yml` | Unified test result aggregation/reporting | `pull_request`, `workflow_run` |
| `publish-ci-tools.yml` | Publishes the pinned supply-chain security tools image with provenance and SBOM | `push`, `workflow_dispatch` |
| `publish-sdk.yml` | SDK publish workflow | `push`, `workflow_dispatch` |
| `runbook-validation.yml` | Runbook reference and format validation | `pull_request`, `push` |
| `release-evidence-bundle.yml` | Release-candidate evidence bundle | `pull_request`, `push`, `workflow_dispatch` |
| `repo-hygiene.yml` | Repository hygiene and consolidated maintenance checks | `pull_request`, `push`, `workflow_dispatch` |

## Drift Guard

To prevent README/workflow filename drift, stale workflow command references, and
missing ownership metadata, CI validates the workflow registry against every
workflow file in `.github/workflows/`.

- Public guards: `make check-workflow-registry` and `make check-workflow-references`
- Package aliases: `pnpm ci:workflow-registry` and `pnpm ci:workflow-references`
- Command source of truth: `docs/development/COMMANDS.md`
- Count limit: at most 55 workflow YAML files

## Maintenance

- When adding/removing/renaming workflow files, update `workflow-registry.json`
  and `WORKFLOW_REGISTRY.md` in the same PR.
- Keep trigger descriptions aligned with each workflow's `on:` section.
- Keep PR-gate workflows aligned with branch protection rules.

## `.depot` mirror-sync requirement

Workflow files exist in two trees that **must stay in sync**:

- `.github/workflows/` — canonical GitHub Actions definitions.
- `.depot/workflows/` — Depot runner equivalents (same steps, `runs-on`
  mapped to the Depot runner).

Treat `.depot` as a strict mirror: any new job, step, trigger, or gate added
to a `.github/workflows/` file must be applied to the matching
`.depot/workflows/` file in the same change set (and vice versa). There is no
automated mirror-drift gate; PR review and layered-governance validation are
the enforcement point, and reviewers must reject one-sided edits. Contract
gates that were mirrored this way include `event-catalog-gate`
(`validate-event-catalog.py --strict`) and the Layer 4
`check_openapi_tenant_scope.py` gate (both present in `.github/workflows/` and
`.depot/workflows/`).
