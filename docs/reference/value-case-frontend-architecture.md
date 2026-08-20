# Value Case Frontend Slice Architecture

> **Audience:** Frontend and platform engineers working in [`apps/web/src/features/value-case/`](../../apps/web/src/features/value-case/).  
> **Pairs with:** [`DESIGN.md`](../../DESIGN.md) (frontend governance contract) and [`docs/reference/frontend-query-patterns.md`](frontend-query-patterns.md).  
> **Source of truth for API contracts:** [`contracts/openapi/layer4-agents.json`](../../contracts/openapi/layer4-agents.json) and [`apps/web/src/features/value-case/api/valueCaseSchemas.ts`](../../apps/web/src/features/value-case/api/valueCaseSchemas.ts).

This document details the architectural invariants, data flow, authorization boundaries, and cache isolation patterns implemented in the modernized Value Case frontend slice (`/value-case/:accountId` in Value Studio).

---

## 1. Architectural Overview

The Value Case slice enforces a strict one-way layered architecture:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Canonical Route (/value-case/:accountId)                              │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Verified Scope (ValueCaseScope: fabricTenantId, tenantSlug, accountId) │
│ Enforced via AuthorizationProvider snapshot (fails closed on mismatch)│
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TanStack Query Layer (valueCaseKeys factory + useValueCaseJourney)     │
│ Query key partitioning by [fabricTenantId, accountId]                  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Transport Boundary (valueCaseSchemas + valueCaseApi)                   │
│ Zod runtime validation, ValueCaseBoundaryError normalization           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Domain Layer (valueCaseModels + valueCaseAdapters + generationInputs)   │
│ Pure immutable models, deterministic top-5 caps, provenance tracking  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Presentation Layer (valueCaseViewModels + DTO-Free UI Components)      │
│ ValueCaseWorkspace, ValueCaseMetrics, ValueCaseResult, History, Panel   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Invariants

### A. Verified-Scope Authorization (`ValueCaseScope`)
- **Isolation by Construction:** The `ValueCaseScope` type (`{ readonly fabricTenantId: string; readonly tenantSlug: string; readonly accountId: string; }`) is constructed exclusively when `useAuthorizationSnapshot()` verifies:
  1. `snapshot.status === "active"` (not unauthenticated or expired).
  2. `snapshot.accountScope.scopeType === "account"`.
  3. `snapshot.accountScope.accountId === routeAccountId`.
- **Fail-Closed Queries:** If the route `accountId` does not match the active session or scope is missing, all protected data queries remain `enabled: false` and the workspace immediately transitions into explicit lifecycle states (`resolving-identity`, `denied`, or `expired`).
- **Hostile Switch Defense:** When tenant or account identities switch mid-flight, queries are immediately cleared and re-partitioned to prevent cross-tenant/cross-account data leaks.

### B. Transport Validation & Normalization (`valueCaseSchemas.ts`)
- Raw HTTP network payloads are treated as untrusted and parsed using Zod schemas (`apiBusinessCaseSchema`, `apiValueCaseContentSchema`, `apiValueCaseArtifactsInputSchema`).
- Parsing failures throw a strongly-typed `ValueCaseBoundaryError` with structured codes (`VALIDATION_FAILED`, `IDENTITY_MISMATCH`, `MALFORMED_PAYLOAD`, `NETWORK_ERROR`).

### C. Pure Immutable Domain Models & Adapters (`valueCaseModels.ts`, `valueCaseAdapters.ts`)
- All domain interfaces (`ValueCaseArtifactVersion`, `ValueCaseNarrative`, `ValueCaseBusinessCase`, `ValueCaseInputs`, `ValueCaseMetrics`) use `readonly` fields and `ReadonlyArray<T>` collections.
- Domain models use standard TypeScript `camelCase` naming, completely decoupled from backend `snake_case` transport fields.
- Adapters provide bidirectional transformations with defensive fallbacks for missing or nullable fields.

### D. Deterministic Generation Inputs Pipeline (`generationInputs.ts`)
When preparing workspace context (stakeholders, validated ground truths, disputed truths, ROI calculations) for generating a new value case:
- **Case-Insensitive Deduplication & Sorting:** Text entries are deduplicated case-insensitively and sorted alphabetically for deterministic generation prompts.
- **Top-5 Caps:** Stakeholders, evidence, assumptions, and risk notes enforce an explicit top-5 cap to keep prompt tokens bounded and focused.
- **Provenance & Availability:** Every item retains its source metadata (`workspace_stakeholder`, `l5_truth`, `roi_calculation`, `manual`). Partial upstream service failures (e.g., L5 truths down) degrade gracefully with explicit `SourceAvailability` indicators rather than failing the entire screen.
- **Immutable Submission Snapshots:** When triggering generation, the exact draft and scope are captured into a frozen snapshot (`createImmutableSubmissionSnapshot`) to ensure mutations reconcile against the exact submission context even if UI inputs change during generation.

