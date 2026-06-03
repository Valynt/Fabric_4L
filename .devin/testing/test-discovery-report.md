# Test Discovery Report

Generated: 2026-04-14

## Executive Summary

| Category | Count | Lines of Code |
|----------|-------|---------------|
| **Backend Python Tests** | 69 files | ~10,500 lines |
| **Frontend TypeScript Tests** | 263 files | TBD |
| **E2E Playwright Tests** | 9 files | TBD |
| **Total** | 341 files | ~12,000+ lines |

---

## Backend Test Inventory

### Layer 1: Ingestion (9 test files, 2,089 lines)

| File | Lines | Focus Area |
|------|-------|------------|
| test_adapters.py | 437 | SEC EDGAR, XBRL parsing, adapter registry |
| test_celery_tasks.py | 610 | Pipeline stages, retry behavior, error paths |
| test_crawler_config.py | 149 | Configuration validation, YAML loading |
| test_crawler_telemetry.py | 214 | Metrics, spans, tracing decorators |
| test_models.py | 113 | ScrapingJob, ScrapingTarget, RawContent |
| test_pdf_adapter.py | 572 | PDF processing, OCR, filing type detection |
| test_playwright_crawler.py | 451 | Browser automation, crawling |
| test_scheduler.py | 110 | Priority queue, round-robin scheduling |
| **test_celery_tasks.py** | *610* | *Largest file - complex pipeline tests* |

**Test Status**: 126 passed, 1 skipped (PDF health check requires Tesseract)

---

### Layer 2: Extraction (8 test files, 2,879 lines)

| File | Lines | Focus Area |
|------|-------|------------|
| test_chunker.py | 202 | Text chunking strategies |
| test_extract_and_ingest_pipeline.py | 546 | L2-L3 orchestration, status flow |
| test_extraction.py | 579 | Entity extraction, LLM integration |
| test_job_sse.py | 106 | Server-sent events for job status |
| test_llm_extractor.py | 91 | LLM client, prompt handling |
| test_ontology_alignment.py | 414 | Ontology mapping, alignment |
| test_sse_streaming.py | 372 | SSE streaming implementation |

**Test Status**: 127 passed, 1 skipped (requires OPENAI_API_KEY)

**Known Issues**:
- SSE streaming tests have deprecation warnings (`datetime.utcnow()`)
- FastAPI `on_event` deprecation warnings

---

### Layer 3: Knowledge (20 test files, 4,515 lines)

| File | Lines | Focus Area |
|------|-------|------------|
| test_api.py | 52 | Basic API health |
| test_config_import_surface.py | 28 | Config module exports |
| test_config.py | 370 | Settings validation |
| test_e2e_pipeline.py | 786 | End-to-end data pipeline |
| test_error_handling_integration.py | 278 | Error handling |
| test_exception_handlers.py | 66 | Exception middleware |
| test_exceptions.py | 509 | Custom exceptions |
| test_graphrag_endpoints.py | 328 | GraphRAG API |
| test_health_endpoints.py | 184 | Health checks |
| test_hybrid_search_api_compat.py | 78 | Hybrid search |
| test_ingestion_endpoints.py | 309 | Ingestion API |
| test_ingestion.py | 86 | Data ingestion |
| test_neo4j_integration.py | 311 | Neo4j connectivity |
| test_neo4j_schema_integration.py | 256 | Schema management |
| test_required_field_validator.py | 199 | Validation logic |
| test_retrieval.py | 52 | Data retrieval |
| test_scenario_engine.py | 198 | Scenario evaluation |
| test_search_endpoints.py | 251 | Search API |
| test_vector_e2e.py | 655 | Vector search E2E |
| test_versioning_registration.py | 102 | Entity versioning |

**Test Status**: ⚠️ **~20 GraphRAG endpoint tests failing**

**Known Issues**:
- GraphRAG endpoint tests fail on invalid params, empty queries
- Neo4j Community edition compatibility issues (enterprise-only constraints)
- Logger misuse with structured kwargs

