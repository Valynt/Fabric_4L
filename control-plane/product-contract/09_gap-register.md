# 09 — Gap Register

Source: Master Product Intent §9 (S1). Gap numbering preserved from source.

Gaps identified by tracing the current repository baseline (commit `76f21bdc2fc277d0fdddf546c32ac75a5ded7e42`); they are implementation deviations from the target contract. Priority reflects customer, security, financial-integrity, and release-certification risk. All gaps are **open** at extraction.

## GAP-01 — Tenant and parent-case ownership not enforced on workspace reads (P0)

- Current implementation: Workspace generation reads a BusinessCaseRecord by case ID without explicitly comparing record tenant to authenticated context; workspace child rows tenant-filtered but parent ownership and tenant-inclusive keys incomplete.
- Required convergence: Enforce tenant, account, and parent-case ownership on every read/write; include tenant in relational uniqueness; add hostile same-ID and cross-ID tests.
- Rules: R-2, R-6. Stories: VP-01, VP-14.

## GAP-02 — Prospect setup does not launch the analysis workflow (P0)

- Current implementation: Prospect setup persists only basic account fields and navigates to Signals; does not launch the complete ingestion and analysis workflow.
- Required convergence: Persist the complete intake contract and start an observable L1–L4 analysis run with durable progress and failure states.
- Stories: VP-02. Journey: J-2.

## GAP-03 — Workspace generation is destructive and schema-divergent (P0)

- Current implementation: Workspace generation exposes existing graph signals and hypotheses, overwrites other tab data with empty collections, and writes value_models while the UI expects valueLines.
- Required convergence: Adopt one canonical model schema; make generation non-destructive, version-aware, capable of creating the artifacts the UI promises.
- Stories: VP-07.

## GAP-04 — Hypothesis conversion does not materialize the model (P0)

- Current implementation: Hypothesis validation creates a driver and lever, but Convert primarily changes status and returns only pre-existing tree or model IDs.
- Required convergence: Make promotion and conversion create persistent, idempotent tree and model artifacts with stable IDs and version.
- Stories: VP-05. Rules: R-2, R-4. Journey: J-5.

## GAP-05 — Promoted drivers lack executable formulas (P0)

- Current implementation: Promoted ValueDriver nodes include estimated impact but no executable formula, while the governed ROI workflow queries ValueDriver.formula.
- Required convergence: Require a valid formula and variables for financial drivers, or explicitly classify the driver as non-financial before calculation.
- Stories: VP-05, VP-07. Journey: J-5.

## GAP-06 — Frontend and L3 ROI contracts diverge (P0)

- Current implementation: Frontend ROI contract uses flat deal-size and annual-benefit fields while the Layer 3 route expects workforce and productivity inputs and returns nested results.
- Required convergence: Converge on one versioned calculation schema; add generated types or bidirectional contract tests.
- Stories: VP-10. Journey: J-7. Rules: R-4.

## GAP-07 — Two divergent value-case workflows (P0)

- Current implementation: Modern web value-case flow and governed Layer 4 business-case workflow use different APIs, records, generation paths, and lifecycle semantics.
- Required convergence: Unify on one canonical case identity, workflow, approval, persistence, export, provenance, and deliverables lifecycle.
- Stories: VP-12. Journey: J-9.

## GAP-08 — Value-case persistence drops upstream identifiers (P0)

- Current implementation: Web value-case persistence can omit evidence IDs, claim IDs, assumption IDs, and the ROI snapshot even when readable inputs were used.
- Required convergence: Persist typed upstream identifiers and immutable snapshots through narrative, approval, publication, export, and provenance.
- Stories: VP-11. Rules: R-7, R-8.

## GAP-09 — Silent synthetic fallback in Layer 4 ROI (P0)

- Current implementation: Layer 4 ROI may fall back to calibrated synthetic inputs and built-in drivers when account data is missing.
- Required convergence: Block silent production fallback; require a visible, authorized assumption workflow and mark downstream eligibility.
- Stories: VP-10. Rules: R-4, R-5.

## GAP-10 — Evidence policy caller-supplied and auto-passing (P0)

- Current implementation: Truth requirements are caller-supplied and can auto-pass when absent; corroboration count reported but not fully enforced in the pass expression.
- Required convergence: Make evidence policy explicit, mandatory for publication, deterministic, configuration-controlled, covered by negative tests.
- Stories: VP-08, VP-12. Rules: R-1, R-5.

## GAP-11 — Browser-local authoritative state (P1)

- Current implementation: Named ROI scenario versions and some workflow selections are browser-local; action-plan recommendations and some edits remain component state.
- Required convergence: Persist authoritative scenarios, selections, action plans, and drafts on the server with version and conflict handling.
- Stories: VP-06, VP-09, VP-10. Rules: R-2.

## GAP-12 — No candidate-SHA-bound end-to-end certification (P0)

- Current implementation: Existing browser journeys frequently use mocks or seeded results; the release manifest identifies the missing single candidate-SHA-bound frontend-to-L6 certification.
- Required convergence: Create one fresh-account, real-service, real-persistence journey through approval and export with deterministic assertions and release evidence.
- Stories: VP-14 (cross-cutting). See `08_definition-of-done.md` Quality and certification item 6.

## Recommended delivery sequence

1. **Foundation and security** — close GAP-01; define canonical case and model identity; enforce tenant-inclusive constraints; freeze target schemas.
2. **Canonical modeling spine** — close GAP-02 through GAP-06 (fresh account → reviewed signals, accepted hypotheses, real driver tree, valid formulas, server scenarios, deterministic calculations).
3. **Governed decision artifact** — close GAP-07 through GAP-10 (converge value-case workflows, preserve identifiers, enforce evidence policy, eliminate silent production defaults).
4. **Durability and collaboration** — close GAP-11 (server persistence, versioning, conflict behavior, cross-device recovery).
5. **Release proof** — close GAP-12 (candidate-SHA-bound certification across frontend, gateway, L1–L6, persistence, authorization, observability, approval, export).
6. **Realization** — activate VP-13 only after the published forecast identity and provenance contract are stable.

## Convergence decisions (fixed)

1. The primary work unit is **Account plus Analysis Case**; every model, calculation, narrative, review, and realization artifact references that identity.
2. The persistent driver, lever, variable, formula, evidence, and scenario graph is the canonical model. A UI-specific value line is a view model, not a second domain model.
3. L3 owns deterministic financial calculation; L4 orchestrates workflows and human gates; L5 governs truth and claims; L6 supplies governed benchmarks.
4. One value-case lifecycle serves Studio, Narrative, Deliverables, approval, publication, export, and realization.
5. Server state is authoritative. Browser state may improve usability but cannot be the only copy of a material business artifact or decision (R-2).
6. Production defaults are explicit assumptions with visible lineage and policy impact, never silent customer data substitutes (R-5).
7. Publication requires verified authorization, a valid current model and ROI snapshot, enforced evidence policy, human approval, and no material stale or degraded condition (R-3, R-6, R-7).
