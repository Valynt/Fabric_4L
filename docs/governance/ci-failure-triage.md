# CI Failure Triage Governance

This artifact defines the minimum triage record for failing CI workflows and the weekly
health review used to keep stabilization work focused on reducing existing categorized
failures. It applies to merge-blocking and recurring scheduled CI failures, including the
primary PR gates in `.github/workflows/pr-checks.yml`, the critical gate matrix in
`.github/workflows/critical-gates.yml`, and the monthly debt-burndown evidence workflow in
`.github/workflows/monthly-debt-burndown.yml`.

## Scope and source workflows

Use this triage process for:

- Required PR checks and per-layer policy gates from `.github/workflows/pr-checks.yml`.
- Merge-blocking auth, tenant-isolation, OpenAPI, and production-config gates from
  `.github/workflows/critical-gates.yml`.
- Recurring debt evidence from `.github/workflows/monthly-debt-burndown.yml`, especially
  compatibility-shim, endpoint-coverage, and duplicate-filename reports.
- Any scheduled, manual, or reusable workflow whose repeated failures begin blocking release
  confidence, branch protection, or production-readiness evidence.

Related governance references:

- CI workflow consolidation and canonical workflow ownership:
  `docs/operations/ci-workflow-consolidation.md`.
- Critical gate ownership and artifact contract:
  `docs/operations/critical-gates-ownership.md`.
- Compatibility debt registry and monthly prune procedure:
  `docs/governance/compatibility-debt-registry.md`.
- Legacy debt baseline overrides:
  `docs/operations/legacy-debt-baseline-overrides.md`.

## Failure categories

Every failing workflow/job must be assigned exactly one primary failure category. Add a
secondary note only when it helps route remediation, but do not leave the primary category
ambiguous.

| Category | Use when | Examples | Default owner hint |
| --- | --- | --- | --- |
| `infra/setup` | The runner, service container, tool bootstrap, OS package, Docker daemon, or CI orchestration failed before project validation meaningfully ran. | Runner image outage, Docker daemon unavailable, checkout/setup action failure, service container never became healthy. | SRE / CI platform owner |
| `dependency/cache` | Dependency resolution, package download, lockfile install, cache restore/save, or generated dependency artifact failed. | `pnpm install --frozen-lockfile` cannot resolve, pip wheel unavailable, cache corruption, tool version drift. | Owning language/platform team |
| `flaky test` | The same commit can pass on rerun without code changes and the observed failure is nondeterministic. | Timing-sensitive Playwright failure, async race, randomized test data, intermittent network-bound mock. | Test owner plus affected service owner |
| `real regression` | The failure reflects a code, behavior, security, tenant-isolation, or product regression introduced by the branch or recent merge. | Unit test detects changed behavior, security gate catches missing auth, smoke test exposes broken path. | Owning service/team |
| `contract drift` | Implementation, generated types, OpenAPI, JSON Schema, frontend expectations, or service-to-service payloads no longer match the source-of-truth contract. | OpenAPI drift check fails, generated DTOs stale, route response shape changes silently. | Architecture / contract owner plus service owner |
| `lint/type debt` | Static analysis, formatting, import topology, legacy debt baseline, mypy/pyright, ESLint, or policy lint fails without proving runtime behavior changed. | Ruff/ESLint violation, mypy error, forbidden import, legacy debt threshold exceeded. | Code owner for changed path |
| `environment/secret issue` | The job is blocked by missing, invalid, expired, or mis-scoped environment configuration, credentials, OIDC/Vault/Infisical wiring, or safe production flag policy. | Missing secret, expired token, wrong environment protection, production safety validator blocks dev bypass flag. | SRE / security platform owner |

## Required triage fields

Create or update a triage record for each failing workflow/job before classifying the run as
known debt. The record can live in an issue, incident, PR comment, debt register, or release
blocker tracker, but it must include all fields below.

| Field | Required content |
| --- | --- |
| Workflow name | GitHub Actions workflow display name or workflow file, for example `PR Checks` / `.github/workflows/pr-checks.yml`. |
| Job name | Exact failing job name, including matrix axis when relevant. |
| Failure category | One primary category from the taxonomy above. |
| First-seen date | First known date the same failure signature appeared, in `YYYY-MM-DD` format. |
| Owner | Team, individual, or on-call role responsible for remediation. |
| Blocking status | `merge-blocking`, `release-blocking`, `non-blocking monitored`, or `informational`. |
| Remediation link | Link to the fixing PR, issue, incident, runbook, debt item, or artifact with next action and exit criteria. |

