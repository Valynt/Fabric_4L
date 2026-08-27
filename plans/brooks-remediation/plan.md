# Brooks-Lint Remediation

**Branch:** `fix/brooks-lint-remediation`
**Description:** One PR resolving the four actionable findings from the Brooks-Lint Health Dashboard (2026-08-27), executed in suggested order 1 → 3 → 2 → 4.

## Goal
Eliminate the six duplicated tenant-spoofing guards, fix the L3 node-name fallback divergence, complete the deprecation-alias removal under governance, and consolidate duplicate integration facade dirs — all as discrete, CI-green commits with regression coverage.

## Context (facts gathered 2026-08-27)
- Six `TenantSpoofingError` guards live in `services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py` at L200, L357, L483, L603, L713, L817 — but there are **two distinct patterns**:
  - **QueryGraphTool** (L161–166): sweeps a `params` dict, tests `"tenant_id" in key.lower()`, then injects `params["tenant_id"] = str(tenant_id)`.
  - **SemanticSearch / GetEntity / GetRelationships / TraverseTree / FindPaths** (start ~L199/356/482/602/712/816): `payload_tenant_id = getattr(input_data, "tenant_id", None)` then raise if mismatch.
- `TenantSpoofingError(ToolValidationError)` defined in `tools/registry.py` (~L249); `TenantContextError` in `shared/domain/context.py`. A natural home for a shared guard exists: `layer4_agents/shared/security/` (already contains `cypher_security.py`, `dil_auth.py`).
- L3 deprecation governance lives in `services/layer3-knowledge/src/services/compat_policy.py` / `compat_metrics.py`. A migration plan already exists at `docs/superpowers/plans/2026-08-26-layer3-facade-migration.md` ("Removal Gate", "Migration Dependency Order").
- `graph_viz.py::_build_graph_node` diverges: top-level `name` falls back to node_id on None, but `properties["name"]` does not.
- Layer4 has both `integration/` (5 files incl. `layer1_client.py`) and `integrations/` (2 files). `interfaces/`(12), `adapters/`(11), `services/`(46) also exist.

## Implementation Steps

### Step 1: Extract shared tenant-spoofing guard [SIMPLE]
**Files:**
- NEW `services/layer4-agents/src/layer4_agents/shared/security/tenant_guard.py`
- `services/layer4-agents/src/layer4_agents/shared/security/__init__.py`
- `services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py`
- NEW test `services/layer4-agents/tests/unit/test_tenant_guard.py`

**What:** Add an `enforce_tenant_context(payload_tenant_id, authenticated_tenant_id)` (or a dict-aware variant) helper in `shared/security/`. The helper must raise the identical `TenantSpoofingError` (same class, same message) as today so `BaseTool.run` still maps it to the stable `TENANT_SPOOFING_DETECTED` code with no stack trace. Replace the five `getattr(input_data, ...)` guards with the helper. **QueryGraphTool's dict-sweep guard is behaviorally different (matches any key containing "tenant_id")** — decide per clarification whether to unify it too or leave its key-sweep intact and only route the raise through the shared helper.
**Testing:** `pytest services/layer4-agents/tests/unit/test_tenant_guard.py` (spoofed / missing / valid tenant) + the existing tenant-security suites must still pass unchanged (proves no contract change). **Verified evidence (2026-08-27) that these suites assert error SHAPE, not just "raises":** `tests/test_query_graph_tenant_security.py` L187-208 `test_base_tool_run_maps_tenant_spoofing_to_structured_result` asserts `result.status == "error"`, `result.error["code"] == "TENANT_SPOOFING_DETECTED"`, and the message; L182 asserts `pytest.raises(TenantSpoofingError, match="Tenant spoofing detected")` for the field-guard tools; L69-70 asserts `pytest.raises(ValueError)` for QueryGraph's structural sweep. Because these assert the exact error code + message, a guard refactor that changes the raised shape will fail the suite — the "no contract change" gate is strong as stated.

