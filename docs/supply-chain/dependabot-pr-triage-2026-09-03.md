# Dependabot PR Triage — 2026-09-03

> **Status:** Maintainer action queue
> **Source:** Open-PR snapshot supplied for PRs 1597–1633 on 2026-09-03
> **Scope:** Version-update pull requests; this is not a vulnerability-alert inventory

## Decision summary

| Disposition | PRs | Maintainer action |
|---|---|---|
| Merge first after green focused CI | #1632 | Security group; run the complete frontend gate before merge |
| Merge routinely after green CI | #1633, #1629, #1598, #1597 | Low-risk grouped or Python test-harness updates |
| Validate, then merge separately | #1601, #1608, #1606, #1603, #1602, #1607, #1599 | Major updates; do not batch because failures need an attributable dependency |
| Close as non-canonical | #1616 | Archived source snapshot; no dependency update is required |
| Verify classification before merge | #1604 | The reported `lucide-react` jump crosses the pre-1.0 minor boundary and should not be treated as routine solely because CI is green |

This ordering reduces the queue without combining unrelated major-version risk. A maintainer should rebase each retained PR on the current default branch immediately before its focused validation so lockfile conflicts and duplicated updates are resolved once.

## Immediate actions

### 1. Close archived snapshot PR #1616

Close #1616 without merging. Its manifest is under `docs/archive/frontend-root-2026-05-02/source-snapshot`, which is historical evidence rather than a package root. The directory is intentionally absent from `.github/dependabot.yml`; both repository Dependabot-coverage scanners prune any directory named `archive`.

Suggested close comment:

> Closing because this lockfile is a historical documentation snapshot and is not part of the pnpm workspace or a deployable dependency root. Archived manifests are intentionally excluded from Dependabot discovery; updating the snapshot would destroy its historical fidelity.

### 2. Process security PR #1632

Treat the security grouping as the first merge candidate, but do not infer runtime vulnerability severity from the group name alone. Review the Dependabot advisory links and lockfile diff, then run:

```bash
pnpm install --frozen-lockfile
pnpm --dir apps/web run lint
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run test
pnpm --dir apps/web run build
pnpm --dir apps/web run test:e2e
```

Merge only if the PR is current with the default branch and required GitHub checks pass.

### 3. Clear routine updates

Process #1633 and #1629 one at a time because grouped lockfile changes may overlap. Merge the first green PR, update the second branch, and close the second if Dependabot supersedes it or its diff becomes empty. Validate #1598 and #1597 with the test-harness suites that import those requirements:

```bash
pytest tests
make contract-tests
```

### 4. Keep major updates isolated

| PR | Focused acceptance checks | Review focus |
|---|---|---|
| #1601 (`vite`) | `pnpm --dir apps/web run test && pnpm --dir apps/web run build && pnpm --dir apps/web run test:e2e` | Vite config, plugins, dev/prod build parity |
| #1608 (`zod`) | Package tests/typecheck plus all workspace consumers | Zod 4 schema and error-format compatibility |
| #1606 (`react-resizable-panels`) | Frontend test/build/E2E plus manual panel resizing | Persisted layout, keyboard resizing, min/max constraints |
| #1603 (`recharts`) | Frontend test/build/E2E plus dashboard visual inspection | Tooltip, responsive container, axis and legend behavior |
| #1602 (`jest-dom`) | Frontend unit/component tests | Matcher registration and removed/deprecated APIs |
| #1607 (`web-vitals`) | Frontend typecheck/test/build | Metric callback shape and supported metric names |
| #1599 (`@types/node`) | Value Studio typecheck/test/build | Node 26 global and module declaration drift versus the actual runtime |

Do not merge a major bump merely because an unrelated repository-wide check is green. Each PR needs its focused acceptance checks, a reviewed migration diff, and a rollback path (revert the individual PR).

### 5. Reclassify #1604 before action

`lucide-react` is below version 1.0 in the reported current version (`0.453.0`), so a jump to `1.37.0` is not a routine patch. Run frontend typecheck, tests, build, and E2E; also search for renamed or removed icons and visually inspect icon-heavy navigation before merge.

## Remote execution checklist

The maintainer performing GitHub operations should record the result directly on each PR:

1. Confirm the PR is still open and Dependabot-authored.
2. Inspect advisory metadata for security-grouped changes.
3. Rebase/update the branch and ensure the diff is non-empty.
4. Run the focused commands above and attach evidence.
5. Require all repository branch-protection checks.
6. Merge with squash, or close with the documented reason.
7. Re-query the open Dependabot PR list and record the remaining count.

## Governance impact

- **Contract shape:** none; dependency PRs must be stopped if generated API types or schemas drift unexpectedly.
- **Tenant isolation:** no intended change; any backend dependency PR with tenant-test regressions is blocked.
- **Compatibility shims:** none intended.
- **Archive policy:** archive manifests preserve historical fidelity and must remain outside active dependency automation.
