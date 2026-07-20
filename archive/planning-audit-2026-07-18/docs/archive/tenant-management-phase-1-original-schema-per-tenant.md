# Fabric 4L — Phase 1 Implementation Plan: Core Isolation Upgrade (Schema-per-Tenant)

**Author:** Manus AI
**Date:** 2026-04-22
**Status:** Ready for Implementation
**Prerequisite:** Navigation Architecture Migration (complete, commit `ceb0390`)
**Depends On:** None (Phase 1 is the foundation for Phases 2 and 3)

---

## 1. Objective

Phase 1 replaces the current Row-Level Security (RLS) isolation strategy with a **schema-per-tenant** architecture across all five backend layers. Each tenant receives a dedicated PostgreSQL schema (e.g., `t_acme_corp`) containing their isolated tables, while the `public` schema retains shared metadata such as the tenant registry, tier definitions, and the global audit log. The migration leverages the `fastapi-tenancy` library (v0.4.0) to manage schema routing via SQLAlchemy's `schema_translate_map` execution options, eliminating the need for `SET LOCAL app.tenant_id` in every transaction [1] [2].

---

## 2. Current State Audit

### 2.1 Database Session Managers

The codebase contains three independent database session managers, each implementing the same RLS enforcement pattern. The following table summarizes their locations, driver types, and current isolation mechanisms.

| Layer | File | Driver | Session Type | Isolation Mechanism |
|-------|------|--------|-------------|---------------------|
| Layer 1 (Ingestion) | `layer1-ingestion/src/shared/database.py` | psycopg2 (sync) | `SessionLocal` | `SET LOCAL app.tenant_id` |
| Layer 4 (Agents) | `layer4-agents/src/database.py` | asyncpg (async) | `async_sessionmaker` | `SET LOCAL app.tenant_id` |
| Layer 5 (Ground Truth) | `layer5-ground-truth/src/.../database.py` | asyncpg (async) | `async_sessionmaker` | No RLS in session manager; RLS in migrations only |

Each manager exposes two FastAPI dependencies: `get_db()` for admin/health-check operations (no tenant context) and `get_db_with_tenant()` for tenant-scoped operations (requires `X-Tenant-ID` header). Layer 4 additionally provides a `db_session()` async context manager for background tasks and services.

### 2.2 RLS Policies in Place

Three migration files define RLS policies across the codebase. The policies follow a consistent pattern: `USING (tenant_id::text = current_setting('app.tenant_id', true))` with an admin bypass for roles `admin_role` and `system_role`.

| Migration | Layer | Tables Covered |
|-----------|-------|----------------|
| `004_add_rls_policies.py` | Layer 1 | `scraping_targets`, `scraping_jobs`, `raw_content`, `extracted_data`, `compliance_logs`, `proxy_pools`, `job_stage_details`, `job_errors` |
| `007_add_rls_policies.py` | Layer 4 | `accounts`, `account_contacts`, `account_notes`, `crm_sync_states`, `feature_flags`, `audit_events`, `oidc_sessions`, `model_registry` |
| `002_add_rls_policies.py` | Layer 5 | `truth_objects`, `truth_sources`, `validation_events`, `maturity_history` |

A fourth migration in Layer 5 (`003_add_model_registry.py`) adds ad hoc RLS policies on `model_versions`, `model_deployments`, and `model_evaluations` using a divergent `current_setting('app.current_org')` convention instead of the standard `app.tenant_id`.

### 2.3 Naming Inconsistencies

The tenant identifier column is named differently across layers. This inconsistency must be normalized before schema isolation can be applied uniformly.

| Layer | Column Name | Example Model |
|-------|------------|---------------|
| Layer 1 | `organization_id` | `ScrapingTarget`, `ScrapingJob`, `RawContent` |
| Layer 2 | `tenant_id` (string) | Ontology schema tables (migration-only, no ORM models) |
| Layer 4 | `tenant_id` (UUID) | `User`, `APIKey`, `FeatureFlag`, `Integration` |
| Layer 5 | `organization_id` | `TruthObject`, `TruthSource`, `ModelVersion` |

