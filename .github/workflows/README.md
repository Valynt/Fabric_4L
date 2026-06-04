# GitHub Actions Workflows

## Overview

This directory currently contains **54** GitHub Actions workflow files.

## Workflow Tiers

### Required (PR merge gates)
These are primary PR gate workflows (blocking when configured in branch protection):

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `pr-checks.yml` | Multi-layer lint/typecheck/tests/policy checks | `pull_request` (main), `push` (main) |
| `critical-gates.yml` | Merge-blocking auth/tenant/OpenAPI/config critical gates | `pull_request` (main), `push` (main) |
| `contract-compliance.yml` | Contract lint + drift and compliance checks | `pull_request` (contract paths), `schedule`, `workflow_dispatch` |
| `security-gates.yml` | SAST/container/dependency security scans | `pull_request` (main), `push` (main), `schedule` |
| `k8s-readiness.yml` | Kubernetes manifest validation and policy checks | `pull_request`/`push` (k8s paths), `workflow_dispatch` |
| `openapi-drift-check.yml` | OpenAPI export + drift detection | `pull_request` (API paths), `push` (main/develop API paths) |

### Scheduled / Continuous Assurance

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `integration-tests.yml` | Full Docker-based integration test suite | `schedule`, `workflow_dispatch` |
| `smoke-gate.yml` | Cross-layer smoke tests | `schedule`, `workflow_dispatch` |
| `performance-load-tests.yml` | K6 critical-path load testing | `push` (perf-relevant paths), `schedule`, `workflow_dispatch` |
| `ai-evals-pipeline.yml` | Agent skill/prompt evaluation pipeline | `pull_request`/`push` (agent paths), `workflow_dispatch` |
| `chaos-testing.yml` | Chaos engineering experiments | `schedule`, `workflow_dispatch`, `workflow_call` |
| `secret-rotation.yml` | Secret rotation automation | `schedule`, `workflow_dispatch` |
| `ci-failure-backlog.yml` | Weekly CI failure backlog artifacts from Actions run metadata | `schedule`, `workflow_dispatch` |

### Active Optional / Manual / Reusable

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `build-deploy.yml` | Build and deploy pipeline | `push` (main), `workflow_dispatch` |
| `deploy.yml` | Deployment workflow | `push` (main), `workflow_dispatch` |
| `environment-promotion.yml` | Dev→Staging→Prod promotion gates | `workflow_run` (Build & Deploy), `workflow_dispatch` |
| `vault-integration.yml` | Reusable Vault/OIDC secret injection workflow | `workflow_call` |
| `penetration-testing.yml` | Manual penetration test workflow | `workflow_dispatch` |
| `zero-trust-validation.yml` | Zero-trust/security policy checks | `pull_request`, `push` |
| `supply-chain.yml` | Supply-chain integrity and provenance checks | `push`, `workflow_dispatch` |
| `test-reporting.yml` | Unified test result aggregation/reporting | `workflow_run` (PR Checks/Integration Tests), `pull_request` |
| `package-sign.yml` | Package signing workflow | `workflow_dispatch` |
| `publish-sdk.yml` | SDK publish workflow | `workflow_dispatch`, `release` |
| `regenerate-sdk.yml` | SDK regeneration workflow | `workflow_dispatch` |
| `runbook-validation.yml` | Runbook reference and format validation | `pull_request`/`push` (runbook paths) |
| `security-validation.yml` | Extended security validation | `workflow_dispatch` |
| `audit-evidence.yml` | Audit evidence collection | `schedule`, `workflow_dispatch` |

## Drift Guard

To prevent README/workflow filename drift, CI now validates every workflow filename referenced in this README exists in `.github/workflows/`.

- Guard script: `.github/scripts/check-workflow-readme-links.py`
- Guard workflow: `.github/workflows/workflow-readme-sync-check.yml`

## Maintenance

- When adding/removing/renaming workflow files, update this README in the same PR.
- Keep trigger descriptions aligned with each workflow's `on:` section.
- Keep PR-gate workflows aligned with branch protection rules.
