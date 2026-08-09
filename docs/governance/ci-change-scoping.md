# CI Change-Scoping Contract

Status: Active
Related: `release/v1/tasks/V1-CI-001.yaml` (aggregate fan-in — sequenced after this),
`.github/paths-filters.yml`, `.github/actions/change-scope/action.yml`

## Problem

CI previously evaluated the repository, not the change: every pull request
ran the full workflow matrix at full fan-out (~200 check runs for a one-line
dependency bump). No layer sat between "a PR exists" and "run everything".
Constant, risk-independent noise wastes compute and — worse — trains
reviewers and agents to rubber-stamp, eroding fail-closed gate discipline.

## Architecture

Change scoping operates at three levels:

### 1. Trigger scoping (workflow level)

Workflows whose checks are **not** required by branch protection use
`paths` / `paths-ignore` filters on their `pull_request` trigger:

| Workflow | PR scope |
|---|---|
| `supply-chain-integrity.yml` | dependency manifests, lockfiles, images, runtime code, CI plumbing |
| `zero-trust-validation.yml` | runtime code, infra/k8s manifests, scripts (nightly schedule remains unscoped) |
| `codeql.yml` | everything except `docs/**` and `**/*.md` |
| `critical-gates.yml` | everything except `docs/**` and `**/*.md` |
| `test-reporting.yml` | everything except `docs/**` and `**/*.md` |
| `release-evidence-bundle.yml` | runtime code, contracts, deploy surfaces, dependency manifests |
| `poc-governance-automation.yml` | CI composites and CI configuration only |

Required-check workflows must NOT use trigger-level `paths` filters — a
non-triggered workflow leaves its required checks permanently "Expected"
and blocks the merge. They use job-level scoping instead.

### 2. Job scoping (intra-workflow gating)

`pr-checks.yml`, `security-gates.yml`, and `prod-readiness.yml` run a
cheap `change-scope` job (the `.github/actions/change-scope` composite,
backed by `tj-actions/changed-files` and the central filter definitions in
`.github/paths-filters.yml`). Fan-out jobs declare
`needs: change-scope` and an `if:` on the scope they exercise, e.g.
per-layer jobs on `layer1`–`layer6`, frontend jobs on `web`, image jobs on
`docker`, manifest validation on `k8s`.

Rules:

- Scopes only ever **skip** work the change provably cannot affect.
- Every scope includes CI/build plumbing (`.github/**`, `scripts/**`,
  `config/**`, `Makefile`, `pytest.ini`) so pipeline changes force a full run.
- Unresolved scope values fail open to `'true'` (full run).
- Non-`pull_request` events (push, schedule, dispatch) resolve every scope
  to `'true'` — main, release branches, and cadence runs are never scoped.

### 3. Scope-aware aggregation (fan-in)

Skipped is not silently equal to passed. Aggregate jobs verify that any
skip was scope-driven (V1-CI-001 invariant: "aggregate gates explicitly
confirm any path-filtered skip is safe"):

- `pr-checks.yml` → `Unified Readiness Gate` treats a skipped child as
  passing only when that child's scope resolved to `'false'`; every other
  skip remains a gate failure.
- `security-gates.yml` → `Security Gates Required` accepts a skipped gate
  only when the corresponding scope resolved to `'false'`; anything else
  fails closed.
- A failed `change-scope` job fails both aggregates (no scope evidence →
  no skips accepted).

## Branch-protection semantics

Required checks that are skipped by a job-level `if:` report the
`skipped` conclusion, which satisfies branch protection. This is safe by
construction: a check gated on scope X is skipped only when the PR touched
no path that scope X validates. The scope filter definitions are therefore
part of the required-check contract — changes to
`.github/paths-filters.yml` or `.github/actions/change-scope/` must be
reviewed as gate changes (and any change under `.github/**` itself forces
a full run).

## Adding a new job or workflow

1. Identify the narrowest scope in `.github/paths-filters.yml` that covers
   every input of the job. If none fits, add a scope (always include the
   CI plumbing paths).
2. Gate the job with `needs: change-scope` +
   `if: needs.change-scope.outputs.<scope> == 'true'`.
3. If the job feeds an aggregate (`Unified Readiness Gate`,
   `Security Gates Required`), register its scope in that aggregate's
   `SCOPES` map so its skips are verified, not assumed.
4. Cadence gates (needing a live environment or a calendar) belong on
   `schedule` / `workflow_dispatch`, not the per-PR path.

## Relationship to V1-CI-001

This contract implements the change-scoping half of the CI signal
architecture remedy. The aggregate PR check contract (nine stable
aggregate checks, shadow migration, merge queue) is specified in
`release/v1/tasks/V1-CI-001.yaml`, depends on V1-CARTO-001, and requires
human-sequenced branch-protection changes; it is intentionally not bundled
here. The scope-aware aggregation above satisfies its path-filter-safety
invariant in advance.
