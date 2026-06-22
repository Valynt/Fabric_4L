# Value Fabric Remediation Plan
**Generated**: 2026-06-22  
**Source**: Repowise Codebase Intelligence Analysis

---

## Executive Summary

The codebase shows **critical health risks** in specific hotspots despite an overall average health score of 8.27. Key concerns:

- **30 files** with health score 1.0 (critical)
- **850 safe-to-delete dead exports** (15,009 lines)
- **Extreme churn** in layer4-agents (up to 33,940% relative churn in 90 days)
- **Knowledge silos** with no assigned owners
- **Bus factor of 1.3** — 2,988 files dependent on single contributors

---

## Priority 0: Critical Health Issues

### 1.1 Identity Middleware Complexity
**File**: `packages/shared/src/value_fabric/shared/identity/middleware.py`
- **Health Score**: 1.0
- **Issues**: CCN 46, max nesting 6, 924 NLOC, 7.89% duplication
- **Impact**: Core auth/tenant isolation path

**Remediation**:
1. Extract smaller functions from the 924-line monolith
2. Reduce cyclomatic complexity by separating concerns (auth, tenant resolution, middleware)
3. Add unit tests (currently has none)
4. Reduce nesting depth from 6 to ≤4

**Timeline**: 1-2 sprints

### 1.2 Layer 1 Main API Complexity
**File**: `services/layer1-ingestion/src/layer1_ingestion/api/main.py`
- **Health Score**: 1.0
- **Issues**: CCN 21, max nesting 6, 2,844 NLOC, 27.84% duplication

**Remediation**:
1. Split into route modules by domain (sources, crawlers, tasks)
2. Extract shared middleware and dependencies
3. Deduplicate 27.84% duplicated code
4. Add integration tests

**Timeline**: 1 sprint

### 1.3 Layer 1 Tasks Complexity
**File**: `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`
- **Health Score**: 1.0
- **Issues**: CCN 34, max nesting 7, 1,925 NLOC, 16.01% duplication

**Remediation**:
1. Extract task types into separate modules
2. Reduce nesting from 7 to ≤4
3. Add task orchestration tests

**Timeline**: 1 sprint

### 1.4 Layer 2 API Complexity
**File**: `services/layer2-extraction/src/layer2_extraction/api/main.py`
- **Health Score**: 1.0
- **Issues**: CCN 32, max nesting 4, 1,901 NLOC, 5.78% duplication

**Remediation**:
1. Separate extraction routes from orchestration
2. Extract extraction pipeline logic
3. Add E2E extraction tests

**Timeline**: 1 sprint

### 1.5 Layer 3 Graph Visualization Complexity
**File**: `services/layer3-knowledge/src/api/routes/graph_viz.py`
- **Health Score**: 1.0
- **Issues**: CCN 46, max nesting 7, 527 NLOC, 20% duplication

**Remediation**:
1. Extract visualization strategies into separate classes
2. Reduce CCN from 46 to ≤15
3. Add visualization output tests

**Timeline**: 1 sprint

### 1.6 100% Duplication Files
**Files** requiring immediate attention:
- `services/layer1-ingestion/src/adapters/sec_edgar.py` (100% duplication)
- `services/layer1-ingestion/src/adapters/xbrl_parser.py` (100% duplication)
- `services/layer1-ingestion/src/compliance/robots_checker.py` (100% duplication)
- `services/layer3-knowledge/src/cache/redis_cache.py` (100% duplication)
- `services/layer4-agents/src/database.py` (100% duplication)
- `services/layer4-agents/src/layer4_agents/database.py` (84.62% duplication)

**Remediation**:
1. Identify source of duplication (likely copy-paste)
2. Consolidate into shared utilities or remove duplicates
3. Add tests to prevent regression

**Timeline**: 1 sprint

---

## Priority 1: Dead Code Removal

### 2.1 Frontend Unused Components (High Confidence)
**Total**: 659 high-confidence unused exports (8,966 lines)

**Largest deletions**:
- `apps/web/src/pages/studio/NarrativeTab.tsx` (371 lines)
- `apps/web/src/pages/InteractiveBusinessCase.tsx` (332 lines)
- `apps/web/src/pages/intelligence/ROITab.tsx` (314 lines)
- `apps/web/src/pages/value-case/ValueCasePage.tsx` (276 lines)
- `apps/web/src/pages/realization/RealizationPage.tsx` (235 lines)

**Remediation**:
1. Use `/dead-code-sweeper` workflow for automated removal
2. Verify no dynamic imports or route references
3. Update routing config if needed
4. Run frontend tests after removal

**Timeline**: 1 sprint

### 2.2 Backend Unused Functions
**Total**: 191 medium-confidence unused exports (6,043 lines)

**Notable deletions**:
- `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py::create_source` (250 lines)
- `services/layer1-ingestion/src/layer1_ingestion/crawler/telemetry.py::ExecutionMetrics` (169 lines)
- `services/layer2-extraction/src/layer2_extraction/models/ontology.py::OntologySchema` (104 lines)
- `services/layer4-agents/src/layer4_agents/api/routes/state_inspector.py::get_performance_metrics` (96 lines)

**Remediation**:
1. Review medium-confidence exports for dynamic usage
2. Remove confirmed unused exports
3. Update OpenAPI specs if endpoints were exposed
4. Run backend tests after removal

**Timeline**: 1 sprint

---

## Priority 2: Churn Stabilization

### 3.1 Layer 4 Extreme Churn
**Issue**: Multiple layer4-agents files with 70-33,940% relative churn in 90 days

