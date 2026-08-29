# Goal: Audit Remediation & Refactor Plan Validity and Scope

## User Request

Audit the codebase against the suggested Remediation & Refactor Plan below to
determine whether each finding is valid, and scope the effort / define the
boundaries for each item. The plan was provided verbatim by the user.

> **Working assumption (autopilot):** this is an **assessment-only** goal. The
> deliverable is a written audit report. No application source code is to be
> modified; the only commits produced are the audit report, goal artefacts, and
> status updates.

## The Remediation & Refactor Plan (verbatim)

### Phase 1: P0/P1 Blockers — Must Fix Immediately

**PROD-001** — Complete release-candidate staging journey evidence
- Execute all seven P0 Playwright journeys.
- Use real tenant-aware authentication and live L1–L6 services.
- Retain JUnit, trace, screenshot/video, logs, release SHA, and seeded-data identity.
- Acceptance: all seven journeys pass against the same immutable candidate, or a
  launch owner explicitly removes the failing journey from scope.

**PROD-002** — Execute coordinated rollback and tenant-integrity restore drill
- Deploy the candidate.
- Write representative data for at least two tenants.
- Roll back application and schema state.
- Restore from backup.
- Prove Tenant A cannot access Tenant B’s restored records.
- Record RTO/RPO and owner approval.
- Acceptance: recovery meets approved targets with no cross-tenant ownership drift.

**IDENTITY-003** — Validate enterprise IdP mapping end to end
- Test success, logout, invalid token, missing tenant mapping, conflicting
  organization claims, role downgrade, and disabled-user behavior.
- Capture redacted audit events.
- Acceptance: malformed or ambiguous identity claims fail closed before
  repository access.

**L3-SEC-004** — Enforce a complete Neo4j query execution inventory
- Inventory all direct Neo4j execution sites.
- Assign explicit classifications: TENANT_SCOPED, PLATFORM_ADMIN, or MIGRATION_ONLY.
- Make CI reject unclassified runtime paths.
- Add hostile tests for every tenant-owned label and every variable-length traversal.
- Acceptance: no tenant request can reach raw `session.run(...)` without
  centralized enforcement.

**DB-SEC-005** — Standardize effective RLS context and validate pool cleanup
- Inspect the effective deployed policy catalog rather than historical source alone.
- Standardize `app.current_tenant` versus `app.tenant_id`.
- Remove application-controlled general-purpose bypass where feasible.
- Test checkout, transaction completion, rollback, and exception cleanup.
- Acceptance: hostile two-tenant tests pass for every tenant-owned table.

**CI-006** — Restore canonical gate reproducibility
- Build or use the supported dependency environment.
- Resolve each open contract/static failure without weakening assertions.
- Ensure Layer 1 and Layer 3 suites collect and terminate deterministically.
- Acceptance: `make verify` and `make production-readiness-gate` pass on the
  release SHA with retained artifacts.

### Phase 2: Safe, High-Leverage Refactors — Implement Now

**L3-SEC-007** — Tenant-scope benchmark-to-ValuePack usage counts
- Status: **Implemented and committed as 0648b46**.
- Added the tenant predicate to the ValuePack side of the optional graph join.
- Added a regression check that rejects an unscoped optional join.

**CI-008** — Add a narrow Cypher call-site manifest
- Build on the existing secured executor rather than inventing another query
  abstraction.
- Parse Python AST to find Neo4j execution calls.
- Require a small reviewed allowlist for schema and migration operations.
- Avoid touching unrelated query formatting or moving files.

**TEST-009** — Strengthen optional-match hostile tests
- Validate each tenant-owned node introduced by MATCH, OPTIONAL MATCH,
  comprehensions, and subqueries.
- Test path relationships as well as path nodes.
- Prefer executable validator tests over broad substring checks.

**DB-010** — Add deployed-policy drift inspection
- Query `pg_policy`/`pg_class` in PostgreSQL-backed CI.
- Compare tables with tenant columns against forced RLS and policy coverage.

## Refined Goal

Produce a defensible, evidence-grounded audit of the 10-item Remediation &
Refactor Plan against the actual codebase at a verified, recent revision of
`origin/main` (HEAD = `00bffb308f8168f4e432a7b6bc13aa3e54501392`, verified in
this worktree). For each of the ten items (PROD-001, PROD-002, IDENTITY-003,
L3-SEC-004, DB-SEC-005, CI-006, L3-SEC-007, CI-008, TEST-009, DB-010), the
audit must state:

1. **Verdict** — VALID, PARTIALLY VALID, INVALID, or UNVERIFIABLE, with rationale.
2. **Evidence** — file paths, line ranges, and commands actually run (with
   observed output summarized) that support the verdict. Evidence must be
   reproducible by the Inspector against the same revision.
3. **Scope / Effort** — which services, directories, tests, and CI surfaces the
   item would touch, an effort rating (S/M/L) per item, and any dependencies
   between items.
4. **Boundaries** — explicit in-scope and out-of-scope statements per item.

The audit is written to `.goals/security-remediation-audit/audit-report.md`
and is the primary deliverable. It does not modify application source.

## Acceptance Criteria

- [ ] Criterion 1 — `.goals/security-remediation-audit/audit-report.md` exists
      and covers **all 10 plan items**; each entry contains a verdict
      (VALID / PARTIALLY VALID / INVALID / UNVERIFIABLE), cited evidence,
      an effort rating (S/M/L), and explicit in-scope/out-of-scope boundaries.