---

### Layer 4: Agents (20 test files, 6,972 lines)

| File | Lines | Focus Area |
|------|-------|------------|
| test_accounts_api.py | 634 | Account sync API |
| test_c1_proxy.py | 160 | C1 proxy integration |
| test_checkpoint_resume_failure_paths.py | 414 | Checkpoint error handling |
| test_checkpoint_resume.py | 495 | Checkpoint/resume core |
| test_code_quality.py | 91 | Code quality checks |
| test_crm_sync_service.py | 656 | CRM synchronization |
| test_feature_flags.py | 422 | Feature flag system |
| test_health_tracker.py | 317 | Health monitoring |
| test_interfaces_exports.py | 190 | Module exports |
| test_langgraph_execution.py | 821 | LangGraph workflows |
| test_llm_budget_guardrails.py | 51 | Budget controls |
| test_llm_cost_metrics.py | 171 | Cost tracking |
| test_messaging.py | 486 | Message bus |
| test_model_registry.py | 291 | Model management |
| test_notification.py | 304 | Notification system |
| test_oidc.py | 317 | OIDC authentication |
| test_provenance.py | 413 | Data lineage |
| test_websocket_manager.py | 693 | WebSocket management |
| test_workflow_controls.py | 449 | Workflow controls |
| test_workflows_real_execution.py | 198 | Real workflow execution |

**Test Status**: ⚠️ **4 failed, 345 passed**

**Known Issues**:
- `test_get_checkpoint_saver_returns_none_on_failure` - Database unavailable
- ModuleNotFoundError importing 'src' during test collection
- AsyncMockMixin coroutine warnings

---

### Layer 5: Ground Truth (3 test files, 1,193 lines)

| File | Lines | Focus Area |
|------|-------|------------|
| test_api.py | 418 | API endpoints |
| test_freshness_monitor.py | 357 | Data freshness |
| test_state_machine.py | 418 | State machine logic |

**Test Status**: Not yet collected

---

### Layer 6: Benchmarks (1 test file)

**Test Status**: Not yet collected

---

### Cross-Layer: tests/ Directory (13 test files, 1,983 lines)

| File | Lines | Focus Area |
|------|-------|------------|
| test_tenant_architecture.py | 161 | Tenant isolation |
| test_testability_architecture.py | 143 | Test architecture |
| test_api_main_architecture.py | 43 | API structure |
| test_l2_l3_contract.py | 94 | L2-L3 contracts |
| test_l3_formulas_contract.py | 151 | Formula contracts |
| test_l3_graph_contract.py | 262 | Graph API contracts |
| test_l3_value_trees_contract.py | 195 | Value tree contracts |
| test_l4_frontend_contract.py | 189 | L4-Frontend contracts |
| test_l4_workflows_contract.py | 205 | Workflow contracts |
| test_tool_manifests.py | 70 | Tool manifest validation |
| test_evaluate_formula.py | 99 | Formula evaluation |
| test_semantic_search.py | 67 | Semantic search |
| test_billing_entitlements_regression.py | 308 | Billing regression |

**Test Status**: ✅ 83 passed

---

## Frontend Test Inventory

### Unit/Integration Tests: 263 files

Located in `frontend/client/src/**/*.test.ts(x)`

**Notable patterns from memory**:
- `useValuePacks.test.tsx` - Recently refined with `createMockResponse<T>()` factory
- `client.test.ts` - Recently refined with `spyAndSuppress()` helper
- `test-utils.tsx` - Shared test utilities with `createWrapperWithRetry()`

### E2E Tests: 9 files

Located in `frontend/e2e/*.spec.ts`

**Recent additions**:
- `navigation.spec.ts` - Advanced Mode toggle tests
- `tier-helpers.ts` - `enableAdvancedMode()` / `disableAdvancedMode()` helpers

---

## Test Framework Configuration

