---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: Temporal planning document
Modern Equivalent: See ROADMAP.md for current status
Status: Historical reference only
---

# Fabric 4L Launch Slice Analysis

**Date:** 2026-04-23
**Objective:** Identify one production-worthy launch slice and drive convergence

---

## Executive Summary

**Recommended Canonical Slice:** Intelligence-to-Delivery Business Case Workflow

**Path:** Prospect Setup → Intelligence Workspace → Value Studio → Business Case → Export with Provenance

The repository has three competing workflow patterns. The Business Case flow has the strongest end-to-end implementation across frontend, Layer 4 orchestration, and provenance/governance.

---

## 1. End-to-End Slice Map

### Frontend Flow

| Step | Route | Component | Backend API | Status |
|------|-------|-----------|-------------|--------|
| Entry | `/workflow/prospect` | `ProspectSetup.tsx` | `POST /accounts` | ✅ Implemented |
| Account | `/accounts` | `Accounts.tsx` | `GET /accounts` | ✅ Implemented |
| Intelligence | `/intelligence/:id/*` | `Signals/Drivers/Evidence/Stakeholders` | L3 Entity API | ⚠️ Partial |
| Synthesis | `/studio/:id/*` | `ActionPlan/ValueModel/Narrative` | L4 Workflows | ⚠️ Partial |
| Delivery | `/deliverables/cases` | `BusinessCaseList.tsx` | `GET /workflows` | ✅ Implemented |
| View | `/deliverables/cases/:id` | `BusinessCase.tsx` | `GET /cases/{id}` | ✅ Implemented |
| Export | (modal) | Export action | `GET /cases/{id}/export` | ✅ Implemented |
| Governance | `/governance/traces` | `DecisionTrace.tsx` | Provenance API | ✅ Implemented |

### Backend Workflows (Layer 4)

**BusinessCaseGeneratorWorkflow** (`@services/layer4-agents/src/workflows/business_case.py`)
- 5-node pipeline: gather_inputs → run_roi → verify_truth → generate_narrative → assemble_document
- Uses ROICalculatorWorkflow as sub-workflow
- Full checkpoint/resume support via PostgresCheckpointSaver
- Truth gating at verify_truth node
- Provenance manifest generation

### API Routes

| Route | File | Status |
|-------|------|--------|
| `POST /workflows` | `api/routes/workflows.py` | ✅ Implemented |
| `GET /workflows/{id}` | `api/routes/workflows.py` | ✅ Implemented |
| `POST /cases` | `api/routes/analysis.py` | ✅ Implemented |
| `GET /cases/{id}` | `api/routes/analysis.py` | ✅ Implemented |
| `GET /cases/{id}/export` | `api/routes/analysis.py` | ✅ Implemented (with provenance) |
| `GET /accounts` | `api/routes/accounts.py` | ✅ Implemented |

---

## 2. Status Classification

### Frontend Components

| Component | Location | Status |
|-----------|----------|--------|
| ProspectSetup | `workflow/pages/ProspectSetup.tsx` | ✅ **IMPLEMENTED** |
| WorkflowLayout | `workflow/components/WorkflowLayout.tsx` | ✅ **IMPLEMENTED** |
| Intelligence Shell | `pages/intelligence/*` | ⚠️ **PARTIAL** (mocked data) |
| Value Studio Shell | `pages/studio/*` | ⚠️ **PARTIAL** (layout complete) |
| BusinessCaseList | `pages/BusinessCaseList.tsx` | ✅ **IMPLEMENTED** |
| BusinessCase | `pages/BusinessCase.tsx` | ✅ **IMPLEMENTED** |
| DecisionTrace | `pages/DecisionTrace.tsx` | ✅ **IMPLEMENTED** |
| Accounts | `pages/Accounts.tsx` | ✅ **IMPLEMENTED** |

### Backend

| Component | File | Status |
|-----------|------|--------|
| BusinessCaseGeneratorWorkflow | `workflows/business_case.py` | ✅ **IMPLEMENTED** |
| ROICalculatorWorkflow | `workflows/roi_calculator.py` | ✅ **IMPLEMENTED** |
| OrchestrationController | `engine/executor.py` | ✅ **IMPLEMENTED** |
| Export Provenance | `services/export_provenance.py` | ✅ **IMPLEMENTED** |

---

## 3. Duplicate & Competing Patterns

### P0 - Critical Duplicates

| Pattern | Location | Status | Recommendation |
|---------|----------|--------|----------------|
| **7-Step Workflow** | `/workflow/*` routes | ❌ **BROKEN** | **RETIRE** - All redirect to `/accounts` |
| **Value Studio** | `/studio/*` | ⚠️ **PARTIAL** | **CONVERGE** - Keep as canonical |
| **Old Model Routes** | `/model/*` | ❌ **DEPRECATED** | Already redirect |

