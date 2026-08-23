# 06 — User Stories

Source: Master Product Intent §6 (S1). Story numbering preserved from source.

Structure (uniform across stories): title, user story statement, design intent, engineering contract, numbered acceptance criteria. Acceptance criteria are cumulative with cross-cutting security, provenance, accessibility, observability, and Definition of Done (`08_definition-of-done.md`) requirements.

Journey/behavior/gap cross-references derive from the S1↔S2 concordance and the delivery sequence in `09_gap-register.md`. Full story text (all acceptance criteria) remains in the source baseline; this catalogue carries the stable IDs, summaries, AC counts, and contract pointers.

## VP-01: Start and resume a scoped case

- Summary: As a value engineer, create or resume an account analysis so all subsequent work belongs to one durable, authorized case.
- Acceptance criteria: 5.
- Journey: J-1. Behaviors: BEH-01. Related gaps: GAP-01.
- Design intent: make identity and scope impossible to miss; resumed case shows freshness, lifecycle, blockers, next valid action.
- Engineering contract: authorization from backend snapshot + request context; case ownership verified against tenant and account; relational uniqueness includes tenant scope.

## VP-02: Connect sources and launch analysis

- Summary: As a value engineer, add approved sources and launch intelligence analysis so the model is grounded in actual account information.
- Acceptance criteria: 5.
- Journey: J-2. Behaviors: BEH-01. Related gaps: GAP-02.
- Design intent: step-aware progress surface preserving last good result; differentiates waiting/running/partial/degraded/failed.
- Engineering contract: start command has one versioned contract, creates observable workflow run, records input version, source IDs, tenant, account, case, execution tier.

## VP-03: Review pain signals

- Summary: As a value engineer, review detected pain signals so weak or incorrect interpretations do not enter the value model.
- Acceptance criteria: 5.
- Journey: J-3. Behaviors: BEH-02.
- Design intent: present source and interpretation together in review context.
- Engineering contract: signal decisions are durable, idempotent, versioned domain actions — not component state or navigation-only affordances.

## VP-04: Generate ranked value hypotheses

- Summary: As a value engineer, generate hypotheses connecting pain, capability, and potential outcome to prioritize credible value opportunities.
- Acceptance criteria: 5.
- Journey: J-4. Behaviors: BEH-02.
- Design intent: show score composition and evidence coverage, not only a single confidence number; preserve comparison across generations.
- Engineering contract: hypothesis engine uses tenant-scoped graph queries; records all ranking inputs, configuration, run ID, source version.

## VP-05: Validate and promote hypotheses

- Summary: As a value engineer, accept, edit, or reject a hypothesis so only human-reviewed reasoning becomes modeled value.
- Acceptance criteria: 5.
- Journey: J-5. Behaviors: BEH-02. Closes gaps: GAP-04 (with GAP-05 in the same stage). Rules: R-2, R-4.
- Design intent: explicit Accept/Edit/Reject/Promote actions with visible downstream impact and confirmation for consequential changes.
- Engineering contract: validation and conversion are separate typed commands with idempotency keys; action labels must correspond to committed backend effects.

## VP-06: Map stakeholders and actions

- Summary: As an account team member, connect stakeholders to outcomes, concerns, and next actions so the value case supports an actual buying decision.
- Acceptance criteria: 5.
- Journey: J-8. Behaviors: BEH-06.
- Design intent: stakeholder work tied to drivers and decisions, not a detached contact list; missing-role readiness gaps shown in context.
- Engineering contract: stakeholder mappings are server-persisted case objects with provenance and version history; action-plan recommendations not browser-only.

## VP-07: Create the driver tree and value model

- Summary: As a value engineer, convert accepted hypotheses into a persistent driver tree so outcomes, drivers, levers, metrics, and formulas form one coherent model.
- Acceptance criteria: 5.
- Journey: J-5. Behaviors: BEH-03. Related gaps: GAP-03, GAP-05.
- Design intent: navigable tree with synchronized details panel, downstream-impact preview, clear financial vs strategic distinction.
- Engineering contract: canonical model schema replaces divergent valueLines and value_models payloads; graph and API return same stable IDs and version.