### 2.4 Background Task Hotspot

The Celery workers in `layer1-ingestion/src/shared/tasks.py` represent the most significant migration challenge. Every pipeline stage function (11 total) opens a database session via `get_db_session()` **without providing a tenant context**. The workers rely on the `organization_id` column stored on the `ScrapingJob` row to filter data at the application level. Under schema-per-tenant isolation, these workers must establish the correct schema context before any ORM operation.

### 2.5 Existing Tenant Infrastructure (Preserved)

The following components will be preserved and integrated with `fastapi-tenancy`:

| Component | File | Role |
|-----------|------|------|
| `RequestContext` | `shared/identity/context.py` | Thread-safe identity context (tenant_id, roles, permissions) via `ContextVar` |
| `GovernanceMiddleware` | `shared/identity/middleware.py` | Resolves tenant from JWT/API key/headers, populates `RequestContext` |
| `TenantScopedCypher` | `shared/identity/isolation.py` | Neo4j query builder with tenant_id predicates (unchanged by schema migration) |
| `tenant_cache_key` | `shared/identity/isolation.py` | Redis key namespacing per tenant (unchanged) |
| `Tenant` model | `layer4-agents/src/tenants/models/tenant.py` | SQLAlchemy ORM model for tenant registry (stays in `public` schema) |
| Tenant service | `layer4-agents/src/tenants/service.py` | CRUD operations for tenants, users, and API keys |
| Tenant API routes | `layer4-agents/src/tenants/api/routes/tenants.py` | FastAPI endpoints for tenant management (super_admin only) |

---

## 3. Target Architecture

### 3.1 Schema Layout

After the migration, the PostgreSQL database will contain the following schema structure:

```
PostgreSQL Database
├── public (shared)
│   ├── tenants          (tenant registry — already exists)
│   ├── tiers            (subscription tier definitions — new in Phase 2)
│   ├── audit_log        (global audit trail — new in Phase 2)
│   └── alembic_version  (shared migration tracking)
│
├── t_acme_corp (tenant schema — created per tenant)
│   ├── accounts
│   ├── account_contacts
│   ├── account_notes
│   ├── scraping_targets
│   ├── scraping_jobs
│   ├── raw_content
│   ├── extracted_data
│   ├── compliance_logs
│   ├── truth_objects
│   ├── truth_sources
│   ├── validation_events
│   ├── feature_flags
│   ├── model_registry
│   ├── integrations
│   └── alembic_version  (per-schema migration tracking)
│
├── t_globex_inc (another tenant schema)
│   └── ... (same table set)
```

### 3.2 Request Flow

The updated request flow for a tenant-scoped API call proceeds as follows:

1. **GovernanceMiddleware** resolves the tenant identity from the JWT claim and populates the `RequestContext` with `tenant_id`, `roles`, and `permissions`.
2. **TenancyMiddleware** (from `fastapi-tenancy`) reads the tenant identifier from the same source (JWT claim) and sets the `fastapi-tenancy` context in the `ContextVar`.
3. The **`get_tenant_db`** dependency (created via `make_tenant_db_dependency(manager)`) yields an `AsyncSession` with `execution_options={"schema_translate_map": {None: "t_<slug>"}}`.
4. All ORM queries issued through this session are automatically routed to the tenant's schema. No `SET LOCAL` is needed.

---

## 4. Task Breakdown

### Task 1.1: Add `fastapi-tenancy` Dependency

**Estimated Effort:** 1 hour

Add the library to the dependency specifications for all backend layers.

| File | Change |
|------|--------|
| `services/layer4-agents/pyproject.toml` | Add `"fastapi-tenancy[full]>=0.4.0"` to `dependencies` |
| `services/layer1-ingestion/pyproject.toml` | Add `"fastapi-tenancy[postgres,migrations]>=0.4.0"` to `dependencies` |
| `services/layer5-ground-truth/pyproject.toml` | Add `"fastapi-tenancy[postgres,migrations]>=0.4.0"` to `dependencies` |

