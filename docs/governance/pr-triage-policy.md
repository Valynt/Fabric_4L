# PR Triage Policy

## Purpose

This policy defines how Value Fabric maintainers identify, label, and dispose of stalled pull
requests so the review queue stays auditable during normal delivery and stabilization windows.
It is intended to make every non-progressing PR explicit: one accountable owner, one next action,
and one disposition label.

## Scope

Apply this policy to every open pull request against `main`, `release/*`, or any active
stabilization branch. Release captains may apply a shorter review window during incidents,
release hardening, or branch cutover, but they must record the shorter window in the PR comment or
tracking board.

## Definition of a Stalled PR

A PR is stalled when it has no material path to merge and has met at least one of these conditions
for **3 business days**:

- No author update: the author has not pushed commits, answered reviewer questions, updated the PR
  description, or confirmed the next action.
- No reviewer action: required reviewers or code owners have not approved, requested changes,
  assigned a delegate, or explained why review is blocked.
- No green CI: required checks are failing, missing, cancelled, or stale, and no owner is actively
  remediating or documenting an environment limitation.
- No merge path: the PR is blocked by conflicts, obsolete architecture, overlapping work, missing
  product decision, or absent release/stabilization approval.

A PR can be marked stalled before 3 business days when it blocks release stabilization, contains a
security-sensitive change, or holds a shared branch lock that prevents other work from landing.

## Required Disposition Labels

Every stalled PR must have exactly one primary disposition label from this list. Additional labels
may describe area, severity, or layer, but they must not replace the primary disposition.

| Label | Use when | Required next action |
|---|---|---|
| `merge-ready` | The PR is approved, current with its target branch, and all required checks are green or explicitly waived by the release captain. | Merge, queue for merge, or record the remaining external dependency. |
| `needs-rebase` | The PR has conflicts, stale generated artifacts, obsolete lockfile/API output, or CI failures caused by target-branch drift. | Rebase or merge the target branch, regenerate affected artifacts, and rerun required checks. |
| `needs-owner` | No accountable maintainer or author is available to drive the PR to disposition. | Assign an owner or close the PR if no owner accepts accountability by the next triage cycle. |
| `close-superseded` | The change is replaced by another PR, design, branch, or shipped implementation. | Link the superseding artifact, close the PR, and preserve any still-needed follow-up issues. |
| `split-required` | The PR is too broad, combines unrelated concerns, or cannot be safely reviewed/tested as one unit. | Identify the minimal mergeable slice and open follow-up PRs or issues for the remainder. |
| `parked-stabilization` | The PR is valid but intentionally deferred to keep a stabilization window focused on release safety. | Record the unblock date/event and the validation required before reactivation. |

## Accountable Owner and Next Action

Each stalled PR must include a triage comment or PR-body update with:

- **Owner:** one named accountable person or team alias responsible for driving the PR to the next
  disposition. Reviewers can be listed separately, but accountability cannot be split across
  multiple unnamed parties.
- **Next action:** one concrete action that can be completed or re-evaluated by the next triage
  cycle, such as "rebase onto `main` and rerun `make verify`" or "close after #1234 merges."
- **Due date or review date:** the date when maintainers will reassess ownership, CI status, and
  disposition.
- **Evidence links:** links to blocking CI runs, superseding PRs, design decisions, release-board
  items, or stabilization exceptions when applicable.

If ownership changes, the new owner must acknowledge the handoff in the PR or the triage tracking
system before the old owner is removed.

## Stale Branch Handling During Stabilization

During release stabilization, branch hygiene is a release-safety control:

1. **Freeze non-essential merges.** Only merge PRs that are `merge-ready` and release-relevant, or
   that have an explicit release-captain exception.
2. **Do not keep stale branches open as implicit backlog.** Branches behind the target branch by
   more than one stabilization cycle must be labeled `needs-rebase`, `parked-stabilization`, or
   `close-superseded`.
3. **Revalidate after rebase.** Any PR rebased during stabilization must rerun the required checks
   for its affected layer and any contract, tenant-isolation, migration, or frontend governance
   checks implicated by the change.
4. **Prefer closing over speculative repair.** If no owner can rebase and validate a stale branch by
   the next triage cycle, apply `needs-owner`; if no owner accepts accountability, close with
   `close-superseded` or a comment explaining why the work is being dropped.
5. **Park deliberately.** Use `parked-stabilization` only when the work remains valuable but is
   intentionally deferred. The PR must state the unblock condition, expected revalidation, and owner.
6. **Avoid branch drift in shared work.** Shared stabilization branches must not accept broad
   refactors, generated artifact churn, or lockfile updates unless those changes are required for
   the release and approved by the release captain.

## Triage Cadence

- Normal delivery: review stalled PRs at least weekly.
- Stabilization windows: review stalled PRs every business day unless the release captain records a
  different cadence.
- After triage, every stalled PR should have an up-to-date primary disposition label, accountable
  owner, next action, and review date.

## Related Governance

- Governance entry point: [`docs/governance.md`](../governance.md)
- PR template: [`.github/pull_request_template.md`](../../.github/pull_request_template.md)
- Launch drift prevention SOP: [`launch-drift-prevention-sop.md`](launch-drift-prevention-sop.md)