## VP-08: Bind evidence and benchmarks

- Summary: As a governance reviewer, link evidence and benchmarks to specific claims, assumptions, and drivers so model support can be independently evaluated.
- Acceptance criteria: 5.
- Journey: J-6. Behaviors: BEH-05.
- Design intent: evidence beside the claim it supports, with detail drawer for source, applicability, freshness, decision history.
- Engineering contract: evidence search, human decision, truth promotion, and publication gating share typed identifiers and a deterministic minimum-source policy.

## VP-09: Manage variables, formulas, and assumptions

- Summary: As a value engineer, inspect and edit transparent model inputs so the customer can understand and challenge the calculation.
- Acceptance criteria: 5.
- Journey: J-6. Behaviors: BEH-04. Related gaps: GAP-11.
- Design intent: a real Variables experience with units, provenance, ranges, validation, impact preview — not a nonfunctional affordance.
- Engineering contract: formula/variable schemas versioned and validated client and server; each calculation stores exact substituted formulas and engine version.

## VP-10: Calculate and compare scenarios

- Summary: As a finance or economic buyer, compare conservative, expected, and optimistic scenarios to evaluate investment risk and return.
- Acceptance criteria: 6.
- Journey: J-7. Behaviors: BEH-04. Related gaps: GAP-06, GAP-09, GAP-11.
- Design intent: side-by-side comparison, sensitivity explanations, current/stale labeling; last valid result visible during recalculation.
- Engineering contract: L3 is the deterministic calculation authority; L4 orchestrates but does not redefine the math; requests/responses are immutable snapshots.

## VP-11: Generate an evidence-linked narrative

- Summary: As an account executive, generate an executive narrative from the selected model so the financial case becomes a persuasive and defensible decision story.
- Acceptance criteria: 6.
- Journey: J-8. Behaviors: BEH-06. Related gaps: GAP-08.
- Design intent: preview frozen inputs, choose audience/sections, compare versions, open every material citation.
- Engineering contract: narrative generation downstream of deterministic model; saved content retains evidence IDs, claim IDs, assumption IDs, ROI snapshot ID, model version, trace ID.

## VP-12: Review, approve, publish, and export

- Summary: As an authorized approver, govern the customer-facing value case so only complete and authorized versions are released.
- Acceptance criteria: 6.
- Journey: J-9. Behaviors: BEH-07, BEH-08. Related gaps: GAP-07, GAP-10.
- Design intent: gate checklist with direct fixes, version comparison, anchored review comments, explicit confirmation of account and version before publication.
- Engineering contract: modern web value-case flow and governed Layer 4 business-case workflow converge on one canonical case record, lifecycle, API, approval, storage, and audit contract.

## VP-13: Track value realization

- Summary: As a customer champion or realization owner, compare actual outcomes with the approved forecast so the team can prove and improve realized value.
- Acceptance criteria: 6.
- Journey: J-10. Behaviors: BEH-09.
- Activation constraint: activate only after the published forecast identity and provenance contract are stable (see `09_gap-register.md` delivery sequence step 6).
- Design intent: forecast vs actual easy to understand; clearly separate historical commitment, current actuals, reforecast.
- Engineering contract: realization measurements are versioned server records linked to published case, source, owner, cadence, audit history.

## VP-14: Enforce scope, observe, audit, and recover

- Summary: As a tenant administrator, governance owner, or operator, prove who did what, within which scope, using which inputs and execution tier so the workflow remains secure, supportable, and certifiable.
- Acceptance criteria: 6.
- Journey: cross-cutting (all stages). Related gaps: GAP-01, GAP-12.
- Design intent: error/degraded/denied/stale/conflict states understandable to a user and actionable by support without exposing protected data.
- Engineering contract: tenant isolation, observability, auditability, idempotency, recoverability, release evidence are part of the feature contract, not operational follow-up.
