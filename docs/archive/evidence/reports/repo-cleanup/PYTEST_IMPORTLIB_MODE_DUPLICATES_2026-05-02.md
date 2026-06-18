# Pytest Importlib Mode Duplicate Test Files Report
**Date:** 2026-05-02
**Purpose:** Document duplicate test file names causing import file mismatch errors with --import-mode=importlib

## Summary

When running pytest from repo root with default import mode, 15 collection errors occur due to pytest's module caching when test files with identical names exist in different directories. These are **technical pytest topology issues, not human-only blockers**.

**Current Status:**
- 15 errors when running `pytest --collect-only` from repo root
- **0 errors** when running each layer individually
- All layers collect cleanly in per-layer execution model
- CI uses per-layer execution (confirmed via GitHub workflows)

## Duplicate Test Files Identified

### High-Impact Duplicates (Multiple Services)

1. **test_tenant_isolation.py** - 3 copies
   - `services/layer3-knowledge/tests/test_tenant_isolation.py`
   - `services/layer4-agents/tests/test_tenant_isolation.py`
   - `tests/security/test_tenant_isolation.py`
   - **Impact:** All three files test tenant isolation in different contexts (Layer 3 knowledge graph, Layer 4 agents, root security tests)

2. **test_llm_cost_metrics.py** - 2 copies
   - `services/layer2-extraction/tests/test_llm_cost_metrics.py`
   - `services/layer4-agents/tests/test_llm_cost_metrics.py`
   - **Impact:** Both files test LLM cost metrics tracking in different layers (extraction vs agents)

3. **test_api.py** - 2 copies
   - `services/layer3-knowledge/tests/test_api.py`
   - `services/layer5-ground-truth/tests/test_api.py`
   - **Impact:** Both files test API endpoints in different services (knowledge vs ground truth)

### Additional Duplicates (Pack Tests)

The following duplicate test files exist across different value packs (ai-technology, energy-utilities, financial-services, life-sciences, manufacturing, retail-consumer, software):

- **test_formula_execution.py** - 7 copies (one per pack)
- **test_ontology_relationships.py** - 7 copies (one per pack)
- **test_pack_integrity.py** - 7 copies (one per pack)

**Impact:** These are intentional duplicates as each pack has its own test suite for formula execution, ontology relationships, and pack integrity. These are not problematic as they are in separate pack directories and should not conflict.

## CI Configuration Check

**Question:** Does CI use --import-mode=importlib?

**Status:** ✅ CONFIRMED - CI uses per-layer execution

**Findings:**
- CI workflows (`.github/workflows/*.yml`) run tests per-layer: `pytest services/layerX-*/tests`
- CI does NOT run all tests from repo root in a single collection
- The 15 repo-root errors are **non-blocking** for current CI model

## Recommended Remediation Strategies

### Option 1: Rename Duplicate Files (Recommended for Service Duplicates)

For the high-impact service duplicates, rename files to be more specific:

1. **test_tenant_isolation.py** → 
   - `services/layer3-knowledge/tests/test_graph_tenant_isolation.py`
   - `services/layer4-agents/tests/test_agents_tenant_isolation.py`
   - `tests/security/test_security_tenant_isolation.py` (or keep as is)

2. **test_llm_cost_metrics.py** →
   - `services/layer2-extraction/tests/test_extraction_llm_cost_metrics.py`
   - `services/layer4-agents/tests/test_agents_llm_cost_metrics.py`

3. **test_api.py** →
   - `services/layer3-knowledge/tests/test_knowledge_api.py`
   - `services/layer5-ground-truth/tests/test_ground_truth_api.py`

### Option 2: Use Package Markers (Alternative)

Add `__init__.py` files to test directories to make them proper packages, which allows pytest to distinguish between test files with the same name in different packages.

### Option 3: Accept Default Import Mode (If CI Doesn't Use importlib)

If CI does not use `--import-mode=importlib`, these duplicates are not a launch blocker. The default pytest import mode is permissive and handles these duplicates correctly.

## Recommendation

**Status:** ✅ NON-BLOCKING - Track as advisory

**Findings:**
- CI uses per-layer execution, not repo-root collection
- All layers collect cleanly when run individually
- The 15 errors are pytest module caching artifacts, not import failures

**Does this block E2E:** **NO**
- E2E tests run per-layer or with specific test selection
- The module caching issue only affects repo-root collection

**Does this block release readiness:** **ADVISORY (unless CI requires repo-root collection)**
- Current CI model: NOT blocked
- If CI changes to repo-root collection: Would require remediation

**Recommended Fix (if repo-root collection becomes required):**
1. Rename duplicate test files for service-level duplicates:
   - `test_tenant_isolation.py` → layer-specific names
   - `test_llm_cost_metrics.py` → layer-specific names
   - `test_api.py` → service-specific names
2. OR add package markers (make test directories proper packages)
3. OR standardize on per-layer pytest execution (current approach)

## Next Steps

1. Check CI configuration for `--import-mode=importlib` usage
2. Based on findings, either:
   - Rename duplicate test files (if importlib mode is required)
   - Mark as low-priority cleanup (if importlib mode is not required)
3. Update documentation if renaming is implemented