### Backend (Python)

**Framework**: pytest with plugins:
- `pytest-asyncio` - Async test support
- `pytest-mock` - Mocking utilities
- `respx` - HTTPX mocking
- `anyio` - Async I/O backends
- `langsmith` - LangChain tracing

**Configuration**:
- Layer 3: `pytest.ini` (WARNING: ignores pyproject.toml)
- Other layers: `pyproject.toml`

**Markers Used**:
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.unit` - Fast, no external deps
- `@pytest.mark.integration` - Requires services
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.e2e` - End-to-end tests

### Frontend (TypeScript)

**Framework**: Vitest + React Testing Library

**Configuration**:
- `frontend/vitest.config.ts`
- React Testing Library for component tests
- MSW for API mocking
- Playwright for E2E

---

## Current `make verify` Status

| Check | Status | Notes |
|-------|--------|-------|
| Lint (ruff) | ✅ PASS | All 6 layers clean |
| Typecheck (mypy) | ❌ FAIL | 809 errors (SQLAlchemy/Pydantic issues) |
| L1 Tests | ✅ PASS | 126 passed, 1 skipped |
| L2 Tests | ✅ PASS | 127 passed, 1 skipped |
| L3 Tests | ❌ FAIL | ~20 GraphRAG endpoint failures |
| L4 Tests | ⚠️ PARTIAL | 345 passed, 4 failed |
| Contract Tests | ✅ PASS | 83 passed |
| Deprecations | ✅ PASS | 0 overdue |

---

## Pre-Existing Failures Inventory

### Layer 3
1. `test_graphrag_endpoint_invalid_max_results` - Invalid param handling
2. `test_graphrag_endpoint_empty_query` - Empty query handling
3. `test_graphrag_endpoint_different_hop_types` - Hop type variations
4. `test_graphrag_response_structured` - Response format

*Root Cause*: Endpoint returning 404s instead of 200s, mock response issues

### Layer 4
1. `test_get_checkpoint_saver_returns_none_on_failure` - CheckpointConnectionError

*Root Cause*: Database unavailable during test (infrastructure, not code)

### Type Errors (809 total)
- `Column[datetime]` vs `datetime` type mismatches
- Missing return type annotations
- SQLAlchemy 2.0/Pydantic V2 compatibility issues

---

## Risk Assessment

### High Risk (Fix First)
1. **L3 GraphRAG tests** - Core API functionality
2. **L4 checkpoint tests** - Agent state management
3. **Type errors** - Blocking typecheck verification

### Medium Risk (Next Priority)
1. **Deprecation warnings** - `datetime.utcnow()` throughout L2
2. **FastAPI lifespan** - `on_event` deprecated, use `lifespan`

### Low Risk (Opportunistic)
1. **Test naming** - Weak names like `test_function1`
2. **Test structure** - AAA pattern not always obvious

---

## Next Steps for Audit

1. ✅ Discovery complete - 69 backend + 341 total test files cataloged
2. 🔄 Begin Phase 2 - Audit Layer 1 tests against quality principles
3. ⏳ Audit Layer 2-3 tests
4. ⏳ Audit Layer 4-6 + shared tests
5. ⏳ Audit frontend tests
6. ⏳ Create unified rewrite queue

---

## Appendix: Test File Lines of Code

### Backend Total by Layer

| Layer | Files | Lines | Avg/File |
|-------|-------|-------|----------|
| L1 Ingestion | 9 | 2,089 | 232 |
| L2 Extraction | 8 | 2,879 | 360 |
| L3 Knowledge | 20 | 4,515 | 226 |
| L4 Agents | 20 | 6,972 | 349 |
| L5 Ground Truth | 3 | 1,193 | 398 |
| L6 Benchmarks | 1 | TBD | - |
| Shared | 8 | TBD | - |
| Cross-layer | 13 | 1,983 | 152 |
| **Total** | **82** | **~19,631** | **239** |