---

### Task 1.2: Create Shared Tenancy Configuration Module

**Estimated Effort:** 2 hours

Create a new shared module that centralizes the `fastapi-tenancy` configuration. This module will be imported by all layers.

**New File:** `packages/shared/src/value_fabric/shared/tenancy/config.py`

```python
"""Shared fastapi-tenancy configuration for all layers.

Reads from environment variables with TENANCY_* prefix.
"""
import os
from fastapi_tenancy import TenancyConfig

def get_tenancy_config() -> TenancyConfig:
    """Build TenancyConfig from environment variables."""
    return TenancyConfig(
        database_url=os.getenv(
            "TENANCY_DATABASE_URL",
            os.getenv("LAYER4_DATABASE_URL",
                       "postgresql+asyncpg://postgres:postgres@postgres:5432/layer4_agents"),
        ),
        isolation_strategy="schema",
        schema_prefix="t_",
        resolution_strategy="jwt",
        jwt_tenant_claim="tenant_id",
        jwt_secret=os.getenv("OIDC_CLIENT_SECRET", ""),
        cache_enabled=True,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        l1_cache_max_size=1000,
        l1_cache_ttl_seconds=60,
        enable_metrics=True,
    )
```

**New File:** `packages/shared/src/value_fabric/shared/tenancy/__init__.py`

---

### Task 1.3: Integrate TenancyMiddleware into Layer 4 Application

**Estimated Effort:** 3 hours

Mount the `TenancyMiddleware` alongside the existing `GovernanceMiddleware` in the Layer 4 FastAPI application.

**Modified File:** `services/layer4-agents/src/api/main.py`

The key changes are:

1. Import `TenancyManager`, `SQLAlchemyTenantStore`, `TenancyMiddleware`, and the shared config.
2. Initialize the `TenancyManager` during the application lifespan.
3. Add the `TenancyMiddleware` to the middleware stack. The `TenancyMiddleware` must be added **after** `GovernanceMiddleware` so that the JWT has already been validated when the tenant is resolved.

```python
from shared.tenancy.config import get_tenancy_config
from fastapi_tenancy import TenancyManager
from fastapi_tenancy.storage.database import SQLAlchemyTenantStore
from fastapi_tenancy.middleware.tenancy import TenancyMiddleware
from fastapi_tenancy.dependencies import make_tenant_db_dependency

tenancy_config = get_tenancy_config()
tenant_store = SQLAlchemyTenantStore(tenancy_config.database_url)
tenancy_manager = TenancyManager(tenancy_config, tenant_store)

# In lifespan:
app = FastAPI(lifespan=tenancy_manager.create_lifespan())

# Middleware order matters — GovernanceMiddleware first, then TenancyMiddleware
app.add_middleware(GovernanceMiddleware, ...)
app.add_middleware(TenancyMiddleware, manager=tenancy_manager)

# New dependency for tenant-scoped sessions
get_tenant_db = make_tenant_db_dependency(tenancy_manager)
```

---

### Task 1.4: Refactor Layer 4 Database Session Management

**Estimated Effort:** 4 hours

Replace the custom RLS-based session management with `fastapi-tenancy`'s dependency injection.

**Modified File:** `services/layer4-agents/src/database.py`

The following functions will be modified:

| Function | Current Behavior | New Behavior |
|----------|-----------------|-------------|
| `get_db_with_tenant()` | Reads `X-Tenant-ID` header, executes `SET LOCAL app.tenant_id` | **Replaced** by `get_tenant_db` from `make_tenant_db_dependency(manager)` |
| `get_db()` | Opens session with empty tenant context (admin bypass) | **Preserved** for health checks and admin operations; operates on `public` schema |
| `db_session()` | Context manager with `SET LOCAL` for background tasks | **Updated** to use `manager.get_session(tenant_identifier)` for schema routing |
| `set_tenant_context()` | Executes `SET LOCAL app.tenant_id` | **Deprecated** — no longer needed with schema isolation |
| `validate_tenant_id()` | UUID format validation | **Preserved** as a utility; `fastapi-tenancy` performs its own validation |

