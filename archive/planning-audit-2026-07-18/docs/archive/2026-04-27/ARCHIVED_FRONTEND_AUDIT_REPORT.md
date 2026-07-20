---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: Temporal frontend audit - synthesis supersedes
Modern Equivalent: See ROADMAP.md for current status
Status: Historical reference only
---

# Frontend UI Audit Report — Route Integrity, API Coverage, and Strategic Constitution

**Audit Date:** 2026-04-26
**Scope:** `frontend/` directory, `contracts/`, `contract.md`, `DEPRECATIONS.md`, `eslint-plugin-fabric-contracts/`, `examples/canonical/`
**Method:** Cold-start structural analysis — no assumptions about builder intent

---

## Executive Summary

The Fabric 4L frontend is a substantial React/TypeScript SPA with **157 routes** (82 authenticated, 3 public, 72 redirects), **42 page components**, and **47 custom hooks**. The codebase has strong foundational patterns (tiered auth guards, error boundaries, lazy loading, Zod-validated API client) but suffers from three systemic problems:

1. **Massive backend-frontend integration gap** — 50+ DIL backend endpoints have zero frontend hooks, types, or UI surfaces
2. **Orphan and mock-dependent pages** — At least 6 pages render hardcoded/mock data with no backend connection
3. **Missing strategic constitution** — The existing `contract.md` defines 6 canonical contracts but none govern the frontend-backend API boundary, type synchronization, or hook architecture

The net effect: the frontend presents a visually complete application shell, but approximately **40% of pages are non-functional facades** that either render static data, use hardcoded mocks, or connect to workspace hooks that generate data via a single generic endpoint rather than the purpose-built DIL services.

---

## Part 1: Incomplete and Inconsistent Routes

### 1.1 Orphan Pages — Files That Exist But Are Not Routed

| Page File | Status | Issue |
|-----------|--------|-------|
| `OntologyBrowser.tsx` | Orphan | Exists as a file, exported, but **never imported in App.tsx**. Zero references in router. |
| `ValueTreeExplorer.tsx` | Orphan | Exists as a file, exported, but **never imported in App.tsx**. Zero references in router. |
| `Home.tsx` | Orphan | Exists but `/home` route renders `ValueNarrativeHome`, not `Home`. Dead code. |

### 1.2 Mock-Dependent Pages — Routes That Render Fake Data

| Route | Page | Evidence |
|-------|------|----------|
| `/context/sources` | `SourceConfiguration.tsx` | Uses `MOCK_SOURCES` array (line 57). Delete/Add buttons show `alert('coming soon')`. |
| `/context/formulas/new` | `FormulaBuilder.tsx` | Contains `// Constants & Mock Data` section (line 50). No API calls. |
| `/model/value-studio/*` (6 stages) | `Stage1Discovery.tsx` through `Stage6Tracking.tsx` | **Zero API calls** across all 6 files (1,955 lines total). All data is hardcoded or prop-drilled from static state. |

### 1.3 Facade Pages — Routes That Render But Don't Connect to Their Backend

