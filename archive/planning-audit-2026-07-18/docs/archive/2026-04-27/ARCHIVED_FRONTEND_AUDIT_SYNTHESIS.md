---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: Temporal frontend synthesis
Modern Equivalent: See ROADMAP.md for current status
Status: Historical reference only
---

# Frontend Audit Synthesis: Analysis of `/frontend/audit-output`

**Date:** 2026-04-26  
**Scope:** Complete analysis of 17 documents across the Tri-Track Audit and 6-File Frontend Design Brief  
**Purpose:** Establish the definitive list of incomplete/inconsistent routes and define the missing strategic constitution

---

## 1. Document Corpus Overview

The `frontend/audit-output` directory contains 17 artifacts produced by a forensic frontend-backend integration analysis:

| Category | Files | Purpose |
|----------|-------|---------|
| **Executive Layer** | `executive-summary.md`, `design-brief-plans.md` | Strategic framing and methodology |
| **Track A (Surface)** | `track-a-route-matrix.md`, `track-a-route-matrix.csv`, `track-a-route-extraction.json`, `track-a-hook-analysis.json` | Route-level data source classification |
| **Track B (API)** | `track-b-openapi-analysis.json`, `track-b-orphan-registry.md` | Backend endpoint orphan inventory |
| **Track C (Contracts)** | `track-c-contract-gaps.md` | Contract compliance evaluation |
| **Design Brief (6 docs)** | `01` through `06` + `plan.md` + `fabric4l.agent.outline.md` | Prescriptive recovery architecture |

---

## 2. The Core Problem: Systemic Integration Failure

The audit reveals a **systemic disconnection** between a visually complete frontend and a functionally rich backend. This is not a "features are missing" problem — it is an **architectural governance failure** where both sides of the stack were built independently without binding contracts.

### Quantified State

| Metric | Value | Implication |
|--------|-------|-------------|
| Total frontend routes | 154 | Large surface area |
| Authenticated routes | 84 | User-facing functional scope |
| Routes with live backend integration (GREEN) | 16 (19%) | Only 1 in 5 routes actually works |
| Routes rendering mock/hardcoded data (RED) | 51 (33%) | One-third of the app is a facade |
| Legacy redirect routes | 70 (45%) | Nearly half the routes just redirect |
| Unevaluated routes (UNKNOWN) | 17 (11%) | Status indeterminate |
| **Facade rate** | **81%** | 68 of 84 authenticated routes non-functional |
| Total backend endpoints | 244 | Significant backend investment |
| Endpoints consumed by frontend | 8 (3.3%) | Almost nothing is wired |
| **Orphan endpoints** | **236 (96.7%)** | Backend capabilities with zero UI surface |

---

## 3. Incomplete and Inconsistent Routes — Definitive List

### 3.1 RED Routes: Confirmed Non-Functional (51 routes)

These routes render hardcoded data, mock objects, or have no backend connection whatsoever.

**Intelligence Workspace (16 routes):**

| Route | Component | Issue |
|-------|-----------|-------|
| `/intelligence` | WorkspaceContextRedirect | Redirect shell, no data surface |
| `/intelligence/:accountId` | AccountContextSync | Context sync only, no data fetch |
| `/intelligence/:accountId/signals` | AccountContextSync | No signal data integration |
| `/intelligence/:accountId/drivers` | AccountContextSync | No driver data integration |
| `/intelligence/:accountId/evidence` | AccountContextSync | No evidence data integration |
| `/intelligence/:accountId/stakeholders` | AccountContextSync | No stakeholder data integration |
| `/intelligence/signals` | WorkspaceContextRedirect | Redirect, no data |
| `/intelligence/drivers` | WorkspaceContextRedirect | Redirect, no data |
| `/intelligence/evidence` | WorkspaceContextRedirect | Redirect, no data |
| `/intelligence/stakeholders` | WorkspaceContextRedirect | Redirect, no data |

**Value Studio (8 routes):**

| Route | Component | Issue |
|-------|-----------|-------|
| `/model/value-studio` | WorkspaceContextRedirect | Redirect shell |
| `/model/value-studio/discovery` | WorkspaceContextRedirect | Hardcoded tab label |
| `/model/value-studio/explorer` | WorkspaceContextRedirect | Hardcoded tab label |
| `/model/value-studio/mapping` | WorkspaceContextRedirect | Hardcoded tab label |
| `/model/value-studio/modeling` | WorkspaceContextRedirect | Hardcoded tab label |
| `/model/value-studio/narrative` | WorkspaceContextRedirect | Hardcoded tab label |
| `/model/value-studio/tracking` | WorkspaceContextRedirect | Hardcoded tab label |
| `/model/value-studio/validation` | WorkspaceContextRedirect | Hardcoded tab label |

