# Audit Report — Remediation & Refactor Plan Validity and Scope

Goal: `.goals/security-remediation-audit/goal.md`
Revision audited: `00bffb308f8168f4e432a7b6bc13aa3e54501392` (== `origin/main`, verified)
Worktree: `C:\Users\BBB\.copilot\repos\Fabric_4L\.worktrees\valyntxyz-studious-bassoon`
Date: 2026-06 (evidence timestamps in `signoff-evidence/`)

This report is **assessment-only**. No application source code was modified.
Each of the ten plan items below states: **Verdict**, **Evidence** (file paths
+ commands actually run, with observed output), **Scope / Effort**, and
**Boundaries**.

Finding IDs (PROD-001 … DB-010) do not appear anywhere in the repository; they
cannot be traced to a committed audit artifact. `.audit_cache/` and
`audit_reports/` (where a repo-audit would persist such findings) are
gitignored (`gitignore:239-240`). The AuditOrchestrator skill
(`.agent/skills/repo-audit/`) defines ten audit areas (A–J); the plan's IDs
are a plausible reformatting of that output, but no committed artifact links
them to concrete findings. Each item below was therefore assessed on its own
merits against the live codebase.

---

## Phase 1 — P0/P1 Blockers

### PROD-001 — Complete release-candidate staging journey evidence

**Verdict: VALID** (evidence of the gap exists in the repository itself).

**Evidence**

- The canonical P0 spec set differs from the plan's "seven journeys":
  - `apps/web/package.json:62` — `test:e2e:validation:p0` runs **12** specs
    (`j1-golden-path-backend-integrated`, `j6-account-prospect-lifecycle`,
    `j6-account-tenant-switching`, `j7-value-realization-and-calculation`,
    `j8-approval-review-gates`, `j9-agent-grounding-governance`,
    `j10-layer-ui-validation`, `j11-golden-path-business-lifecycle`,
    `j20-billing-entitlement-gates`, `security/tenant-isolation-validation`,
    `security/deep-link-tenant-isolation-deep`, `export-workflows`).
  - `apps/web/package.json:80` — `test:e2e:validation:p0:deep` runs exactly
    **7** specs (`j1-golden-path-deep`, `j7-calculation-evidence-deep`,
    `j8-approval-review-deep`, `j9-agent-grounding-deep`,
    `j10-layer-ui-validation-deep`, `security/tenant-isolation-deep`,
    `export/export-workflows-deep`). The plan's "seven P0 journeys" most
    plausibly refers to this `:deep` P0 set; the standard P0 set has 12.
- Playwright artifact retention is configured and fit for the acceptance
  criterion: `apps/web/playwright.config.ts:63-77` —
  `reporter: [['junit', {outputFile: 'e2e-results/junit.xml'}], …]`,
  `trace: 'retain-on-failure'`, `screenshot: 'only-on-failure'`,
  `video: 'retain-on-failure'`.
- **Live P0 evidence is missing:** the only committed live-P0 run is a
  failure. `signoff-evidence/e2e/e2e-live-p0-20260613.json` —
  candidate `rc-2026-06-13-116815f3`, `status: "fail"`, `total: 26,
  passed: 0, failed: 26`, including `j1-golden-path-backend-integrated.spec.ts
  :: (syntax error — file unparsable, whole spec blocked)`.
- `signoff-evidence/p0-journeys-20260613.json` —
  surrogate environment, `total: 15, passed: 1, failed: 14`,
  classification `RE_TESTABLE`, summary "auth and runtime crash resolved;
  remaining failures are frontend route/UX drift".
- These files prove the go-to-release gate was **not** satisfied for the last
  candidate. No in-repo artifact shows all P0 journeys passing against a
  single immutable candidate.

**Scope / Effort: L**
- Touch: `apps/web/` Playwright spec fixes (the failing routes/UX), e2e
  evidence capture (`e2e-results/`, `signoff-evidence/`), a release workflow
  that records release SHA + seeded-data identity. No test-selection change is
  first-order: the P0 definition already exists (12 standard / 7 deep).
- Dependencies: requires a live L1–L6 stack and immutable candidate — nothing
  in this bullet can be closed statically.
