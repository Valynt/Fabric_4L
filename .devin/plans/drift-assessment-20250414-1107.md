# Drift Assessment Report 2026-04-14

**Assessment Time**: 2026-04-14T11:07:00Z
**Scope**: L1-L4 APIs, Frontend/Backend Contracts, Schema Evolution
**Status**: ⚠️ CRITICAL DRIFT DETECTED

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Drift Instances** | 9 |
| **Critical** | 4 |
| **Warning** | 3 |
| **Info** | 2 |

---

## Critical Drift Items

### 1. Layer 3 OpenAPI Contract is Mislabeled/Incorrect [CRITICAL]

**Location**: `contracts/openapi/layer3-knowledge.json`

**Issue**: File contains Layer 1 ingestion API specs, not Layer 3 knowledge graph API

**Evidence**:
```json
{
  "info": {
    "title": "Value Fabric - Layer 1: Intelligent Data Ingestion",
    "description": "Production-grade web data ingestion service..."
  },
  "paths": {
    "/api/v1/ingestion/targets": { ... },
    "/api/v1/ingestion/content": { ... }
  }
}
```

**Expected**: Layer 3 graph API routes (`/v1/query/graph`, `/v1/entity/{id}/context`, `/v1/search/hybrid`, `/v1/entity/traverse`)

**Actual**: Layer 1 ingestion routes only

**Impact**: Frontend cannot validate against correct API contract; all L3 contract tests fail

**Remediation**:
1. Regenerate Layer 3 OpenAPI from actual `layer3-knowledge/src/api/main.py`
2. Fix `scripts/export_openapi.py` to properly export L3 specs
3. Verify routes match frontend expectations in `useGraphQuery.ts`

---

### 2. Frontend API Routes Mismatch OpenAPI Contract [CRITICAL]

**Location**: Frontend hooks vs contracts/openapi/

**Issue**: Frontend calls routes that don't exist in OpenAPI specs

**Evidence** (from `frontend/client/src/hooks/useGraphQuery.ts`):
```typescript
apiClient.post('l3', '/query/graph', {...})           // Missing from L3 OpenAPI
apiClient.get('l3', `/entity/${id}/context`)          // Missing from L3 OpenAPI
apiClient.post('l3', '/entity/traverse', {...})     // Missing from L3 OpenAPI
apiClient.post('l3', '/search/hybrid', {...})        // Missing from L3 OpenAPI
```

**Contract Test Failure**:
```
AssertionError: OpenAPI drift detected for Layer 3 monitored endpoints.
Missing in contracts/openapi/layer3-knowledge.json:
['/v1/ingest', '/v1/ingest/status/{source_id}', '/v1/query/graph', '/v1/search/hybrid']
```

**Impact**: No contract validation possible for core graph API operations

**Remediation**:
1. Export correct OpenAPI specs from running L3 service
2. Add missing routes to OpenAPI if they exist in implementation
3. Update frontend to use correct route prefixes if implementation differs

---

### 3. Missing Schema Definitions in OpenAPI [CRITICAL]

**Location**: `contracts/openapi/layer3-knowledge.json` components/schemas

**Issue**: Referenced schemas don't exist, causing contract test failures

**Evidence** (from contract test output):
```
SchemaValidationError: $: unresolved $ref #/components/schemas/IngestRequest
SchemaValidationError: $: unresolved $ref #/components/schemas/Formula
SchemaValidationError: $: unresolved $ref #/components/schemas/GraphRAGResponse
```

**Missing Schemas**:
- `IngestRequest` - L2→L3 payload contract
- `Formula` - Formula governance API
- `GraphRAGResponse` - Graph query response
- `EntityContextResponse` - Entity context API
- `SearchResponse` - Hybrid search results

**Impact**: Cannot validate any API responses against contracts

**Remediation**:
1. Regenerate all OpenAPI specs with complete schema definitions
2. Ensure `scripts/export_openapi.py` exports schemas, not just paths
3. Add schema generation tests to prevent future omissions

---

### 4. OpenAPI Export Script Failing [CRITICAL]

**Location**: `scripts/export_openapi.py`

**Issue**: Module import errors prevent regeneration of contracts

**Evidence**:
```
ERROR: [Layer 1] Import failed: No module named 'layer1_ingestion'
ERROR: [Layer 2] main.py not found
ERROR: [Layer 3] Export failed: No module named 'layer3_knowledge'
ERROR: [Layer 4] Export failed: No module named 'layer4_agents'

Exported 0/4 OpenAPI specifications
```

**Root Cause**: Python path/module resolution issues in isolated module loading

**Impact**: Cannot regenerate contracts to fix drift

**Remediation**:
1. Fix module path setup in `export_openapi.py` line 52
2. Ensure each layer's package is installable (`pip install -e services/layerN/`)
3. Add PYTHONPATH setup or use proper package imports

---

## Warning Items

### 5. Uncommitted Contract Test Files [WARNING]

**Location**: `tests/contract/`

**Evidence**:
```
?? tests/contract/IMPLEMENTATION_SUMMARY.md
?? tests/contract/test_l3_formulas_contract.py
?? tests/contract/test_l3_graph_contract.py
?? tests/contract/test_l3_value_trees_contract.py
?? tests/contract/test_l4_workflows_contract.py
```

**Impact**: Test coverage exists but is not in version control