**Settings & Governance (15 routes):**

| Route | Component | Issue |
|-------|-----------|-------|
| `/settings/access/keys` | PermissionsAdmin | No backend hook |
| `/settings/access/roles` | PermissionsAdmin | No backend hook |
| `/settings/access/teams` | PermissionsAdmin | No backend hook |
| `/settings/content/approvals` | FormulaGovernance | No backend hook |
| `/settings/content/formulas` | FormulaGovernance | No backend hook |
| `/settings/content/versions` | FormulaGovernance | No backend hook |
| `/settings/system/billing/*` | BillingRoute | Hooks exist but not wired to route |

**Other RED routes (12 routes):**

| Route | Component | Issue |
|-------|-----------|-------|
| `/command-center` | CommandCenter | No backend endpoint exists |
| `/home` | ValueNarrativeHome | Static landing, no data |
| `/context/sources` | SourceConfiguration | `useSources` serves mock data |
| `/context/ontology/entities/:entityId` | EntityDetail | No hook wired |
| `/deliverables/calculators` | InteractiveBusinessCase | No backend endpoint |

### 3.2 UNKNOWN Routes: Unverified Integration (17 routes)

These routes have hooks registered but endpoint coverage is unconfirmed — they may be partially functional or entirely facade.

| Route | Component | Hook | Concern |
|-------|-----------|------|---------|
| `/context/agents` | AgentWorkflows | useWorkflows | 9 orphan workflow endpoints unconnected |
| `/context/formulas/:formulaId` | FormulaBuilder | useFormula | Evaluation endpoints not wired |
| `/context/formulas/new` | FormulaBuilder | useFormula | Creation flow unverified |
| `/context/ingestion/jobs` | IngestionJobs | useIngestion | Backend binding unconfirmed |
| `/context/ontology` | OntologyEditor | useOntology | 14 orphan ontology endpoints |
| `/deliverables/cases` | BusinessCaseList | useBusinessCases | Endpoint binding unverified |
| `/deliverables/cases/:caseId` | BusinessCase | useBusinessCases | Detail view unverified |
| `/deliverables/views/cfo` | BusinessCase | useBusinessCases | Rendering endpoint unverified |
| `/deliverables/views/executive` | BusinessCase | useBusinessCases | Rendering endpoint unverified |
| `/deliverables/views/technical` | BusinessCase | useBusinessCases | Rendering endpoint unverified |
| `/governance/audit/changes` | DecisionTrace | useProvenance | Ground truth endpoints unconnected |
| `/governance/audit/log` | DecisionTrace | useProvenance | Ground truth endpoints unconnected |
| `/governance/compliance` | DecisionTrace | useProvenance | Ground truth endpoints unconnected |
| `/governance/evidence` | DecisionTrace | useProvenance | Ground truth endpoints unconnected |
| `/governance/integrity` | DecisionTrace | useProvenance | Ground truth endpoints unconnected |
| `/governance/provenance` | DecisionTrace | useProvenance | Ground truth endpoints unconnected |
| `/governance/traces` | DecisionTrace | useProvenance | Ground truth endpoints unconnected |

### 3.3 Inconsistency Patterns Across GREEN Routes

Even the 16 GREEN routes exhibit inconsistencies:

| Inconsistency | Evidence | Impact |
|---------------|----------|--------|
| **Query key conventions** | Three competing patterns: `billingKeys.subscription()`, `QK.entities.list()`, raw string arrays | Cache invalidation unreliable |
| **Error handling** | 15+ different patterns across 47 hooks | Unpredictable user experience |
| **Cache configuration** | Majority use React Query defaults; no standard stale time | Over-fetching or stale data |
| **Tenant context** | Not all hooks validate tenant before request | Potential cross-tenant data leakage |
| **Type safety** | Multiple hooks use `any` types; no generated types | Runtime type errors in production |
| **Loading states** | No skeleton system; each page handles loading differently | Inconsistent perceived performance |

---

## 4. The Backend Orphan Crisis by Layer

The 236 orphan endpoints represent massive backend investment with zero user-facing value:

| Layer | Total Endpoints | Connected | Orphan | Orphan Rate |
|-------|----------------|-----------|--------|-------------|
| Layer 1 (Ingestion) | 26 | 0 | 26 | 100% |
| Layer 2 (Extraction) | 29 | 7 | 22 | 75.9% |
| Layer 3 (Knowledge) | 89 | 1 | 88 | 98.9% |
| Layer 4 (Agents) | 84 | 0 | 84 | 100% |
| Layer 5 (Ground Truth) | 13 | 0 | 13 | 100% |
| Signals | 3 | 0 | 3 | 100% |

