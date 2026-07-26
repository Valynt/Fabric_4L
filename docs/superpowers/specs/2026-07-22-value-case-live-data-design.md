# Value Case Generation — Live-Data Inputs Design

## Context

An earlier audit claimed Layer 5 (Ground Truth) and Layer 6 (Benchmarks) had minimal frontend integration. That assessment is now stale. Repository inspection confirms:

- **Layer 5** is consumed by `GovernanceEvidence`, `GovernanceCompliance`, `GovernanceAuditLog`, `GovernanceChangeHistory`, and `HealthMonitor` via `useGroundTruthGovernance` against the live L5 API.
- **Layer 6 / ROI & benchmarks** feed `BenchmarkPolicies`, `ROITab`, `ValueModelTab`, `CFOView`, `ExecutiveView`, `BusinessCase`, `FormulaBuilder`, `DriverTreePage`, and `ValueCasePage`.
- Both layers have generated TypeScript client types (`api/generated/l5/`, `api/generated/l6/`) and contract tests.

The remaining, narrower risk is **live-usability**: a logged-in user can still hit hardcoded mock data during core workflows.

## Concrete Problem

`apps/web/src/pages/value-case/ValueCasePage.tsx` (`handleGenerate`) passes entirely hardcoded inputs to `useValueCaseArtifacts().generateArtifact.mutate()`:

```ts
stakeholders: ["Economic buyer", "Business champion", "Technical evaluator"]
accepted_evidence: ["Validated calculator assumptions", "Accepted business pains from discovery"]
scenario_assumptions: ["Conservative ramp in Q1", "Expected adoption by Q2"]
roi_metrics: { three_year_value: "$1.8M", roi: "214%", payback: "9 months" }
risk_notes: ["Change management capacity", "Competing budget priorities"]
```

These strings are static, not tenant-scoped, and ignore the account's actual workspace state, evidence, claims, and calculations.

## Goal

Replace the hardcoded `ValueCaseArtifactsInput` with live, tenant-scoped data derived from the account workspace and platform layers, while preserving the existing generation/publish flow and contract boundaries.

## Assumptions

1. The user wants a **production-safe** design, not a quick hack. Human review of generated inputs is acceptable.
2. The value-case workflow should remain a **single-account, tenant-isolated** feature.
3. Existing hooks (`useStakeholdersData`, `useEvidence`, `useGroundTruthGovernance`, `useROICalculator`, workspace tab queries) are trusted data sources.
4. The design should reuse existing UI primitives and TanStack Query patterns.

---

## Approach A — Fully Automated Generation

**Description:** On clicking Generate, the page assembles inputs transparently from live queries and immediately invokes `generateArtifact.mutate()`.

**Trade-offs:**
- ✅ Fastest user path; one-click generation.
- ✅ Removes all hardcoded values in one change.
- ❌ User cannot see or correct what went into the value case.
- ❌ If any live source is empty or low-quality, output degrades silently.
- ❌ Harder to debug and harder to satisfy governance/audit requirements.

## Approach B — Pre-Generation Review Panel (Recommended)

**Description:** Clicking Generate opens a panel/modal that populates inputs from live data, lets the user edit each field, then confirms generation. The populated state is also what gets persisted in `ValueCaseContent.inputs`.

**Trade-offs:**
- ✅ Eliminates hardcoded mock data.
- ✅ Keeps human in the loop for governance and accuracy.
- ✅ Surfaces missing/weak data explicitly (e.g., "No validated evidence found").
- ✅ Aligns with existing right-rail / overlay UX patterns.
- ❌ Slightly more UI work than Approach A.
- ❌ Requires loading states for multiple sources.

## Approach C — Hybrid Minimum-Viable Fix

**Description:** Replace only the obviously static fields (`roi_metrics` from ROI calculations, `accepted_evidence` from L5 truths) and keep the remaining fields as editable defaults in a small inline form. Stakeholders, assumptions, and risks remain templated.

**Trade-offs:**
- ✅ Smallest initial diff.
- ✅ Reduces the most egregious mock numbers.
- ❌ Leaves significant hardcoded surface area.
- ❌ Creates an inconsistent UX (some live, some fake).

---

## Recommended Design: Approach B — Pre-Generation Review Panel

### 1. Data Source Mapping

