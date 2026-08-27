# BEH-06: Business case generation

```yaml
id: BEH-06
name: business-case-generation
journey_stage: J-8            # Generate the decision narrative
stories: [VP-06, VP-11, VP-14]
closes_gaps: [GAP-07, GAP-08]
rules: [R-1, R-4, R-5, R-8]
boundary: web -> api -> L4 (+ value-studio domain service)
components:
  - BusinessCasePages
  - ValueCasePage
  - StudioShell                # Value model / Narrative / Action plan tabs
  - ValueCasesRouter
  - ValueCaseOrchestrator      # value-studio domain service
  - NarrativeGenerator         # L4 governed generation from immutable snapshot
primary_gates: [AG-02, AG-03]
```

## Product

An account executive generates an evidence-linked decision narrative **from the exact reviewed model** — never from loose context (VP-11; jobs 5). Stakeholder mappings and action plans tie the case to an actual buying decision (VP-06).

Correct behavior, normatively:
- Generation runs **downstream of the deterministic model**: build an immutable input snapshot (model version + ROI snapshot + evidence/claim/assumption IDs + source freshness + generation configuration), then produce cited narrative content **without changing the calculation** (R-4, §7.2.3).
- Saved content retains evidence IDs, claim IDs, assumption IDs, ROI snapshot ID, model version, and trace ID — a web value-case write that omits them is a defect (closes GAP-08).
- **One canonical case identity, lifecycle, API, approval, storage, and audit contract** serves both the modern web value-case flow and the governed L4 business-case workflow (closes GAP-07; convergence decisions 1 and 4).
- All material claims are supported, qualified, or blocked (J-8 exit). Unverified claims and defaults remain visible (R-1, R-5).
- Stakeholder mappings and action-plan recommendations are server-persisted case objects with provenance and version history — not detached contact lists or browser-only state (VP-06 eng; GAP-11 adjacency).
- Generate endpoints run the promised workflow or are renamed to Create/Persist; a route never accepts a completed object while implying it generated it (§7.4.2).

## Architecture

```
 apps/web                            services/api              generation path
 ┌─────────────────────────┐         ┌────────────────────┐
 │ BusinessCase.tsx         │         │ routers/           │──▶ L4: governed narrative
 │ BusinessCaseList.tsx     │────────▶│  value_cases.py    │    workflow: snapshot ▶
 │ InteractiveBusinessCase  │         └────────────────────┘    cited sections ▶
 │ value-case/ValueCasePage │                    │               persisted draft
 │ studio/ValueModelTab.tsx │                    ▼
 │ studio/NarrativeTab.tsx  │         services/value-studio/
 │ studio/ActionPlanTab.tsx │         domain/services/
 │ features/value-studio/   │         value_case_orchestrator.ts
 │  StudioShell.tsx         │         domain/contracts/value_case.ts
 └─────────────────────────┘
   one canonical case ID + lifecycle across every surface (GAP-07)
```

## Implementation

### Verified anchors

| Path | What it is | Role in this behavior |
|---|---|---|
| `apps/web/src/pages/BusinessCase.tsx` | Business case page | Case view/edit against canonical record |
| `apps/web/src/pages/BusinessCaseList.tsx` | Case list | Case inventory within tenant/account scope |
| `apps/web/src/pages/InteractiveBusinessCase.tsx` | Interactive case page | Section-level cited content interaction |
| `apps/web/src/pages/value-case/ValueCasePage.tsx` | Value case page | Modern web value-case flow (to converge with L4 path, GAP-07) |
| `apps/web/src/features/value-case/` | Value-case feature shell | Feature composition for the value-case journey |
| `apps/web/src/pages/studio/ValueModelTab.tsx` | Studio value model tab | Model view feeding narrative snapshot |
| `apps/web/src/pages/studio/NarrativeTab.tsx` | Narrative tab | Audience/section selection, preview of frozen inputs, version compare |
| `apps/web/src/pages/studio/ActionPlanTab.tsx` | Action plan tab | Stakeholder-tied next actions (VP-06); server-persisted |
| `apps/web/src/features/value-studio/StudioShell.tsx` | Studio shell | One case identity across studio tabs |
| `apps/web/src/features/value-studio/studioTabRegistry.ts` | Studio tab registry | Tab composition over shared case state |
| `services/api/app/routers/value_cases.py` | Value cases router | Canonical case API: snapshot, generation, persistence, lifecycle |
| `services/value-studio/src/domain/services/value_case_orchestrator.ts` | Domain orchestrator | Value-case domain logic and lifecycle transitions |
| `services/value-studio/src/domain/contracts/value_case.ts` | Domain contract | Canonical value-case types |
| `contracts/tool-manifests/generate_business_case.json` | Tool manifest | Agent-callable generation contract (same workflow) |
| `contracts/tool-manifests/generate_section.json` | Tool manifest | Section-level generation contract |

