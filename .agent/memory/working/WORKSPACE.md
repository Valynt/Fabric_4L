# Workspace (live task state)

## Active task
- Goal: Merge the latest main into the supply-chain security PR and preserve the Axios lockfile review fixes.
- Status: IN PROGRESS — resolving merge conflicts and validating the combined branch.
- Prior work: Axios lockfile tests compare importer specifiers with package.json and enforce a >=1.18.0 resolved version; the web lockfile entry is aligned to axios 1.19.0.

## Decisions
- #1597 and #1598 are covered by grouped dependency PR #1629.
- #1616 is not covered by #1629/#1633 because it targets the archived frontend snapshot; retained open.
- #1632 is blocked by @faker-js/faker manifest/lockfile mismatch.
- Major, small-fix, and feature/refactor PRs remain held pending rebase and green CI.

## Next action
- A maintainer with protected-branch/write permissions must rebase manually, rerun required CI, close duplicate/superseded PRs, and merge serially.
