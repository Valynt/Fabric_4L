# Layer 3 Test Inventory

Generated: 2026-05-28

## Backend Tests
| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| Layer 3 Knowledge | 0 unit tests | 86 integration tests | 15 security tests | 0 E2E tests |

## Test Categories

### Integration Tests (86 files)
- test_account_authorization.py
- test_api.py
- test_api_tenant_propagation.py
- test_api_wrapper_startup_regression.py
- test_audited_graph_mutation.py
- test_audited_mutation.py
- test_audited_mutation_write_enforcement.py
- test_backup_runtime_bindings.py
- test_backup_tenant_scoping.py
- test_benchmark_policies_route.py
- test_cache_characterization.py
- test_cache_oss1_parity.py
- test_cache_ports.py
- test_canonical_endpoint_surface.py
- test_config.py
- test_config_import_surface.py
- test_cross_tenant_hostile.py
- test_cross_tenant_hostile_behavioral.py
- test_cypher_scope_remediation.py
- test_dil_phase1.py
- test_dil_phase2.py
- test_documents_error_shape.py
- test_e2e_pipeline.py
- test_embedding_dimension_policy.py
- test_entities_route_tenant_scoped_regression.py
- test_entity_resolution.py
- test_entrypoint_route_resolution_regression.py
- test_error_contract_adapter.py
- test_error_handling_integration.py
- test_evidence_embedding_failure.py
- test_evidence_links_tenant_isolation.py
- test_exception_handlers.py
- test_exception_mapping.py
- test_exceptions.py
- test_formula_dsl_security.py
- test_formula_governance_tenant_extraction.py
- test_graph_alias_deprecation_policy.py
- test_graph_viz_security_boundaries.py
- test_graphrag_endpoints.py
- test_health_endpoints.py
- test_hybrid_search_api_compat.py
- test_i03_variables_production_fail_closed.py
- test_ingestion.py
- test_ingestion_endpoints.py
- test_ingestion_route_docstring_policy.py
- test_knowledge_subgraph_routes.py
- test_l3_l4_cross_layer_tenant_isolation.py
- test_l3_tenant_isolation_migrated_modules.py
- test_layer3_compat_deprecation_phases.py
- test_layer3_compat_metrics_thresholds.py
- test_layer3_high_value_security_and_contract_gates.py
- test_layer3_route_tenant_dependency_regression.py
- test_monolith_route_delegation_guardrail.py
- test_neo4j_integration.py
- test_neo4j_schema_integration.py
- test_observability.py
- test_observability_contract_integration.py
- test_pack_loader.py
- test_packaged_system_routes.py
- test_query_execution_boundary.py
- test_query_execution_guard.py
- test_query_search_error_context.py
- test_query_validator.py
- test_required_field_validator.py
- test_retrieval.py
- test_roi_formula_security.py
- test_scenario_engine.py
- test_search_endpoints.py
- test_status_contract_alignment.py
- test_strict_builder_enforcement.py
- test_sync_manager_tenant_isolation.py
- test_system_routes.py
- test_tenant_context_extraction.py
- test_tenant_id_migration_expansion_labels.py
- test_tenant_isolation.py
- test_tenant_isolation_static.py
- test_tenant_read_isolation.py
- test_trace_context_propagation_integration.py
- test_value_packs.py
- test_value_packs_tenant_extraction.py
- test_valuepack_model_forwarder_guard.py
- test_vault_config_source.py
- test_vector_e2e.py
- test_vector_store_tenant_write_isolation.py
- test_versioning_registration.py

### Security Tests (15 files)
- test_account_authorization.py
- test_cross_tenant_hostile.py
- test_cross_tenant_hostile_behavioral.py
- test_formula_dsl_security.py
- test_formula_governance_tenant_extraction.py
- test_graph_viz_security_boundaries.py
- test_i03_variables_production_fail_closed.py
- test_l3_l4_cross_layer_tenant_isolation.py
- test_layer3_high_value_security_and_contract_gates.py
- test_query_execution_guard.py
- test_roi_formula_security.py
- test_tenant_isolation.py
- test_tenant_isolation_static.py
- test_tenant_read_isolation.py
- test_vector_store_tenant_write_isolation.py

## Key Invariants Discovered

### Tenant Isolation
- **Rule**: No cross-tenant reads or writes in Neo4j or vector store
- **Enforcement**: Neo4jTenantSessionSecured, tenant-scoped queries
- **Code Path**: `src/api/dependencies_tenant_secured.py`, `src/api/dependencies_tenant.py`

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: API key authentication, RequestContext
- **Code Path**: `src/auth/middleware.py`, `src/auth/api_keys.py`

### Authorization
- **Rule**: No authorization bypass via headers, params, body fields
- **Enforcement**: AuthorizationChecker, role-based access
- **Code Path**: `src/auth/middleware.py`

### Input Validation
- **Rule**: No unvalidated input reaching Neo4j queries or vector operations
- **Enforcement**: QueryValidator, Cypher scope remediation
- **Code Path**: `src/api/routes/_utils.py`, query validation modules

### Vector Store Security
- **Rule**: Vector operations must enforce tenant isolation
- **Enforcement**: Explicit tenant_id parameter, metadata stripping
- **Code Path**: `src/retrieval/`, vector store tenant scoping

## Test Markers
- `@pytest.mark.unit` - Unit test marker
- `@pytest.mark.asyncio` - Async test functions

## Discovery Notes
- Layer 3 has comprehensive security test coverage (15 security tests)
- Strong focus on tenant isolation in Neo4j and vector store
- Good coverage of cross-tenant hostile scenarios
- Query execution guard tests present
- Vector store tenant write isolation tests
- Graph visualization security boundary tests
- Layer 3-4 cross-layer tenant isolation tests
