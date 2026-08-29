# L3-SEC-007: Tenant-Scope Benchmark↔ValuePack Usage Counts (+ TEST-009 fold-in)

**Branch:** `fix/l3-sec-007-valuepack-tenant-scoping` (new branch, operator-confirmed — keeps the assessment-only audit branch clean)
**Description:** Close the live cross-tenant `usage_count` leak identified by the completed security-remediation audit: add the tenant predicate to the `vp:ValuePack` side of the three unscoped `OPTIONAL MATCH` joins in L3, and replace the regex-gap hostile tests with executable validator + behavioral assertions.

## Goal
The audit on `valyntxyz-studious-bassoon` proved the plan's L3-SEC-007 "implemented as 0648b46" claim is false and the unscoped joins remain live at `origin/main`. This PR implements the fix (the audit's single most important finding) plus the TEST-009 ratification so the leak can neither exist nor regress silently.

## Context (facts verified 2026-08-28)
- **Live unscoped joins** (asset `vp:ValuePack` is tenant-owned — `TENANT_OWNED_LABELS` includes `ValuePack`, `src/utils/cypher_security.py:103`):
  - `services/layer3-knowledge/src/api/routes/benchmarks.py:133` — `list_benchmarks`: `OPTIONAL MATCH (vp:ValuePack)-[:hasBenchmark]->(b)` with only `b.tenant_id = $tenant_id`; returns `count(DISTINCT vp) as usage_count`.
  - `services/layer3-knowledge/src/api/routes/benchmarks.py:209` — `get_benchmark`: same unscoped `vp` side → per-benchmark `usage_count`.
  - `services/layer3-knowledge/src/api/routes/formulas.py:1312` — `delete_formula` ref-count guard: `OPTIONAL MATCH (vp:ValuePack)-[:USES_FORMULA]->(f)` with `WHERE f.tenant_id = $tenant_id` only → `count(vp) as ref_count` and the delete-block decision can be influenced cross-tenant.
- **Canonical correct pattern already exists** in the sibling route: `value_packs.py:458-461` scopes the far side inline — e.g. `OPTIONAL MATCH (vp)-[:hasBenchmark]->(b:BenchmarkDataset {tenant_id: $tenant_id})`. ValuePack nodes carry `tenant_id` (see `value_packs.py:411`); there is **no** `global_system`/ownership-mode variant for ValuePack (that concept exists only on L6 BenchmarkDataset).
- **Existing hostile tests are substring checks** (TEST-009 gap): `test_benchmarks_cross_tenant_isolation.py::test_list_benchmarks_query_has_tenant_filter` and `test_all_cypher_match_clauses_include_tenant_id` (L106), plus `test_formula_governance_cross_tenant_isolation.py::test_all_cypher_match_on_formula_nodes_include_*` (L113), assert a tenant filter exists somewhere in the template — they pass even when the `vp` node is unscoped.
- **Validators:** `validate_tenant_scoped_cypher` (`src/utils/cypher_security.py`, re-exported via `src/services/cypher_scope_guard.py` shim) is the canonical static check; `QueryValidator(fail_closed=True)` is used by `Neo4jTenantSessionSecured.run` (`api/dependencies_tenant_secured.py:102,212`). The AST gate `scripts/ci/check_layer3_cypher_scope.py` classifies queries Safe/Unsafe/Unknown with an allowlist.
- **Commit convention (from goal.md):** `type(scope): [B/I] description`, `Assisted-by:` trailer, `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>` trailer.

## Implementation Steps

### Step 1: Tenant-scope the `vp` side of the three live optional joins [COMPLEX]
**Files:**
- `services/layer3-knowledge/src/api/routes/benchmarks.py` (L133, L209)
- `services/layer3-knowledge/src/api/routes/formulas.py` (~L1312, `delete_formula` ref-count query)

**What:** Add the tenant predicate to the `vp:ValuePack` node in each of the three `OPTIONAL MATCH` clauses, mirroring the canonical `value_packs.py` style: `OPTIONAL MATCH (vp:ValuePack {tenant_id: $tenant_id})-[:hasBenchmark]->(b)`. `$tenant_id` is already a bound parameter at every call site (`list_benchmarks`/`get_benchmark` pass `tenant_id=tenant_id`; `delete_formula` passes it via `neo4j.run(..., tenant_id=tenant_id)`). No other `ValuePack`-introducing clause in these files exists (verified — the only matches are the three cited clauses).
**Testing:** `pytest` the existing security suites (`test_benchmarks_cross_tenant_isolation.py`, `test_formula_governance_cross_tenant_isolation.py`) — they must pass unchanged since the filter-count assertions are still satisfied by the `b.tenant_id`/`f.tenant_id` filters; then add a dedicated hostile test in Step 2 that specifically proves the `vp` count cannot be cross-tenant.