| Route | Page | Backend Exists? | Frontend Hook? | Gap |
|-------|------|----------------|----------------|-----|
| `/intelligence/:accountId/signals` | `SignalsTab.tsx` | L4 `/v1/accounts/{id}/signals` | `useWorkspaceTabQuery` (generic) | Uses generic workspace query, not the dedicated signals endpoint |
| `/intelligence/:accountId/drivers` | `DriversTab.tsx` | L4 `/v1/analysis/whitespace` | `useWorkspaceTabQuery` (generic) | Same generic pattern |
| `/intelligence/:accountId/evidence` | `EvidenceTab.tsx` | L3 `/v1/evidence/*` (DIL) | `useWorkspaceTabQuery` (generic) | Does NOT connect to the Evidence Library API |
| `/intelligence/:accountId/stakeholders` | `StakeholdersTab.tsx` | L4 `/v1/enrichment/*` (DIL) | `useWorkspaceTabQuery` (generic) | Does NOT connect to the Enrichment API |
| `/studio/:accountId/action-plan` | `ActionPlanTab.tsx` | L4 `/v1/value-hypotheses/*` (DIL) | `useWorkspaceTabQuery` (generic) | Does NOT connect to Value Hypothesis Engine |
| `/studio/:accountId/value-model` | `ValueModelTab.tsx` | L3 `/v1/roi/*` (DIL) | `useWorkspaceTabQuery` (generic) | Does NOT connect to ROI Calculator |
| `/studio/:accountId/narrative` | `NarrativeTab.tsx` | L4 `/v1/narratives/*` (DIL) | `useWorkspaceTabQuery` (generic) | Does NOT connect to Narrative Builder |
| `/deliverables/views/cfo` | `BusinessCase.tsx` | Distinct view needed | Renders same `BusinessCase` | CFO, Executive, Technical views all render identical component |
| `/deliverables/views/executive` | `BusinessCase.tsx` | Distinct view needed | Renders same `BusinessCase` | No role-specific rendering logic |
| `/deliverables/views/technical` | `BusinessCase.tsx` | Distinct view needed | Renders same `BusinessCase` | No role-specific rendering logic |

### 1.4 Navigation Ghost — Nav Entry Without Route

| Nav Entry | Expected Route | Actual Route | Issue |
|-----------|---------------|--------------|-------|
| Deliverables → Embeds | `/deliverables/embeds` | Does not exist | TieredNav renders the link, but App.tsx has no matching `<Route>`. Clicking produces a 404/NotFound. |

### 1.5 Redirect Loops and Self-Referencing Routes

| Route | Redirects To | Issue |
|-------|-------------|-------|
| `/context/ontology` | `/context/ontology` | Self-redirect. Should redirect to `/context/ontology/entities` or render a landing page. |
| `/model/value-studio/discovery` | `WorkspaceContextRedirect` → `/studio/:accountId/action-plan` | Redirects to a different workspace entirely (studio action-plan, not discovery). Semantic mismatch. |
| `/model/value-studio/mapping` | `WorkspaceContextRedirect` → `/studio/:accountId/action-plan` | Same issue — mapping redirects to action-plan. |

### 1.6 Duplicate Route Patterns

The router contains **two parallel workspace systems** that have not been reconciled:

| System | Routes | Pages | Status |
|--------|--------|-------|--------|
| **Old: Value Studio Stages** | `/model/value-studio/{discovery,mapping,modeling,validation,narrative,tracking}` | `Stage1Discovery.tsx` through `Stage6Tracking.tsx` | 6 pages, 0 API calls, all static. Now redirected to new system. |
| **New: Intelligence + Studio Tabs** | `/intelligence/:accountId/{signals,drivers,evidence,stakeholders}` + `/studio/:accountId/{action-plan,value-model,narrative}` | Tab components using `useWorkspaceTabQuery` | Active but uses generic workspace endpoint, not DIL services. |

The old Value Studio stages are dead code — they exist as 1,955 lines of static UI that are only reached via redirects to the new system. They should be removed per the deprecation strategy.

---

## Part 2: Backend API Endpoints with Zero Frontend Integration

### 2.1 DIL Endpoints — Complete Backend, Zero Frontend

All 9 DIL services (built in Phases 1-3) have fully functional backend APIs but **no frontend hooks, types, query keys, or UI surfaces**.

| Backend Service | Layer | Endpoint Prefix | Endpoints | Frontend Hook | Frontend Type | Frontend Page |
|----------------|-------|-----------------|-----------|---------------|---------------|---------------|
| Product Portfolio | L3 | `/v1/products` | 8 | None | None | None |
| Evidence Library | L3 | `/v1/evidence` | 7 | None | None | None |
| Competitive Intel | L3 | `/v1/competitive-intel` | 10 | None | None | None |
| ROI Calculator | L3 | `/v1/roi` | 8 | None | None | None |
| Enrichment Pipeline | L4 | `/v1/enrichment` | 4 | None | None | None |
| Value Hypothesis Engine | L4 | `/v1/value-hypotheses` | 6 | None | None | None |
| Narrative Builder | L4 | `/v1/narratives` | 5 | None | None | None |
| Intelligence Orchestrator | L4 | `/v1/intelligence` | 4 | None | None | None |
| **Total** | | | **52** | **0** | **0** | **0** |

