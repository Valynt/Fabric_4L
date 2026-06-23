# Branch Hygiene Before Stabilization

## Purpose

This policy defines the branch-inventory and cleanup expectations that must be completed before a
stabilization window starts. Use it during release planning, launch hardening, and any pre-stabilization
intake where stale or ambiguous branches could obscure the source of truth.

## Scope

Apply this policy to all remote branches in the repository, including feature, fix, release, hotfix,
agent-generated, and experiment branches. Protected branches such as `main` and active `release/*`
branches remain governed by branch protection and release rules; they must still be inventoried, but
must not be deleted through hygiene cleanup.

## Branch Inventory

Before stabilization begins, publish a branch inventory grouped by owner. Each row must include the
branch age, last commit date, associated pull request, and proposed disposition.

Recommended inventory format:

| Owner | Branch | Age | Last commit date | Associated PR | Disposition | Notes |
|---|---|---:|---|---|---|---|
| `<team-or-person>` | `<branch-name>` | `<days>` | `<YYYY-MM-DD>` | `<PR # / URL / none>` | `<category>` | `<cleanup or stabilization note>` |

Inventory requirements:

- Group branches under the accountable owner or owning team. Use `Unowned` only as a temporary
  triage bucket.
- Calculate age from the branch creation date when available; otherwise use the oldest unique commit
  date that is not shared with the baseline branch.
- Record the last commit date from the remote branch head.
- Link the associated PR when one exists. If multiple PRs reference the branch, identify the active PR
  and note closed or superseded PRs in `Notes`.
- Mark branches without discoverable owners or PRs as cleanup candidates unless release leadership
  explicitly grants a temporary owner and due date.

## Disposition Categories

Every branch in the inventory must receive one of the following categories:

| Category | Definition | Required action before stabilization |
|---|---|---|
| `active` | Work is still in progress, has a named owner, and has a current PR or documented delivery date. | Confirm owner, PR, scope, and whether the branch is allowed to continue outside the stabilization baseline. |
| `merge candidate` | Branch is expected to merge before stabilization or become part of the stabilization baseline. | Confirm review status, required checks, contract impact, and merge order. |
| `abandoned` | Branch has no active owner, no current PR, or no credible path to merge. | Close related PRs if needed, archive evidence if required, then delete the remote branch after confirmation. |
| `superseded` | Work has been replaced by another branch, PR, release candidate, or baseline implementation. | Confirm replacement, document the successor, close stale PRs, then delete the remote branch after confirmation. |
| `release/hotfix` | Branch supports an active release, release candidate, patch, or emergency production fix. | Keep until the release/hotfix is merged, tagged, or explicitly retired by release leadership. |
| `protected` | Branch is protected by repository policy, branch protection, or release governance. | Inventory only; do not delete unless governance explicitly changes protection status. |

## Stabilization Entry Rules

Stabilization must not begin until branch ownership and baseline scope are explicit:

1. **No ownerless or PR-less work enters stabilization.** Branches without an associated PR or named
   owner must be closed, archived, or assigned a temporary owner with a dated cleanup decision before
   stabilization begins.
2. **Stabilization targets a named baseline.** The release captain must name the stabilization baseline
   branch or release candidate before intake closes, for example `main`, `release/2026.06`, or
   `rc/2026.06.0-rc1`.
3. **Merge candidates are reconciled against the baseline.** Any `merge candidate` not included in the
   named baseline must either be reclassified as `active`, `superseded`, or `abandoned`, or explicitly
   deferred to a later release.
4. **Protected and release/hotfix branches require release-owner confirmation.** These branches may stay
   open during stabilization only when the release owner confirms their role and retention window.

## Remote Branch Deletion Checklist

Use this checklist before deleting merged, abandoned, or superseded remote branches:

- [ ] Confirm the branch is not protected and is not the named stabilization baseline or release
      candidate.
- [ ] Confirm the branch has merged, been superseded, or been declared abandoned by the accountable
      owner or release captain.
- [ ] Confirm associated PRs are merged, closed, or explicitly linked to a successor branch/PR.
- [ ] Confirm required evidence, tags, release notes, or audit artifacts have been preserved elsewhere
      if the branch supported a release, hotfix, incident, or governance review.
- [ ] Confirm no open workflow, deployment, environment, or automation still references the branch.
- [ ] Delete the remote branch only after confirmation, then update the branch inventory with the
      deletion date and confirming owner.

Example command after confirmation:

```bash
git push origin --delete <branch-name>
```

## Evidence Expectations

Keep the finalized inventory and cleanup decisions with the stabilization intake record, release notes,
or launch evidence bundle. The evidence should identify the named baseline branch or release candidate,
the final disposition for each remote branch, and the date cleanup completed.
