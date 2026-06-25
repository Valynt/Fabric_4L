> **STATUS: ARCHIVED** — historical misalignment snapshot (2026-05-02). See [docs/archive/INDEX.md](archive/INDEX.md). Current contract alignment is governed by [contracts/GOVERNANCE.md](../contracts/GOVERNANCE.md).

# Backend-Frontend Misalignment Report

**Generated:** May 2, 2026  
**Severity Scale:** 🔴 Critical | 🟡 Warning | 🟢 Info  

---

## Executive Summary

| Category | Count | Status |
|----------|-------|--------|
| Critical Gaps | 3 | 🔴 |
| Warning Items | 4 | 🟡 |
| Info Items | 2 | 🟢 |
| **DIL Integration** | 52 endpoints | ✅ 100% hooked |

**Overall Assessment:** Frontend and backend are well-aligned. All 52 DIL endpoints have corresponding hooks. Main gaps are in internal service exposure and workflow integration patterns.

---

## 🔴 Critical Gaps

### 1. L5 Ground Truth - No Direct Frontend Integration
**Severity:** Critical  
**Description:** L5 Ground Truth service (validation, truth objects, evidence grading) has no direct frontend hooks. Frontend expects `useTruths`, `useTruthAuditTrail` but L5 is only accessible via L4 proxy.

**Frontend Expects:**
- `useTruths()` - List truth objects
- `useTruthAuditTrail(id)` - View audit trail
- `useTruthFreshnessSummary()` - Freshness dashboard
- `useStaleTruths()` - Find stale data
- `useMaturityLadder()` - Maturity scoring

**Backend Provides:**
- L5 internal API at `layer5_ground_truth/api/router.py`
- 10+ endpoints including `/validate`, `/truths`, `/stats`, `/maturity`
- Only accessible via L4 workflow calls

**Impact:** Governance pages cannot show truth validation data directly.

**Recommendation:** 
- Option A: Add L4 proxy routes to expose L5 read-only endpoints
- Option B: Create direct L5 hooks for frontend (requires auth passthrough)

---

### 2. L6 Benchmarks - Minimal Exposure
**Severity:** Critical  
**Description:** L6 Benchmarks service is only accessible via L3 `/v1/roi/benchmarks/{industry}`. Frontend cannot access full benchmark capabilities.

**Frontend Expects:**
- `useBenchmarks()` - List all benchmarks
- `useBenchmark(id)` - Get specific benchmark
- `useBenchmarkPolicies()` - Get benchmark policies
- `useUpdateBenchmarkPolicy()` - Update policies

**Backend Provides:**
- L6 at `layer6-benchmarks/src/api/routes/benchmarks.py`
- Only 5 endpoints exposed
- L3 provides `/v1/roi/benchmarks` subset

**Impact:** Competitive intelligence and market analysis features limited.

**Recommendation:**
- Expose L6 directly through API gateway or create L4 proxy routes

---

### 3. useWorkspaceCase Hook - Generic Workspace Query
**Severity:** Critical  
**Description:** Frontend uses `useWorkspaceCase` (generic workspace endpoint) instead of dedicated DIL service hooks for many pages.

**Evidence:**
- 74% of pages use generic workspace query instead of specific hooks
- Per FRONTEND_AUDIT_REPORT.md findings

**Files Affected:**
- `pages/intelligence/SignalsTab.tsx` - Uses generic query
- `pages/studio/ActionPlanTab.tsx` - Uses generic query  
- `pages/studio/NarrativeTab.tsx` - Uses generic query

**Impact:** Pages render stale/cached data instead of real-time DIL data.

**Recommendation:**
- Migrate pages to specific DIL hooks (`useProducts`, `useCaseStudies`, `useCompetitors`, etc.)

---

## 🟡 Warning Items

### 4. Agent Streaming - Limited Error Handling
**Severity:** Warning  
**Description:** `useAgentEvents.ts` (AG-UI event streaming) needs continued error recovery review.

**Frontend:** `agui/useAgentEvents.ts`  
**Backend:** `layer4-agents/src/api/routes/agent_stream.py` (8,336 bytes)

**Gap:** No automatic reconnection on network failure.

---

### 5. Formula Governance - Complex State Sync
**Severity:** Warning  
**Description:** Formula approval workflows have potential state sync issues between `useFormulaApprovals` and backend.