### E. Query Key Partitioning & Mutation Cache Reconciliation (`valueCaseKeys.ts`, `useValueCaseJourney.ts`)
- **Key Partitioning:** Query keys follow `["value-case", "scope" | "versions", fabricTenantId, accountId, ...]`.
- **Exact Cache Reconciliation:** On mutation success (`generateCase`, `publishCase`), the query client updates the exact scope cache key (`valueCaseKeys.scope(submissionScope)`) and invalidates with `{ exact: true }`, preventing inadvertent invalidation of other tenant or account caches.

### F. DTO-Free Presentation View-Models & Architecture Barrier
- Presentational components (`ValueCaseWorkspace`, `ValueCaseMetrics`, `ValueCaseResult`, `ValueCaseVersionHistory`, `ValueCaseGenerationPanel`) never consume raw API DTOs.
- Components exclusively consume formatted view-models (`ValueCaseResultViewModel`, `ValueCaseMetricCardViewModel`, `ValueCaseVersionSummaryViewModel`, `ValueCaseVersionDiffViewModel`) produced by `valueCaseViewModels.ts`.
- **Architecture Barrier Enforcement:** A dedicated static analysis test (`ValueCaseArchitectureBarrier.test.ts`) inspects all files under `components/` and `presentation/` to assert that no raw transport DTOs or API schema types are imported directly.

---

## 3. Directory Layout

```
apps/web/src/features/value-case/
├── api/
│   ├── valueCaseSchemas.ts        # Zod schemas & ValueCaseBoundaryError
│   └── valueCaseApi.ts            # Typed validated HTTP endpoints
├── domain/
│   ├── valueCaseModels.ts         # Immutable domain models & ValueCaseScope
│   ├── valueCaseAdapters.ts       # DTO ↔ Domain transformation adapters
│   └── generationInputs.ts        # Deterministic input aggregation & snapshots
├── queries/
│   ├── valueCaseKeys.ts           # Scoped TanStack query key factory
│   └── useValueCaseJourney.ts     # Master feature hook orchestrating the slice
├── presentation/
│   └── valueCaseViewModels.ts     # View-model transformers and formatters
├── components/
│   ├── ValueCaseWorkspace.tsx     # Main workspace & lifecycle state container
│   ├── ValueCaseMetrics.tsx       # Responsive 3-year value/ROI/payback cards
│   ├── ValueCaseResult.tsx        # Value case narrative & artifact viewer
│   ├── ValueCaseVersionHistory.tsx# Version selector and metric diff summary
│   ├── ValueCaseGenerationPanel.tsx # Input review & editing sheet
│   └── index.ts                   # Component exports
├── __tests__/
│   ├── valueCaseSchemas.test.ts
│   ├── valueCaseAdapters.test.ts
│   ├── generationInputs.test.ts
│   ├── valueCaseCacheReconciliation.test.ts
│   ├── valueCaseViewModels.test.ts
│   ├── ValueCaseComponents.test.tsx
│   ├── hostileIdentitySwitch.test.tsx
│   └── ValueCaseArchitectureBarrier.test.ts
└── index.ts                       # Public feature slice exports
```

---

## 4. Verification Suite

| Test Suite | Purpose |
|---|---|
| `valueCaseSchemas.test.ts` | Asserts Zod validation rules and error normalization |
| `valueCaseAdapters.test.ts` | Asserts bidirectional DTO ↔ Domain transformations and identity checks |
| `generationInputs.test.ts` | Asserts sorting, deduplication, top-5 limits, and provenance tracking |
| `valueCaseCacheReconciliation.test.ts` | Asserts exact scope cache partitioning and invalidation |
| `valueCaseViewModels.test.ts` | Asserts view-model formatting and metric difference calculations |
| `ValueCaseComponents.test.tsx` | Asserts component rendering, empty states, and user interactions |
| `hostileIdentitySwitch.test.tsx` | Asserts multi-tenant cross-account isolation and unauthorized access denial |
| `ValueCaseArchitectureBarrier.test.ts` | Static linting barrier ensuring UI components never import transport DTOs |