**Critical observation:** The entire Data Intelligence Layer (52 endpoints across L3/L4) that we just built has zero frontend surface. Every product, evidence, competitive intel, ROI, value hypothesis, narrative, enrichment, and intelligence endpoint is orphaned.

---

## 5. The Missing Strategic Constitution

The audit identifies **9 contracts** that should govern the system — 6 canonical (from CONTRACT.md) and 3 missing. The compliance picture is dire:

### 5.1 Canonical Contract Status

| Contract | Status | Compliance | Critical Gap |
|----------|--------|------------|--------------|
| 2.1 Tenant Context Propagation | Proposed | 60% | Not all hooks validate tenant; no hook-level enforcement |
| 2.2 DB Session and Isolation | Ratified | 80% | Frontend transparent (backend enforces) |
| 2.3 Middleware and Auth Flow | Ratified | 90% | Rate limiting not surfaced to UI |
| 2.4 Tool Invocation Boundary | Proposed | 30% | **No frontend ToolRegistry exists** |
| 2.5 Agent Output Shape | Proposed | 40% | **Agent outputs not typed in frontend** |
| 2.6 UI State Progression | Proposed | 70% | Some server state outside React Query |

### 5.2 Three Missing Contracts (Not Yet Defined)

**Missing Contract A: API Boundary Contract (CRITICAL)**

> Defines the standardized rules for how every frontend hook communicates with every backend endpoint — error handling, pagination, filtering, sorting, retry policies, and response shape normalization.

**Current state:** 47 hooks with 15+ different error handling patterns. No standard pagination. No standard filtering. Each hook reinvents the wheel.

**Missing Contract B: Type Synchronization Contract (CRITICAL)**

> Mandates automated OpenAPI-to-TypeScript generation with CI gates that fail builds when schemas drift.

**Current state:** All frontend types are manually maintained. Multiple hooks use `any`. No generation pipeline exists. The 244 backend endpoints have formal Pydantic/Zod schemas that are never consumed by the frontend.

**Missing Contract C: Hook Architecture Contract (HIGH)**

> Standardizes React Query patterns — query key naming, cache policies, mutation handling, optimistic updates, and the three-tier hook hierarchy.

**Current state:** Three competing query key conventions. No optimistic updates anywhere. No standard cache policies. No tier separation between HTTP mechanics, domain logic, and page composition.

---

## 6. Strategic Approach and Recovery Framework

The design brief proposes a **Contract-First Recovery Methodology** with a single north star metric:

> **Functional Route Percentage (FRP)** = GREEN authenticated routes / total authenticated routes

**Current FRP: 19% (16/84)**

### 6.1 Phased Recovery Plan

| Phase | Sprints | FRP Target | Key Deliverables |
|-------|---------|------------|------------------|
| **Phase 1: Kill the Mocks** | 1–3 | 35% (+13 routes) | Wire Accounts, AgentWorkflows, HealthMonitor, OntologyEditor, EntityDetail, IngestionJobs |
| **Phase 2: Endpoint Adoption** | 4–8 | 60% (+21 routes) | Formulas, BusinessCase, Deliverables, Governance, ValuePacks, Graph, Settings |
| **Phase 3: Yellow to Green** | 9–12 | 85% (+21 routes) | Intelligence Workspace rebuild, Value Studio rebuild, UI/UX Component Strategy |
| **Phase 4: Constitution** | Ongoing | 95%+ | CI gates, Contract Council, Facade Budget enforcement |

### 6.2 The Three-Tier Hook Architecture (Proposed)

The design brief prescribes a strict layered hook system to replace the current ad-hoc approach:

| Tier | Responsibility | Current State | Target State |
|------|---------------|---------------|--------------|
| **Tier 1: Protocol Hooks** | HTTP mechanics, Zod validation, tenant injection | Does not exist; `apiClient.ts` called directly | `createProtocolHook` factory with schema validation |
| **Tier 2: Domain Hooks** | React Query wrappers with `useFabricQuery`/`useFabricMutation` | 26 green hooks, inconsistent patterns | Standardized domain hooks with `QK.{domain}.{action}` keys |
| **Tier 3: Page Hooks** | Compose domain hooks into page-specific data shapes | Does not exist; pages call domain hooks directly | Unified loading/error aggregation per route |

### 6.3 CI Enforcement Gates (Proposed)