### Step 2: Executable validator + behavioral regression (TEST-009 fold-in) [COMPLEX]
**Files:**
- NEW `services/layer3-knowledge/tests/security/test_optional_join_tenant_scope.py`
- `services/layer3-knowledge/tests/security/test_benchmarks_cross_tenant_isolation.py` (tighten `test_all_cypher_match_clauses_include_tenant_id`)
- `services/layer3-knowledge/tests/security/test_formula_governance_cross_tenant_isolation.py` (tighten the formula equivalent)

**What:**
1. **Executable validator assertion (replaces the regex gap):** unit tests that run `validate_tenant_scoped_cypher` on the *old* unscoped template and assert it raises `TenantCypherValidationError` naming `ValuePack`, and on the *new* scoped template and assert it passes. This is the "executable validator test over broad substring checks" the audit asks for.
2. **Behavioral hostile test:** using the existing fake/tenant-session fixtures, create Tenant A's `Benchmark` and a Tenant B `ValuePack` linked via `[:hasBenchmark]`; assert Tenant A's `list_benchmarks`/`get_benchmark` `usage_count` is 0 (not 1), and that `delete_formula` for a Tenant A formula with a Tenant B `[:USES_FORMULA]` link does not raise the "referenced" `ConflictError`.
3. **Tighten the existing filter-count tests** so they enumerate *every* tenant-owned node introduced by each clause (MATCH **and** OPTIONAL MATCH) and require each to be scoped, rather than asserting "at least one filter".
**Testing:** `pytest services/layer3-knowledge/tests/security/ -k "optional_join or benchmarks or formula"` plus the new file; all must pass; assert the new validator test fails when reverted against the Step-1-unscoped templates (prove it bites).

### Step 3: Household maintenance — guard/CI ratchet + contract docs [SIMPLE]
**Files:**
- `scripts/ci/check_layer3_cypher_scope.py` (read-only invocation, no change expected)
- `config/ci/*` allowlists (only if the gate newly classifies a query Unknown)

**What:** Run the static AST scope gate, the `validate_tenant_scoped_cypher` checks from the CI scope script, and confirm all three queries classify Safe with no new Unknown/Unsafe findings; verify `git status` shows only the intended source/test files. No doc touch needed — verified `docs/reference/layer-runtime-path-governance.md` does not enumerate these queries.
**Testing:** `python scripts/ci/check_layer3_cypher_scope.py`; `make test-layer3` (or the named security suites if the full layer run is too heavy); confirm no allowlist edits are needed.

### Step 4: Goal-status continuity (no application code) [SIMPLE] <span style="color:green">IN SCOPE — operator-confirmed</span>
**Files:** `.goals/security-remediation-audit/status.json` (append follow-up record), `summary.md` (note the fix landed)
**What:** Record that L3-SEC-007 is now executed against the live code, linking this PR as the implementing change, so the audit's trend tracking is closed rather than left open-ended.
**Testing:** Read-only; no source impact.

## Decisions (autopilot — operator review supersedes)
1. **Scoping style:** inline `{tenant_id: $tenant_id}` on the `vp` node, matching the canonical `value_packs.py` pattern. Trailing `WHERE vp.tenant_id = $tenant_id` after the OPTIONAL MATCH is equivalent but diverges from the established sibling style.
2. **TEST-009 scope:** this PR folds in the `vp` optional-join executable regression only. The broader TEST-009 extras (comprehensions, subqueries, relationship-path assertions) stay a follow-up.
3. **Branch:** new `fix/l3-sec-007-valuepack-tenant-scoping`, forked from `origin/main`; single PR.
4. **Goal continuity:** Step 4 (`.goals/security-remediation-audit/status.json` follow-up record + `summary.md` note) is in scope.
5. **Docs:** no doc change required (`layer-runtime-path-governance.md` does not enumerate these queries).

## Open Questions
- None blocking — all three clarified. Remaining confirmations: TEST-009 breadth kept narrow (vp optional-join only).