### 2.2 Pre-Existing Backend Endpoints Missing Frontend Hooks

Beyond DIL, several pre-existing backend endpoints also lack dedicated frontend integration:

| Backend Endpoint | Layer | Frontend Status |
|-----------------|-------|-----------------|
| `/v1/agents/roi-calculation` | L4 | No dedicated hook (only via generic workflow submission) |
| `/v1/analysis/whitespace` | L4 | No dedicated hook |
| `/v1/checkpoints/*` | L4 | No hook |
| `/v1/state-inspector/*` | L4 | No hook |
| `/v1/health-badges/*` | L4 | No hook |
| `/v1/feature-flags/*` | L4 | No hook |

### 2.3 OpenAPI Specification Gaps

| Spec File | Total Paths | DIL Paths | Coverage |
|-----------|-------------|-----------|----------|
| `layer3-knowledge.json` | 79 | 1 (only `/v1/agents/roi-calculation`) | **1.3%** of DIL endpoints documented |
| `layer4-agents.json` | 72 | 0 | **0%** of DIL endpoints documented |

The OpenAPI specs have not been updated to include any of the 52 DIL endpoints. This means:
- No automated TypeScript type generation is possible for DIL
- No contract testing between frontend and backend
- No API documentation for frontend developers

---

## Part 3: Type System Fragmentation

### 3.1 Dual Type Definition Files

| File | Lines | Purpose | Maintenance |
|------|-------|---------|-------------|
| `api/types.ts` | 128 | "Contract-Aligned Type Definitions" — manually maintained | Header says "validated against Zod" but no Zod schemas exist for these types |
| `types/api.ts` | 296 | Runtime DTO types with manual parsers (`parseEntityResults`, etc.) | Contains hand-written parser functions instead of Zod schemas |

These two files serve overlapping purposes with no clear boundary. Neither file contains any DIL-related types.

### 3.2 Hook-Local Type Definitions

Many hooks define their own types inline rather than importing from a shared contract:

| Hook | Local Types Defined |
|------|-------------------|
| `useAccounts.ts` | `Account`, `Opportunity`, `AccountActivity`, `Interaction`, `SyncStatus`, `CRMProvider` |
| `useWorkflows.ts` | Workflow types defined locally |
| `useBusinessCases.ts` | Business case types defined locally |
| `useIngestion.ts` | Ingestion job types defined locally |

This creates a pattern where the same backend entity (e.g., `Account`) has different type shapes depending on which hook you import from.

### 3.3 Missing Type Generation Pipeline

There is **no OpenAPI-to-TypeScript generation pipeline**. The comment in `api/types.ts` states:

> "These types are manually maintained to align with the OpenAPI specs."

This is a manual synchronization process that will inevitably drift, especially as 52 new DIL endpoints need types.

---

## Part 4: Strategic Constitution Gaps

### 4.1 What Exists (contract.md)

The existing `contract.md` defines 6 canonical contracts with clear status tracking:

| Contract | Status | Enforcement Date |
|----------|--------|-----------------|
| 2.1 Tenant Context Propagation | Proposed | 2026-06-23 |
| 2.2 DB Session and Isolation | Ratified | 2026-06-23 |
| 2.3 Middleware and Auth Flow | Ratified | 2026-06-23 |
| 2.4 Tool Invocation Boundary | Proposed | 2026-06-23 |
| 2.5 Agent Output Shape | Proposed | 2026-06-23 |
| 2.6 UI State Progression | Proposed | 2026-06-23 |

The ESLint plugin (`eslint-plugin-fabric-contracts`) exists with 12 rules, and the frontend `.eslintrc.js` references it. The `DEPRECATIONS.md` tracks 11 anti-patterns with instance counts. The `examples/canonical/ui/` directory contains `guards.ts` and `route-manifest.ts`.

### 4.2 What Is Missing — The Seven Absent Contracts