### Step 2 — Fix node-name fallback divergence — [SIMPLE]
**Files:** `services/layer3-knowledge/src/api/routes/graph_viz.py`, `services/layer3-knowledge/tests/test_graph_viz.py`
**What:** Make `_build_graph_node`/its callers populate `properties["name"]` from the resolved local `name` (after the `or node_id` fallback), or drop `properties["name"]` and keep one source of truth.
**Testing:** Add regression test for the `name is None` case asserting top-level `name` and `properties["name"]` agree; run `pytest services/layer3-knowledge/tests/test_graph_viz.py`.

### Step 3 — Govern deprecation-alias removal — [COMPLEX, gated on metrics]
**Files:** `services/layer3-knowledge/src/services/compat_metrics.py`, `compat_policy.py`, `contracts/openapi/layer3-knowledge.json`, `apps/web/src/api/generated/l3/index.ts`, `services/layer3-knowledge/src/api/routes/graph_viz.py`, `contract`+security test files in the 99-file diff, doc `docs/superpowers/plans/2026-08-26-layer3-facade-migration.md`

**What:** Only proceed once `compat_metrics` legacy-alias counters trend to zero. Enforce commit sequencing contract → backend → generated TS → frontend mapper so CI stays green at each commit. Grep frontend (outside `generated/`) for reads of removed aliases (`relationship_type`, `.label`, `.confidence`); grep OpenAPI/contract tests for stale field reads. Once removal lands, delete `compat_shims`. NOTE: this work is the "L3 facade migration" already planned — confirm whether THIS PR or the existing plan PR owns it (see clarification).
**Testing:** `make contract-tests`, `pnpm run check:api-types`, `pytest tests/contract/test_l3_graph_contract.py`, run the file-grep audit for stale aliases; CI must be green at each commit boundary.

### Step 4 — Consolidate integration/ vs integrations/ — [COMPLEX]
**Files:** `services/layer4-agents/src/layer4_agents/integrations/` (connector.py, factory.py, __init__.py), `.../integration/` (layer1-3,5 clients, claim_types.py), package README or an ADR under `docs/`
**What:** Confirm canonical dir (`integration/` where `layer1_client.py` lives), map each `integrations/*` module to its target/adapter home, migrate via re-export shims during transition, document placement rule vs `interfaces/`/`adapters/`/`services/`, then delete the deprecated dir. Guard: do not move `interfaces/adapters/services` logic that is not part of this facade duplicate.
**Testing:** `pytest` for affected importer modules; run a repo grep that no module imports from canonical `integrations/` path afterward; update imports to the canonical home.

### Step 5 — Follow-up / monitoring (no code)
- run-full Tech Debt Assessment on weakest dimension after 1–4; re-run Health Dashboard to establish trend.

## Decisions (autopilot — operator review supersedes)
1. **QueryGuard pattern** — keep the structural dict-scan in QueryGraphTool (catches sub-key params), route ONLY its raise through the shared helper; the other five use the helper's field-based `enforce_tenant_context`. All six share one `TenantSpoofingError` exit path.
2. **Step 3 (deprecation) ownership** — THIS PR implements Steps 1, 3, and 4. For the deprecation-alias removal, this PR owns **gate verification + commit sequencing + stale-consumer audit only**; the removal merge is owned by the existing `docs/superpowers/plans/2026-08-26-layer3-facade-migration.md` plan PR. This PR surfaces a gate PASS/BLOCK for that removal.
3. **integration/ canonical dir** — `integration/` is canonical (hosts `layer1_client.py`). `integrations/connector.py`/`factory.py` move to a new `integration/connectors/` subpackage; pure adapter/interface logic stays under existing `interfaces/`/`adapters/`/`services/` placement rules.
4. **Branch** — base off `main` default, single PR `fix/brooks-lint-remediation`.