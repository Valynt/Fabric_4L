# Test Gap Analysis

Generated: 2026-05-28

## Executive Summary

The repository has strong security test coverage with 200+ tenant isolation tests and adversarial test suites across most layers. However, **critical gaps exist** for recent bug fixes related to trace ID sanitization, generator parameter consistency, and Celery task naming.

**Priority: P0** - Tests for recently fixed bugs must be added to prevent regression.

---

## Gap Analysis by Invariant

### 1. Tenant Isolation

**Status:** ✅ WELL COVERED

**Existing Tests:**
- `services/layer1-ingestion/tests/security/test_celery_tenant_isolation_postgres.py`
- `services/layer1-ingestion/tests/security/test_tenant_isolation_bypass_attempts_postgres.py`
- `services/layer4-agents/tests/test_tenant_isolation.py`
- `services/layer3-knowledge/tests/test_tenant_isolation.py`
- `services/layer5-ground-truth/tests/test_cross_tenant_hostile.py`
- `services/layer6-benchmarks/tests/test_cross_tenant_hostile.py`

**Gap:** None - comprehensive coverage across all layers

---

### 2. Authentication

**Status:** ✅ WELL COVERED

**Existing Tests:**
- `services/api/app/tests/test_auth_enforcement.py`
- `services/layer4-agents/tests/test_authorization_adversarial.py`
- `services/layer4-agents/tests/conftest_auth.py`

**Gap:** None

---

### 3. Authorization

**Status:** ✅ WELL COVERED

**Existing Tests:**
- `services/layer4-agents/tests/test_authorization_adversarial.py`
- `services/layer5-ground-truth/tests/test_route_scope_authorization.py`

**Gap:** None

---

### 4. Input Validation

**Status:** ✅ WELL COVERED

**Existing Tests:**
- `services/layer4-agents/tests/test_input_validation_adversarial.py`
- `services/layer2-extraction/tests/test_api_key_resolver_hostile_cases.py`

**Gap:** None

---

### 5. Trace ID Sanitization

**Status:** ⚠️ CRITICAL GAP - P0

**Recent Fix (2026-05-28):**
- Restored `sanitize_trace_id()` call in `packages/shared/src/value_fabric/shared/error_handling/middleware.py:60`
- Fixed generator parameter inconsistency in `packages/shared/src/value_fabric/shared/observability/trace_context.py:38`

**Existing Tests:**
- `packages/shared/src/value_fabric/shared/error_handling/tests/test_error_handling.py:283-300` - Tests `_sanitize_trace_id` function
- `packages/shared/src/value_fabric/shared/error_handling/tests/test_error_handling.py:332-337` - Tests middleware rejects invalid characters

**Gap:**
- ❌ No test specifically for the **regression** where sanitization was removed
- ❌ No test for generator parameter consistency in `resolve_trace_context`
- ❌ No adversarial test for malicious trace IDs with null bytes, SQL injection patterns

**Required Tests:**
1. Regression test: Verify middleware always calls `sanitize_trace_id`
2. Adversarial test: Trace ID with null bytes (`\x00`) is rejected
3. Adversarial test: Trace ID with SQL injection patterns (`' OR 1=1 --`) is rejected
4. Generator parameter test: Verify generator is passed through when invalid ID triggers regeneration

---

### 6. Celery Task Dispatch

**Status:** ⚠️ CRITICAL GAP - P0

**Recent Fix (2026-05-28):**
- Restored full task name `"layer2_extraction.shared.tasks.run_extraction_task"` in `services/layer1-ingestion/src/shared/tasks.py:802`

**Existing Tests:**
- `services/layer1-ingestion/tests/unit/test_l2_celery_dispatch.py:103-131` - Tests task dispatched with fully qualified name

**Gap:**
- ❌ Test exists but may not verify the **regression** (short name would fail)
- ❌ No integration test with actual Celery worker to verify task registration
- ❌ No test for HTTP fallback when Celery dispatch fails

**Required Tests:**
1. Regression test: Verify short task name would cause NotRegistered error
2. Integration test: Verify task is registered with full name in Celery app
3. Fallback test: Verify HTTP fallback triggers on Celery failure

---

### 7. Error Handling

**Status:** ✅ WELL COVERED

**Existing Tests:**
- `packages/shared/src/value_fabric/shared/error_handling/tests/test_error_handling.py` - Comprehensive error envelope tests
- `services/api/app/tests/test_production_safety.py` - Production error safety

**Gap:** None

---

### 8. Database Session Management

**Status:** ✅ WELL COVERED

**Existing Tests:**
- `services/layer7-billing/tests/test_tenant_isolation.py:195-284` - Tests `db_session_for_context` behavior
- `services/layer4-agents/tests/test_database_session_tenant_enforcement.py`

**Gap:** None

---

### 9. Rate Limiting

**Status:** ✅ WELL COVERED

**Existing Tests:**
- `services/layer4-agents/tests/test_tenant_rate_limits.py`
- `services/layer4-agents/tests/test_rate_limiting_edge_cases.py`

