# Dead Code Sweep Report

**Date:** 2026-05-06  
**Scope:** Full sweep (frontend + all backend layers)  
**Confidence Threshold:** HIGH (unreachable, no imports, no references)

---

## Executive Summary

- **Files Scanned:** Frontend (apps/web/src) + Backend (services/layer1-6)
- **Dead Code Candidates Found:** 1
- **Files Removed:** 1 (253 lines)
- **False Positives:** 0
- **Impact:** Minimal - LandingPage was an unused marketing page not connected to routing

---

## Frontend Scan Results

### Orphan Pages Detection

**Method:** Compared page files in `apps/web/src/pages/` against lazy imports in `apps/web/src/shell/router.tsx`

**Findings:**

- ✅ **LandingPage.tsx** - NOT imported in router.tsx (253 lines) - **REMOVED**
- ✅ OntologyBrowser.tsx - Does not exist (already removed in previous cleanup)
- ✅ Home.tsx - Does not exist (ValueNarrativeHome.tsx is the actual home page)
- ✅ Stage1-6 pages - Do not exist (already removed in previous cleanup)

### Mock Data Blocks Detection

**Method:** Searched for MOCK_, mockData, and placeholder patterns

**Findings:**

- ✅ No actual mock data blocks found
- ✅ Only placeholder text in UI inputs (e.g., "Enter your name") - not dead code

### Duplicate Systems Detection

**Method:** Checked for legacy vs new workspace systems

**Findings:**

- ℹ️ Studio tabs exist and are still routed (legacy workspace) - **NOT DEAD** - actively used
- ℹ️ ValueStudioShell is still used by Studio tabs - **NOT DEAD**
- ℹ️ ROITab exists in two locations (intelligence/ and calculator/) - both used - **NOT DEAD**
- ℹ️ EvidenceTab exists in two locations (intelligence/ and studio/) - both used - **NOT DEAD**

### Obsolete Directory

**Finding:**

- ℹ️ `frontend/` directory is marked OBSOLETE with contents archived to `docs/archive/frontend-root-2026-05-02/source-snapshot/` - **NOT DEAD** (already migrated)

---

## Backend Scan Results

### Layer 4 (Agents) - tools and routes

**Tools Scan:**

- ✅ All 14 tool files in `services/layer4-agents/src/tools/` are imported in `__init__.py`
- ✅ All 25 tools are registered in `create_default_registry()`
- ✅ No unused tool files found

**Routes Scan:**

- ✅ All 22 route files in `services/layer4-agents/src/api/routes/` are imported in `main.py`
- ✅ No unused route files found

### Layer 1 (Ingestion)

**Routes Scan:**

- ✅ `compatibility.py` is included in `app_monolith.py` (line 363)
- ✅ All routes are properly registered

### Layer 2 (Extraction)

**Routes Scan:**

- ✅ `audit.py`, `extraction.py`, `ontology.py`, `system.py` are all included in `main.py` (lines 1554-1557)
- ✅ WebSocket router is included (line 226)
- ✅ All routes are properly registered

### Layer 3 (Knowledge)

**Routes Scan:**

- ✅ All 14 route files are included via `include_router_mounts` in `app_monolith.py` (line 639)
- ✅ Routes: value_trees, formulas, value_packs, formula_governance, variables, models, entities, products, evidence, competitive_intel, roi_calculator, benchmarks, system
- ✅ All routes are properly registered

### Layer 5 (Ground Truth)

**Routes Scan:**

- ✅ `router.py` is included in `main.py` (line 237)
- ✅ `model_registry_routes.py` is conditionally included (line 242)
- ✅ All routes are properly registered

### Layer 6 (Benchmarks)

**Routes Scan:**

- ✅ `benchmarks.py` and `system.py` are included in `main.py` (lines 497-498)
- ✅ All routes are properly registered

---

## Removed Files

### HIGH Confidence Removal

| File                                    | Lines | Reason                                                    | Verification                                          |
|----------------------------------------|-------|-----------------------------------------------------------|-------------------------------------------------------|
| apps/web/src/pages/LandingPage.tsx    | 253   | Not imported in router.tsx, no references in codebase     | Grepped entire codebase - only self-reference found     |

---

## Safety Rules Adherence

- ✅ Did not delete any test files
- ✅ Did not delete any migration files
- ✅ Did not delete any critical directories
- ✅ Verified each candidate through import checks, string references, and grep searches
- ✅ Only removed HIGH confidence candidates (unreachable, no imports, no references)

---

## Recommendations

1. **No further cleanup needed** - The codebase is clean with minimal dead code
2. **Consider removing legacy Studio workspace** - The `/studio` routes are marked as legacy but still active. Consider deprecation plan if not needed.
3. **Monitor for new dead code** - Run this sweep quarterly or after major refactors

---

## Verification Commands

To verify the removal was successful:

```bash
# Check LandingPage no longer exists
ls apps/web/src/pages/LandingPage.tsx  # Should fail

# Check router still works
pnpm build  # Should succeed

# Run tests
pnpm test  # Should pass
```

---

**Report Generated:** 2026-05-06  
**Sweep Duration:** ~10 minutes  
**Total Lines Removed:** 253  
**Risk Level:** LOW (unused marketing page)