The `db_session()` context manager for background tasks will be updated to accept a tenant slug and use the manager's session factory:

```python
@asynccontextmanager
async def db_session(
    tenant_identifier: str | None = None,
    *,
    require_tenant: bool = True,
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for tenant-scoped sessions outside FastAPI."""
    if require_tenant and not tenant_identifier:
        raise TenantContextError("Tenant identifier is mandatory.")

    if tenant_identifier:
        async with tenancy_manager.get_session(tenant_identifier) as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    else:
        # Admin/system operations on public schema
        factory = get_session_factory()
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
```

**Impact on Dependents:** All files that import `get_db_with_tenant` from `database.py` must be updated to use the new `get_tenant_db` dependency. A grep of the codebase shows the following consumers:

| File | Import |
|------|--------|
| `layer4-agents/src/tenants/api/routes/tenants.py` | Uses `get_db` (admin, no change needed) |
| `layer4-agents/src/tenants/api/routes/users.py` | Uses `get_db_with_tenant` → update to `get_tenant_db` |
| `layer4-agents/src/tenants/api/routes/api_keys.py` | Uses `get_db_with_tenant` → update to `get_tenant_db` |
| `layer4-agents/src/feature_flags/service.py` | Uses `db_session()` → update call signature |
| `layer4-agents/src/services/crm_sync_scheduler.py` | Uses `db_session()` → update call signature |
| `layer4-agents/src/services/oidc_cleanup.py` | Uses `db_session_factory` → update to new factory |
| `layer4-agents/src/engine/executor.py` | Uses `db_session()` → update call signature |

---

### Task 1.5: Refactor Layer 1 Celery Workers

**Estimated Effort:** 6 hours

This is the highest-risk task. The 11 pipeline stage functions in `layer1-ingestion/src/shared/tasks.py` must be updated to establish tenant schema context before any database operation.

**Modified File:** `services/layer1-ingestion/src/shared/tasks.py`

**Strategy:** Create a helper function that wraps the existing `get_db_session()` to resolve the tenant schema from the job's `organization_id`:

```python
from shared.tenancy.config import get_tenancy_config
from fastapi_tenancy import TenancyManager
from fastapi_tenancy.storage.database import SQLAlchemyTenantStore

# Initialize once at module level
_config = get_tenancy_config()
_store = SQLAlchemyTenantStore(_config.database_url)
_manager = TenancyManager(_config, _store)

def get_tenant_session(organization_id: UUID):
    """Get a sync session scoped to the tenant schema.

    Resolves the tenant slug from the organization_id (UUID)
    and returns a session with search_path set to the tenant schema.
    """
    # Look up tenant slug from public.tenants table
    tenant = _manager.get_tenant_by_id_sync(organization_id)
    return _manager.get_sync_session(tenant.identifier)
```

Each pipeline stage function must be updated to use this helper instead of the bare `get_db_session()`. For example:

```python
# Before:
with get_db_session() as session:
    job = session.query(ScrapingJob).get(job_id)

# After:
with get_db_session() as admin_session:
    job = admin_session.query(ScrapingJob).get(job_id)
    org_id = job.organization_id

with get_tenant_session(org_id) as session:
    # All subsequent queries are scoped to the tenant schema
    ...
```

**Note:** Layer 1 uses synchronous SQLAlchemy (`psycopg2`), while `fastapi-tenancy` is async-first. If `fastapi-tenancy` does not expose a synchronous session API, a thin adapter using `asyncio.run()` or `run_sync()` will be required. Alternatively, the `search_path` can be set manually on the sync session:

```python
session.execute(text(f"SET search_path TO t_{tenant_slug}, public"))
```

---

### Task 1.6: Refactor Layer 5 Database Module

**Estimated Effort:** 3 hours

