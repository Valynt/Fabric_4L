# Incident Note: Mandatory Security Regression Merge-Control Bypass

- **Date:** 2026-07-17
- **Classification:** CI governance control failure
- **Affected branch:** `main`

## What was believed to exist

`main` was believed to require the mandatory security regression check before a
pull request could merge.

## Why the control was ineffective

**Verified:** branch protection required `Mandatory Security Regression Gate`,
while GitHub Actions emitted `mandatory-security-regression`. GitHub treats
these as different check-run contexts. **Verified:** administrator enforcement
was disabled, no pull-request review rule was configured, and the active
`Protect` ruleset contained no required-status-check rule.

## Demonstrating pull requests

**Verified:** PR #1015 (`a6d7b6bcefe2c6ab5880f1e31f40a722b3d3aa94`) and
PR #1016 (`46ca9cce334234386a4d428f9ad0baa01c468748`) merged on 2026-07-17
while their final check rollups contained completed failures. Examples common
to both included `Structural Preflight`, `Dev Auth Bypass Guard`, `Critical
Gate: openapi-drift`, and `Critical Gate: production-config-policy-layer6`.
These were completed job failures, not a runner-startup-only condition.

**Not verified:** this investigation did not establish that either merged PR
introduced a vulnerability. PR #1015 changed Codex hook path resolution and
PR #1016 changed Clerk/Codex guidance; their content and the failed validation
jobs require separate remediation assessment.

## Corrective and preventive actions

**Verified:** branch protection now requires the exact emitted
`mandatory-security-regression` context and restricts it to GitHub Actions app
`15368`; strict checking, administrator enforcement, CODEOWNER review, one
approval, conversation resolution, and force-push/deletion protections are
enabled. The active ruleset has no bypass actors.

**Verified:** the source contract now tests workflow naming, trigger coverage,
no path/job/matrix/continue-on-error bypass, fail-closed gate semantics,
CODEOWNERS coverage, and effective-settings validation. The gate no longer
tolerates cross-layer matrix failures as partial success.

## Follow-up

**Verified:** temporary PR #1019 was made ready for review with its required
`mandatory-security-regression` context still queued/unsatisfied. A normal
merge attempt by the repository administrator was rejected with “the base
branch policy prohibits the merge”; no `--admin` emergency override was used.

**Externally constrained:** clean, failed, skipped, cancelled, and timed-out
terminal live results remain to be recorded once GitHub Actions runners leave
the current queue and the enforcement PR has a runnable green baseline. The
branch-protection payload and deterministic validators provide current
configuration evidence; they do not substitute for those behavioral cases.
