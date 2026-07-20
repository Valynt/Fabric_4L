# Mandatory Security Regression Merge Policy

## Canonical required check

`mandatory-security-regression` is the stable GitHub check-run context for the
mandatory security regression gate. It is emitted by job key
`mandatory-security-regression` in `.github/workflows/security-gates.yml` and
is restricted in branch protection to the GitHub Actions app (`15368`). The
context is a governed interface: a rename requires this policy, the checked-in
contract, the workflow, the required-status configuration, and live branch
protection to change together in a CODEOWNERS-reviewed pull request.

The workflow runs for every pull request whose base branch is `main`, without
`paths` or `paths-ignore` filters. The job has no job-level condition, matrix,
or `continue-on-error`. A failed, cancelled, skipped, missing, or timed-out
check therefore cannot satisfy the required check.

## Merge enforcement

`main` uses branch protection with the canonical context as a strict required
check. Administrator enforcement, CODEOWNER review, one approving review, and
conversation resolution are required. Direct pushes, force pushes, and branch
deletions are prohibited. The active `Protect` ruleset has no bypass actors and
is not used as an alternate required-check control.

## Emergency exception process

There is no standing administrator bypass for this gate. An exception is
allowed only for an active production incident where waiting for normal CI
would materially worsen customer impact. A member of `@value-fabric/security-leads`
and a member of `@value-fabric/sre-leads` must jointly authorize it, record an
incident or change ticket, document the affected commit and written
justification, and retain the GitHub audit-log evidence. The exception expires
after the single emergency change (maximum four hours). A post-event review
must occur within one business day; routine delivery, flaky tests, and schedule
pressure are explicitly prohibited reasons.

## Evidence and validation

Run the offline contract test with:

```bash
python scripts/ci/check_mandatory_security_gate_contract.py
python scripts/ci/validate_mandatory_security_gate_enforcement.py \
  --branch-protection-file <GitHub-protection-response.json> \
  --ruleset-file <GitHub-ruleset-response.json>
```

The dated evidence record in `docs/validation/security_regression/` captures
the effective GitHub settings after each enforcement change.