Recommended optional fields:

- Failure signature or log excerpt identifier.
- Affected branch or release train.
- Last reproduced run URL and last passing run URL.
- Rerun result, if testing for flakiness.
- Contract, schema, migration, or tenant-isolation impact.

### Triage record template

```markdown
## CI failure triage record

- Workflow name:
- Job name:
- Failure category:
- First-seen date:
- Owner:
- Blocking status:
- Remediation link:
- Failure signature:
- Last failing run:
- Last passing run:
- Notes / exit criteria:
```

## Weekly CI health KPIs

Publish a weekly CI health summary for required PR gates and any scheduled workflow that has
failed more than once during the reporting window.

| KPI | Definition | Reporting guidance |
| --- | --- | --- |
| Total runs | Count of workflow runs included in the reporting window. | Segment by required PR gates, critical gates, and scheduled/debt workflows when possible. |
| Failed runs | Count of runs whose final conclusion was not successful. | Include cancelled/timed-out runs when they represent CI instability; exclude intentional manual cancellations from failure-rate math with a note. |
| Failure rate | `failed runs / total runs`, reported as a percentage. | Show both aggregate rate and rate by workflow for `.github/workflows/pr-checks.yml` and `.github/workflows/critical-gates.yml`. |
| Flaky rerun recovery rate | Percentage of categorized `flaky test` failures that passed on rerun without code changes. | Track numerator and denominator; recurring high recovery still counts as stabilization debt. |
| Top recurring failures | The most frequent failure signatures by workflow/job/category. | Include owner, first-seen date, blocking status, and remediation link for each top item. |

Weekly summaries should call out movement since the prior week:

- New failure signatures added.
- Failure signatures remediated and verified by passing runs.
- Categories whose failure count increased.
- Flaky tests converted to deterministic regression fixes.
- Debt-burndown artifacts from `.github/workflows/monthly-debt-burndown.yml` that changed
  stabilization priority.

## Stabilization scope rule

Stabilization work must reduce already-categorized CI failures before adding new stabilization
scope. A stabilization PR or project may add new scope only after it demonstrates at least one
of the following:

1. A categorized failure signature was removed or made non-recurring by a passing workflow run.
2. A merge-blocking or release-blocking failure was downgraded through a documented fix, not by
   weakening the gate.
3. A flaky test was converted into a deterministic test or quarantined under an approved policy
   with owner, exit criteria, and remediation date.
4. A contract-drift or lint/type-debt failure was tied to an approved debt item with a clear
   burndown plan and no increase in the affected baseline.

Do not expand stabilization scope to adjacent workflows, new dashboards, or unrelated cleanup
until the active categorized failure backlog is smaller than it was at the start of the effort.
When scope must expand because a failure reveals a shared root cause, link the new work back to
the original triage record and explain how it reduces the categorized failure count.

## Workflow-specific triage notes

### `.github/workflows/pr-checks.yml`

- Treat failures in structural preflight, per-layer lint/typecheck/test jobs, contract checks,
  and legacy debt enforcement as potential merge-blockers until categorized.
- Route `contract drift` failures to the relevant service owner and contract owner; verify that
  OpenAPI, JSON Schema, generated TypeScript, frontend consumers, and tests are aligned before
  marking the failure remediated.
- Route `lint/type debt` failures to the code owner for the changed path and do not increase
  baselines without an explicit debt approval.

### `.github/workflows/critical-gates.yml`

- Preserve the merge-blocking intent of the critical gate matrix. A failing critical gate should
  remain blocking unless the owner documents why the signal is not actionable for the current
  change.
- Use the gate ID and artifact paths from `docs/operations/critical-gates-ownership.md` when
  writing remediation links.
- Security, tenant-isolation, and production-config failures should be classified as
  `real regression`, `contract drift`, or `environment/secret issue`; do not classify them as
  `flaky test` without a rerun and owner confirmation.

### `.github/workflows/monthly-debt-burndown.yml`

- Use monthly artifacts to identify recurring compatibility, endpoint-coverage, and duplicate UI
  filename debt that should influence weekly CI health priorities.
- A monthly debt finding is not automatically a CI failure, but it becomes triage debt when it
  causes or predicts repeated PR gate failures.
- Link remediation to the relevant debt registry entry or cleanup PR, and verify that the next
  monthly artifact shows the expected reduction.
