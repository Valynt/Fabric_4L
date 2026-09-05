# GAP-3 — Formula scenario endpoint (rewrite)

**Freeze SHA:** `4bb4e142c2ccbc56297de843e71534d956bb198f`  
**Correction:** the previous packet stated the L3 endpoint was absent. That was wrong.  
**Do not propose a duplicate endpoint.**

The route is registered and has an implementation. Remaining questions are schema alignment, tenant-scoped authoritative data, and zero-value fallback — human choices, not a missing route.

## 1. Registration and implementation (evidence)

| Surface | Evidence |
|---|---|
| Router | `services/layer3-knowledge/src/api/routes/formulas_evaluation_routes.py` registers `POST /formulas/scenario` → `formulas.calculate_scenario`, `response_model=formulas.ScenarioResponse` |
| Handler | `services/layer3-knowledge/src/api/routes/formulas.py` `async def calculate_scenario` |
| Engine | `services/layer3-knowledge/src/agents/scenario_engine.py` `ScenarioEngine.calculate_scenario` |
| Static route test | `services/layer3-knowledge/tests/test_route_characterization_static.py` asserts `("POST", "/formulas/scenario", "calculate_scenario")` |
| FE hook | `apps/web/src/hooks/useFormulaScenario.ts` posts to `/formulas/scenario` |
| Thesys client | `apps/web/src/api/thesysClient.ts` `evaluateWhatIf` posts to `/formulas/scenario` |
| Contract map | `docs/contracts/frontend-backend-contract-map.md` marks Formula Scenario `implemented` |
| Auth allowlist | `contracts/route-auth-allowlist.yaml` lists `POST /formulas/scenario` as an **intentionally unauthenticated** public route |
| Hook registry | `apps/web/contracts/endpoint-hook-registry.json` status **`unmapped`** for `POST /v1/formulas/scenario` |
| OpenAPI | GitHub code search for `ScenarioRequest` / `"/formulas/scenario"` under `contracts/openapi` on this SHA: **0 hits** |

RFC-001 (file status **Approved**, 2026-04-27, council note in the RFC file) specified adding this path. The path exists. The RFC schema is not what shipped.

## 2. RFC / consumer schema divergence

Four request shapes are in tree at the freeze SHA. None of these is “the missing endpoint.”

| Source | Identity field | Adjustments | Other | Response |
|---|---|---|---|---|
| RFC-001 (Approved) | `formula_id` (required) | `[{variable_id, new_value}]` | — | `formula_id, original_value, adjusted_value, delta_percentage, new_roi, new_payback_months, warnings` |
| Backend Pydantic `ScenarioRequest` | `base_case_id` (required) | `[{name, value, original_value}]` | optional `base_case_data` dict; **bypasses repository lookup** if set | `scenario_id` + original/adjusted/delta/roi/payback + `formula_used` + `calculation_steps` + `warnings` |
| FE hook `useFormulaScenario` | `base_case_id` | `[{name, value, original_value}]` | no `base_case_data` | matches backend (uses generated `l3.components['schemas']['ScenarioResponse']`) |
| Thesys `evaluateWhatIf` | `base_case_id` | same as hook | **sends `base_case_data`** from the client | `WhatIfResult` subset (no warnings) |
| FE contract test `formulas.contract.test.ts` | `formula_id` | `scenarios: [{name, variables: Record<string,number>}]` | — | `{formula_id, scenarios: [{name, result, unit, confidence}]}` |
| Contract map row | — | `{ formula_id, variables }` | — | `FormulaEvaluationResult` |

**Factual:** RFC-001, the live handler, the FE contract test, and the contract-map row describe four different APIs on the same path. OpenAPI on this SHA does not contain the path the RFC said would be added.

**Not a decision:** which schema is canonical. Options for the signer (do not infer):