**Remediation**: Commit or remove untracked contract test files

---

### 6. Modified Files Without Drift Assessment [WARNING]

**Modified files** (from `git status`):
- `tests/contract/test_l4_frontend_contract.py` - Contract tests modified
- `frontend/client/src/test-utils.tsx` - Test utilities modified
- `services/layer3-knowledge/src/performance/cache.py` - L3 performance code modified
- `services/layer4-agents/tests/conftest.py` - L4 test config modified
- `packages/shared/src/value_fabric/shared/identity/jwt.py` - Shared identity code modified (P0 per AGENTS.md)

**Impact**: Changes to shared identity (jwt.py) require security review per AGENTS.md rules

**Remediation**:
1. Run `make verify` before committing shared identity changes
2. Document drift assessment for all modified contract-related files

---

### 7. L2→L3 Ingest Contract Test Failing [WARNING]

**Location**: `tests/contract/test_l2_l3_contract.py`

**Evidence**:
```
test_l2_ingest_payload_shape_validates_against_l3_openapi_schema FAILED
  SchemaValidationError: $: unresolved $ref #/components/schemas/IngestRequest

test_l3_ingestion_and_query_endpoints_are_present_in_openapi_contract FAILED
  Missing in contracts/openapi/layer3-knowledge.json:
  ['/v1/ingest', '/v1/ingest/status/{source_id}', '/v1/query/graph', '/v1/search/hybrid']
```

**Impact**: Cross-layer integration contract not validated

**Remediation**: Fix L3 OpenAPI contract first, then re-run L2→L3 tests

---

## Info Items

### 8. Schema Evolution Status [INFO]

**Location**: Migrations across layers

| Layer | Migration Status |
|-------|-----------------|
| L1 (ingestion) | `/migrations/versions/` exists |
| L3 (knowledge) | `/src/migrations/` exists |
| L4 (agents) | `/migrations/versions/` (8 items) |
| L5 (ground-truth) | `/migrations/` exists |

**Note**: Unable to verify schema alignment without working OpenAPI export

---

### 9. Integration Tests Passing [INFO]

**Location**: `tests/integration/billing_entitlements/`

**Result**: 8 passed, 1 skipped in 0.06s

**Coverage**: Billing entitlements, feature flags, quota enforcement

**Note**: Billing integration is healthy; graph/formula APIs need same validation

---

## Recommended Actions

### Immediate (P0 - Before Any Release)

1. **Fix OpenAPI Export Script** (`scripts/export_openapi.py`)
   - Fix module import paths for all 4 layers
   - Ensure proper PYTHONPATH or package installation
   - Test export succeeds: `python scripts/export_openapi.py`

2. **Regenerate Layer 3 OpenAPI**
   - Verify routes match frontend expectations
   - Include all schemas (Formula, GraphRAGResponse, etc.)
   - Validate against running L3 service

3. **Review Shared Identity Changes**
   - `packages/shared/src/value_fabric/shared/identity/jwt.py` and `models.py` are modified
   - Per AGENTS.md P0 rules: requires security review
   - Run `make verify` before committing

### Short-term (P1 - This Week)

4. **Commit or Clean Up Contract Tests**
   - 5 untracked files in `tests/contract/`
   - Include in CI pipeline with other tests

5. **Add Frontend/Backend Alignment Validation**
   - Compare TypeScript interfaces to OpenAPI schemas
   - Add automated check to CI

6. **Fix L2→L3 Cross-Layer Contract**
   - Verify `IngestRequest` schema exists in L3 OpenAPI
   - Ensure L2 client uses correct route prefixes

### Medium-term (P2 - Next Sprint)

7. **Implement Automated Drift Detection in CI**
   ```yaml
   drift-check:
     runs-on: ubuntu-latest
     steps:
       - run: python scripts/export_openapi.py
       - run: git diff --exit-code contracts/openapi/ || echo "::warning::Drift detected"
       - run: python -m pytest tests/contract/ -v
   ```

8. **Schema Evolution Monitoring**
   - Add migration vs model validation
   - Track Neo4j graph schema changes

---

## Concrete Checklist

- [x] Contract tests executed with results captured
- [x] OpenAPI regeneration attempted (failed - module issues)
- [x] Frontend hooks compared to backend schemas (drift detected)
- [x] Cross-layer integration tests pass/fail recorded
- [ ] Schema evolution checked (pending working OpenAPI export)
- [x] Drift report generated with severity classification
- [ ] Critical drift items have assigned owners

---

## Safety Rules Violations

| Rule | Status | Violation |
|------|--------|-----------|
| Never ignore Critical drift before production deploy | ⚠️ | 4 critical items unaddressed |
| Document all drift findings with evidence | ✅ | Report generated |
| Prefer fixing upstream over downstream workarounds | ⚠️ | OpenAPI export needs fix |
| Run this workflow before any release candidate | ✅ | Running now |

---

## Next Steps

1. **Immediate**: Fix `scripts/export_openapi.py` module imports
2. **Today**: Regenerate L3 OpenAPI and validate against frontend
3. **This Week**: Commit contract tests, add drift detection to CI
4. **Before Next Release**: Re-run drift assessment, ensure all critical items resolved

---

*Generated by /drift-assessment workflow*
*Evidence captured from: pytest output, git status, OpenAPI files, frontend hooks*
