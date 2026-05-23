# Test Gap Analysis

Generated: 2026-05-22
Scope: Layer 3 (Knowledge) - Focus on graph_viz.py and query execution

## Coverage Matrix

| Invariant | Priority | Existing Coverage | Gap Type | Action Required |
|-----------|----------|-------------------|----------|-----------------|
| Missing tenant context → 400 | P0 | ✅ test_graph_viz_security_boundaries.py | None | - |
| Cross-tenant data access blocked | P0 | ✅ test_endpoint_tenant_isolation.py | None | - |
| Unscoped Cypher queries blocked | P0 | ✅ test_cypher_scope_guard.py | None | - |
| Query depth > MAX_QUERY_DEPTH → 422 | P1 | ⚠️ Unit tests only | Integration | Add route-level depth validation tests |
| Query timeout → CYPHER_TIMEOUT code | P1 | ❌ Missing | Full | Add timeout handling tests |
| Relationship type injection blocked | P1 | ✅ test_graph_viz_security_boundaries.py | None | - |
| Entity-not-found → 404 (not 403) | P1 | ✅ test_graph_viz_security_boundaries.py | None | - |
| Neo4j unavailability → 503 | P1 | ✅ test_graph_viz_security_boundaries.py | None | - |
| Empty tenant_id in context → 400 | P2 | ✅ test_graph_viz_security_boundaries.py | None | - |
| Malformed tenant_id → rejected | P2 | ❌ Missing | Full | Add tenant_id format validation tests |

## Critical Gaps (P1 - High Priority)

### Gap 1: Query Timeout Integration Tests
**Invariant**: Query timeout enforced to prevent resource exhaustion
**Current State**: No integration tests verify timeout behavior
**Impact**: DoS vulnerability via long-running queries
**Required Tests**:
- Positive: Query completing within timeout returns 200
- Negative: Query exceeding timeout returns 400 with CYPHER_TIMEOUT code
- Adversarial: Malicious query with deep traversal blocked by timeout

### Gap 2: Route-Level Depth Validation
**Invariant**: Query depth must not exceed MAX_QUERY_DEPTH
**Current State**: Unit tests exist for `TenantQueryExecutor._extract_max_depth`, but no route-level tests
**Impact**: Bypass possible if FastAPI Query validation fails
**Required Tests**:
- Integration: `/entities/{id}/subgraph` with depth=11 returns 422
- Integration: `/v1/graph/subgraph` with depth=11 returns 422
- Positive: Valid depth values (1-10) accepted

## Medium Gaps (P2 - Medium Priority)

### Gap 3: Tenant ID Format Validation
**Invariant**: Malformed tenant_id must be rejected
**Current State**: No tests for invalid tenant_id formats
**Impact**: Potential injection or bypass with malformed IDs
**Required Tests**:
- Negative: Empty string tenant_id rejected
- Negative: tenant_id with special characters rejected
- Negative: tenant_id with SQL injection patterns rejected
- Positive: Valid UUID tenant_id accepted

## Additional Observations

### Strengths
- Comprehensive tenant isolation coverage across multiple test files
- Good coverage for Cypher query validation (scope guard)
- Security boundary tests for graph_viz routes are well-structured

### Weaknesses
- Missing timeout integration tests (critical for DoS prevention)
- Route-level parameter validation needs more coverage
- No tests for malformed tenant_id formats
- Limited adversarial test cases for injection patterns

### Test Quality Issues
- Some tests use mocks that may not reflect real Neo4j behavior
- Integration tests marked with `@pytest.mark.integration` may not run in CI
- Missing regression tests for discovered violations

## Recommended Test Engineering Plan

### Phase 1: Critical Gap Closure (P1)
1. Add timeout integration tests to `test_graph_viz_security_boundaries.py`
2. Add route-level depth validation tests
3. Verify timeout error code matches contract (CYPHER_TIMEOUT)

### Phase 2: Medium Priority (P2)
4. Add tenant_id format validation tests
5. Add adversarial injection tests for tenant_id parameter
6. Add regression tests for any discovered violations

### Phase 3: Cross-Layer Verification
7. Verify timeout behavior consistent across all layers
8. Verify depth limits consistent across all graph traversal endpoints
9. Verify tenant_id validation consistent across all services

## Risk Assessment

| Gap | Security Impact | Exploitability | Remediation Effort | Priority |
|-----|-----------------|----------------|-------------------|----------|
| Query timeout | High (DoS) | Medium | Low | P1 |
| Route-level depth validation | Medium (DoS) | Low | Low | P1 |
| Tenant ID format validation | Low (injection) | Low | Low | P2 |

## Next Steps

Proceed to Phase 4: Autonomous Test Engineering to implement missing tests.
