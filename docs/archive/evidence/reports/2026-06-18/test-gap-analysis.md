# Test Gap Analysis

Generated: 2026-05-27

## Critical Gaps by Invariant

### Tenant Isolation

| Invariant | Positive Tests | Negative Tests | Adversarial Tests | Gap |
|-----------|----------------|----------------|-------------------|-----|
| No cross-tenant reads/writes | ✅ layer1, layer2, layer4 | ✅ layer1, layer2 | ⚠️ layer7-billing missing | **P0** |
| Tenant context immutability | ⚠️ Limited coverage | ❌ Missing | ❌ Missing | **P1** |
| Storage key normalization | ❌ Missing | ❌ Missing | ❌ Missing | **P1** |

### Authentication

| Invariant | Positive Tests | Negative Tests | Adversarial Tests | Gap |
|-----------|----------------|----------------|-------------------|-----|
| No unauthenticated access | ✅ api layer | ✅ api layer | ⚠️ layer4-agents partial | **P1** |
| No authorization bypass | ✅ api layer | ⚠️ Limited | ❌ Missing | **P1** |
| JWT token validation | ✅ api layer | ✅ api layer | ⚠️ Missing edge cases | **P2** |

### Input Validation

| Invariant | Positive Tests | Negative Tests | Adversarial Tests | Gap |
|-----------|----------------|----------------|-------------------|-----|
| Pydantic schema validation | ✅ layer6, layer7 | ⚠️ layer7-billing limited | ❌ Missing | **P1** |
| Password security | ✅ api layer | ✅ api layer | ⚠️ Missing brute force tests | **P2** |

### Database Isolation

| Invariant | Positive Tests | Negative Tests | Adversarial Tests | Gap |
|-----------|----------------|----------------|-------------------|-----|
| tenant_id NOT NULL | ✅ layer5 validation | ⚠️ Limited | ❌ Missing | **P1** |
| RLS policy enforcement | ✅ layer5 validation | ⚠️ Limited | ❌ Missing | **P1** |
| get_db_from_context usage | ⚠️ CI lint only | ❌ Runtime tests | ❌ Missing | **P1** |

### Async Task Propagation

| Invariant | Positive Tests | Negative Tests | Adversarial Tests | Gap |
|-----------|----------------|----------------|-------------------|-----|
| Tenant context in Celery | ✅ layer1 security | ⚠️ L1→L2 dispatch new | ❌ Missing | **P1** |
| Message queue tenant_id | ⚠️ Limited | ❌ Missing | ❌ Missing | **P1** |

### Cross-Service Communication

| Invariant | Positive Tests | Negative Tests | Adversarial Tests | Gap |
|-----------|----------------|----------------|-------------------|-----|
| Header propagation | ❌ Missing | ❌ Missing | ❌ Missing | **P0** |
| L1→L2 Celery dispatch | ✅ Configuration tests | ❌ Runtime tests | ❌ Missing | **P1** |
| API contract stability | ✅ OpenAPI drift check | ⚠️ Limited | ❌ Missing | **P2** |

## Layer-Specific Critical Gaps

### layer7-billing (P0 - Critical Path)

**Missing Tests:**
1. **Tenant isolation for billing operations** - No cross-tenant tests for plan creation, usage events, invoices
2. **Adversarial billing manipulation** - No tests for:
   - Cross-tenant plan access
   - Usage event injection
   - Invoice tampering
3. **Rate limiting for billing API** - No tenant-scoped rate limiting tests
4. **Input validation for billing payloads** - Limited Pydantic validation tests

**Impact:** Billing/metering is critical revenue path with minimal security test coverage.

### layer1-ingestion (P1 - High Priority)

**Missing Tests:**
1. **L1→L2 Celery dispatch runtime validation** - Only configuration tests exist
2. **Celery fallback to HTTP on failure** - No tests for fallback path
3. **Cross-tenant Celery task isolation** - Limited coverage
4. **Rate limiting for ingestion API** - No tenant-scoped rate limiting tests

### layer2-extraction (P1 - High Priority)

**Missing Tests:**
1. **Celery task tenant context propagation** - New tasks lack tenant isolation tests
2. **Extraction cache tenant isolation** - Limited cross-tenant cache tests
3. **LLM cost metrics tenant scoping** - No cross-tenant cost leak tests

### layer4-agents (P1 - High Priority)

