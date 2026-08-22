# BEH-04: Formula & ROI calculation

```yaml
id: BEH-04
name: formula-roi-calculation
journey_stage: J-7            # Calculate and compare; formula definition from J-6
stories: [VP-09, VP-10, VP-14]
closes_gaps: [GAP-05, GAP-06, GAP-09, GAP-11]
rules: [R-1, R-4, R-5]
boundary: web -> api -> L3 (+ L6 benchmarks)
components:
  - FormulaBuilder
  - FormulaList
  - ROITab
  - CalculatorRouter
  - CalculationEngine          # L3 deterministic authority
  - BenchmarkGateway           # L6 governed benchmarks
  - ScenarioService            # server-persisted named scenarios
primary_gates: [AG-02, AG-03]
```

## Product

Value engineers inspect and edit transparent model inputs (units, ranges, provenance, formulas); finance buyers compare conservative / expected / optimistic scenarios with sensitivity — and every number is deterministic, reproducible, and honestly labeled (VP-09, VP-10; jobs 3).

Correct behavior, normatively:
- **Financial math is deterministic and reproducible** (R-4). An LLM MAY narrate a result; it MUST NOT replace a formula, invent an input, or alter an approved calculation. L3 is the deterministic calculation authority; L4 orchestrates but does not redefine the math (convergence decision 3).
- One versioned calculation schema end to end — the flat frontend ROI fields and the nested L3 workforce/productivity contract converge; generated types or bidirectional contract tests enforce it (closes GAP-06).
- No silent production fallback to calibrated synthetic inputs or built-in drivers when account data is missing: a default is usable only through an explicit, authorized assumption workflow with visible lineage and publication impact (closes GAP-09; R-5).
- Every financial driver reaching calculation has a valid formula + variables, or is explicitly non-financial (GAP-05).
- Named scenarios are server-persisted, forkable, comparable, tied to a model version — never browser-local (closes GAP-11; R-2).
- Each calculation persists request, result, cash flows, substituted formulas, engine version, lineage: the **ROI Snapshot** is the immutable source of financial truth (§5.2, §7.2.2).

## Architecture

```
 apps/web                      services/api                authority
 ┌────────────────────┐        ┌──────────────────────┐
 │ FormulaBuilder.tsx  │        │ routers/calculator.py │──▶ L3: deterministic ROI engine
 │ FormulaBuilder/     │──────▶ │  (versioned schema,   │    (calculation authority;
 │ FormulaList.tsx     │        │   snapshot persist)   │    request/result immutable)
 │ calculator/ROITab.tsx│◀──────└──────────────────────┘
 │ MyModels.tsx        │   ROI snapshot                     │
 └────────────────────┘                                ▼
   tool manifests: calculate_roi.json,               L6: governed benchmarks
   evaluate_formula.json, sensitivity_analysis.json  (applicability, provenance)
```

LLM/provider paths may degrade narrative enrichment but can never change deterministic outputs (§7.3.5).

## Implementation

### Verified anchors

| Path | What it is | Role in this behavior |
|---|---|---|
| `apps/web/src/pages/FormulaBuilder.tsx` | Formula builder page | Governed expression editing: variables, units, bounds, lineage |
| `apps/web/src/pages/FormulaBuilder/` | Builder component dir | Formula validation UX, impact preview |
| `apps/web/src/pages/FormulaList.tsx` | Formula list | Per-driver formula inventory; financial vs non-financial status |
| `apps/web/src/pages/calculator/ROITab.tsx` | ROI calculator tab | Scenario inputs, side-by-side comparison, sensitivity, current/stale labeling |
| `apps/web/src/pages/MyModels.tsx` | Models page | Model/version selection feeding calculation |
| `services/api/app/routers/calculator.py` | Calculator router | Versioned calculation commands; snapshot persistence; scope checks |
| `services/api/app/routers/benchmarks.py` | Benchmarks router | L6 benchmark retrieval for ranges/inputs |
| `contracts/tool-manifests/calculate_roi.json` | Tool manifest | Agent-callable ROI contract; same math as UI path |
| `contracts/tool-manifests/evaluate_formula.json` | Tool manifest | Formula evaluation contract |
| `contracts/tool-manifests/sensitivity_analysis.json` | Tool manifest | Sensitivity contract |
| `contracts/openapi/layer6-benchmarks.json` | L6 OpenAPI spec | Benchmark identity/applicability/provenance contract |
| `services/api/app/routers/value_cases.py` | Value cases router | Snapshot ↔ case-version binding consumed downstream |

### Inputs / outputs
- **In**: model version (tree + formulas + variables + units), named scenario (server-persisted), benchmark links, cash-flow policy.
- **Out**: immutable ROI Snapshot — request, substituted formulas, outputs (ROI, NPV, IRR, payback, cash flows), warnings, engine version, lineage, trace ID.

### State transitions
- Scenario: server record, `draft -> selected/current`; fork creates new scenario with lineage; never browser-local.
- Calculation: `idle -> generating -> idle | retrying`; last valid result stays visible during recalculation; result labeled `current` or `stale` when inputs change.
- Lifecycle coupling: an approved upstream version stays immutable; recalculation targets drafts only (R-7 handoff to BEH-08).

### Failure modes
- Missing account data → explicit assumption workflow (user sees default, reason, downstream impact, publication rule); silent synthetic fallback is prohibited (GAP-09, R-5).
- Fallback/benchmark-derived/demo inputs → visibly labeled through calculation and downstream surfaces; materially degraded outputs not publishable (R-5).
- Engine/provider fault → calculation fails visibly; no LLM-substituted math (R-4); deterministic assertions unaffected by time/randomness/provider behavior.
- Stale inputs after model edit → snapshot marked `stale`; recalculation or re-review required; approval never silently retained on a changed draft.
- Schema drift between frontend and L3 → contract test failure blocks merge (GAP-06).

## Verification

**Tests**
- Unit + property: determinism (same inputs → same outputs regardless of time/randomness/provider), formula validation, bounds/units, sensitivity math (Hypothesis/fast-check style).
- Mutation tests on calculation-critical logic (critical mutation score target per test metrics).
- Contract: one versioned calculation schema; generated TS types vs service schema; `calculate_roi.json` / `evaluate_formula.json` / `sensitivity_analysis.json` manifest conformance; unknown-field and malformed-input rejection (controls under AG-03).
- Integration (real persistence): snapshot immutability; scenario fork/compare; engine-version recording; fallback-path labeling persisted into the snapshot.
- Browser: ROI input → calculate → compare three scenarios; stale labeling after edit; last-valid-result-during-recalculation.

**Tenant-isolation assertions**
- Calculation requests re-verify tenant + case ownership of the model version; foreign model/scenario/snapshot IDs denied before execution.
- Benchmark applicability scoped per tenant entitlements; no cross-tenant cache keys for scenarios or snapshots (Redis isolation under AG-05).

**Release gates**
- **AG-02 code-quality-and-tests** — unit/property/mutation proof of deterministic math; integration coverage of snapshot persistence.
- **AG-03 contract-compliance** — the GAP-06 schema convergence; cross-layer L3↔L4 calculation contract; tool-manifest drift checks.
- **AG-05 tenant-isolation-and-behavior** — account-scope enforcement and cache isolation on the calculation path.

**Required evidence**
- EV: junit-and-json test-run evidence with recorded `random_seed` and `dependency_lock_hash` (determinism proof).
- EV: contract-test results binding frontend types to the versioned calculation schema.
- EV: benchmark-conformance results against the L6 spec.
- EV: negative-test evidence that synthetic fallback cannot activate silently in production configuration.
