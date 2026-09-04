# FE-VOS-STUDIO-001 — Agentic Value Studio, Slice 1 (Mission-Led Shell)

**Status:** Slice 1 delivered for review
**Date:** 2026-09-04
**Branch:** `feat/value-studio-slice-1` (fork `valyntxyz/Fabric_4L`; cross-repo draft PR into `Valynt/Fabric_4L`)

Slice 1 delivers the mission-led Value Studio page as a fully composed,
fully tested front-end shell over a deterministic fixture projection. No
backend command channel, projection endpoint, or event stream is connected in
this slice; every domain action is honest about that (see DEC-FE-005).

## 1. Scope and canonical route

**In scope (Slice 1):** one typed, versioned case projection rendered end to
end — opportunity header, audience lenses, journey status, mission strip,
impact summary, model patch card, branch comparison, Review Required decision
rail, intent preview, edit-decision form, evidence drawer, mission activity
feed, Steer Flo panel — across the ten named states in §4.

**Canonical route:** `/t/:tenantSlug/accounts/:accountId/studio/mission`
(DEC-FE-001). Value Studio is account-scoped, so the page lives under the
canonical tenant/account prefix like every other workspace route; the shell
redirect `/studio → /studio/action-plan` is untouched, and `mission` is
registered as an explicit route ahead of the `studio/:tabId` catch-all.

**Out of scope (Slice 2+):** see §2, "Deliberately unresolved".

## 2. Decision log

| ID | Decision | Rationale | Status |
| --- | --- | --- | --- |
| DEC-FE-001 | Canonical route is `/t/:tenantSlug/accounts/:accountId/studio/mission`, registered explicitly ahead of `studio/:tabId` | Account-scoped workspace convention; explicit registration avoids ambiguity with the tab catch-all and keeps the route inventory gate honest | Closed |
| DEC-FE-002 | Strict projection/view-model boundary: the FE never derives or overwrites projection values; `viewModel.ts` only formats and maps enums | The projection payload is authoritative (FE-DATA-001); missing economics map to explicit copy ("Pending", "Not yet calculable"), never zero (FE-IMP-002/003/004) | Closed |
| DEC-FE-003 | Fixture strategy: hand-authored deterministic fixtures behind one exported clock (`FIXTURE_NOW`) and reference ids; no `Date.now`/`Math.random`/model-generated content | Reproducible state matrix for §8.1; reviewable diffs; contract hygiene gates forbid nondeterminism in feature code | Closed (removed with the Phase-2 backend adapter) |
| DEC-FE-004 | Single adapter seam (`adapter.ts`): components consume `ValueStudioViewState` produced by `FixtureValueStudioAdapter` behind `ValueStudioProjectionAdapter`; TanStack Query hook owns caching, never truth | Phase 2 swaps the adapter for the backend projection endpoint without touching component props or view states | Closed |
| DEC-FE-005 | Intent-preview model: accept/edit/defer produce a typed preview (command type + expected model/decision versions + will/will-not lists) built from the projection only; Slice-1 Proceed/pause/resume/undo surface `COMMAND_BACKEND_NOTICE` instead of simulating success | FE-INTENT-001/002: preview is never free-form model text; the browser never mutates domain state or fabricates a success path while the command channel is unconnected | Closed |
| DEC-FE-006 | State model: first-match-wins composition — loading skeleton → full-page error (correlation id + retry) → unauthorized (no protected body data) → empty → offline/stale/partial banners over the ready grid | §8.1/§10/§11.4: full-page states replace the body; degraded states keep the last authoritative projection visible and pause submissions (FE-RAIL-008/009) | Closed |
| DEC-FE-007 | Route/nav integration through existing canon: `navigationService` route state `studio-mission`, `NAV_SCHEMA` child under Value Studio, router handle via `accountStdPolicy("studio.mission")` | One source of truth for paths; navigation appears in the sidebar and route inventory without new conventions | Closed |

### Deliberately unresolved (Slice 2+)

| Open item | Owner | Notes |
| --- | --- | --- |
| Backend projection adapter behind the existing seam | Platform/backend | Replaces `FixtureValueStudioAdapter`; owns refetch/stale policy (§10.2) |
| Mission command channel (accept/edit/defer/pause/resume/undo) | Mission backend | Removes `COMMAND_BACKEND_NOTICE`; preview already carries expected versions for optimistic-concurrency checks |
| Activity event streaming (cursor `latestEventCursor`) | Mission backend | Slice 1 renders the projected trail only |
| Deterministic calculation service integration | Calc service | Impact remains read-only in the FE regardless |
| Generative lens rendering | Product/platform | Thesys/OpenUI evaluated and **not adopted**; static fallback path (`StaticGenerativeUIFallback`) shipped instead |
| Publication workflow beyond blocked/provisional display | Governance | Current states render backend-owned labels only |
| Rewind/undo of activity events | Mission backend | Undo control renders only when the event's `allowedActions` authorize it |

## 3. Component inventory

Page composition (`ValueStudioPage.tsx`) plus, under `components/`:
`OpportunityHeader`, `LensSelector`, `JourneyStatus`, `MissionStrip`,
`SteerFloTrigger`, `SteerFloPanel`, `ImpactSummary`, `ModelPatchCard`,
`BranchComparison`, `DecisionRail`, `DecisionIntentPreview`,
`EditDecisionForm` (+ extracted `editDecisionSchema.ts`), `EvidenceDrawer`,
`MissionActivityFeed`, `GenerativeUIFallbackBoundary`,
`StaticGenerativeUIFallback`, `InlineError`, `OfflineBanner`,
`ValueStudioSkeletons`.

Support modules: `types.ts` (projection contract), `fixtures.ts`
(deterministic factory + ten named states), `adapter.ts` (seam),
`useValueStudioProjection.ts` (TanStack Query hook), `viewModel.ts`
(format/display mapping only), `intentPreview.ts` (typed previews),
`queryParams.ts` (`lens`/`decision`/`fixture`), `analyticsEvents.ts` (§14
event names, feature-logger emission only).

## 4. Ten named states (§8.1)

`loading`, `blocked` (default — §1.4 reference state), `empty`, `partial`,
`error`, `offline`, `stale`, `unauthorized`,
`resolved-decision-but-still-finance-blocked`, `static-renderer-fallback`.

Each is selectable in Phase 1 via `?fixture=<name>`; deep links use
`?decision=DISP-01` and lenses survive refresh via `?lens=<id>` (FE-LENS-004).

## 5. Verification

Test coverage lives in
`apps/web/src/features/value-studio/mission/__tests__/` (nine files: fixture
contract, query params, view-model, intent preview, edit-decision schema,
MissionStrip, ImpactSummary, DecisionRail, page composition incl. route/nav
registration, all ten states, interactions, analytics, axe). Run:

```bash
cd apps/web
pnpm exec vitest run src/features/value-studio   # targeted suite
pnpm exec vitest run                              # full frontend suite
pnpm exec tsc --noEmit                            # typecheck
pnpm run lint                                     # hygiene + any-threshold + legacy-api + shims
pnpm run test:route-inventory                     # baseline: 10 TieredNav findings (none reference studio/mission)
pnpm run check:async-boundaries                   # baseline: 7 findings outside value-studio
```

Known inherited baseline failures are enumerated in the draft PR's
verification section with their evidence.

## 6. Phase 2 — smallest safe next step

Land the backend projection adapter behind the existing
`ValueStudioProjectionAdapter` seam (DEC-FE-004): same `ValueStudioViewState`
contract, same query key shape, fixtures removed with the `?fixture=`
parameter. No component props change; the state machine in §2 DEC-FE-006 is
unchanged.