### Inputs / outputs
- **In**: selected scenario + model version + ROI snapshot (immutable), audience and section selection, stakeholder mappings, generation configuration.
- **Out**: value-case draft version with cited sections; persisted identifier set (evidence/claim/assumption/ROI-snapshot IDs, model version, trace ID); lifecycle state `draft`.

### State transitions
- Lifecycle: `draft -> in_review` (handoff to BEH-08); edits to a reviewed/approved version always create a **new draft with lineage** (R-7).
- Operation: `idle -> generating -> idle | retrying`; generation acknowledged fast with visible stage progress; job survives navigation.
- Content: `ready | degraded | stale`; an upstream material input change marks the draft `stale` and requires recalculation or re-review (§7.2.6).
- Synchronization: conflicts return both version identities; never silent overwrite.

### Failure modes
- LLM/provider failure → narrative enrichment degrades visibly; deterministic financial outputs unchanged (R-4); degradation recorded with fallback tier and may block publication (§7.3.5, R-5).
- Snapshot inputs unreadable or scope-invalid → generation fails closed; no narrative from partial or foreign state (R-6).
- Claim without support reaching a section → claim qualified or blocked, never silently asserted (J-8 exit).
- Divergent persistence paths (web vs L4 workflow) → contract tests fail; one canonical record only (GAP-07).
- Duplicate generate command → idempotent; stable case/draft/version IDs (§7.4.3).

## Verification

**Tests**
- Unit: snapshot assembly completeness (all typed IDs present — GAP-08 negative cases), lifecycle transitions, lineage on edit.
- Contract: value-case schemas (`value_case.ts` domain contract vs API schema); `generate_business_case.json` / `generate_section.json` manifest conformance; convergence tests proving web flow and L4 workflow share one record/lifecycle (GAP-07).
- Integration (real persistence): generate → draft persists with citations and trace ID; duplicate/retry safety; stale marking after upstream change.
- AI evaluation: citation correctness against golden datasets; deterministic schema/provenance assertions (LLM-as-judge never sole evidence).
- Browser: choose audience/sections → generate → open every material citation; compare versions; degraded-provider state visible.

**Tenant-isolation assertions**
- Case reads/writes verify tenant + account + parent ownership (GAP-01-class hostility applied to case records).
- Generation prompts, retrieval, memory, and traces tenant-scoped (AI isolation controls under AG-05); no foreign content can enter a snapshot.
- Snapshot and draft object paths tenant-prefixed.

**Release gates**
- **AG-02 code-quality-and-tests** — unit/integration/browser coverage; mutation tests on snapshot assembly.
- **AG-03 contract-compliance** — case API schema, tool-manifest drift, web↔L4 convergence contract tests.
- **AG-05 tenant-isolation-and-behavior** — AI prompt/memory/trace/tool isolation; account-scope enforcement.

**Required evidence**
- EV: junit-and-json test-run evidence for snapshot/lifecycle suites.
- EV: contract-test results for the canonical case schema and tool manifests.
- EV: AI-evaluation run record (citation correctness, golden dataset).
- EV: Playwright traces for the generate-and-cite journey.
