---
description: Closed-loop operating system for continuously improving Value Fabric with repowise intelligence while preserving contract, tenant, security, and governance invariants
---

# Repowise Autonomous Continuous Improvement Loop

This workflow defines a repeatable system loop for autonomous codebase improvement using
repowise intelligence. It is intentionally bounded: the loop may discover, rank, and fix
small safe improvements, but it must stop when evidence is stale, risk is unclear, or a
change would weaken Value Fabric's contract-first, tenant-safe, layered architecture.

## Operating Principles

1. **Evidence before edits.** Every action starts from current repowise findings, repository
   source-of-truth files, and existing tests.
2. **P0/P1 before polish.** Security, tenant isolation, contract drift, dead safe-to-delete
   code, and broken tests always outrank maintainability improvements.
3. **Small batches.** Each loop should produce one reviewable improvement batch with a clear
   validation command, not a broad rewrite.
4. **Contracts are hard gates.** API contracts, JSON schemas, agent output shapes, tenant
   propagation, frontend expectations, and production-readiness gates must not be weakened.
5. **No infinite autonomy.** The loop has explicit budgets, stop conditions, and escalation
   triggers.

## Loop Cadence

Run this loop when a maintainer asks for autonomous improvement, before production-readiness
reviews, or as a scheduled maintenance cycle. A single cycle should target one domain:

- `security`
- `contracts`
- `tenant-isolation`
- `dead-code`
- `code-health`
- `risk-hotspots`
- `frontend-governance`
- `agent-workflows`
- `documentation-drift`

Default batch budget:

```yaml
batch_budget:
  max_files_touched: 8
  max_source_files_touched: 5
  max_test_files_touched: 5
  max_findings_per_batch: 3
  max_self_correction_loops: 2
  max_tool_errors: 3
  require_human_review_for:
    - auth_or_identity_changes
    - database_migrations
    - public_api_shape_changes
    - provider_adapter_changes
    - production_gate_changes
    - destructive_dead_code_removal
```

## Phase 0 — Initialize State

Create or update the state object before any edits. Persist it in the execution report for the
cycle; do not commit transient reports unless they satisfy the repository reports policy.

```json
{
  "workflow_id": "repowise-autonomous-continuous-improvement",
  "cycle_id": "YYYY-MM-DD-domain-slug",
  "stage": "initialize",
  "domain": "security|contracts|tenant-isolation|dead-code|code-health|risk-hotspots|frontend-governance|agent-workflows|documentation-drift",
  "baseline_ref": null,
  "repowise_snapshot": {
    "overview": null,
    "health": null,
    "security": null,
    "risk": null,
    "dead_code": null,
    "why": null
  },
  "findings": {
    "P0": [],
    "P1": [],
    "P2": [],
    "P3": []
  },
  "selected_batch": [],
  "files_touched": [],
  "tests_run": [],
  "decisions": [],
  "blocked_by": null,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Phase 1 — Observe with Repowise

Run the smallest repowise assessment set that covers the selected domain. For full-codebase
maintenance cycles, run all baseline tools.

| Domain | Required repowise calls | Purpose |
|---|---|---|
| `security` | `get_security`, `get_risk`, `get_context` | Find CVEs, secrets, risky auth/security hotspots, and ownership/context. |
| `contracts` | `get_overview`, `get_risk`, `search_codebase`, `get_context` | Locate route/schema/type drift and co-change partners. |
| `tenant-isolation` | `search_codebase`, `get_symbol`, `get_risk`, `get_context` | Trace tenant propagation through routes, services, repositories, and tests. |
| `dead-code` | `get_dead_code`, `get_risk`, `get_context` | Identify safe removals and dependent/co-change risks. |
| `code-health` | `get_health`, `get_risk`, `get_symbol` | Identify biomarker issues, fragile files, and high-impact symbols. |
| `risk-hotspots` | `get_risk`, `get_health`, `get_why` | Prioritize hotspots with architectural intent and health signals. |
| `frontend-governance` | `get_health`, `search_codebase`, `get_context` | Find UI drift while preserving `DESIGN.md` conventions. |
| `agent-workflows` | `get_overview`, `get_why`, `get_risk`, `search_codebase` | Preserve provider-agnostic workflow, tool, prompt, and output contracts. |
| `documentation-drift` | `get_why`, `get_context`, `search_codebase` | Align docs with canonical implementation and governance paths. |

Record:

- affected files and owners;
- exact repowise finding identifiers or stable descriptions;
- confidence, severity, and freshness;
- related tests/contracts/docs;
- whether the finding is actionable without new product decisions.

## Phase 2 — Orient Against Repository Invariants

Before selecting work, cross-check findings against these source-of-truth paths:

- root `AGENTS.md` for repository-wide rules;
- `docs/AGENTS.md` for agent/workflow guidance;
- `packages/platform-contract/CONTRACT.md` for platform contract rules;
- `docs/development/DISCOVERY_MAP.md` for issue-to-source routing;
- `DESIGN.md` before any `apps/web/` change;
- `contracts/`, `packages/platform-contract/`, and affected service tests before API or
  payload changes.

Classify each finding:

- **P0 — must fix now:** live secret, critical/high security issue, failing critical gate,
  tenant-isolation bypass, contract break, production gate bypass, safe-to-delete dead code in
  critical paths with high confidence and low dependency risk.
- **P1 — next batch:** high-risk hotspot, medium security issue, repeated fragile pattern,
  missing denied-behavior test, contract/documentation drift with clear source of truth.
- **P2 — scheduled debt:** maintainability biomarker, ownership gap, duplicate utility, stale
  docs, low-confidence unused export.
- **P3 — opportunistic:** cosmetic cleanup, local readability improvement, non-critical
  optimization.

Reject or escalate findings that require product decisions, risky migrations, broad rewrites,
credential rotation outside the repo, or changes to identity/auth libraries.

## Phase 3 — Decide the Next Batch

Select at most three related findings from the highest non-empty priority tier. A valid batch
must have:

- a single domain and clear acceptance criteria;
- canonical files identified;
- expected tests or checks listed before edits;
- no unresolved contract, tenant, security, or frontend-governance ambiguity;
- a rollback strategy limited to reverting the batch commit.

Decision rule:

```text
if any P0 finding is actionable safely:
  select only P0 findings