| `ValueCaseArtifactsInput` field | Live source | Hook / endpoint | Fallback when empty |
|--------------------------------|-------------|-----------------|---------------------|
| `stakeholders` | Workspace stakeholders tab | `useStakeholdersData(caseId)` | Empty list + prompt to map stakeholders |
| `accepted_evidence` | L5 validated truths for the opportunity | `useTruths({ status: "validated", applies_to_opportunity: accountId })` | Empty list + prompt to add evidence |
| `scenario_assumptions` | User-editable in panel (no live workspace tab exists yet) | Manual input | Empty list + editable placeholder |
| `roi_metrics` | Latest account ROI calculation | `useROICalculations({ account_id })` | Empty metrics + prompt to run calculator |
| `risk_notes` | L5 disputed/rejected truths + workspace hypotheses risks | `useTruths({ status: "disputed" })`, workspace hypotheses | Empty list + editable placeholder |

Notes:
- All queries must be tenant-scoped via the existing API client and authenticated context.
- Filtering by `account_id` and `case_id` must be preserved; do not trust client-side IDs.

### 2. New Hook: `useValueCaseGenerationInputs`

Create `apps/web/src/hooks/useValueCaseGenerationInputs.ts`.

Responsibilities:
- Accept `accountId` and `caseId`.
- Orchestrate the live queries above in parallel.
- Map query results into a `ValueCaseArtifactsInput` draft.
- Expose loading, error, and `isReady` states.
- Expose a `buildDraft()` function that returns the populated input.
- Return per-field provenance metadata for the UI (e.g., `source: "l5_truth"`, `id`, `confidence`).

Design principles:
- Pure mapping function; no side effects.
- Returns the same shape as `ValueCaseArtifactsInput` so the existing `generateArtifact` mutation needs no change.
- Handles empty sources gracefully (empty arrays, not hardcoded strings).

### 3. UI: Pre-Generation Panel

Add a new component: `apps/web/src/components/value-case/ValueCaseGenerationPanel.tsx`.

Behavior:
- Triggered by the existing Generate/Regenerate button on `ValueCasePage`.
- Opens as a right-rail panel or modal (reuse existing `RightRailPanel` or `Sheet` patterns).
- Displays each input field with:
  - Live-loaded items as chips/badges.
  - Source indicator (e.g., "from Ground Truth", "from Workspace").
  - Remove / add controls.
  - Inline empty-state guidance.
- Includes primary action: **Generate Value Case**.
- On confirm, calls `generateArtifact.mutate(draft)` and closes the panel.

State management:
- Panel holds local editable state derived from `useValueCaseGenerationInputs`.
- Dirty state tracked to warn on close if edits exist.
- No global state added; uses TanStack Query for server data.

### 4. Error Handling

- If any live query fails, show a non-blocking warning with retry.
- If all required sources are empty, disable Generate and show actionable empty states (link to Stakeholders tab, ROI calculator, etc.).
- Preserve existing `generateArtifact.isError` handling in `ValueCasePage`.

### 5. Contract & Type Safety

- Reuse `ValueCaseArtifactsInput` interface; no API contract change.
- Ensure `api/generated/l5` and `api/generated/l3` types are used for query responses.
- Add a contract test asserting that `useValueCaseGenerationInputs` never returns the legacy hardcoded strings.

### 6. Testing

- **Unit:** Test the input-mapping hook with mocked query results, including empty-source fallbacks.
- **Component:** Test the panel renders live items, allows removal/addition, and calls `generateArtifact` with the edited draft.
- **Contract:** Verify that `ValueCasePage` no longer contains the literal hardcoded strings from the current `handleGenerate`.
- **Integration:** Optional live-stack test generating a value case end-to-end for a seeded account.

### 7. Rollout / Scope

- This design targets **only** the value-case generation workflow.
- Does not refactor unrelated `ValueNarrativeHome` or other mock-data paths unless they share the same hardcoded values.
- Leaves existing publish/update flows unchanged.

---

## Implementation Plan Preview

1. Add `useValueCaseGenerationInputs` hook with parallel live queries and draft builder.
2. Add `ValueCaseGenerationPanel` component wired into `ValueCasePage`.
3. Replace `handleGenerate` hardcoded payload with panel-open action.
4. Add unit and component tests.
5. Add contract/regression test to prevent hardcoded strings from returning.
6. Run `pnpm --dir apps/web test` and `pnpm --dir apps/web run typecheck`.

---

## Open Questions for Implementation

- Should the panel be a modal or right-rail panel? (Existing right-rail pattern is preferred.)
- Should edited inputs be persisted as a draft before generation? (Recommendation: no, keep local state only.)
- Which L5 truth statuses count as "accepted evidence"? (Recommendation: `validated` only; allow user to add `proposed`.)