**Frontend Hooks:**
- `useFormulas.ts` - Formula CRUD
- `useFormulaApprovals` - Approval workflow
- `useFormulaVersions.ts` - Version history
- `useFormulaDependents.ts` - Dependency tracking

**Backend:** `layer3-knowledge/src/api/routes/formula_governance.py` (24,740 bytes)

**Gap:** No real-time sync for approval status changes.

---

### 6. Ontology Editor - L2/L3 Coupling
**Severity:** Warning  
**Description:** `pages/OntologyEditor.tsx` requires both L2 (extraction config) and L3 (ontology storage) APIs.

**Gap:** No unified ontology API; frontend must coordinate between layers.

---

### 7. L1 Ingestion Jobs - No Real-time Progress
**Severity:** Warning  
**Description:** `pages/IngestionJobs.tsx` polls for job status; no WebSocket/SSE for real-time progress.

**Frontend:** `hooks/useJobStream.ts` (19,437 bytes)  
**Backend:** L1 has no streaming endpoint

**Gap:** 10-30 second delay on job status updates.

---

## 🟢 Info Items

### 8. DIL Hooks - Fully Integrated
**Severity:** Info  
**Description:** All 52 DIL endpoints have corresponding frontend hooks.

**Coverage:**
- L3 Products: 12 endpoints → 13 hooks (`useProducts.ts`)
- L3 Evidence: 9 endpoints → 9 hooks (`useEvidence.ts`)
- L3 Competitive: 10 endpoints → 10 hooks (`useCompetitiveIntel.ts`)
- L3 ROI: 7 endpoints → 8 hooks (`useROICalculator.ts`)
- L4 Enrichment: 4 endpoints → 4 hooks (`useEnrichment.ts`)
- L4 Hypotheses: 7 endpoints → 7 hooks (`useHypotheses.ts`)
- L4 Narratives: 5 endpoints → 5 hooks (`useNarratives.ts`)
- L4 Intelligence: 3 endpoints → 3 hooks (`useIntelligence.ts`)

**Status:** ✅ Complete integration

---

### 9. Formula System - Well Connected
**Severity:** Info  
**Description:** Formula CRUD, governance, variables, and value trees are fully integrated.

**Hooks:** `useFormulas`, `useVariables`, `useValueTrees`  
**Backend:** 30+ endpoints across formulas, variables, value_trees routers

**Status:** ✅ Complete integration

---

## Action Items

### Immediate (P0)
1. **Add L5 proxy routes in L4** - Expose read-only truth data
2. **Migrate workspace pages** - Switch from generic query to DIL hooks
3. **Add L6 benchmark routes** - Full benchmark API exposure

### Short-term (P1)
4. **Add SSE to L1 jobs** - Real-time job progress streaming
5. **Unify ontology API** - Single endpoint for L2/L3 ontology ops
6. **Add agent stream resilience** - Auto-reconnect on failure

### Long-term (P2)
7. **Formula real-time sync** - WebSocket for approval status
8. **Graph query optimization** - Batch entity requests

---

## Appendix: Hook-to-Backend Verification Matrix

| Hook File | Backend File | Endpoint Count | Status |
|-----------|--------------|----------------|--------|
| `useProducts.ts` | `products.py` | 12/12 | ✅ |
| `useEvidence.ts` | `evidence.py` | 9/9 | ✅ |
| `useCompetitiveIntel.ts` | `competitive_intel.py` | 10/10 | ✅ |
| `useROICalculator.ts` | `roi_calculator.py` | 7/7 | ✅ |
| `useFormulas.ts` | `formulas.py` | 8/8 | ✅ |
| `useVariables.ts` | `variables.py` | 8/8 | ✅ |
| `useWorkflows.ts` | `workflows.py` | 11/11 | ✅ |
| `useAccounts.ts` | `accounts.py` | 9/9 | ✅ |
| `useBilling.ts` | `billing.py` | 25/25 | ✅ |
| `useValuePacks.ts` | `value_packs.py` | 16/16 | ✅ |
| `useGraphQuery.ts` | `entities.py` + `main.py` | 6/6 | ✅ |
| `useTruths` (missing) | `layer5/api/router.py` | 0/10 | 🔴 |