- [ ] Criterion 2 — Every piece of cited evidence is checkable: each file
      reference exists at the audited revision (`00bffb308`), and each command
      claimed to have been run is recorded with its actual (summarized) output
      in the report. No fabricated file paths, SHAs, or command outputs.
- [ ] Criterion 3 — L3-SEC-007 is specifically resolved: the report proves or
      disproves the "implemented and committed as 0648b46" claim. Note:
      `0648b46` is NOT a valid object in this worktree; the report must locate
      the real state (present-elsewhere / absent / different SHa / different
      commit) and cite the actual code plus the regression check, if any.
- [ ] Criterion 4 — For each VALID or PARTIALLY VALID item, the report defines
      effort scope: files/directories/services to touch, an S/M/L effort rating,
      key risks, and ordering dependencies between items.
- [ ] Criterion 5 — Items whose validity cannot be determined from the
      repository alone (e.g., live-release evidence, external IdP behavior, DR
      drills) are labeled UNVERIFIABLE IN-REPO with the specific external
      evidence that would be required to confirm them.
- [ ] Criterion 6 — No application source code is modified. `git status` after
      the Builder commit shows only goal artefacts under `.goals/` (and no
      changes elsewhere).

## Scope Boundaries

**In scope:**
- Read-only audit of the repository against the 10-item plan.
- Grep/search/read of any file in the worktree; running read-only and
  collection-level commands (pytest --collect-only, git log, targeted test
  runs where they are fast and non-mutating) to substantiate evidence.
- Producing `.goals/security-remediation-audit/audit-report.md` plus goal
  artefacts (`status.json`, inspector feedback, summary).
- Verifying the L3-SEC-007 claim specifically (real commit/state, tenant
  predicate on the ValuePack side, regression check).
- Verifying existence/absence/failure-status of the gates named by CI-006
  (`make verify`, `make production-readiness-gate`) only insofar as they can be
  assessed statically or by fast local collection; full live `make verify` is
  only attempted if it is cheap and reliable in this environment.

**Out of scope:**
- Implementing or fixing any of the ten findings (assessment only; a
  recommendation section may describe what a fix would entail, without doing it).
- Changes to application source, tests, contracts, workflows, or docs outside
  `.goals/security-remediation-audit/`.
- Executing live P0 Playwright journeys, live rollback/restore drills, live IdP
  flows, or provisioning real infrastructure (these are UNVERIFIABLE-IN-REPO
  items and the report says so).
- Running the full heavy `make verify` / `make production-readiness-gate`
  suites if the environment cannot reproduce them; evidence of their current
  failure/pass state from CI configs and collect-only checks is sufficient.

## Applicable Project Conventions

**Quality gate command:**
- Targeted read-only checks only (this is an audit): `git log`, `git grep`,
  `pytest --collect-only` on named suites, `pnpm --dir apps/web exec tsc --noEmit`
  (only if needed to inspect type surface).
- Report-required gates to *reference* (not fix): `make contract-tests`,
  `make verify`, `make production-readiness-gate`.

**Commit convention:**
- Format: `type(scope): [B/I] description` (conventional commits, ≤72 chars).
- Builder commit trailer: `Assisted-by: OpenAI:GPT-5.6 Luna`
- Inspector commit trailer: `Assisted-by: OpenAI:GPT-5.6 Sol`
- Also include project trailer: `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`
- Commit directly to the current worktree branch (`valyntxyz-studious-bassoon`);
  do not create new branches.

**Guidelines:**
- `docs/contract.md`, `docs/governance.md`,
  `docs/reference/layer-runtime-path-governance.md`
- `.agent/skills/repo-audit/SKILL.md` (the audit system that plausibly
  originated this plan; its `config.yaml` defines ten audit areas A–J that map
  to the finding IDs).
- `AGENTS.md` (root) and per-service `AGENTS.md`.

**Rules:**
- Tenant isolation invariant: `tenant_id` must come from authenticated context.
- Contract-first: no speculative claims about API shapes without evidence.
- No fabricated evidence: every cited file/sha must be verified to exist.
- The repository root is the worktree
  `C:\Users\BBB\.copilot\repos\Fabric_4L\.worktrees\valyntxyz-studious-bassoon`;
  do not touch the main checkout.

## Context Map (helpful starting points, to be confirmed/refined by audit)

- Layer 3 Neo4j execution: `services/layer3-knowledge/src/` — search for
  `session.run(`, `driver.execute_query(`, `OPTIONAL MATCH`, `MATCH`.
- Layer 6 benchmarks → ValuePack usage counts: `services/layer6-benchmarks/src/`.
- Layer 4 agents (agent orchestration, guards): `services/layer4-agents/src/layer4_agents/`.
- Layer 5 ground truth: `services/layer5-ground-truth/src/layer5_ground_truth/`.
- Shared tenant/context helpers: `packages/shared/src/value_fabric/shared/`.
- RLS / migrations: per-service Alembic dirs and any SQL policy files under
  `services/*/alembic/`, `infra/`, and SQL seed files.
- Frontend e2e (PLAYWRIGHT journeys): `apps/web/` — Playwright config and
  `e2e/`/`tests/e2e` directories.
- CI gates: `.github/workflows/` and `Makefile` targets (`contract-tests`,
  `verify`, `production-readiness-gate`).
- Keycloak / IdP realm seed: `infra/` and any keycloak realm JSON.