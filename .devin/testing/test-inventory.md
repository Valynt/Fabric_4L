# Test Inventory - Fabric 4L

Generated: 2026-04-26

## Backend Tests

| Layer | Unit Tests | Integration Tests | Security Tests | Notes |
|-------|-----------|-------------------|----------------|-------|
| Layer 1 (Ingestion) | 15 | 2 | 0 | Fast path pipeline, router edge cases |
| Layer 2 (Extraction) | 9 | 1 | 0 | Extraction pipeline, SSE streaming |
| Layer 3 (Knowledge) | 28 | 4 | 3 | Neo4j schema, query validator, tenant isolation |
| Layer 4 (Agents) | 42 | 2 | 1 | Feature flags, tenant isolation, checkpoint/resume |
| Layer 5 (Ground Truth) | 6 | 1 | 0 | Model registry tests |
| Shared | 7 | 0 | 4 | MCP gateway auth security |
| Cross-layer (tests/) | 0 | 11 | 10 | OWASP Top 10, cross-layer tenant isolation |
| **Total** | **107** | **21** | **18** | |

## Frontend Tests

| Category | Count | Framework | Notes |
|----------|-------|-----------|-------|
| Unit/Component | 41 | Vitest | Hooks, components, contexts, services |
| E2E | 17 | Playwright | Feature specs across all major workflows |

## CI Gates

| Gate | Status | Command | Markers |
|------|--------|---------|---------|
| Unit | ✅ Active | `pytest -m unit -n auto` | `@pytest.mark.unit` |
| Integration | ✅ Active | `pytest -m integration --timeout=120` | `@pytest.mark.integration` |
| Security | ✅ Active | `pytest -m security --timeout=60` | `@pytest.mark.security` |
| Contract | ✅ Active | `pytest -m contract --timeout=60` | `@pytest.mark.contract` |
| Performance | ✅ Active | `pytest -m performance --timeout=300` | `@pytest.mark.performance` |
| E2E Smoke | ✅ Active | `pnpm exec playwright test` | Playwright specs |

## Test Distribution by Layer

### Layer 1 (Ingestion) - 15 tests
- `test_router_performance.py`
- `test_fast_path_pipeline.py` (integration)
- `test_router_edge_cases.py` (integration)
- `test_celery_tasks.py`
- `test_playwright_crawler.py`
- `test_pdf_adapter.py`
- `test_scheduler.py`

### Layer 2 (Extraction) - 9 tests
- `test_extract_and_ingest_pipeline.py` (integration)
- `test_extraction.py`
- `test_llm_extractor.py`
- `test_ontology_alignment.py`
- `test_sse_streaming.py`
- `test_tier_policy.py`

### Layer 3 (Knowledge) - 28 tests
- `test_tenant_isolation.py` (security)
- `test_tenant_read_isolation.py` (security)
- `test_tenant_context_extraction.py` (security)
- `test_neo4j_schema_integration.py` (integration)
- `test_e2e_pipeline.py` (integration)
- `test_query_validator.py`
- `test_graphrag_endpoints.py`
- `test_search_endpoints.py`
- `test_ingestion.py`
- `test_scenario_engine.py`

### Layer 4 (Agents) - 42 tests
- `test_tenant_isolation.py` (security + integration)
- `test_feature_flags.py`
- `test_phase3_control_plane.py`
- `test_model_registry.py`
- `test_workflow_controls.py`
- `test_case_permissions_and_audit.py`
- `test_tenant_lifecycle.py`
- `test_integration_service.py`

### Cross-layer Security Tests - 10 tests
- `test_owasp_top10_complete.py` (10 security tests)
- `test_cross_layer_tenant_isolation.py` (11 integration tests)
- `test_dil_security.py`

## Gaps Identified

1. **No dedicated authorization boundary tests** - Missing tests for role-based access control
2. **No RLS policy verification tests** - RLS migrations exist but no runtime verification
3. **No webhook idempotency tests** - Critical for operational safety
4. **Frontend auth guard tests incomplete** - Missing negative test coverage
5. **No secrets redaction tests** - Secrets protection not verified
6. **No input validation boundary tests** - Schema validation not tested adversarially
