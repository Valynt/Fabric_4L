# Goal: Implement L3-SEC-007 Tenant-Scoped ValuePack Usage Counts

## User Request

The user invoked the Goal skill with the argument `plans/l3-sec-007-valuepack-tenant-scoping/plan.md` — the approved remediation plan from the completed `.goals/security-remediation-audit` assessment. The user's standing instruction (from the plan's approval flow): **"proceed"** with implementing the plan.

The plan (branch decision superseded by operator): close the live cross-tenant `usage_count` / delete-block leak identified as L3-SEC-007 by adding the tenant predicate to the `vp:ValuePack` side of the three unscoped `OPTIONAL MATCH` joins in Layer 3, fold in the TEST-009 executable validator + behavioral regression, run the CI scope gate, and close the audit's goal-status continuity.

## Refined Goal

Implement the approved 4-step L3-SEC-007 remediation on branch `valyntxyz-studious-bassoon` (operator-confirmed; do **not** create the plan's new branch — commit directly to the current worktree branch). Step 1 source fixes are already applied and staged (uncommitted) in `benchmarks.py` and `formulas.py`, including the discovered delete-step fix (FormulaVersion/Variable + `(f:Formula)` label) without which `delete_formula` remains double-broken (fail-closed 500). The goal is: (a) keep/verify Step 1 source fixes, (b) author the Step 2 executable validator + behavioral hostile regression tests in a new file plus tighten the existing substring tests, (c) verify the Step 3 CI scope gate shows no new findings, and (d) close Step 4 goal-status continuity in `.goals/security-remediation-audit/`. All validation must be actually run and pass; residual pre-existing failures (create/update_formula fetch + delete-rels) are flagged, not fixed.

## Acceptance Criteria

- [ ] Criterion 1 — Source fixes (Step 1) present and being committed: `OPTIONAL MATCH (vp:ValuePack {tenant_id: $tenant_id})` in list_benchmarks and get_benchmark (`services/layer3-knowledge/src/api/routes/benchmarks.py`), and in the `delete_formula` ref-count query (`services/layer3-knowledge/src/api/routes/formulas.py`), plus the delete-step query scoped (`(f:Formula)` label, `fv:FormulaVersion {tenant_id: $tenant_id}`, `v:Variable {tenant_id: $tenant_id}`).
- [ ] Criterion 2 — New file `services/layer3-knowledge/tests/security/test_optional_join_tenant_scope.py` authored with:
  1. Executable validator tests running `validate_tenant_scoped_cypher`: the OLD unscoped `vp` templates (benchmark + formula variants) raise `TenantCypherValidationError` naming `ValuePack`, and the NEW scoped templates pass; delete-step coverage: old raises naming `FormulaVersion(fv)`/`Variable(v)`, new passes.
  2. Behavioral hostile tests (mock-session pattern, monkeypatching `create_neo4j_tenant_session`): Tenant A Benchmark with a Tenant B ValuePack `[:hasBenchmark]` link yields `usage_count == 0` in list_benchmarks/get_benchmark; `delete_formula` for a Tenant A formula with a Tenant B `[:USES_FORMULA]` link does NOT raise the referenced `ConflictError`. `get_benchmark` needs a `single()`-compatible mock; `delete_formula` takes `tenant=SimpleNamespace(tenant_id="tenant-a")`.
  3. A runtime test asserting the REAL `delete_formula` cypher blocks pass `Neo4jTenantSessionSecured._validate_cypher_text` (proves the previously-double-broken endpoint is un-broken).
- [ ] Criterion 3 — Existing tests tightened: `test_all_cypher_match_clauses_include_tenant_id` in `test_benchmarks_cross_tenant_isolation.py` (and the formula equivalent) require every tenant-owned node in each clause (MATCH **and** OPTIONAL MATCH) to be scoped, not just "at least one filter".
- [ ] Criterion 4 — Tests actually pass: `pytest services/layer3-knowledge/tests/security/ -k "optional_join or benchmarks or formula"` with `-p no:randomly`, AND the broader layer3 security suite (existing ~30 tests) stays green; `python scripts/ci/check_layer3_cypher_scope.py services/layer3-knowledge/src --report-json` passes with no new Unknown/Unsafe for the three queries and no allowlist edits.
- [ ] Criterion 5 — Step 4: `.goals/security-remediation-audit/status.json` gains a follow-up record (preserve its line-9 4-space indent quirk) and `summary.md` notes the fix landed, linking this branch/commits.
- [ ] Criterion 6 — Commits made directly on `valyntxyz-studious-bassoon` with `type(scope): [B] description` titles (≤72 chars), `Assisted-by: OpenAI:GPT-5.6 Luna` and `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>` trailers. Suggested split: `fix(l3-security): [B] ...` for source + `test(l3-security): [B] ...` for tests (+ optionally the goal-status record).

## Scope Boundaries

**In scope:**
- `services/layer3-knowledge/src/api/routes/benchmarks.py` (list_benchmarks, get_benchmark usage-count joins)
- `services/layer3-knowledge/src/api/routes/formulas.py` (delete_formula ref-count + delete-step queries)
- NEW `services/layer3-knowledge/tests/security/test_optional_join_tenant_scope.py`
- `services/layer3-knowledge/tests/security/test_benchmarks_cross_tenant_isolation.py` (tighten regex test)
- `services/layer3-knowledge/tests/security/test_formula_governance_cross_tenant_isolation.py` (tighten formula equivalent)
- `.goals/security-remediation-audit/status.json` + `summary.md` (Step 4 continuity)
- Running the security test suites and the layer3 CI scope gate

**Out of scope:**
- Fixing the pre-existing runtime validator failures in `create_formula`/`update_formula` fetch steps and `update_formula` `DELETE r` query (fail-closed, no leak — flag as residual risk only)
- Layer 4 allowlist drift in `check_layer3_cypher_scope.py` (pre-existing; layer3-only invocation must pass)
- Broader TEST-009 extras (comprehensions, subqueries, relationship-path assertions) — vp optional-join only
- Any change to `.goals/security-remediation-audit/` beyond the Step 4 follow-up record
- Creating a new branch (operator overrode plan Decision #3)
- Live Neo4j / runtime integration — mock-session tests only

## Applicable Project Conventions

**Quality gate command:**
- `pytest services/layer3-knowledge/tests/security/ -k "optional_join or benchmarks or formula" -p no:randomly` (targeted)
- Full layer3 security suite: `pytest services/layer3-knowledge/tests/security/ -p no:randomly`
- `python scripts/ci/check_layer3_cypher_scope.py services/layer3-knowledge/src --report-json`
- `make test-layer3` (only if needed as broader confirmation; the named suites are sufficient)

**Commit convention:**
- Format: `type(scope): [B/I] description` (conventional commits, ≤72 chars)
- Builder commit trailer: `Assisted-by: OpenAI:GPT-5.6 Luna`
- Inspector commit trailer: `Assisted-by: OpenAI:GPT-5.6 Sol`
- Also include project trailer: `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`
- Commit directly to the current worktree branch (`valyntxyz-studious-bassoon`); do not create new branches.

**Guidelines:**
- `docs/contract.md`, `docs/governance.md`
- `docs/reference/layer-runtime-path-governance.md` (verified: does not enumerate these queries; no doc change needed)
- `.agent/skills/repo-audit/SKILL.md` (origin of the plan)
- `AGENTS.md` (root and per-service)

**Rules:**
- Tenant isolation invariant: `tenant_id` must come from authenticated context, never request body
- Contract-first; no silent response-shape changes
- Behavior-first testing: intended allowed + intended denied + explicit failure mode must be encoded
- No fabricated evidence: cite files/lines actually verified; run the validation commands actually reported
- Worktree root is `C:\Users\BBB\.copilot\repos\Fabric_4L\.worktrees\valyntxyz-verbose-adventure`; do not touch the main checkout
- Do NOT modify `.agent/protocols/permissions.md`; do not hand-edit `.agent/memory/semantic/LESSONS.md`

## Pre-Validated Facts (from this session, verified 2026-08-28/29)

- HEAD at goal creation: `091cf96cecbcd0432a9d15da5faf79ac31ff85f2` (merge of origin sync on top of audit commits `5527ba0ae`, `2b66b8046`).
- Staged (uncommitted) Step 1 edits: `benchmarks.py` (L133, L209), `formulas.py` (L1310, L1331-1332), plus the staged plan file `plans/l3-sec-007-valuepack-tenant-scoping/plan.md`.
- Runtime matrix (via real `Neo4jTenantSessionSecured._validate_cypher_text`): list_benchmarks/get_benchmark PASS; delete_formula block 0 (ref-count) PASS; delete_formula block 1 (delete-step) PASS; create_formula/update_formula fetch + delete-rels FAIL (pre-existing, out of scope).
- `validate_tenant_scoped_cypher` negative proof: old unscoped templates raise naming `ValuePack(vp)` / `FormulaVersion(fv)` / `Variable(v)`; new scoped benchmark/formula templates pass.
- Canonical pattern: `value_packs.py` scopes far side inline `{tenant_id: $tenant_id}`; ValuePack nodes carry tenant_id; no global_system variant.