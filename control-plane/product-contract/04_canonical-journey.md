# 04 — Canonical Journey

Source: Master Product Intent §4.1–4.10 (S1); frontend surfaces from the S1↔S2 concordance (context pack §15).

Framing: "The experience must feel like one continuous account-scoped workspace even when the implementation crosses Intelligence, Value Studio, calculation, evidence, narrative, deliverables, and realization services."

Stage IDs J-1..J-10 map to source sections §4.1–§4.10 in order. Story IDs reference `06_user-stories.md`; behavior IDs reference `control-plane/behaviors/` (BEH-01..BEH-09, aligned to journey order).

## J-1: Start or resume the case

- Entry: verified authorization and permitted account scope.
- Action: create or select an account and provide business context.
- System: persist all submitted context; resolve one canonical case ID; restore existing work.
- Exit: durable case exists; user sees current readiness and next prerequisite.
- Stories: VP-01, VP-14. Behaviors: BEH-01.
- Frontend surfaces: `ProspectSetup.tsx`, `Accounts.tsx`, onboarding, org selection; auth via Clerk.

## J-2: Connect sources and run analysis

- Entry: durable case exists (J-1 exit).
- Action: add approved sources; start analysis.
- System: ingestion, extraction, projection, and enrichment run as real background work with progress, retries, partial-failure detail, and trace identity.
- Exit: source status and degraded conditions explicit.
- Stories: VP-02. Behaviors: BEH-01.
- Frontend surfaces: `intelligence/` Enrichment tab, `IngestionJobs`, `ExtractionEngine`, prospect setup adapter (GAP-02: setup currently does not launch the workflow).

## J-3: Review signals

- Entry: analysis run has produced candidate signals (J-2 exit).
- Action: accept, edit, reject, or request customer confirmation on each signal.
- System: preserve source passage, original generated value, confidence factors, author decision, and audit history.
- Exit: only dispositioned signals eligible for hypothesis generation.
- Stories: VP-03. Behaviors: BEH-02.
- Frontend surfaces: `intelligence/` tabs; `ReviewQueuePage` (accept/correct extractions, L5 ground-truth loop).

## J-4: Generate and validate hypotheses

- Entry: dispositioned signals exist (J-3 exit).
- Action: generate, rank, compare, edit, accept, and reject pain→capability→outcome links.
- System: store score components, evidence coverage, model input version, and human disposition.
- Exit: accepted hypotheses ready for promotion.
- Stories: VP-04. Behaviors: BEH-02.
- Frontend surfaces: `intelligence/` Hypotheses tab; `hypothesis/` (Discovery Questions, Assumptions, Persona Fit).

## J-5: Materialize the driver tree

- Entry: accepted hypotheses exist (J-4 exit).
- Action: promote accepted hypotheses.
- System: create persistent tree and model IDs plus outcome, driver, lever, variable, and evidence links.
- Exit: every financial lever has a governed formula or explicit non-financial classification.
- Stories: VP-05, VP-07. Behaviors: BEH-02, BEH-03.
- Frontend surfaces: "Hypothesis Validation → Driver" flow; `DriverTreePage` / `ValueTreeExplorer` (GAP-04, GAP-05 live here).

## J-6: Define variables, evidence, and scenarios

- Entry: driver tree materialized (J-5 exit).
- Action: edit units, ranges, owners, sources, formulas, evidence, benchmarks, and named scenarios.
- System: validate formulas and units; show downstream impact; version changes; preserve source classification.
- Exit: required inputs and evidence gates resolved or explicitly blocked.
- Stories: VP-06, VP-08, VP-09. Behaviors: BEH-03, BEH-04, BEH-05.
- Frontend surfaces: `FormulaBuilder` + `FormulaList`; `evidence/` (Solution Cost, Alternatives); stakeholder surfaces; `TargetsAdmin` for benchmarks.

## J-7: Calculate and compare

- Entry: required inputs and evidence gates resolved or explicitly blocked (J-6 exit).
- Action: calculate conservative, expected, and optimistic scenarios; inspect sensitivity.
- System: deterministic math; persist request, result, cash flows, engine version, and lineage.
- Exit: selected scenario is current, reproducible, and reviewable.
- Stories: VP-10. Behaviors: BEH-04.
- Frontend surfaces: `calculator/ROITab`; `studio/ValueModelTab`; `MyModels`, `ValuePacks` (GAP-06 ROI contract mismatch lives here).

## J-8: Generate the decision narrative

- Entry: a current, reproducible, reviewable scenario is selected (J-7 exit).
- Action: choose audience and sections, then generate.
- System: build an immutable input snapshot; create cited narrative content without changing the calculation.
- Exit: all material claims supported, qualified, or blocked.
- Stories: VP-11. Behaviors: BEH-06.
- Frontend surfaces: `BusinessCase`, `BusinessCaseList`, `InteractiveBusinessCase`, `ValueNarrativeHome`, `studio/NarrativeTab`, `ActionPlanTab`.

## J-9: Review, approve, publish, and export

- Entry: material claims supported, qualified, or blocked (J-8 exit).
- Action: comment, request changes, approve, publish, export.
- System: enforce authorization, evidence, freshness, calculation, and human-review gates.
- Exit: exact approved version is immutable, auditable, and exportable with provenance.
- Stories: VP-12. Behaviors: BEH-07, BEH-08.
- Frontend surfaces: `deliverables/` → `CFOView`, `ExecutiveView`, `TechnicalView`; comments, version history, audit log, compliance/evidence pages.

## J-10: Track realization

- Entry: an approved, published forecast exists (J-9 exit).
- Action: define baseline, targets, measures, sources, cadence, and owners; record actuals.
- System: compare forecast vs actuals without rewriting history.
- Exit: variance and learning visible and reusable under governed applicability rules.
- Stories: VP-13. Behaviors: BEH-09.
- Frontend surfaces: `realization/RealizationPage`.

## Cross-cutting

- VP-14 (enforce scope, observe, audit, recover) applies to every stage.
- Frontend surfaces: `AgentWorkflows`, `DecisionTrace`, `CommandCenter`; notifications; admin/integrations.