- Command (evidence): `Get-Content signoff-evidence/e2e/e2e-live-p0-20260613.json`,
  `Select-String apps/web/package.json -Pattern "test:e2e:validation:p0"`.

**Boundaries**
- In scope: re-running the defined P0 (standard or deep) against an immutable
  candidate; fixing the failing specs/routes needed for the gate; retaining
  JUnit/trace/screenshots/video/logs/SHA/seed identity; or an explicit launch
  owner scope-removal decision.
- Out of scope: inventing a new "seven-journey" definition that contradicts the
  committed P0 sets; non-P0 (P1/P2) journey fixes not needed for the gate.

---

### PROD-002 — Execute coordinated rollback and tenant-integrity restore drill

**Verdict: PARTIALLY VALID** — the rollback policy and a failed image-level
drill exist; the specific coordinated, two-tenant, cross-tenant-proof restore
drill does not.

**Evidence**

- Policy exists with recoverable targets: `.fabric/gate-engineering/rollback-recovery-policy.md:22-24`
  — RPO ≤ 5 min, RTO ≤ 1 hour (quarterly DR drill), restore verification
  quarterly via `pnpm ops:restore:dry-run`.
- A real drill was run and **failed by design**, proving the plan's concern:
  `signoff-evidence/p0-rollback-20260613.json` —
  `rollback_type: image-level-rollback-drill`, `rollback_result: FAILED
  (EXPECTED DRILL OUTCOME)`. Failure: rolled-back image lacked the `canonical`
  package dependency → `ModuleNotFoundError: No module named 'canonical'`.
  Recovery of the live candidate: `recovery_time_seconds: 58`, PASS. Doctrine
  was updated (`docs/runbooks/deployment-rollout-and-rollback.md`) to require
  coordinated image + source/config dependency rollback.
- The evidence file's own recommendation confirms the gap the plan targets:
  "Do not claim production rollback readiness until a coordinated
  image+dependency rollback is rehearsed in a production-like environment with
  immutable, version-pinned images." Classification: `RE_TESTABLE`.
- **Not shown anywhere:** representative data for two tenants, a schema-state
  rollback leg, restore-from-backup leg, a hostile Tenant-A-reads-Tenant-B
  check on restored rows, or recorded RTO/RPO + owner approval for the
  coordinated drill.

**Scope / Effort: M**
- Touch: deploy/restore scripts + compose overrides, backup/restore runbook,
  two-tenant seed fixture, cross-tenant restore assertion, `signoff-evidence/`.
- Dependencies: needs a running candidate (overlaps with PROD-001's stack).

**Boundaries**
- In scope: coordinated image+dependency rollback drill, schema-state rollback,
  restore-from-backup, two-tenant isolation proof on restored data, RTO/RPO and
  owner-approval evidence.
- Out of scope: re-running the already-completed image-level drill as
  acceptance; changing the RPO/RTO targets without owner approval.

---

### IDENTITY-003 — Validate enterprise IdP mapping end to end

**Verdict: PARTIALLY VALID** — token-level fail-closed behavior is tested;
the enterprise IdP mapping scenarios (missing tenant mapping, conflicting
organization claims, role downgrade, disabled user) and redacted-audit capture
are not evidenced.

**Evidence**

- Robust OIDC token validation unit coverage exists:
  `services/layer4-agents/tests/test_oidc_id_token_validation.py`
  (invalid signature/issuer/audience, expired, malformed, nonce, stale `iat`);
  `services/layer4-agents/tests/test_oidc.py`,
  `tests/integration/test_oidc_flow.py`, `tests/integration/test_oidc_live.py`,
  `tests/security/test_oidc.py`.
- The backend is IdP-agnostic OIDC (no Keycloak-specific code deps;
  `docs/operations/keycloak-integration.md`).
- `signoff-evidence/p0-sso-20260613.json` (candidate `rc-2026-06-13-116815f3`,
  local Keycloak surrogate) — checks show token claims carry `tenant_id`,
  `org_id`, `realm_access.roles` (historical PASS), invalid credentials /
  invalid bearer rejected with 401, `token_validation: VERIFIED_FAIL_CLOSED`,
  but `well_known` and `admin_console_reachable` are **NOT_EXERCISED** (no
  Docker daemon), and classification is `RE_TESTABLE`. Recommendation explicitly
  says "SSO/OIDC validation against a real enterprise IdP (or Clerk staging
  tenant) remains required before Core GA."
