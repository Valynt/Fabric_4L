# L2 Component — value-studio

## Purpose

TypeScript value-case domain service (`services/value-studio/`). Owns the value-case domain
orchestration behind the Studio surfaces. One canonical value-case lifecycle serves Studio,
narrative, deliverables, approval, publication, export, and realization (GAP-07 convergence).

NOTE: this service has no README (verified). Treat its contracts and tests as the authority.

## Owned journey stages / behaviors

- BEH-06 business-case-generation — `src/domain/services/value_case_orchestrator.ts`,
  `src/domain/contracts/value_case.ts`
- BEH-07 deliverable-rendering — domain model behind the three audience views
- BEH-08 approval-and-publication — case lifecycle states: draft, in_review,
  changes_requested, approved, published, superseded (R-7 immutability)

## Key verified paths

- `services/value-studio/src/domain/services/value_case_orchestrator.ts`
- `services/value-studio/src/domain/contracts/value_case.ts`
- `services/value-studio/tests/`
- Root: `package.json`, `tsconfig.json`, `vitest.config.ts`

## Dependencies

- Frontend Studio shell: `apps/web/src/features/value-studio/`,
  `apps/web/src/pages/studio/{ValueModelTab,NarrativeTab,ActionPlanTab}.tsx`.
- `services/api` router `value_cases.py`; tool manifest
  `contracts/tool-manifests/generate_business_case.json`.
- MUST persist typed upstream identifiers (evidence IDs, claim IDs, assumption IDs, ROI snapshot
  ID, model version) — GAP-08.

## Primary gates

- **AG-02** code-quality-and-tests — Vitest domain tests, lifecycle state transitions.
- **AG-03** contract-compliance — versioned value-case schema shared with frontend and gateway.
- **AG-09** change-risk-and-approval — lifecycle/approval semantics changes are high-risk.