The following contracts are **not defined anywhere** in the codebase but are required for the frontend-backend integration to function as a governed system:

#### Missing Contract 1: Frontend-Backend API Type Synchronization

**Problem:** Types are manually maintained in two separate files with no generation pipeline. 52 new DIL endpoints have zero type coverage.

**What the contract should define:**
- Single source of truth for API types (OpenAPI spec → generated TypeScript)
- Automated generation pipeline (e.g., `openapi-typescript` or `orval`)
- CI gate: generated types must match backend OpenAPI spec
- Prohibition on hand-written API types outside the generated file
- Zod schema generation for runtime validation

#### Missing Contract 2: Hook Architecture and Naming Convention

**Problem:** Hooks are inconsistently organized. Some use `useWorkspaceTabQuery` (generic), others use dedicated hooks (`useAccounts`). No naming convention exists.

**What the contract should define:**
- One hook per backend service (e.g., `useProducts`, `useCompetitiveIntel`, `useROI`)
- Naming convention: `use{Entity}` for queries, `use{Action}{Entity}` for mutations
- Query key namespace convention (currently `QK` object, but no DIL keys exist)
- Cache invalidation rules per mutation
- Error handling pattern (currently `console.error` in `onError` — no user-facing feedback)

#### Missing Contract 3: Query Key Registry

**Problem:** `queryKeys.ts` defines keys for existing features but has **zero entries** for any DIL service. There is no convention for how new services register their keys.

**What the contract should define:**
- Mandatory query key registration for every backend service
- Hierarchical key structure matching the backend service topology
- Invalidation dependency graph (e.g., enriching an account should invalidate intelligence briefing)

#### Missing Contract 4: Page Lifecycle Contract

**Problem:** Pages have wildly inconsistent lifecycle patterns. Some have loading states, error handling, and skeleton views. Others render static data. The Value Studio stages have zero API integration.

**What the contract should define:**
- Every authenticated page MUST have: loading skeleton, error state, empty state
- Pages MUST use React Query for server state (not local state or Zustand for API data)
- Pages MUST NOT contain hardcoded mock data (SourceConfiguration, FormulaBuilder violate this)
- Pages MUST connect to their corresponding backend service via a dedicated hook

#### Missing Contract 5: Workspace Data Flow Contract

**Problem:** The Intelligence and Studio workspaces use a single generic endpoint (`useWorkspaceTabQuery` → `GET /analysis/cases/{caseId}/workspace/{tab_key}`) for all data. This bypasses the purpose-built DIL services entirely.

**What the contract should define:**
- Workspace tabs MUST fetch from their dedicated backend service
- The generic workspace endpoint is for persistence/caching only, not primary data source
- Data flow: DIL Service → Hook → Tab Component (not: Generic Endpoint → Tab Component)
- Workspace generation (`POST /workspace/generate`) should orchestrate DIL services, not replace them

#### Missing Contract 6: Feature Flag and Tier Gating Contract

**Problem:** The `AuthenticatedRoute` wrapper accepts a `requiredTier` prop, and `RouteGuard` checks it. But there is no contract defining which features belong to which tier, and the tier gating is not connected to backend feature flags.