**Evidence:** `@frontend/client/src/App.tsx:714-728` shows all workflow steps redirect to `/accounts`:
```typescript
<Route path="/workflow/ai-model"><Navigate to="/accounts" /></Route>
<Route path="/workflow/driver-tree"><Navigate to="/accounts" /></Route>
// ... etc
```

### Duplicate Components

| Primary | Duplicate | Action |
|---------|-----------|--------|
| `pages/BusinessCase.tsx` | `workflow/pages/ValueCase.tsx` | **MERGE** - Use BusinessCase.tsx |
| `pages/intelligence/*.tsx` | `workflow/pages/Intelligence.tsx` | **RETIRE** workflow/Intelligence.tsx |
| `components/AppShell.tsx` | `workflow/WorkflowLayout.tsx` | **CONVERGE** - Keep AppShell |

---

## 4. Launch Blockers

### P0 - Critical (Fix Before Launch)

| Blocker | Impact | Location |
|---------|--------|----------|
| Workflow steps redirect to `/accounts` | Cannot complete flow | `App.tsx:714-728` |
| Intelligence workspace lacks real data | Empty tabs | `pages/intelligence/*.tsx` |
| Value Studio incomplete | Cannot synthesize | `pages/studio/*.tsx` |
| ProspectSetup backend integration | No data persistence | `ProspectSetup.tsx:1356-1375` |

### P1 - High Priority

| Blocker | Impact | Location |
|---------|--------|----------|
| PDF export generation | Export stubbed | `services/export_storage.py` |
| DecisionTrace visualization | Minimal UI | `pages/DecisionTrace.tsx` |

---

## 5. Recommended Convergence

### Keep (Canonical Slice)

| Layer | Components |
|-------|-----------|
| Frontend | ProspectSetup, Accounts, Intelligence (4 tabs), Studio (3 tabs), BusinessCaseList, BusinessCase, DecisionTrace |
| Backend L4 | BusinessCaseGeneratorWorkflow, ROICalculatorWorkflow, OrchestrationController, all routes, export_provenance |
| Shared | Audit emitter, identity context, checkpointing |

### Retire

| Layer | Components |
|-------|-----------|
| Frontend | 7-step workflow redirects, workflow/Intelligence.tsx, workflow/ValueCase.tsx, useWorkflowStore |

---

## 6. Next Actions

### Phase 1: Stabilize Core Flow (Week 1-2)

1. **Fix workflow redirects** (`App.tsx`)
   - Remove Navigate-to-accounts from workflow routes
   - Wire `/workflow/intelligence` → `/intelligence/{accountId}`

2. **Connect ProspectSetup to backend**
   - Implement `onCreateSetup` → `POST /accounts`
   - Navigate to intelligence workspace on success

3. **Enable real data in Intelligence workspace**
   - Connect SignalsTab to L3 entity search
   - Connect DriversTab to value driver API

### Phase 2: Complete Synthesis (Week 2-3)

4. **Complete Value Studio tabs**
   - Wire ActionPlanTab to workflow trigger
   - Connect ValueModelTab to formula evaluation

5. **Verify business case integration**
   - Ensure BusinessCaseList shows workflows
   - Verify BusinessCase view reads from API

### Phase 3: Governance (Week 3-4)

6. **Test export pipeline end-to-end**
7. **Enhance DecisionTrace visualization**

---

## 7. Evidence Citations

- **Workflow redirects:** `@frontend/client/src/App.tsx:714-728`
- **Business case workflow:** `@services/layer4-agents/src/workflows/business_case.py:1-287`
- **Orchestration controller:** `@services/layer4-agents/src/engine/executor.py:74-910`
- **Workflow routes:** `@services/layer4-agents/src/api/routes/workflows.py:218-610`
- **Analysis routes:** `@services/layer4-agents/src/api/routes/analysis.py:215-504`
- **Account routes:** `@services/layer4-agents/src/api/routes/accounts.py:123-365`
- **Export provenance:** `@services/layer4-agents/src/services/export_provenance.py`

---

## 8. Summary Matrix

| Criterion | Business Case Slice | 7-Step Workflow |
|-----------|---------------------|-----------------|
| Frontend Complete | ✅ Yes | ❌ No |
| Backend Complete | ✅ Yes | ❌ No |
| Orchestration | ✅ Full | ❌ None |
| Provenance | ✅ Yes | ❌ No |
| Export | ✅ Yes | ❌ No |
| Governance | ✅ Yes | ❌ No |
| Demo-Ready | ✅ Yes | ❌ No |

**Recommendation:** Proceed with Business Case Slice. Retire 7-step workflow. Converge on Intelligence → Studio → Deliverables.
