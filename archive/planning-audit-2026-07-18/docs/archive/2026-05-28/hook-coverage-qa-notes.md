# Hook Coverage QA Notes

## Baseline and Current Snapshot

- Historical release baseline (from QA tracker): **41/134 tested hooks**.
- Current inventory command (this change):
  - `rg --files apps/web/src | rg 'use[A-Z].*\.(ts|tsx)$' | rg -v '\.test\.'`
  - plus adjacency check for `*.test.*` companion files under same directories.
- Current repo snapshot in this branch: **40/103 hook files have direct companion tests**.

> Note: the `41/134` metric and the current `40/103` metric are derived using different inventory scopes (historical tracker vs file-based companion-test scan). Keep the 41/134 value as the release-over-release historical baseline until the inventory method is unified.

## Priority Hooks Added in This Change

1. `useValueCaseArtifacts` (data-fetching + mutation lifecycle)
2. `useTenantMembership` (auth / tenant-scoping UX guard)
3. `useWorkflowContext` (workflow state orchestration / URL branching)

## Coverage Gate

- Added priority hook tests to `vitest.critical-coverage.config.ts`.
- Added corresponding source files to coverage include list.
- Updated critical suite thresholds to **`69/73/81/69`** (lines/functions/branches/statements) to enforce a non-regression gate aligned with the currently included critical suite footprint.

## Next Step Recommendation

- Standardize inventory logic into a single script under `apps/web/scripts/quality/` and publish one canonical hook-coverage percentage in CI artifacts.