**Modified File:** `services/layer5-ground-truth/src/layer5_ground_truth/database.py`

Layer 5 currently has no tenant context in its session manager. The `get_db()` dependency and `db_session()` context manager must be updated to use `fastapi-tenancy`'s schema routing, following the same pattern as Layer 4.

**Additional Consideration:** Layer 5 uses `organization_id` instead of `tenant_id`. Rather than renaming all columns (which would require extensive migration and code changes), the recommended approach is to configure the tenant resolution to map `organization_id` to the `fastapi-tenancy` tenant identifier at the middleware level. The `organization_id` columns will be retained in the models but will become redundant once schema isolation is in place; they can be deprecated and eventually removed in a future cleanup phase.

---

### Task 1.7: Update Alembic Configuration for Multi-Schema Migrations

**Estimated Effort:** 4 hours

Each layer's Alembic `env.py` must be updated to iterate over all registered tenant schemas when running migrations.

**Modified Files:**

| File | Change |
|------|--------|
| `services/layer1-ingestion/migrations/env.py` | Add tenant schema iteration loop |
| `services/layer4-agents/migrations/env.py` (to be created — currently missing) | Create with tenant schema iteration |
| `services/layer5-ground-truth/alembic.ini` + `env.py` | Add tenant schema iteration loop |

