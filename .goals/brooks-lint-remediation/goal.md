# Goal: Execute Brooks-Lint Remediation Plan

## User Request

Execute `plans/brooks-remediation/plan.md` — implement the four actionable
findings from the Brooks-Lint Health Dashboard (2026-08-27) as discrete,
CI-green commits with regression coverage. The plan is pre-approved
(autopilot decisions documented; operator review supersedes).

## Refined Goal

Implement the Brooks remediation plan in this worktree, in detection order
Steps 1-2-3-4 where applicable, producing CI-green changes with regression
tests. Concretely: (1) extract a shared tenant-spoofing guard in
`layer4_agents/shared/security/` and route the six duplicated tenant guards'
raise path through it; (2) fix the Layer-3 node-name fallback divergence in
`graph_viz.py::_build_graph_node`; (3) run the deprecation gate + stale-consumer
audit for the L3 alias removal WITHOUT performing the removal merge (owned by
a separate plan PR); (4) consolidate the duplicate `integrations/` facade
directory into the canonical `integration/connectors/` with re-export shims.
All changes keep tenant isolation, error shapes, and API contracts unchanged.

## Acceptance Criteria

- [ ] Criterion 1 — Step 1: A shared `enforce_tenant_context(payload_tenant_id, authenticated_tenant_id)`
      helper (plus a dict-scan-aware raise path for QueryGraphTool) exists in
      `layer4_agents/shared/security/tenant_guard.py`; the five field-based
      guards in `knowledge_tools.py` call it; the six raise paths still raise
      the identical `TenantSpoofingError` with the same message. New unit
      tests in `tests/unit/test_tenant_guard.py` cover spoofed / missing /
      valid tenant.
- [ ] Criterion 2 — Step 1 regression: existing tenant-security suites
      (`tests/test_query_graph_tenant_security.py`) pass unchanged, proving
      no contract change (they assert error code `TENANT_SPOOFING_DETECTED`).
- [ ] Criterion 3 — Step 2: `_build_graph_node` produces a single
      source-of-truth name; `properties["name"]` agrees with the resolved
      top-level `label` in the `label is None` case. A regression test in
      `services/layer3-knowledge/tests/test_graph_viz.py` asserts the two
      fields agree.
- [ ] Criterion 4 — Step 3: A gate check (PASS/BLOCK) for L3 deprecation-alias
      removal is surfaced based on live `compat_metrics` legacy-alias counters
      trending to zero; a stale-consumer grep audit of the changed diff for
      reads of removed aliases (`relationship_type`, `.label`, `.confidence`)
      is recorded. NO removal merge is performed in this PR.
- [ ] Criterion 5 — Step 4: `integrations/` content migrates to
      `integration/connectors/` with re-export shims kept; the placement rule
      (`integration` vs `interfaces`/`adapters`/`services`) is documented; no
      importer references the old canonical `integrations/` path after migration.
- [ ] Criterion 6 — Quality gates: `make contract-tests` (or targeted
      equivalent) passes; targeted pytest for L3 `test_graph_viz.py` and L4
      unit tenant tests pass; frontend `pnpm run check:api-types` passes (if
      front-end types touch).

## Scope Boundaries

**In scope:**
- `layer4_agents/shared/security/tenant_guard.py` + wiring into
  `knowledge_tools.py` raises.
- `graph_viz.py` node-name fallback + regression test.
- L3 deprecation gate + audit (no removal).
- `integration/` vs `integrations/` facade consolidation + docs.
- Regression tests for all above.

**Out of scope:**
- The L3 deprecation-alias removal merge itself (owned by
  `docs/superpowers/plans/2026-08-26-layer3-facade-migration.md` PR).
- Any behavior changes to tenant isolation, error codes/messages, or API
  response shapes.
- Moving `interfaces/adapters/services` logic not part of this facade duplicate.
- Full heavy `make verify` (targeted gates first).

## Applicable Project Conventions

**Quality gate command:**
- `python3 -m pytest services/layer4-agents/tests/unit/test_tenant_guard.py services/layer4-agents/tests/test_query_graph_tenant_security.py`
- `python3 -m pytest services/layer3-knowledge/tests/test_graph_viz.py`
- `python3 -m pytest tests/contract/test_l3_graph_contract.py`
- `make contract-tests`
- `pnpm run check:api-types` (frontend drift)
- `make verify`

**Commit convention:**
- Format: `type(scope): [B/I] description` (conventional commits, <= 72 chars)
- Builder commit trailer: `Assisted-by: OpenAI:GPT-5.6 Luna`
- Inspector commit trailer: `Assisted-by: OpenAI:GPT-5.6 Sol`
- Also include project trailer: `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`

**Guidelines:**
- `docs/contract.md`
- `docs/governance.md`
- `docs/reference/layer-runtime-path-governance.md`

**Rules:**
- Multi-tenant isolation invariant: `tenant_id` must come from authenticated context.
- Contract-first development: zero silent response shape modifications.
- Monorepo package management: pnpm only.
- This is a WORKTREE on branch `valyntxyz-reimagined-telegram`; commit directly
  to that branch (do not create new branches).
- The single actionable deliverable is clean CI-green commits on this branch.

## Verified Facts (2026-08-27)

- `TenantSpoofingError(ToolValidationError)` defined in `tools/registry.py` L249;
  `ToolRegistry` maps it to structured `TENANT_SPOOFING_DETECTED`.
- Five field-based guards `getattr(input_data, "tenant_id", None)`, raising
  `TenantSpoofingError("Tenant spoofing detected: payload tenant_id does not
  match authenticated context")` — locations ~L200/360/487/607/717/821.
- QueryGraphTool uses a dict-sweep `_ensure_tenant_parameters` matching any key
  containing `"tenant_id"`.
- `shared/security/__init__.py` currently only `from __future__ import annotations`.
- `graph_viz.py::_build_graph_node` call sites pass `properties={"name": r_dict.get("label")}`
  while top-level `label` falls back to node_id — divergence on None.