**Highest churn files**:
- `services/layer4-agents/src/harness/tests/test_live_l5_validator.py` (33,940%)
- `services/layer4-agents/src/integration/layer3_client.py` (21,940%)
- `services/layer4-agents/src/integration/layer2_client.py` (15,540%)
- `services/layer4-agents/src/integration/layer1_client.py` (14,580%)

**Root Cause** (from ADR-022): Layer 4 internal decomposition in progress — Billing extraction as pilot

**Remediation**:
1. Complete ADR-022 decomposition plan to stabilize architecture
2. Extract billing service into separate module
3. Stabilize integration client contracts
4. Add contract tests to prevent churn
5. Implement feature flags for gradual rollout

**Timeline**: 2-3 sprints

### 3.2 Change Entropy Hotspots
**Files** with scattered, noisy commits:
- `scripts/ci/run_live_workflow_validation.sh` (change entropy 2.57)
- `packages/shared/src/value_fabric/shared/fastapi_framework/tests/test_app.py` (change entropy 1.88)

**Remediation**:
1. Consolidate related changes into single commits
2. Add commit message guidelines for these files
3. Consider splitting monolithic scripts

**Timeline**: 1 sprint

---

## Priority 3: Knowledge Management

### 4.1 Knowledge Silo Resolution
**Issue**: 16+ critical files with no assigned owner

**Unowned files**:
- `apps/web/src/auth/ClerkAuthBridge.tsx`
- `apps/web/src/components/routing/RequireClerkAuth.tsx`
- `apps/web/src/components/routing/UnifiedRouteGuard.tsx`
- `apps/web/src/contexts/AuthContext.tsx`
- `apps/web/src/pages/ClerkSignIn.tsx`
- Various admin and governance pages

**Remediation**:
1. Assign owners via CODEOWNERS file
2. Document ownership expectations in AGENTS.md
3. Create onboarding docs for critical paths
4. Schedule knowledge transfer sessions

**Timeline**: 1 sprint

### 4.2 Bus Factor Improvement
**Issue**: Average bus factor 1.3, 2,988 files with bus factor 1

**Remediation**:
1. Identify critical single-owner files (auth, tenant isolation, core middleware)
2. Assign secondary reviewers for PRs touching these files
3. Implement rotation for critical component maintenance
4. Document tribal knowledge in architecture docs

**Timeline**: Ongoing, 2-3 sprints for initial coverage

---

## Priority 4: Technical Debt

### 5.1 Nested Complexity
**Files** with nesting depth ≥8:
- `apps/web/scripts/playwright-route-audit-fast.ts::main` (8 levels, CCN 27)
- `docs/archive/frontend-root-2026-05-02/source-snapshot/scripts/playwright-route-audit-fast.ts::main` (8 levels)

**Remediation**:
1. Extract nested logic into helper functions
2. Use early returns to reduce nesting
3. Remove archived duplicate if confirmed unused

**Timeline**: 1 sprint

### 5.2 Canonical Runtime Path Migration
**Status**: In progress per ADR-021

**Remaining work**:
- Complete Layer 1 migration (pilot)
- Migrate Layers 2, 6
- Thin out `value_fabric/layerX/` shims
- Update cross-layer imports

**Timeline**: 2-3 sprints

---

## Execution Plan

### Sprint 1 (Immediate)
1. **P0 Health**: Fix 100% duplication files (6 files)
2. **Dead Code**: Remove high-confidence frontend unused exports
3. **Knowledge**: Assign owners to unowned critical auth files
4. **Complexity**: Reduce nesting in Playwright audit script

### Sprint 2
1. **P0 Health**: Refactor identity middleware (CCN 46 → ≤15)
2. **P0 Health**: Split Layer 1 main API (2,844 NLOC)
3. **Dead Code**: Remove backend unused exports
4. **Churn**: Begin Layer 4 decomposition (ADR-022)

### Sprint 3
1. **P0 Health**: Refactor Layer 1 tasks and Layer 2 API
2. **P0 Health**: Fix Layer 3 graph visualization complexity
3. **Churn**: Complete Layer 4 billing extraction
4. **Canonical Path**: Complete Layer 1 migration

### Sprint 4
1. **Bus Factor**: Implement secondary reviewer rotation
2. **Canonical Path**: Migrate Layers 2, 6
3. **Churn**: Stabilize integration clients
4. **Validation**: Full regression test suite

---

## Success Metrics

- **Health**: Reduce files with score 1.0 from 30 to ≤5
- **Dead Code**: Remove ≥10,000 lines of safe-to-delete code
- **Churn**: Reduce layer4-agents 90-day churn to ≤50% for all files
- **Coverage**: Achieve ≥80% test coverage for refactored critical files
- **Bus Factor**: Increase average bus factor to ≥2.0

---

## Verification Commands

```bash
# Health check after refactoring
python -m pytest services/layer1-ingestion/tests/ -v
python -m pytest services/layer2-extraction/tests/ -v
python -m pytest services/layer3-knowledge/tests/ -v
python -m pytest services/layer4-agents/tests/ -v

# Dead code verification
pnpm --dir apps/web run test
python scripts/ci/test_dead_code_removal.py

# Contract validation
make verify
python scripts/ci/gate_engineering_validator.py validate
```

---

## Dependencies

- **ADR-021**: Layer 3 Canonical Runtime Path (in progress)
- **ADR-022**: Layer 4 Internal Decomposition (in progress)
- **Clerk Auth**: Recent tenant resolution implementation (completed per memory)
- **Gate Engineering**: Production readiness gates (active)