- Scenarios in the plan not covered by any committed test or evidence file:
  missing tenant mapping, conflicting organization claims, role downgrade,
  disabled-user behavior, and redacted audit-event capture.

**Scope / Effort: M**
- Touch: `services/layer4-agents/tests/test_oidc*` (new scenario tests for
  tenant-mapping conflict / missing-map / disabled user / role downgrade),
  audit capture in `packages/shared/src/value_fabric/shared/identity/`
  middleware, a live IdP (Keycloak profile `sso` or Clerk staging tenant),
  `signoff-evidence/`.
- Dependencies: live IdP environment; `docker compose --profile sso up` where
  Docker is available.

**Boundaries**
- In scope: the six listed behaviors, fail-closed-before-repository-access,
  redacted audit-event capture.
- Out of scope: swapping OIDC for a vendor-specific IdP SDK; changing the
  token schema/claims contract without updating `docs/contract.md` and the
  OpenAPI specs.

---

### L3-SEC-004 — Enforce a complete Neo4j query execution inventory

**Verdict: PARTIALLY VALID / MOSTLY ADDRESSED** — an AST-based inventory,
reviewed allowlist, and CI enforcement already exist, but with a different
taxonomy ("Safe" + expiry) than the plan's TENANT_SCOPED / PLATFORM_ADMIN /
MIGRATION_ONLY, and the absolute "no tenant request reaches raw
`session.run(...)` without centralized enforcement" is not literally true (many
routes call `neo4j.run(...)` directly, tenant-scoped by convention).

**Evidence**

- CI enforcement is committed: `.github/workflows/pr-checks.yml:825` runs
  `python scripts/ci/check_layer3_cypher_scope.py services/layer3-knowledge/src
  --report-json`. The script uses Python AST (`scripts/ci/check_layer3_cypher_scope.py:15: import ast`,
  `:143: tree = ast.parse(...)`) to find `.run(` / `.execute_query(` sites.
- Reviewed allowlist: `config/production-readiness/l3-cypher-tenant-inventory-allowlist.json`
  — `owner: platform-security`, `schema: 1`, **76 allowlisted findings** with
  `expires_on` dates and justifications (e.g., `entities.py::list_entities`
  re-allowlisted after a rebase shifted line numbers). Sidecar inventory:
  `docs/audit/l3-cypher-tenant-inventory.json`.
- Policy statement: `services/layer3-knowledge/src/db/__init__.py:11` —
  "Direct ``session.run(...)`` calls are intentionally forbidden in high-risk
  paths" (with exceptions, implemented as review + allowlist).
- Centralized helpers exist: `TenantQueryExecutor`
  (`services/layer3-knowledge/src/db/query_execution.py:283`),
  `run_scoped_query` (~`:623`), `execute_tenant_cypher`,
  `TenantScopedCypher` in `packages/shared/src/value_fabric/shared/identity/isolation.py`.
- Hostile tests exist for tenant-owned labels: `services/layer3-knowledge/tests/security/`
  (`test_benchmarks_cross_tenant_isolation.py`,
  `test_formula_governance_cross_tenant_isolation.py`,
  `test_models_cross_tenant_isolation.py`), plus
  `services/layer3-knowledge/tests/test_cross_tenant_hostile.py`,
  `test_cross_tenant_hostile_behavioral.py`, `test_tenant_isolation_static.py`,
  wired in `config/ci/pytest_policy.yaml:50-51`.
- **Gap:** the taxonomy is "Safe" vs the plan's three explicit classes; 76
  allowlisted (expiring) findings are tolerated by CI, so "unclassified" is not
  categorically rejected; variable-length traversal coverage is not
  evidenced.
- **Live evidence of what the acceptance criterion forbids:** raw `neo4j.run`
  with tenant predicates but no executor wrapper is pervasive in
  `services/layer3-knowledge/src/api/routes/*` (see L3-SEC-007 for the
  concrete unscoped case).