**What the contract should define:**
- Tier-to-feature mapping table (which DIL features are Standard vs Advanced vs Admin)
- Backend feature flag synchronization (L4 has `/v1/feature-flags/*` but frontend doesn't use it)
- Graceful degradation pattern when a feature is tier-gated
- Navigation spine filtering based on tier (TieredNav exists but tier filtering is incomplete)

#### Missing Contract 7: Error Shape and User Feedback Contract

**Problem:** The API client transforms errors into `ApiError` objects with `trace_id`, but hooks handle errors with `console.error` only. No user-facing error feedback pattern exists.

**What the contract should define:**
- Backend error shape: `{ message, code, trace_id, details }` (already defined in `api/types.ts`)
- Frontend error display: toast notifications for mutations, inline error states for queries
- Error categorization: retryable vs fatal vs auth-expired
- Trace ID display pattern for support escalation (ErrorBoundary already does this, but hooks don't)

---

## Part 5: Inconsistency Catalog

### 5.1 State Management Boundary Violations

| Pattern | Where | Issue |
|---------|-------|-------|
| Zustand for server state | `ingestionStore.ts`, `entityStore.ts` | Server state should be in React Query, not Zustand |
| React Query for UI state | Some hooks manage UI state via query params | UI state should be in Zustand or component state |
| Dual state for same data | `accountContextStore.ts` + `useAccounts` hook | Account data exists in both Zustand store and React Query cache |

### 5.2 Navigation Pattern Violations

The `DEPRECATIONS.md` tracks 56 instances of imperative navigation (`router.push()`) and 34 instances of URL string concatenation. The ESLint rules `no-imperative-navigation` and `no-url-concatenation` are set to `"error"` but the violations persist, suggesting either:
- The ESLint plugin is not running in CI
- The rules have exceptions/overrides not visible in the config

### 5.3 Duplicate Workspace Systems

| System | Files | Lines | API Integration | Status |
|--------|-------|-------|----------------|--------|
| Value Studio Stages (old) | 8 files | 1,955 | None | Dead code — redirects to new system |
| Intelligence + Studio Tabs (new) | 7 files | ~2,100 | Generic workspace endpoint only | Active but not connected to DIL |

The old system should be deleted. The new system should be connected to DIL services.

---

## Part 6: Strategic Recommendations

### Recommendation 1: Establish the Frontend-Backend API Contract (Highest Priority)

Add a **7th canonical contract** to `contract.md`:

> **Contract 2.7: Frontend-Backend API Synchronization**
>
> All API types are generated from OpenAPI specifications. No hand-written API types are permitted. The generation pipeline runs in CI and blocks merges when types drift.

**Deliverables:**
1. Update L3 and L4 OpenAPI specs to include all 52 DIL endpoints
2. Install `openapi-typescript` and generate `api/generated-types.ts`
3. Create CI gate: `npm run generate:types && git diff --exit-code`
4. Deprecate `api/types.ts` and `types/api.ts` in favor of generated types

### Recommendation 2: Build the DIL Hook Layer

Create 8 new hooks matching the 8 DIL backend services:

| Hook | Backend Service | Query Keys |
|------|----------------|------------|
| `useProducts.ts` | L3 `/v1/products` | `QK.products.*` |
| `useEvidenceLibrary.ts` | L3 `/v1/evidence` | `QK.evidenceLibrary.*` |
| `useCompetitiveIntel.ts` | L3 `/v1/competitive-intel` | `QK.competitiveIntel.*` |
| `useROICalculator.ts` | L3 `/v1/roi` | `QK.roi.*` |
| `useEnrichment.ts` | L4 `/v1/enrichment` | `QK.enrichment.*` |
| `useValueHypotheses.ts` | L4 `/v1/value-hypotheses` | `QK.valueHypotheses.*` |
| `useNarratives.ts` | L4 `/v1/narratives` | `QK.narratives.*` |
| `useIntelligence.ts` | L4 `/v1/intelligence` | `QK.intelligence.*` |

### Recommendation 3: Connect Workspace Tabs to DIL Services

Refactor the 7 workspace tab components to fetch from DIL services instead of the generic workspace endpoint:

| Tab | Current Source | Target Source |
|-----|---------------|---------------|
| `SignalsTab` | `useWorkspaceTabQuery("signals")` | `useAccountSignals(accountId)` |
| `DriversTab` | `useWorkspaceTabQuery("drivers")` | `useValueHypotheses(accountId)` |
| `EvidenceTab` | `useWorkspaceTabQuery("evidence")` | `useEvidenceLibrary({ account_id })` |
| `StakeholdersTab` | `useWorkspaceTabQuery("stakeholders")` | `useEnrichment(accountId)` |
| `ActionPlanTab` | `useWorkspaceTabQuery("action-plan")` | `useValueHypotheses(accountId)` + `useIntelligence.dealReadiness(accountId)` |
| `ValueModelTab` | `useWorkspaceTabQuery("value-model")` | `useROICalculator(accountId)` |
| `NarrativeTab` | `useWorkspaceTabQuery("narrative")` | `useNarratives(accountId)` |

### Recommendation 4: Delete Dead Code

| Target | Lines | Reason |
|--------|-------|--------|
| `pages/value-studio/Stage1-6*.tsx` | 1,955 | Dead code — all routes redirect to new workspace system |
| `pages/value-studio/ValueStudioShell.tsx` | ~200 | Only used by dead Stage pages |
| `pages/Home.tsx` | ~100 | Orphan — `/home` renders `ValueNarrativeHome` |
| `pages/OntologyBrowser.tsx` | ~200 | Orphan — not imported in App.tsx |
| `pages/ValueTreeExplorer.tsx` | ~200 | Orphan — not imported in App.tsx |
| Mock data in `SourceConfiguration.tsx` | ~50 | Replace with API integration |
| Mock data in `FormulaBuilder.tsx` | ~30 | Replace with API integration |

### Recommendation 5: Fix Broken Routes

| Route | Fix |
|-------|-----|
| `/deliverables/embeds` | Either add a route in App.tsx or remove from TieredNav |
| `/context/ontology` self-redirect | Redirect to `/context/ontology/entities` |
| `/deliverables/views/{cfo,executive,technical}` | Create role-specific view components or pass a `viewMode` prop to BusinessCase |

### Recommendation 6: Enforce ESLint in CI

Verify that the `eslint-plugin-fabric-contracts` rules are actually running in CI. The `DEPRECATIONS.md` reports 56 imperative navigation violations and 34 URL concatenation violations, but the ESLint config sets these to `"error"`. Either:
- The plugin is not installed (check `node_modules/eslint-plugin-fabric-contracts`)
- CI does not run `eslint`
- The violations are in files excluded by `ignorePatterns`

---

## Appendix A: Complete Route Inventory

**Total Routes:** 157
- Authenticated: 82
- Public: 3 (login, login/callback, signup)
- Redirects: 72

**Pages with API integration:** 10 of 42 (24%)
**Pages with loading states:** 36 of 42 (86%)
**Pages with error handling:** 33 of 42 (79%)
**Pages with zero API calls:** 31 of 42 (74%)
**Hooks with DIL integration:** 0 of 47 (0%)
**DIL endpoints with frontend types:** 0 of 52 (0%)
**OpenAPI DIL coverage:** 1 of 52 (1.9%)

## Appendix B: Contract Status Matrix

| Contract | Defined? | Ratified? | Enforced? | CI Gate? |
|----------|----------|-----------|-----------|----------|
| 2.1 Tenant Context | Yes | No (proposed) | No | No |
| 2.2 DB Session/RLS | Yes | Yes | Partial | No |
| 2.3 Middleware/Auth | Yes | Yes | Partial | No |
| 2.4 Tool Invocation | Yes | No (proposed) | No | No |
| 2.5 Agent Output | Yes | No (proposed) | No | No |
| 2.6 UI State Progression | Yes | No (proposed) | No | ESLint rules exist but may not run |
| **2.7 API Type Sync** | **No** | **No** | **No** | **No** |
| **2.8 Hook Architecture** | **No** | **No** | **No** | **No** |
| **2.9 Query Key Registry** | **No** | **No** | **No** | **No** |
| **2.10 Page Lifecycle** | **No** | **No** | **No** | **No** |
| **2.11 Workspace Data Flow** | **No** | **No** | **No** | **No** |
| **2.12 Feature/Tier Gating** | **No** | **No** | **No** | **No** |
| **2.13 Error Shape/Feedback** | **No** | **No** | **No** | **No** |

---

## Document Metadata

| Field | Value |
|-------|-------|
| Author | Security Auditor (cold-start) |
| Date | 2026-04-26 |
| Scope | Frontend UI, API contracts, strategic constitution |
| Files Examined | 157 routes, 42 pages, 47 hooks, 2 type files, 6 contracts, 12 ESLint rules |
| Findings | 3 orphan pages, 6 mock-dependent pages, 10 facade pages, 1 nav ghost, 52 unintegrated endpoints, 7 missing contracts |
