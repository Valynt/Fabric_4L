# Layer 2 Test Inventory

Generated: 2026-05-28

## Backend Tests
| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| Layer 2 Extraction | 1 unit test | 47 integration tests | 4 security tests | 0 E2E tests |

## Test Categories

### Unit Tests (1 file)
- test_celery_tasks.py

### Integration Tests (47 files)
- test_api_key_resolver_hostile_cases.py
- test_api_rate_limit_contract.py
- test_api_route_topology.py
- test_api_tenant_propagation.py
- test_artifact_completeness.py
- test_artifact_metadata_contracts.py
- test_cache.py
- test_chunker.py
- test_coreference_resolver.py
- test_coreference_tier_llmclient.py
- test_cross_tenant_hostile.py
- test_cross_tenant_hostile_behavioral.py
- test_deduplicator.py
- test_deduplicator_extended.py
- test_deduplicator_full.py
- test_deterministic_ids.py
- test_extract_and_ingest_pipeline.py
- test_extraction.py
- test_extraction_cache.py
- test_extraction_entities_endpoint.py
- test_i03_llm_client_production_safety.py
- test_job_store.py
- test_l2_l3_pipeline_integration.py
- test_llm_cost_metrics.py
- test_llm_extractor.py
- test_missing_tenant_context_hostile.py
- test_ontology_alignment.py
- test_pending_ingestion_store.py
- test_production_fail_closed_i02.py
- test_prompt_loader.py
- test_prompt_template_metadata_propagation.py
- test_provenance.py
- test_quarantine_flow.py
- test_runtime_store_bindings.py
- test_security_guard.py
- test_semantic_aligner.py
- test_signal_lifecycle_service.py
- test_sse_streaming.py
- test_sse_streaming_behavior.py
- test_startup_dependencies.py
- test_startup_dependency_verifier.py
- test_structured_logging_smoke.py
- test_tier_policy.py
- test_validation.py
- test_value_metric.py

### Security Tests (4 files)
- test_api_key_resolver_hostile_cases.py
- test_cross_tenant_hostile.py
- test_cross_tenant_hostile_behavioral.py
- test_missing_tenant_context_hostile.py

## Key Invariants Discovered

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: RequestContext, require_authenticated from shared.identity
- **Code Path**: `src/layer2_extraction/api/deps.py`

### Tenant Context
- **Rule**: Tenant context must be propagated through extraction pipeline
- **Enforcement**: RequestContext passed through extraction jobs
- **Code Path**: `src/layer2_extraction/api/deps.py`, integration layer

### Input Validation
- **Rule**: No unvalidated input reaching LLM calls or persistence
- **Enforcement**: Pydantic schemas, validation module
- **Code Path**: `src/layer2_extraction/validation/`

### LLM Safety
- **Rule**: LLM calls must have cost tracking and prompt versioning
- **Enforcement**: LLMCall tracking, provenance tracking
- **Code Path**: `src/layer2_extraction/output/provenance.py`

### Quarantine Flow
- **Rule**: Failed extractions must be quarantined with tenant isolation
- **Enforcement**: QuarantineStore with tenant_id scoping
- **Code Path**: `src/layer2_extraction/integration/quarantine_store.py`

## Test Markers
- `@pytest.mark.asyncio` - Async test functions (SSE streaming, async operations)

## Discovery Notes
- Layer 2 has fewer dedicated security tests (4) compared to Layer 1 (14)
- Strong focus on extraction pipeline validation and provenance tracking
- Good coverage of cross-tenant hostile scenarios
- LLM integration safety tests present
- SSE streaming tests for real-time extraction updates
- Tenant context propagation tested via hostile test cases