**Scope / Effort: M**
- Touch: `scripts/ci/check_layer3_cypher_scope.py`, the two inventory JSONs,
  `services/layer3-knowledge/src/api/routes/*` (re-trunk calls through the
  executor or justify a classification), hostile tests for remaining labels
  and variable-length traversals, `pr-checks.yml`.
- Dependencies: overlaps TEST-009 (hostile coverage) and CI-008 (manifest);
  do L3-SEC-007 first because it is the one concrete known-broken site.

**Boundaries**
- In scope: classify every direct execution site explicitly; make CI fail on
  unclassified runtime paths; hostile tests for tenant-owned labels and
  variable-length traversals.
- Out of scope: a wholesale Cypher rewrite or moving files; removing the
  allowlist mechanism without a replacement classification gate.

---

### DB-SEC-005 — Standardize effective RLS context and validate pool cleanup

**Verdict: PARTIALLY VALID / MOSTLY ADDRESSED.** The premise that
`app.current_tenant` exists as a competing GUC is **false** in this repo —
`app.tenant_id` is the single canonical GUC. The remaining pieces
(deployed-policy inspection, harness bypass review, pool-cleanup tests) are
partially present.

**Evidence**

- Canonical GUC is `app.tenant_id` everywhere: `services/api/migrations/versions/0001_clerk_auth_baseline.sql`,
  `0002_fabric_api_records_jsonb_bridge.sql`, and
  `services/layer4-agents/migrations/sql/031_harness_tables.sql` policies.
- **`git grep -l "app.current_tenant" -- "*.sql"` → exit 1, zero matches.** The
  "standardize `app.current_tenant` versus `app.tenant_id`" action item is
  moot — there is a single GUC already.
- Deployed-policy inspection exists as a gate: `scripts/ci/migration_status_report.py`
  (lines 340-428) queries `pg_class` for `relrowsecurity` /
  `relforcerowsecurity` and `pg_policies`, asserts forced RLS +
  `app.tenant_id` reference, and is wired as `Makefile:198 db-migrate-check`
  ("Read-only database migration drift gate; fails on drift"). **This is
  DB-010's mechanism already present.**
- Application-controlled bypass exists and is plausibly the target of the plan:
  `services/layer4-agents/migrations/sql/031_harness_tables.sql:120-134` —
  `tenant_isolation_policy` compares `current_setting('app.tenant_id', true)`;
  `admin_bypass_policy` grants **empty-**`app.tenant_id` access to
  `admin_role, system_role`. This is role-scoped, but is exactly a
  general-purpose "empty tenant = everything" policy to review.
- Pool cleanup coverage: `tests/integration/test_transaction_rollback.py`
  exists (transaction completion / rollback / exception cleanup checks).

**Scope / Effort: M**
- Touch: review/remove/justify the empty-GUC bypass policies in
  `services/*/migrations/sql`; extend `migration_status_report.py`
  (deployed-policy drift gate); extend pool-cleanup tests; run hostile
  two-tenant tests per tenant-owned table (many exist; per-table inventory not
  evidenced).
- Dependencies: none blocking; a PostgreSQL-backed CI DB is needed to exercise
  `db-migrate-check`.

**Boundaries**
- In scope: GUC standardization (verify/limit to `app.tenant_id`), bypass
  removal or explicit role-scoped justification, pool-cleanup validation,
  two-tenant hostile RLS tests for every tenant-owned table.
- Out of scope: renaming the GUC (breaking all existing policies/migrations
  without a compat plan); `app.current_tenant` support work (no such code exists).

---

### CI-006 — Restore canonical gate reproducibility

**Verdict: UNVERIFIABLE-IN-REPO** (gate infrastructure is fully wired; the
current pass/fail state of `make verify` / `make production-readiness-gate`
cannot be determined without executing the full environment).

**Evidence**

- `Makefile:100 verify:` (aggregates all checks), `Makefile:927
  production-readiness-gate:` → `scripts/ci/run_production_readiness_gate.py`
  + `scripts/ci/validate_production_readiness_manifest.py`.
- CI requires the gate: `.github/workflows/pr-checks.yml:503,526`
  (`production-readiness-gate` job → `make production-readiness-gate`) and
  `:2821,2835` (`pnpm run test:critical-behaviors`); the job is a peer
  dependency of merge (`pr-checks.yml:2950,2995`).