- A. Adopt the live backend/hook (`base_case_id`) and amend RFC-001 / OpenAPI / FE contract test / contract-map to match.
- B. Adopt RFC-001 (`formula_id` + `variable_id`/`new_value`) and change the existing handler and consumers. Still the same path.
- C. Adopt the FE contract-test schema (`formula_id` + named `scenarios[]`). Still the same path.
- D. Leave divergence as accepted debt with a named owner and date.

Duplicate `POST /formulas/scenario-v2` (or any second path) is **out of bounds** for this gap unless the operator writes that choice.

## 3. Tenant-scoped authoritative data resolution

RFC-001 §5 (cited): *“The `formula_id` is validated against the tenant's owned formulas. A user cannot run scenarios against formulas belonging to another tenant.”* Auth: Bearer, tenant-scoped.

Observed implementation (cited):

- `calculate_scenario` takes `ScenarioRequest` only. It does **not** declare `require_tenant_context`.
- The path is on the **public unauthenticated allowlist** (`contracts/route-auth-allowlist.yaml`, reason: “Scenario simulation endpoint”), alongside `/formulas/evaluate`.
- Handler comment says: “Attempt to resolve from Neo4j ROICalculation (optional fallback).” The body does **not** query Neo4j. If `base_case_data` is missing it synthesizes zeros (see §4).
- If `base_case_data` **is** present, the handler uses the **client-supplied dict** and “bypasses repository lookup.” `thesysClient.evaluateWhatIf` sends that dict from the browser.
- `base_case_id` is accepted and unused for lookup in the handler body that shipped.

**Factual:** tenant-scoped authoritative resolution of the base case (or formula) is **not implemented** on this path. RFC §5 is not met by the current handler. This is not a missing route; it is an authz/data-resolution gap on the existing route.

Options (do not infer):

- A. Keep public + client `base_case_data` (current behavior) and amend RFC-001 §5.
- B. Require authenticated tenant context, resolve `base_case_id` (or `formula_id`) from tenant-scoped storage, ignore client `base_case_data`.
- C. Require authenticated tenant context but still allow client `base_case_data` as an overlay, with a named threat model.

## 4. Zero-value fallback

Handler (cited): if `base_case_data is None`, append warning *“Base case data not provided; using zero-value fallback. Pass base_case_data for accurate scenario modeling.”* and set `total_value=0.0`, `implementation_cost=0.0`, `roi_ratio=0.0`, `payback_months=0.0`. Comment: “so the endpoint never 501s.”

Engine (cited) on those zeros:

- `delta_percentage` → `0.0` when `original_value` is 0
- `_calculate_roi` → `0.0` when `impl_cost <= 0`
- `_calculate_payback` → `999.0` (`MAX_PAYBACK_MONTHS`, “never pays back”) when `total_value <= 0`
- generic adjustment with `original_value == 0` is skipped
- `adjusted_value` floored at `0.0`

RFC-001 router description on the evaluation routes file: `400 Invalid adjustments or missing base case data`. The handler does not 400; it returns 200 with zeros and a warning.

FE hook does not send `base_case_data`, so **the hook’s default call hits the zero-value path** unless some other layer injects it. Thesys client does send `base_case_data`.

Options (do not infer):

- A. Keep 200 + warning + zeros (current).
- B. 400 when `base_case_data` is absent and lookup finds nothing (matches the route’s 400 description and RFC missing-data intent).
- C. Actually perform the Neo4j/tenant lookup the comment describes, and 404 if missing.

## 5. Sub-scope for the decision table

| Sub | Question | Not |
|---|---|---|
| GAP-3a | Which request/response schema is canonical among RFC, handler, hook, contract test, contract-map? | A new path |
| GAP-3b | Publish or restore OpenAPI `/formulas/scenario` to match the canonical schema | A second endpoint |
| GAP-3c | Tenant-scoped authoritative resolution vs public allowlist + client `base_case_data` | — |
| GAP-3d | Zero-value 200 vs 400/404 on missing base case | — |
| GAP-3e | Hook-registry `unmapped` vs hook that already calls the path | — |

Human choice column stays blank until the operator fills it.
