# Pre-Stabilization Intake Gate

Use this operational gate before entering a stabilization window for a release, launch, or major integration milestone. The goal is to make the branch and pull-request surface area explicit before the team freezes scope, selects the release branch, and starts burn-down work.

## When to Run This Gate

Run this gate before any stabilization phase begins and repeat it if the stabilization window is restarted, the release branch changes, or a critical integration branch is added after entry.

## Required Branch Inventory

Before stabilization begins, the release lead must capture a branch inventory from the canonical remote and record the result in the stabilization tracker or release issue.

The inventory must include:

| Field | Requirement |
|---|---|
| Branch name | Exact remote branch name. |
| Owner | Engineering owner accountable for merge, close, or archival decisions. |
| Purpose | Short description of the change stream or release relevance. |
| Base branch | Current intended integration target, such as `main` or the selected release branch. |
| Last activity | Most recent commit date or PR activity date. |
| Diff scope | High-level affected layers, services, docs, contracts, migrations, or frontend surfaces. |
| Release relevance | `critical`, `candidate`, `non-critical`, or `unknown`. |
| Disposition | `merge`, `rebase`, `close`, `split`, or `park`. |

Minimum branch inventory commands:

```bash
git fetch --all --prune
git branch -r --sort=-committerdate
```

If the repository is mirrored across automation accounts or protected remotes, inventory must identify the remote used as the source of truth.

## Required Open-PR Inventory

All open pull requests targeting `main`, the release branch, or any branch expected to merge into the release branch must be triaged before stabilization entry.

Record each PR with the following fields:

| Field | Requirement |
|---|---|
| PR | Number and title. |
| Owner | Directly responsible individual or team. |
| Source branch | Branch being merged. |
| Target branch | Branch receiving the PR. |
| Status | `draft`, `ready`, `blocked`, `needs-review`, or `approved`. |
| Mergeability | `clean`, `conflicted`, `behind-base`, `requires-rebase`, or `unknown`. |
| CI status | `passing`, `failing`, `pending`, `not-run`, or `unknown`, with failing checks named. |
| Release relevance | `critical`, `candidate`, `non-critical`, or `unknown`. |
| Disposition | `merge`, `rebase`, `close`, `split`, or `park`. |
| Notes / blocker | Explicit blocker, owner action, or follow-up issue link. |

Disposition rules:

- `merge`: PR is release-relevant, reviewed, CI-clean or approved for a documented exception, and safe to include.
- `rebase`: PR is release-relevant but must update onto the selected base before review or merge.
- `close`: PR is obsolete, superseded, unsafe, or no longer aligned with the release scope.
- `split`: PR contains mixed critical and non-critical work; release-critical changes must be separated from unrelated scope.
- `park`: PR is valid but non-critical for stabilization and must wait until the freeze is lifted.

## Temporary Merge / Freeze Policy

Once this gate is entered, stabilization uses a temporary freeze for non-critical changes:

1. Only release-critical fixes, CI fixes, security fixes, data-loss fixes, tenant-isolation fixes, contract-drift fixes, and release-branch operational fixes may merge during stabilization.
2. Non-critical features, refactors, cosmetic changes, broad dependency upgrades, and opportunistic cleanup must be parked unless the stabilization owner grants an explicit exception.
3. Parked PRs must be labeled or noted as parked and must not be rebased repeatedly unless needed to keep ownership clear.
4. Mixed-scope PRs must be split before merge; critical fixes should land independently of unrelated enhancements.
5. New PRs opened during the freeze must declare whether they are critical to stabilization and identify the gate or blocker they resolve.
6. Any exception must name the approver, affected surface area, CI evidence, and rollback plan.

The freeze ends only when the release lead records that stabilization is complete, cancelled, or superseded by a new stabilization window.

## Entry Criteria

Stabilization may begin only when all criteria below are complete:

- [ ] CI baseline captured for the selected base branch, including the commit SHA, timestamp, required checks, and any known failing checks.
- [ ] Active PRs triaged with owner, status, mergeability, CI status, release relevance, disposition, and blocker notes.
- [ ] Release branch selected and communicated, including whether stabilization targets `main`, a named release branch, or a temporary integration branch.
- [ ] Owners assigned for branch inventory, PR triage, CI baseline follow-up, release-branch protection, and exception approval.

## Stabilization Intake Record Template

```markdown
# Stabilization Intake — <release or milestone>

- Date / time (UTC):
- Release lead:
- Selected base / release branch:
- Baseline commit SHA:
- CI baseline summary:
- Freeze start:
- Freeze end target:

## Owners

| Responsibility | Owner | Backup |
|---|---|---|
| Branch inventory |  |  |
| PR triage |  |  |
| CI baseline follow-up |  |  |
| Release-branch protection |  |  |
| Exception approval |  |  |

## Branch Inventory

| Branch | Owner | Purpose | Base | Last activity | Diff scope | Release relevance | Disposition |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## Open PR Inventory

| PR | Owner | Source | Target | Status | Mergeability | CI status | Release relevance | Disposition | Notes / blocker |
|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |  |

## Exceptions

| Request | Approver | Reason | CI evidence | Rollback plan |
|---|---|---|---|---|
|  |  |  |  |  |
```
