# Workspace (live task state)

## Active task
- Goal: Fix failing GitHub Actions `Contract Compliance / contract-compliance (pull_request)` job.
- First step: Inspect workflow run/job logs and identify deterministic failure.

## Active hypotheses
- The workflow pins a Node version that no longer satisfies dependency engine requirements, causing `pnpm install --frozen-lockfile` to fail before contract checks run.