elif P0 findings require escalation:
  document blocker and select no lower-priority work unless explicitly approved
elif P1 findings are actionable safely:
  select one small P1 batch
else:
  select P2/P3 only when it reduces future risk and does not churn stable code
```

## Phase 4 — Act with Targeted Changes

Implement the smallest safe change that satisfies the selected batch. Follow the existing
workflow mapped from the repowise signal:

| Repowise signal | Execution workflow |
|---|---|
| `get_security` live secret/CVE/pattern | `security-auditor` or dependency update workflow |
| `get_dead_code` safe removal | `dead-code-sweeper` |
| `get_health` biomarker or low health | `code-quality-improvement` |
| `get_risk` hotspot/co-change gap | `contract-enforcement-auditor` or code-boundary workflow |
| `get_why` decision drift | code-boundary or documentation-drift workflow |
| frontend health/design drift | frontend governance workflow after reading `DESIGN.md` |

Implementation guardrails:

- preserve tenant context and authenticated-context precedence;
- preserve public API response shapes unless contracts/types/tests are updated together;
- preserve provider-agnostic agent orchestration;
- add or update behavior tests for changed production-critical behavior;
- avoid generated files unless the repository command owns regeneration;
- never commit secrets or transient local evidence.

## Phase 5 — Verify and Re-Assess

Run validation in this order:

1. narrow tests for changed files;
2. relevant contract/security/frontend checks;
3. broader gates when warranted by risk.

Examples:

```bash
python -m pytest path/to/relevant/tests
python -m pytest tests/security
python -m pytest tests/contract
pnpm --dir apps/web run test
pnpm --dir apps/web run typecheck
make verify
```

Then re-run the repowise calls that produced the selected findings. The batch is complete only
when one of these is true:

- repowise no longer reports the finding;
- repowise reports a lower severity/risk with no new P0/P1 regression;
- the finding is documented as a false positive with source citations and validation evidence.

## Phase 6 — Report, Commit, and Handoff

Report every cycle with:

- baseline repowise signals used;
- selected findings and priority;
- files changed;
- tests/checks run with pass/fail status;
- before/after repowise result for the selected findings;
- residual risk and escalation items.

If code changed, commit the batch using a conventional commit and include:

```text
Co-authored-by: Ona <no-reply@ona.com>
```

## Stop Conditions

Stop the loop and escalate rather than continuing autonomously when:

- circuit breaker trips;
- a P0 security or tenant issue requires credentials, production access, or policy decisions;
- validation fails twice for different root causes;
- repowise findings conflict with source-of-truth contracts or tests;
- a batch would exceed the file budget;
- a fix requires public API, migration, identity, auth, or production-gate changes without an
  explicit request;
- no P0/P1 findings remain and remaining work is cosmetic churn.

## Continuous Improvement Metrics

Track these metrics per cycle and trend them over time:

- P0/P1 open count by domain;
- median and lowest health scores in touched areas;
- security findings by severity and EPSS/KEV status when available;
- safe-to-delete dead code count;
- hotspot score deltas;
- contract drift count;
- tenant-isolation denied-behavior test coverage;
- validation commands passed/blocked;
- rollback count.

## Completion Checklist

- [ ] State object initialized and updated through all phases.
- [ ] Repowise findings captured with severity, confidence, and affected files.
- [ ] Findings prioritized P0-P3 against repository invariants.
- [ ] Highest-priority actionable batch selected; lower-priority work deferred.
- [ ] Source-of-truth files and relevant tests/contracts reviewed before edits.
- [ ] Targeted changes made within batch budget.
- [ ] Narrow and relevant broader validation commands run and recorded.
- [ ] Repowise reassessment completed for selected findings.
- [ ] Residual risks and escalations documented.
- [ ] Commit created for code/docs changes with the required co-author trailer.
