# Security Scanning Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Restore fail-closed, reproducible scanner orchestration and evidence without weakening controls.

**Architecture:** Canonicalize overlapping workflows, validate scanner/process/report states separately, and record tool/finding metadata in versioned JSON. Keep heavy CI evidence explicitly blocked when the execution environment cannot produce it.

**Tech Stack:** GitHub Actions, Python/PyYAML/pytest, Bash, CodeQL, Semgrep, Bandit, Trivy, OSV, pip-audit, pnpm audit, Gitleaks, Syft, Grype, Cosign, ZAP, Nikto.

## Global Constraints

- Never suppress scanner/runtime failures or unresolved actionable High/Critical findings.
- Never weaken thresholds, branch protection, rules, or scope to manufacture green status.
- Only the root orchestrator performs Git and GitHub mutations.

---

### Task 1: Encode fail-closed workflow contracts

**Files:** `tests/ci/test_security_scanning_certification.py`, `tests/ci/test_penetration_testing_workflow_assets.py`

- [x] Add assertions for immutable CodeQL actions and explicit queries.
- [x] Add assertions rejecting DAST fallbacks and unconditional completion.
- [x] Add assertions for canonical release SBOM delegation and supply-chain result enforcement.
- [x] Run focused pytest with the repository's dependency preflight disabled only because missing dependencies are separately reported.

### Task 2: Repair workflow truthfulness

**Files:** `.github/workflows/codeql.yml`, `.github/workflows/penetration-testing.yml`, `.github/workflows/sbom.yml`, `.github/workflows/supply-chain-integrity.yml`, `tests/penetration/nikto-scan.sh`

- [x] Pin CodeQL actions and select explicit suites.
- [x] Enforce ZAP finding state and condition SARIF upload on successful conversion.
- [x] Make Nikto runtime/report failures nonzero and remove zero-result fabrication.
- [x] Delegate release SBOM triggers to the canonical workflow.
- [x] Reject failed prerequisite jobs before publishing supply-chain summaries.

### Task 3: Publish governance and evidence metadata

**Files:** `security/scanning/tool-inventory.json`, `security/scanning/consolidated-findings.json`, `docs/security/scanning-certification.md`

- [x] Record purpose, scope, config, workflow, trigger, version, output, threshold, ownership, overlap, and disposition.
- [x] Record normalized findings and external blockers without unsupported vulnerability claims.
- [x] Document commands, troubleshooting, DAST safety, SBOM artifacts, and remaining gaps.

### Task 4: Verify, commit, and deliver

- [ ] Run YAML parsing, shell syntax, focused pytest, workflow registry checks, and broader practical repository checks.
- [ ] Commit once with the required co-author trailer.
- [ ] Create exactly one PR record through `make_pr`.
- [ ] If authenticated GitHub/Docker access remains absent, do not claim CI, merge, scanner, artifact, or post-merge success; report the smallest owner action.
