# Layer 1 Test Inventory

Generated: 2026-05-28

## Backend Tests
| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| Layer 1 Ingestion | 31 unit tests | 3 integration tests | 14 security tests | 0 E2E tests |

## Test Categories

### Unit Tests (31 files)
- test_adapters.py
- test_batch_operations.py
- test_canonical_imports.py
- test_celery_dispatch_regression.py
- test_celery_tasks.py
- test_content_extractor.py
- test_crawler_config.py
- test_crawler_telemetry.py
- test_database_optional_tenant_security.py
- test_event_outbox.py
- test_h03_security_config.py
- test_import_surface.py
- test_l2_celery_dispatch.py
- test_m02_exception_remediation.py
- test_models.py
- test_pdf_adapter.py
- test_pii_scanner.py
- test_playwright_crawler.py
- test_quality_gate.py
- test_robots_checker_modes.py
- test_scheduler.py
- test_skill_list_endpoints.py
- test_smart_router.py
- test_source_intelligence_skills.py
- test_target_status_transitions.py
- test_task_unavailable_error_sanitization.py
- test_todo_placeholder_regressions.py
- test_url_safety_validator.py
- test_validation.py
- test_xbrl_parser_extended.py

### Security Tests (14 files)
- test_celery_tenant_isolation_postgres.py
- test_crawl_decisions_tenant_isolation_postgres.py
- test_global_robots_cache_isolation_postgres.py
- test_maintenance_tenant_enumeration.py
- test_production_gates_postgres.py
- test_require_tenant_false_allowlist_postgres.py
- test_rls_enforcement_postgres.py
- test_system_maintenance_authorization_postgres.py
- test_targets_tenant_isolation.py
- test_tenant_isolation_bypass_attempts_postgres.py
- test_url_safety_hostile.py
- conftest.py
- conftest_postgres.py

### Integration Tests (3 directories)
- api/ (6 test files)
- benchmarks/ (1 test file)
- contract/ (3 test files)
- crawler/ (4 test files)
- domain/ (3 test files)
- integration/ (3 test files)
- observability/ (1 test file)
- pipeline/ (1 test file)

## Key Invariants Discovered

### Tenant Isolation
- **Rule**: No cross-tenant reads or writes
- **Enforcement**: RLS policies via `SET LOCAL app.tenant_id`, GovernanceMiddleware
- **Code Path**: `src/shared/database.py`, `src/api/main.py`

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: GovernanceMiddleware, Fabric auth envelope
- **Code Path**: `src/api/main.py` (get_tenant_id, get_current_user_id)

### Authorization
- **Rule**: No authorization bypass via headers, params, body fields
- **Enforcement**: Role checks, super-admin validation for cross-tenant operations
- **Code Path**: `src/shared/database.py` (get_db_with_optional_tenant_sync)

### Input Validation
- **Rule**: No unvalidated input reaching persistence, queues, tools, or LLM calls
- **Enforcement**: Pydantic schemas, SecurityMiddleware
- **Code Path**: `src/api/main.py` (Pydantic models), SecurityMiddleware

### URL Safety
- **Rule**: Block localhost, metadata IPs, and internal network access
- **Enforcement**: URLSafetyError, validate_url_safety
- **Code Path**: `src/compliance/url_safety.py`

## Test Markers
- `@pytest.mark.requires_postgres` - Tests requiring PostgreSQL backend
- `@pytest.mark.asyncio` - Async test functions
- `@pytest.mark.parametrize` - Parameterized tests

## Discovery Notes
- Layer 1 has comprehensive security test coverage with 14 dedicated security test files
- Strong tenant isolation enforcement via RLS policies
- Fail-safe mode enabled for tenant context validation
- PostgreSQL-specific tests marked with `requires_postgres`
- Good coverage of adversarial scenarios (bypass attempts, injection, etc.)