- Behavior contract gates exist: `Makefile:276-282` (`check-behavior-contract`
  via `scripts/ci/behavior_readiness_audit.py`).
- Allowlist/debt baselines exist (`config/ci/pytest_policy.yaml`,
  `config/ci/skip registers`, l3-cypher allowlist), i.e., the gate system is
  designed for known-debt tolerance — the plan's "resolve without weakening
  assertions" is a standing policy question, not an absent mechanism.
- Layer 1 / Layer 3 deterministic collection is an environmental claim; no
  committed evidence of nondeterminism was found, and no committed artifact
  proves a green `make verify` on a release SHA either — the P0 evidence (see
  PROD-001) is red on the nearest candidate.

**Scope / Effort: L**
- Touch: environment provisioning (supported dependency env for Python
  services + frontend), resolution of whatever contract/static failures
  surface, CI yaml to retain artifacts.
- Dependencies: requires the live stack and Docker; cannot be scoped by file
  path before running.

**Boundaries**
- In scope: reproducing the canonical gates on a release SHA and retaining
  artifacts; fixing surfaced failures without weakening assertions.
- Out of scope: redefining `verify` / `production-readiness-gate` contents;
  deferring to local-only success without CI parity.

---

## Phase 2 — Safe, High-Leverage Refactors

### L3-SEC-007 — Tenant-scope benchmark-to-ValuePack usage counts

**Verdict: VALID — the finding is real AND the plan's implementation claim is
FALSE.** The commit `0648b46` does not exist in this repository, and the
unscoped `OPTIONAL MATCH (vp:ValuePack)` joins are still present at HEAD.

**Evidence**

- **Commit claim disproved:**
  `git cat-file -t 0648b46` → `fatal: ... 0648b46: Not a valid object name`.
  `git log` shows no `0648b46` in the worktree history (HEAD lineage:
  `00bffb308 ← 216fd863d ← f188cb355 ← f3067ec55 …`). `origin/main` == HEAD,
  so the claim is false for the remote tip too.
- **Vulnerable code still present (list endpoint):**
  `services/layer3-knowledge/src/api/routes/benchmarks.py:129-137` —
  ```cypher
  MATCH (b:Benchmark)
  WHERE b.tenant_id = $tenant_id
  {extra_where}
  OPTIONAL MATCH (vp:ValuePack)-[:hasBenchmark]->(b)
  RETURN b, count(DISTINCT vp) as usage_count
  ```
  The `Benchmark` node is tenant-scoped; the **`ValuePack` side is not**. A
  malicious tenant owning a `ValuePack` can observe another tenant's
  `Benchmark` via this join, and `usage_count` leaks across tenants.
- **Vulnerable code still present (single benchmark):**
  `benchmarks.py:206-211` — same `OPTIONAL MATCH (vp:ValuePack)-[:hasBenchmark]->(b)`
  with `WHERE b.tenant_id = $tenant_id`, same unscoped `vp`.
- **Same pattern elsewhere:** `services/layer3-knowledge/src/api/routes/formulas.py:1310`
  (delete-formula ref-count) —
  `OPTIONAL MATCH (vp:ValuePack)-[:USES_FORMULA]->(f)` / `count(vp)` with only
  `f.tenant_id = $tenant_id` scoped.
- **No tenant predicate on `vp` anywhere in those files:**
  `Select-String benchmarks.py,formulas.py -Pattern "vp.tenant_id"` → no
  matches (grep exit 128).
- **No regression check exists:**
  `git grep "vp.tenant_id\|ValuePack.*tenant_id"` over
  `services/layer3-knowledge/tests` and `tests/layer3` → no matches. The
  plan's "Added a regression check that rejects an unscoped optional join" is
  therefore also false.
- The existing benchmark hostile test does **not** cover the `vp` side: it
  regex-matches only `:Benchmark|:BenchmarkPolicy` node patterns and checks
  the whole Cypher block for the substring `tenant_id` — which passes because
  `b.tenant_id` is present.
  `services/layer3-knowledge/tests/security/test_benchmarks_cross_tenant_isolation.py`
  (15 tests; `test_all_cypher_match_clauses_include_tenant_id` at :106).