**Gap:** None

---

### 10. OpenTelemetry Tracing

**Status:** ⚠️ MODERATE GAP

**Recent Changes:**
- L3 migrated from custom tracing to OpenTelemetry SDK
- Custom tracer deleted, middleware rewritten

**Existing Tests:**
- `services/layer3-knowledge/tests/test_trace_context_propagation_integration.py`
- `services/layer4-agents/tests/test_agent_workflow_traceability.py`

**Gap:**
- ❌ No tests verify OTel span attributes match previous custom tracer
- ❌ No tests verify trace ID propagation across OTel spans
- ❌ No tests for OTel instrumentation on all L3 routes

**Required Tests:**
1. OTel span attribute test: Verify tenant_id, route, method are set on spans
2. Trace propagation test: Verify trace ID spans across service boundaries
3. Instrumentation coverage test: Verify all routes have OTel instrumentation

---

## Critical Test Gaps Summary

| Priority | Invariant | Gap | Impact |
|----------|-----------|-----|--------|
| P0 | Trace ID Sanitization | Missing regression test for removed sanitization | Security regression |
| P0 | Trace ID Sanitization | Missing adversarial tests for null bytes, SQL injection | Security vulnerability |
| P0 | Trace ID Sanitization | Missing generator parameter consistency test | Contract violation |
| P0 | Celery Task Dispatch | Missing regression test for short task name | L1→L2 dispatch failure |
| P1 | OpenTelemetry Tracing | Missing OTel span attribute tests | Observability regression |
| P1 | OpenTelemetry Tracing | Missing trace propagation tests | Distributed tracing breakage |

## Recommended Test Additions

### P0 - Trace ID Sanitization Regression Tests

**File:** `packages/shared/src/value_fabric/shared/error_handling/tests/test_trace_id_sanitization_regression.py`

```python
def test_middleware_always_sanitizes_trace_id():
    """Regression test: middleware must call sanitize_trace_id even after refactors."""
    # Verify the middleware code path includes sanitization
    # This test should fail if sanitization is removed again

def test_trace_id_with_null_bytes_rejected():
    """Adversarial test: null bytes in trace ID should be rejected."""
    # Test with \x00 in trace ID header
    # Verify new ID is generated instead

def test_trace_id_with_sql_injection_rejected():
    """Adversarial test: SQL injection patterns in trace ID should be rejected."""
    # Test with ' OR 1=1 -- in trace ID header
    # Verify sanitized or regenerated

def test_generator_parameter_passed_on_invalid_id():
    """Verify generator parameter is used when invalid ID triggers regeneration."""
    # Test with custom generator and invalid trace ID
    # Verify regenerated ID uses custom generator
```

### P0 - Celery Task Dispatch Regression Tests

**File:** `services/layer1-ingestion/tests/unit/test_l2_celery_dispatch_regression.py`

```python
def test_short_task_name_causes_not_registered():
    """Regression test: short task name should fail with NotRegistered."""
    # Test that "run_extraction_task" (without module path) fails
    # This prevents future accidental use of short names

def test_full_task_name_registered_in_celery_app():
    """Integration test: verify full task name is registered in L2 Celery app."""
    # Check L2 Celery app registry for full task name
    # Verify task is discoverable

def test_http_fallback_on_celery_failure():
    """Test HTTP fallback triggers when Celery dispatch fails."""
    # Mock Celery send_task to raise exception
    # Verify HTTP fallback is attempted
```

### P1 - OpenTelemetry Tracing Tests

**File:** `services/layer3-knowledge/tests/test_otel_tracing_contract.py`

```python
def test_otel_span_includes_tenant_id():
    """Verify OTel spans include tenant_id attribute."""
    # Make request with tenant context
    # Verify span has tenant_id attribute

def test_otel_span_includes_route_and_method():
    """Verify OTel spans include route and method attributes."""
    # Make request to specific route
    # Verify span has route and method attributes

def test_trace_id_propagates_across_spans():
    """Verify trace ID is consistent across child spans."""
    # Make request that creates multiple spans
    # Verify all spans have same trace_id
```

## Test Coverage Metrics

**Current Coverage Estimate:**
- Backend: ~85% (strong security/tenant isolation coverage)
- Frontend: ~70% (component tests, some E2E)
- Critical Invariants: ~90% (most invariants covered)
- Recent Fixes: **0%** (no regression tests for P0 fixes)

**Target Coverage:**
- Backend: 95%
- Frontend: 85%
- Critical Invariants: 100%
- Recent Fixes: 100% (regression tests mandatory)

## Next Steps

1. **Immediate (P0):** Add regression tests for trace ID sanitization and Celery task naming
2. **Short-term (P1):** Add OpenTelemetry tracing contract tests
3. **Medium-term:** Expand adversarial test coverage for all invariants
4. **Long-term:** Achieve 95% backend test coverage with automated coverage gating
