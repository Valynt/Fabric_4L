# PR Backlog Health Runbook

## Purpose

Prevent a repeat of the backlog-draining scenario where required CI gates fail broadly across many open PRs. This runbook defines the weekly review that flags stale PRs and tracks the pass rate of required checks on `main`.

## Trigger

- Scheduled: every Monday at 09:00 UTC via `.github/workflows/pr-backlog-health.yml`.
- Ad-hoc: when the open PR count exceeds 20, or when a required check on `main` fails for more than one consecutive commit.

## Severity

SEV3 — process hygiene. No immediate customer impact, but unchecked backlog accumulation blocks releases and masks real failures.

## Preconditions

- GitHub CLI (`gh`) authenticated with `repo` and `write:issues` scopes in the workflow.
- Label `pr-backlog-health` exists in the repository.

## Body

The workflow appends two sections to the report issue body:

1. **Backlog metrics** — stale PRs and required-check pass rate on `main`,
   produced by `scripts/ci/collect_pr_backlog_metrics.py`.
2. **Recurring CI failure backlog** — cross-PR failure signatures deduplicated
   by workflow/job/failure signature over the last 14 days, produced by
   `scripts/ci/generate_ci_failure_backlog.py` (capped at 500 collected failed
   runs). One broken `main` dependency surfaces as a single owned incident row
   with run IDs and a latest-log link, instead of scattered per-PR failures.

## Immediate Actions

1. Open the latest `PR Backlog Health Report` issue (created by the scheduled workflow).
2. Review the list of PRs older than 14 days.
3. Review the required-check pass rate on `main` for the last 7 days.
4. Review the recurring failure-backlog section for signatures with repeated
   occurrences. Treat each recurring signature as one incident; triage it via
   the CI gate remediation playbook rather than fixing PRs one at a time.

## Diagnosis Steps

1. For each stale PR, determine whether it is:
   - blocked by a repo-wide gate (affects many PRs), or
   - blocked by a PR-specific failure.
2. For repo-wide gate failures, follow the CI gate remediation playbook: root-cause on `main`, fix once, merge, then update all affected PRs.
3. For recurring failure signatures in the failure-backlog section, confirm they are not already tracked as an open incident (cross-check the failure-backlog JSON from the failed runs window against any open incident issues) before filing a new one.
4. For PR-specific failures, add the `needs-author` label and request a fix.
5. For conflicting PRs, add the `needs-rebase` label.

## Resolution Steps

1. If a repo-wide gate is red, create a `chore/ci-gate-remediation` branch and fix the gate with an atomic commit per root cause.
2. Open a single remediation PR, ensure all required checks pass, and squash-merge it.
3. Update remaining open PR branches oldest-first.
4. Merge PRs that turn green; label the rest `needs-author` or `needs-rebase`.

## Validation

- After remediation, the next scheduled report should show:
  - zero PRs older than 21 days without activity, and
  - required-check pass rate on `main` at 100% for the last 7 days.

## Rollback / Fallback

- If the automated report fails to run, execute the equivalent `gh` commands locally and open a manual issue.

## Customer / Stakeholder Communication

- Notify PR authors and release owners of repo-wide gate failures, the remediation owner, safe actions to take, and the next status update. Do not characterize PR-specific failures as platform-wide.

## Evidence to Preserve

- PR ledger with disposition (`merged`, `needs-author`, `needs-rebase`, `closed-stale`).
- Root-cause table per failing gate.
- Before/after metrics: open PR count, required-check pass rate on `main`, average PR age.

## Related Gates

- `Structural Preflight`
- `contract-compliance`
- `prod-readiness`
- `behavior-tests`
- `mandatory-security-regression`
- `Layer 5 - Source Contract`
- `Layer 5 - Tenant Isolation Regression`
- `Layer 5 - Contract Shape Regression`

## Related Runbooks

- [CI Infisical OIDC recovery](ci-infisical-oidc-recovery.md)
- [Incident command](../01-incident-command.md)

## Post-Incident Follow-Up

- Assign owners and due dates for recurring gate failures, stale PR disposition, workflow/report repairs, and any required update to this runbook.