**Scope / Effort: S** (smallest item)
- Touch: `services/layer3-knowledge/src/api/routes/benchmarks.py:133,209`
  (add `vp.tenant_id = $tenant_id` or scope the join to the authenticated
  tenant), optionally `formulas.py:1310`; one regression test that rejects an
  unscoped `OPTIONAL MATCH` on a tenant-owned label.
- Dependencies: precede TEST-009 (add the hostile test) and L3-SEC-004
  (classify the site).

**Boundaries**
- In scope: the ValuePack-side tenant predicate, a regression check,
  corresponding hostile test.
- Out of scope: changing usage-count semantics, moving files, query
  reformatting unrelated to tenant scoping.

---

### CI-008 — Add a narrow Cypher call-site manifest

**Verdict: MOSTLY ADDRESSED / ALREADY IMPLEMENTED.** The requested AST
manifest + reviewed allowlist already exists as
`scripts/ci/check_layer3_cypher_scope.py` + the allowlist inventory, wired
into CI. Remaining work is tightening, not building.

**Evidence**

- `scripts/ci/check_layer3_cypher_scope.py` parses Python AST
  (`:15 import ast`, `:143 ast.parse`) to locate Neo4j execution calls and is
  wired at `.github/workflows/pr-checks.yml:825`.
- It builds on the secured-executor/non-raw-session model (see L3-SEC-004) and
  is backed by a reviewed allowlist for tolerated sites:
  `config/production-readiness/l3-cypher-tenant-inventory-allowlist.json`
  (76 entries, `owner: platform-security`, expiry-dated `expires_on`) and
  `docs/audit/l3-cypher-tenant-inventory.json`.
- The "small reviewed allowlist for schema and migration operations" is
  realized today as a general `run-call-unresolved` allowlist; if the plan
  wants schema/migration *only*, the allowlist should be narrowed.

**Scope / Effort: S**
- Touch: `scripts/ci/check_layer3_cypher_scope.py` (report format/class
  allowlist), the inventory JSONs, `pr-checks.yml` (no new job needed).

**Boundaries**
- In scope: narrowing the allowlist to schema/migration where feasible;
  classification output alignment; regression tests for the checker itself.
- Out of scope: building a new query-abstraction layer; renaming/moving the
  existing script or files it scans.

---

### TEST-009 — Strengthen optional-match hostile tests

**Verdict: VALID** (the specific optional-join/`vp`-side hostile coverage is
genuinely missing; existing hostile tests cover `MATCH` on Benchmark/Formula
nodes and raw-Cypher rejection but not the `vp` node or path relationships).

**Evidence**

- Existing hostile infra to build on: `services/layer3-knowledge/tests/security/test_benchmarks_cross_tenant_isolation.py`
  (benchmark read/write/fail-closed), `test_formula_governance_cross_tenant_isolation.py`,
  `test_models_cross_tenant_isolation.py`, `services/layer3-knowledge/tests/test_cross_tenant_hostile.py`,
  `test_cross_tenant_hostile_behavioral.py`, `tests/security/*hostile*`.
- The benchmark test's `test_all_cypher_match_clauses_include_tenant_id`
  (`:106-128`) only scans `re.findall` for `MATCH ... :(Benchmark|BenchmarkPolicy)`
  and asserts the substring `tenant_id` appears in the block — it **misses
  `OPTIONAL MATCH (vp:ValuePack)`** and **misses path relationships**
  (`-[:hasBenchmark]->`), exactly what the plan calls out.
- Executable validator infrastructure exists to prefer over substring checks:
  `services/layer3-knowledge/src/security/query_validator.py` +
  `services/layer3-knowledge/tests/test_query_validator.py`
  (`TestQueryValidator`, `TestValidatedNeo4jSession`,
  `TestQueryValidatorEdgeCases`).

**Scope / Effort: S**
- Touch: `services/layer3-knowledge/tests/security/test_benchmarks_cross_tenant_isolation.py`
  (add `vp`-side + relationship-path assertions or move them to validator
  tests), optionally extend `query_validator.py`. No production-code change
  required beyond L3-SEC-007.