The updated `env.py` pattern (using `fastapi-tenancy`'s built-in runner):

```python
from fastapi_tenancy.migrations import run_tenant_migrations
from shared.tenancy.config import get_tenancy_config

def run_migrations_online():
    config = get_tenancy_config()
    run_tenant_migrations(
        alembic_config=context.config,
        tenancy_config=config,
        target_metadata=target_metadata,
    )
```

If `fastapi-tenancy`'s migration runner is not suitable, a manual loop can be implemented:

```python
def run_migrations_online():
    connectable = engine_from_config(...)
    with connectable.connect() as connection:
        # 1. Run public schema migrations
        context.configure(connection=connection, target_metadata=shared_metadata)
        with context.begin_transaction():
            context.run_migrations()

        # 2. Run tenant schema migrations
        tenants = connection.execute(text("SELECT slug FROM public.tenants WHERE status = 'active'"))
        for (slug,) in tenants:
            schema_name = f"t_{slug}"
            connection.execute(text(f"SET search_path TO {schema_name}, public"))
            context.configure(
                connection=connection,
                target_metadata=tenant_metadata,
                version_table_schema=schema_name,
            )
            with context.begin_transaction():
                context.run_migrations()
```

---

### Task 1.8: Create RLS Removal Migrations

**Estimated Effort:** 2 hours

Create new Alembic migration scripts to drop the existing RLS policies and disable RLS on all affected tables. These migrations run in the `public` schema before the schema-per-tenant transition.

**New Files:**

| Layer | Migration File | Tables |
|-------|---------------|--------|
| Layer 1 | `005_remove_rls_policies.py` | 8 tables from `004_add_rls_policies.py` |
| Layer 4 | `012_remove_rls_policies.py` | 8 tables from `007_add_rls_policies.py` |
| Layer 5 | `004_remove_rls_policies.py` | 4 tables from `002_add_rls_policies.py` + 3 from `003_add_model_registry.py` |

Each migration follows the inverse of the original RLS migration:

```python
def upgrade():
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

def downgrade():
    # Re-enable RLS (copy from original migration)
    ...
```

---

### Task 1.9: Data Migration — Move Existing Rows into Tenant Schemas

**Estimated Effort:** 8 hours

For each existing tenant in the `public.tenants` table, create the tenant schema and migrate the existing rows from the shared tables into the tenant-specific schema.

**New File:** `scripts/migrate_to_schema_per_tenant.py`

The migration script will:

1. Query all active tenants from `public.tenants`.
2. For each tenant, create the schema `t_{slug}` if it does not exist.
3. Run Alembic migrations to create tables within the new schema.
4. Copy rows from the shared tables where `tenant_id = <tenant_uuid>` into the corresponding tenant schema tables.
5. Verify row counts match.
6. Optionally delete the migrated rows from the shared tables (after validation).

This script must be idempotent and support incremental execution for large datasets.

---

### Task 1.10: Update Test Suite

**Estimated Effort:** 4 hours

Update the existing test infrastructure to work with schema-per-tenant isolation.

**Modified Files:**

| File | Change |
|------|--------|
| `layer4-agents/tests/test_oidc_cleanup.py` | Update `db_session_factory` mock to return schema-scoped sessions |
| `layer1-ingestion/tests/unit/test_celery_tasks.py` | Update `get_db_session` patches to use tenant-scoped sessions |
| All test fixtures | Add test tenant provisioning (create schema, run migrations) |

**New File:** `packages/shared/src/value_fabric/shared/testing/tenant_fixtures.py`

```python
"""Shared pytest fixtures for schema-per-tenant testing."""
import pytest
from fastapi_tenancy import TenancyManager

@pytest.fixture
async def test_tenant(tenancy_manager: TenancyManager):
    """Provision a test tenant with its own schema."""
    tenant = await tenancy_manager.register_tenant(
        identifier="test-tenant",
        name="Test Tenant",
        metadata={"plan": "enterprise"},
        app_metadata=Base.metadata,
    )
    yield tenant
    await tenancy_manager.delete_tenant(tenant.id, hard=True)
```

---

## 5. Execution Order and Dependencies

The tasks must be executed in the following order. Tasks within the same step can be parallelized.

| Step | Tasks | Dependency |
|------|-------|-----------|
| 1 | Task 1.1 (add dependency) | None |
| 2 | Task 1.2 (shared config) | Step 1 |
| 3 | Task 1.3 (Layer 4 middleware) + Task 1.8 (RLS removal migrations) | Step 2 |
| 4 | Task 1.4 (Layer 4 sessions) + Task 1.6 (Layer 5 sessions) | Step 3 |
| 5 | Task 1.5 (Layer 1 Celery workers) | Step 4 |
| 6 | Task 1.7 (Alembic multi-schema) | Step 4 |
| 7 | Task 1.9 (data migration script) | Step 6 |
| 8 | Task 1.10 (test suite updates) | Step 4 |

---

## 6. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| `fastapi-tenancy` does not expose a synchronous session API for Layer 1 Celery workers | High | Fall back to manual `SET search_path TO t_{slug}, public` on sync sessions |
| Data migration script corrupts or loses rows during the move to tenant schemas | Critical | Run in dry-run mode first; verify row counts; keep source rows until validation passes |
| Layer 5 `organization_id` naming causes mapping failures | Medium | Configure `fastapi-tenancy` to accept `organization_id` as the tenant claim; add an alias in the tenant store |
| Alembic `version_table_schema` not supported in older Alembic versions | Low | Pin `alembic>=1.12.0` (already in Layer 1 requirements) |
| Connection pool exhaustion from per-schema engine caching | Medium | Configure `fastapi-tenancy` engine cache with bounded pool sizes; monitor via `get_metrics()` |

---

## 7. Rollback Strategy

If the schema-per-tenant migration encounters critical issues, the rollback path is:

1. **Revert the `env.py` changes** to restore single-schema Alembic behavior.
2. **Re-enable RLS** by running the downgrade path of the RLS removal migrations (Task 1.8).
3. **Revert the session manager changes** to restore `SET LOCAL app.tenant_id` behavior.
4. **Drop tenant schemas** if they were created during testing (data remains in the shared tables until the migration script's delete step is executed).

The RLS removal migrations include full downgrade functions that re-create the original policies, ensuring a clean rollback path.

---

## 8. Acceptance Criteria

Phase 1 is considered complete when:

1. All API endpoints in Layers 1, 4, and 5 use schema-per-tenant isolation instead of RLS.
2. A test tenant can be provisioned with `manager.register_tenant()`, and all tables are created in the tenant's schema.
3. Cross-tenant data access is impossible: a session scoped to Tenant A cannot query rows in Tenant B's schema.
4. Celery workers in Layer 1 correctly resolve the tenant schema from the job's `organization_id` before executing queries.
5. Alembic migrations can be applied to all tenant schemas in a single command.
6. The existing test suite passes with the updated session management.
7. Neo4j (`TenantScopedCypher`) and Redis (`tenant_cache_key`) isolation remain unchanged and functional.

---

## 9. File Inventory

The following table provides a complete inventory of all files created, modified, or deleted in Phase 1.

| Action | File | Description |
|--------|------|-------------|
| **Create** | `shared/tenancy/__init__.py` | Package init |
| **Create** | `shared/tenancy/config.py` | Shared `TenancyConfig` builder |
| **Create** | `shared/testing/tenant_fixtures.py` | Pytest fixtures for schema-per-tenant tests |
| **Create** | `scripts/migrate_to_schema_per_tenant.py` | Data migration script |
| **Create** | `layer1-ingestion/migrations/versions/005_remove_rls_policies.py` | Drop Layer 1 RLS policies |
| **Create** | `layer4-agents/migrations/versions/012_remove_rls_policies.py` | Drop Layer 4 RLS policies |
| **Create** | `layer5-ground-truth/.../migrations/versions/004_remove_rls_policies.py` | Drop Layer 5 RLS policies |
| **Modify** | `layer4-agents/pyproject.toml` | Add `fastapi-tenancy[full]` |
| **Modify** | `layer1-ingestion/pyproject.toml` | Add `fastapi-tenancy[postgres,migrations]` |
| **Modify** | `layer5-ground-truth/pyproject.toml` | Add `fastapi-tenancy[postgres,migrations]` |
| **Modify** | `layer4-agents/src/api/main.py` | Mount `TenancyMiddleware`, init `TenancyManager` |
| **Modify** | `layer4-agents/src/database.py` | Replace RLS session management with schema routing |
| **Modify** | `layer1-ingestion/src/shared/database.py` | Replace RLS session management with schema routing |
| **Modify** | `layer5-ground-truth/src/.../database.py` | Add tenant-scoped session support |
| **Modify** | `layer1-ingestion/src/shared/tasks.py` | Add tenant schema resolution to all 11 pipeline stages |
| **Modify** | `layer1-ingestion/migrations/env.py` | Add tenant schema iteration |
| **Modify** | `layer5-ground-truth/.../migrations/env.py` | Add tenant schema iteration |
| **Modify** | `layer4-agents/src/tenants/api/routes/users.py` | Update to `get_tenant_db` dependency |
| **Modify** | `layer4-agents/src/tenants/api/routes/api_keys.py` | Update to `get_tenant_db` dependency |
| **Modify** | `layer4-agents/src/feature_flags/service.py` | Update `db_session()` call signature |
| **Modify** | `layer4-agents/src/services/crm_sync_scheduler.py` | Update `db_session()` call signature |
| **Modify** | `layer4-agents/src/services/oidc_cleanup.py` | Update session factory reference |
| **Modify** | `layer4-agents/src/engine/executor.py` | Update `db_session()` call signature |
| **Modify** | `layer4-agents/tests/test_oidc_cleanup.py` | Update mocks for schema-scoped sessions |
| **Modify** | `layer1-ingestion/tests/unit/test_celery_tasks.py` | Update mocks for schema-scoped sessions |

---

## References

[1]: https://docs.sqlalchemy.org/en/21/core/connections.html#translation-of-schema-names "SQLAlchemy Documentation — Translation of Schema Names"
[2]: https://github.com/fastapi-extensions/fastapi-tenancy "fastapi-tenancy — Production-ready multi-tenancy for FastAPI"
[3]: https://mergeboard.com/blog/6-multitenancy-fastapi-sqlalchemy-postgresql/ "MergeBoard — Multitenancy with FastAPI, SQLAlchemy and PostgreSQL"
[4]: https://alembic.sqlalchemy.org/en/latest/cookbook.html "Alembic Documentation — Cookbook"