| Gate | Trigger | Behavior |
|------|---------|----------|
| `detect_mock_data` | PR modifies page components | Fail if hardcoded arrays/mock objects found |
| `endpoint_coverage` | Backend schema changes | Fail if endpoint has no hook after 4 weeks |
| `type_sync_check` | PR touches generated types | Fail if generated types differ from committed |

### 6.4 Governance Model: The Contract Council

Three rules to prevent recurrence:

1. **No endpoint without a hook spec** — Backend PRs require frontend engineer approval of the hook specification
2. **No mock data beyond the introducing sprint** — Mock data is a sprint-scoped development aid, not a shipping artifact
3. **CONTRACT.md is the source of truth** — Implementation drift from contracts is a bug, not a style difference

---

## 7. Critical Assessment and Gaps in the Audit Itself

While the audit is thorough, several concerns emerge from analyzing the corpus:

### 7.1 Audit Limitations

| Concern | Evidence | Impact |
|---------|----------|--------|
| **Duplicate endpoint counting** | Track B lists some endpoints twice (e.g., `GET /v1/accounts` appears twice) | Actual orphan count may be lower than 236 |
| **REDIRECT routes inflate denominator** | 70 of 154 routes are `Navigate` redirects — not user-facing pages | The "154 routes" headline overstates surface area |
| **GREEN classification is generous** | A route is GREEN if any hook makes any HTTP call — doesn't verify data completeness | Some GREEN routes may render partial data |
| **DIL endpoints not in Track B** | The 52 DIL endpoints we built are not reflected in the Track B analysis (which predates our work) | Actual orphan count is higher: 236 + 52 = 288 |
| **No E2E validation** | Classification is static analysis only — no runtime verification that GREEN routes actually render correct data | False positives possible |

### 7.2 Missing from the Constitution

The proposed contracts address the frontend-backend boundary but miss several critical governance areas:

| Missing Area | Why It Matters |
|--------------|----------------|
| **Feature flag contract** | No standard for how backend feature flags gate frontend routes |
| **Deprecation contract** | No process for sunsetting routes/endpoints (70 redirects accumulated without governance) |
| **Performance budget contract** | No standards for bundle size, time-to-interactive, or API latency per route |
| **Accessibility contract** | No standards for WCAG compliance across the 84 authenticated routes |
| **Testing contract** | No standard for what test coverage a GREEN route requires (unit, integration, E2E) |
| **Versioning contract** | No standard for how API version changes propagate to frontend route behavior |

---

## 8. Recommended Next Steps

Based on this analysis, the following actions are prioritized by immediate impact:

### Immediate (This Week)

1. **Ratify the 3 missing contracts** — API Boundary, Type Synchronization, Hook Architecture — as formal documents in `contracts/`
2. **Implement the type generation pipeline** — Connect the 244 backend OpenAPI specs to frontend TypeScript generation
3. **Wire the 52 DIL endpoints** — The Data Intelligence Layer we just built has zero frontend surface; create the hook families for products, evidence, competitive intel, ROI, hypotheses, narratives, enrichment, and intelligence

### Short-Term (Sprint 1-3)

4. **Execute Phase 1 of the roadmap** — Accounts expansion, AgentWorkflows, HealthMonitor, OntologyEditor
5. **Build the Integration Dashboard** — Make the FRP metric visible to the entire team
6. **Sunset `/command-center` and `/deliverables/calculators`** — Remove routes with no backend contract

### Medium-Term (Sprint 4-8)

7. **Execute Phase 2** — Onboard 50+ endpoints using the standardized hook architecture
8. **Implement CI gates** — `detect_mock_data`, `endpoint_coverage`, `type_sync_check`
9. **Establish the Contract Council** — Lightweight RFC process for new endpoints

---

## 9. Conclusion

The Fabric 4L frontend is a **stage set** — visually complete but structurally hollow. The audit documents provide an exhaustive forensic analysis confirming that **81% of authenticated routes are non-functional facades** and **96.7% of backend endpoints have no frontend consumer**. The root cause is not technical debt but **architectural governance absence**: no binding contracts existed between frontend and backend teams about who owns which integration surface.

The 6-file design brief provides a credible recovery plan with measurable targets (FRP from 19% to 95% over 12 sprints), a concrete hook architecture (three-tier system with protocol, domain, and page layers), and an enforcement mechanism (CI gates + Contract Council + Facade Budget). The plan is sound but ambitious — it requires sustained engineering commitment and cross-team governance that did not previously exist.

The most urgent gap is that the **Data Intelligence Layer we just built (52 endpoints, 9 services) has zero frontend representation**. These endpoints are the newest orphans in a system already suffering from a 96.7% orphan rate. Connecting them should be the first concrete action after contract ratification.
