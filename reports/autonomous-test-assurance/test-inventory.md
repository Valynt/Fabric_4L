# Test Inventory

Generated: 2026-05-22

## Backend Tests

### Layer 1 (Ingestion)
- Unit Tests: 15+ files (test_adapters, test_batch_operations, test_celery_tasks, etc.)
- Integration Tests: 5+ files (test_fast_path_pipeline, test_router_edge_cases, etc.)
- Security Tests: 3+ files (test_targets_tenant_isolation, test_url_safety_hostile, test_cross_tenant_hostile)
- Contract Tests: 1 file (test_l1_targets_openapi)

### Layer 2 (Extraction)
- Unit Tests: ~10 files
- Integration Tests: ~5 files
- Security Tests: 2+ files

### Layer 3 (Knowledge)
- Unit Tests: 2 files (test_graph_viz_security_boundaries, test_query_execution_guard)
- Integration Tests: Multiple in tests/layer3/
- Security Tests: tenant isolation, query execution guard
- **Active Files in IDE**: graph_viz.py, test_graph_viz_security_boundaries.py, test_query_execution_guard.py

### Layer 4 (Agents)
- Unit Tests: 30+ files (test_crm_webhook_auth_unit, test_fail_closed_authz_guards, test_tenant_isolation, etc.)
- Integration Tests: 10+ files
- Security Tests: 8+ files (test_security_fixes, test_tenant_isolation, test_agent_tenant_isolation, test_tools_authorization)

### Layer 5 (Ground Truth)
- Unit Tests: 5+ files (test_truth_object_validation, test_truth_object_tenant_id_required)
- Integration Tests: 10+ files (test_cross_tenant_hostile, test_tenant_id_consistency, test_transition_concurrency)
- Security Tests: 5+ files (test_security_fixes, test_route_scope_authorization, test_startup_environment_gating)

### Layer 6 (Benchmarks)
- Unit Tests: 5+ files (test_metrics_contract, test_benchmark_edge_cases, test_settings_validation)
- Integration Tests: 3+ files (test_benchmark_api, test_api_tenant_propagation)
- Security Tests: 3+ files (test_scope_authorization, test_repository_tenant_isolation, test_cross_tenant_hostile)

### API Gateway
- Unit Tests: 15+ files (test_auth_enforcement, test_tenant_isolation, test_jwks_and_token_validation)
- Security Tests: 8+ files (test_impersonation_security, test_production_safety, test_database_tenant_boundary)

## Frontend Tests

### Unit/Component Tests
- Count: 60+ files (*.test.ts)
- Framework: Vitest
- Coverage: hooks, components, API client, auth

### Integration Tests
- Count: 20+ contract tests (*.contract.test.ts)
- Framework: Vitest
- Coverage: API contracts, OpenAPI drift

### E2E Tests
- Count: Playwright tests
- Framework: Playwright
- Coverage: Auth, workflows, accessibility

## CI Gates

| Gate | Status | Command |
|------|--------|---------|
| structural-preflight | Active | .github/workflows/preflight.yml |
| per-layer lint/typecheck/test | Active | .github/workflows/pr-checks.yml |
| contract-checks | Active | .github/workflows/contract-compliance.yml |
| security-gates | Active | .github/workflows/security-gates.yml |
| mandatory tests | Active | scripts/test-python-production.sh --mandatory-only |
| backend-integrated | Active | .github/workflows/backend-integrated-reproducibility.yml |

## Discovery Notes

### Auth Patterns Discovered
- `require_request_tenant_id` dependency in L3 (tenant-scoped routes)
- `Depends()` pattern used extensively across all layers
- JWT token validation in API gateway
- OIDC integration in L4 tenants module

### Tenant Isolation Patterns
- RLS policies referenced in L5 migrations
- Tenant context propagation via headers (X-Tenant-ID)
- Query parameterisation for tenant scoping in Cypher queries
- Fail-closed behavior when tenant context missing

### Test Markers (pytest.ini)
- mandatory: CI gate tests (unit + contract + security)
- unit: Fast unit tests (<100ms)
- integration: Real dependencies
- security: OWASP Top 10
- tenant_boundary: Cross-tenant isolation tests
- contract_static: OpenAPI validation without live services
- service_required: Contract tests with live endpoints
- requires_postgres/redis/neo4j: Infrastructure-gated tests

### Anomalies
- L3 has minimal unit tests (2 files) despite being critical knowledge graph layer
- Active development on graph_viz.py security boundaries (recent test additions)
- RLS policy validation exists but may need expanded coverage
- Frontend has extensive contract tests but backend integration coverage varies by layer

### Current Focus (Based on Open Files)
- Layer 3 graph visualization security boundaries
- Query execution guard for tenant fail-closed behavior
- Cross-tenant access prevention in Neo4j queries
