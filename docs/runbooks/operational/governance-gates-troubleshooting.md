# Governance Gates Troubleshooting

## Purpose

This runbook documents ownership, diagnosis, and resolution for the governance
automation that gates PRs and merges. It exists to reduce single-author
operational risk: every gate below was added or tightened by a governance
audit (PR review of #1374–#1384) and must remain operable by more than one
person.

## Gates Covered

| Gate | Script / Config | CI Wiring | Owner |
|------|-----------------|-----------|-------|
| Operational debt registry | `scripts/ci/check_operational_debt.py` + `config/ci/operational_debt_registry.yaml` | `make check-operational-debt` (in `VERIFY_CHECKS`) | Platform Governance |
| PR size policy | `scripts/ci/check_pr_size_policy.py` | `.github/workflows/pr-checks.yml` ("Enforce PR size policy") | Platform Governance |
| Branch protection drift | `scripts/ci/validate_branch_protection_checks.py` + `config/ci/required-status-checks.json` | `.github/workflows/branch-protection-validation.yml` | Platform Governance |
| Contract drift (pre-commit) | `scripts/ci/contract_compliance_gate.py --validate-only` | `.pre-commit-config.yaml` (`contract-drift-check` hook) | Platform Governance |
| mypy baseline ratchet | `scripts/ci/check_mypy_baseline.py` + `config/ci/mypy_baseline_layer1.json` | `make typecheck-layer1`; `mypy-baseline-write-layerN` to regenerate | Platform Leads |

## Trigger

- A CI job named above fails on a PR.
- `make verify` or `make check-operational-debt` fails locally.
- A contributor reports they had to use `--no-verify` to commit.
- A branch-protection drift alert fires (scheduled `branch-protection-validation.yml`).

## Severity

- **Operational debt expiry**: High — an expired debt entry fails closed and
  blocks all PRs until renewed or removed. This is intentional; do not bypass.
- **PR size policy failure**: Low — add a `**Size justification:**` field or
  split the PR. Never disable the gate.
- **Branch protection drift**: High — the drift may indicate a required check
  or review policy was removed, weakening merge enforcement.
- **Pre-commit contract-drift hook failure**: Medium — the hook now runs
  `--validate-only` (pure JSON validation, <1s). If it fails, the contract
  JSON is malformed; do not `--no-verify`.

## Diagnosis Steps

### Operational debt registry failure

1. Run `python scripts/ci/check_operational_debt.py --registry config/ci/operational_debt_registry.yaml`.
2. The error names the expired or malformed entry.
3. If **expired**: either renew it (set a future `expires_on` with a fresh
   `ticket`) or remove the underlying debt (implement the `remediation`).
   Do not extend the date without a real remediation plan.
4. If **malformed**: fix the schema (required fields: `id`, `category`,
   `severity`, `owner`, `ticket`, `expires_on`, `source`, `summary`,
   `impact`, `remediation`, `verification`).

### PR size policy failure

1. The CI step "Enforce PR size policy" reports the net additions count and
   size class (small/medium/large).
2. If **large** (>1000 net additions excluding generated/lockfile paths):
   add a `**Size justification:**` line to the PR body explaining why it
   cannot be split, OR split the PR.
3. If the count looks wrong, verify excluded paths in
   `scripts/ci/check_pr_size_policy.py` `EXCLUDED_PATHS`.

### Branch protection drift

1. Run `python scripts/ci/validate_branch_protection_checks.py --config config/ci/required-status-checks.json --api-response-file <live-protection.json>`.
2. Fetch live protection: `gh api repos/bmsull560/Fabric_4L/branches/main/protection`.
3. The drift report names each mismatched check or review policy.
4. If a **review policy** drift is reported (e.g.,
   `required_conversation_resolution: expected True but enforced False`):
   this means merge-before-review-fix is possible again (see PR #1365 →
   #1375). Re-enable the setting via branch protection UI or API.
5. If a **status check** drift is reported: add the missing check name to
   branch protection, or remove it from `required-status-checks.json` if it
   was renamed (with evidence).

### Pre-commit contract-drift hook failure

1. The hook runs `python scripts/ci/contract_compliance_gate.py --validate-only`.
2. If it fails, a contract JSON file in `contracts/openapi/` or
   `contracts/jsonschema/` is malformed.
3. Run `python scripts/ci/contract_compliance_gate.py --validate-only` directly
   to see which file failed.
4. Fix the JSON; do **not** use `--no-verify`. The hook takes <1s.

## Resolution Steps

1. Apply the least-risk corrective action for the confirmed failure mode.
2. Never weaken a gate to make a PR pass — register the gap as debt instead.
3. If a gate is genuinely wrong, fix the gate in a separate PR with its own
   validation, and update this runbook.

## Validation

- Re-run the specific gate: `make check-operational-debt`,
  `python scripts/ci/check_pr_size_policy.py`, or
  `python scripts/ci/validate_branch_protection_checks.py ...`.
- For branch protection, confirm `gh api .../branches/main/protection`
  matches `config/ci/required-status-checks.json`.

## Related Gates

- `structural-preflight` (import topology, package-manager enforcement)
- `contract-compliance` (OpenAPI drift)
- `production-readiness-gate`
- `behavior-tests`

## Related Runbooks

- [`alerting-source-of-truth.md`](alerting-source-of-truth.md) — canonical
  alert-rule edit paths
- [`docs/development/LOCAL_CI_VALIDATION_PARITY.md`](../../development/LOCAL_CI_VALIDATION_PARITY.md)
  — local-vs-CI validation predictor matrix

## Post-Incident Follow-Up

- If a gate was bypassed, add a behavior-debt ticket and a
  `TODO(behavior-debt)` comment at the bypass site.
- If debt was extended, update the `ticket` field to point to the tracking
  issue proving progress.