**Boundaries**
- In scope: options for every tenant-owned node introduced by `MATCH` /
  `OPTIONAL MATCH` / comprehensions / subqueries in the benchmark/formula
  routes; path relationships; validator-executable checks.
- Out of scope: rewriting the entire hostile test suite; live-Neo4j-dependent
  tests that cannot run in CI.

---

### DB-010 — Add deployed-policy drift inspection

**Verdict: MOSTLY ADDRESSED / ALREADY IMPLEMENTED.** The requested
`pg_policy`/`pg_class` comparison against forced RLS + tenant-column coverage
exists as `scripts/ci/migration_status_report.py`, gated by
`make db-migrate-check`.

**Evidence**

- `scripts/ci/migration_status_report.py:357-358` — `SELECT c.relname,
  c.relrowsecurity, c.relforcerowsecurity FROM pg_class c …`; `:371` —
  `FROM pg_policies …`; `:407-417` — fails tables that are not RLS-forced or
  whose policies do not reference `app.tenant_id`; `:425` —
  `"uses_app_tenant_id": uses_tenant_guc`.
- Wired as `Makefile:198-199 db-migrate-check / db-migrate-status`
  ("fails on drift") and `db-production-readiness-gate` (`Makefile:951`).
- This is effectively "query `pg_policy`/`pg_class` in PostgreSQL-backed CI,
  compare tables with tenant columns against forced RLS and policy coverage" —
  the plan's wording — already implemented.

**Scope / Effort: S**
- Touch: extend `migration_status_report.py` to run in PR CI for L1/L4 SQL if
  not already wired, or add it to the production-readiness gate if desired;
  add a drift fixture test. Likely no new script needed.

**Boundaries**
- In scope: running deployed-policy inspection in PR/PostgreSQL-backed CI;
  drift-failure assertions; coverage reporting per tenant-owned table.
- Out of scope: duplicate tooling; historical-source-only inspection replacing
  the live `pg_policies` check.

---

## Cross-cutting findings

1. **L3-SEC-007's "implemented and committed as 0648b46" is the single most
   important result of this audit:** the commit does not exist (`git cat-file
   -t 0648b46` fails), and the unscoped `OPTIONAL MATCH (vp:ValuePack)` joins
   in `benchmarks.py:133/209` and `formulas.py:1310` remain at `origin/main`.
2. **P0 definition discrepancy:** the plan says "seven P0 journeys"; the
   committed standard P0 set is 12 specs, while `:p0:deep` is exactly 7.
   Whoever executes PROD-001 must pin which set is in scope.
3. **PROD-001/PROD-002/IDENTITY-003 all point at the same physical stack:** a
   live L1–L6 environment with an IdP. These three items are environment-bound
   and share setup cost.
4. **CI-008, DB-010, and much of L3-SEC-004 / DB-SEC-005 are already largely
   implemented** under different names/taxonomy. The plan would buy the most
   value by verifying the existing gates reproduce rather than re-building
   them.

## Verification table (commands run)

| Command | Result (summarized) |
|---|---|
| `git rev-parse HEAD` | `00bffb308f8168f4e432a7b6bc13aa3e54501392` |
| `git rev-parse origin/main` | `00bffb308f8168f4e432a7b6bc13aa3e54501392` (== HEAD) |
| `git cat-file -t 0648b46` | `fatal: Not a valid object name 0648b46` |
| `git status --short` | `?? .goals/security-remediation-audit/` only (clean otherwise) |
| `git grep -l "app.current_tenant" -- "*.sql"` | exit 1 — no matches |
| `Select-String benchmarks.py, formulas.py -Pattern "vp.tenant_id"` | no matches |
| `Select-String apps/web/package.json -Pattern "test:e2e:validation:p0"` | 12-spec standard P0, 7-spec `:p0:deep` |
| `Read signoff-evidence/e2e/e2e-live-p0-20260613.json` | `fail`, 26/26 failed on `rc-2026-06-13` |
| `Read signoff-evidence/p0-rollback-20260613.json` | image-level rollback FAILED, 58s recovery, RE_TESTABLE |
| `Read signoff-evidence/p0-sso-20260613.json` | RE_TESTABLE; well_known/console NOT_EXERCISED |