**Missing Tests:**
1. **Agent output tenant scoping** - No tests for cross-tenant agent result leakage
2. **Agent tool call authorization** - Limited adversarial testing
3. **LangGraph workflow tenant context** - No end-to-end tenant isolation tests

### layer5-ground-truth (P2 - Medium Priority)

**Missing Tests:**
1. **TruthObject validation tenant isolation** - Limited cross-tenant validation
2. **Maturity ladder tenant scoping** - No cross-tenant access tests

### layer6-benchmarks (P2 - Medium Priority)

**Missing Tests:**
1. **Benchmark data tenant isolation** - No cross-tenant benchmark leak tests
2. **Peer comparison tenant scoping** - No cross-tenant comparison tests

## Integration Test Gaps

### Cross-Layer Integration

| Integration | Test Coverage | Gap |
|-------------|---------------|-----|
| L1 → L2 Celery dispatch | ⚠️ Configuration only | **P1** - Runtime validation missing |
| L2 → L3 Graph ingestion | ⚠️ Limited | **P1** - End-to-end tenant isolation missing |
| L3 → L4 Agent queries | ❌ Missing | **P0** - No cross-layer tenant isolation tests |
| L4 → L5 Validation | ❌ Missing | **P1** - No validation path tests |
| L5 → L6 Benchmarking | ❌ Missing | **P2** - No benchmark integration tests |

### Backend-Integrated E2E

**Status:** No backend-integrated E2E tests exist (only frontend Playwright)

**Gap:** **P0** - Critical production flows lack end-to-end validation:
- Full ingestion → extraction → validation pipeline
- Agent workflow execution with tenant isolation
- Billing/metering end-to-end flow

## Adversarial Test Gaps

### Missing Adversarial Scenarios

1. **Header Injection Attacks**
   - x-tenant-id header manipulation
   - x-fabric-tenant-id signature bypass
   - Missing tenant context exploitation

2. **Parameter Pollution**
   - tenant_id parameter injection in query strings
   - Multiple tenant_id values in payloads
   - tenant_id in unexpected fields

3. **Race Conditions**
   - Concurrent cross-tenant access attempts
   - Tenant context switching during request
   - Async context leakage

4. **Privilege Escalation**
   - Role manipulation in JWT tokens
   - Admin bypass attempts
   - Impersonation beyond allowed scope

5. **Resource Exhaustion**
   - Tenant-scoped rate limit bypass
   - Celery queue flooding
   - Storage quota exhaustion

## Regression Test Gaps

### Historical Violations Without Regression Tests

1. **organization_id → tenant_id rename** - Migration 006 fixed RLS, but no regression tests prevent reversion
2. **Direct header access** - Anti-pattern deprecated but no CI enforcement tests
3. **get_db() usage** - Lint enforcement exists but no runtime validation tests
4. **Celery tenant context** - Historical issues but no comprehensive regression suite

## Priority Summary

### P0 - Critical (Fix Immediately)
1. layer7-billing tenant isolation tests
2. Backend-integrated E2E tests
3. Cross-layer tenant isolation tests (L3→L4)

### P1 - Material (Fix Soon)
1. L1→L2 Celery dispatch runtime validation
2. Storage key normalization tests
3. get_db_from_context runtime validation
4. Adversarial header injection tests
5. layer4-agents output tenant scoping

### P2 - Improvement (Nice to Have)
1. JWT edge case tests
2. Password brute force tests
3. layer5/layer6 cross-tenant tests
4. API contract adversarial tests

## Recommended Test Engineering Strategy

### Phase 1: Critical Path Security (P0)
1. Add layer7-billing cross-tenant isolation tests
2. Add backend-integrated E2E test suite
3. Add L3→L4 cross-layer tenant isolation tests

### Phase 2: Cross-Service Validation (P1)
1. Add L1→L2 Celery dispatch runtime tests
2. Add storage key normalization tests
3. Add get_db_from_context runtime validation
4. Add adversarial header injection tests

### Phase 3: Layer-Specific Hardening (P1)
1. Add layer4-agents output tenant scoping tests
2. Add layer2-extraction Celery task tenant context tests
3. Add layer1-ingestion rate limiting tests

### Phase 4: Adversarial Coverage (P2)
1. Add JWT edge case tests
2. Add password brute force tests
3. Add race condition tests
4. Add privilege escalation tests
