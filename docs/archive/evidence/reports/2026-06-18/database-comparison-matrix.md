# Database Comparison Matrix

Generated for PR 1: Database and HTTPException Inventory

## Layer 1 (Ingestion) - `services/layer1-ingestion/src/shared/database.py`

### PostgreSQL URL Handling
- **Schemes supported**: `postgresql://` (sync engine via psycopg2)
- **DSN parsing**: Uses `settings.database_url` from config
- **Async support**: No - uses sync SQLAlchemy engine
- **URL source**: Environment variable `LAYER1_DATABASE_URL_SYNC`

### Engine/Session Setup
- **Engine type**: Sync SQLAlchemy engine
- **Session factory**: `sessionmaker(autocommit=False, autoflush=False)`
- **Connection args**: `options="-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}"`
- **Pool size**: Configurable via `DB_POOL_SIZE` (default 20)
- **Max overflow**: Configurable via `DB_MAX_OVERFLOW` (default 30)
- **Pool pre-ping**: Enabled
- **Echo**: Controlled by `settings.debug`

### Pool Configuration
- **Size**: 20 (env: `DB_POOL_SIZE`)
- **Max overflow**: 30 (env: `DB_MAX_OVERFLOW`)
- **Statement timeout**: 300000ms (5 minutes, env: `DB_STATEMENT_TIMEOUT_MS`)
- **Pre-ping**: True
- **Explicit config**: Yes, via environment variables

### Tenant/RLS Setup
- **RLS method**: `SET LOCAL app.tenant_id = :tenant_id`
- **Validation**: Custom `validate_tenant_id()` function
- **Reserved keywords**: `system`, `admin`, `internal`
- **Fail-safe mode**: Configurable via `FAIL_SAFE_MODE` (default True)
- **Session marking**: `_mark_session_tenant_context()` / `_mark_session_tenant_bypass()`

### Transaction Handling
- **Commit**: Manual via `session.commit()`
- **Rollback**: Manual via `session.rollback()` in except block
- **Context manager**: `get_db_session()` handles commit/rollback
- **Auto-commit**: False
- **Auto-flush**: False

### Session Lifecycle
- **FastAPI dependencies**: `get_db()`, `get_db_with_tenant()`, `get_db_from_context()`, `get_db_from_context_sync()`
- **Context manager**: `get_db_session()` for non-FastAPI usage
- **Session closure**: Explicit `session.close()` in finally block
- **Tenant enforcement**: Manual validation before session use

### Shutdown/Engine Disposal
- **Engine disposal**: Not explicitly implemented
- **Connection pool cleanup**: Not explicitly implemented
- **Lifespan management**: Not integrated with FastAPI lifespan

### Health Check
- **Implementation**: Not found in database.py
- **DSN leakage**: N/A
- **Sanitization**: N/A

### Test Coverage
- **PostgreSQL tests**: Not found in database.py
- **SQLite tests**: Not found in database.py
- **Test fixtures**: Not found in database.py

### Metrics Integration
- **Prometheus metrics**: `get_metrics()` from `prometheus_metrics`
- **Pool state metrics**: Not tracked
- **Privileged session metrics**: Tracked via `_privileged_db_session_metrics`

---

## Layer 4 (Agents) - `services/layer4-agents/src/database.py`

### PostgreSQL URL Handling
- **Schemes supported**: `postgresql+asyncpg://`, `postgresql://`, `postgres://`, `postgresql+psycopg://`
- **DSN parsing**: Uses `get_database_url()` with fallback to `CHECKPOINT_DATABASE_URL`
- **Async support**: Yes - uses async SQLAlchemy with asyncpg
- **URL source**: Environment variable `LAYER4_DATABASE_URL` or `CHECKPOINT_DATABASE_URL`
- **Production safety**: `_assert_rls_safe_database_url()` validates scheme and username in production

### Engine/Session Setup
- **Engine type**: Async SQLAlchemy engine with `create_async_engine()`
- **Session factory**: `async_sessionmaker(class_=TenantEnforcedAsyncSession)`
- **Connection args**: None (asyncpg handles this)
- **Pool size**: From `settings.database_pool_size`
- **Max overflow**: From `settings.database_max_overflow`
- **Pool pre-ping**: True
- **Echo**: False
- **Future**: True

### Pool Configuration
- **Size**: From `settings.database_pool_size`
- **Max overflow**: From `settings.database_max_overflow`
- **Pre-ping**: True
- **Explicit config**: Yes, via Pydantic settings
- **Pool timeout**: Not explicitly set
- **Pool recycle**: Not explicitly set

### Tenant/RLS Setup
- **RLS method**: `SELECT set_config('app.tenant_id', :tenant_id, true)` (asyncpg-safe)
- **Validation**: Custom `validate_tenant_id()` with shared fallback
- **Reserved keywords**: `system`, `admin`, `internal`
- **Fail-safe mode**: Configurable via `FAIL_SAFE_MODE` (default True)
- **Session marking**: `_mark_session_tenant_context()` / `_mark_session_tenant_bypass()`
- **Session enforcement**: `TenantEnforcedAsyncSession` blocks SQL before tenant context set
- **Flush enforcement**: Event listener enforces tenant context before flush

### Transaction Handling
- **Commit**: Manual via `await session.commit()`
- **Rollback**: Manual via `await session.rollback()` in except block
- **Context manager**: Async context managers in dependencies
- **Auto-commit**: False
- **Auto-flush**: False
- **Expire on commit**: False

### Session Lifecycle
- **FastAPI dependencies**: `get_db()`, `get_db_with_tenant()`, `get_db_from_context()`, `get_db_with_optional_tenant()`, `get_tiered_db_session()`
- **Context manager**: `db_session_for_context()` for non-FastAPI usage
- **Session closure**: Async context manager handles cleanup
- **Tenant enforcement**: `TenantEnforcedAsyncSession` with pre-execution checks
- **Deprecated dependencies**: `get_db()`, `get_db_with_tenant()`, `get_db_with_optional_tenant()`, `get_tiered_db_session()` (with warnings)

### Shutdown/Engine Disposal
- **Engine disposal**: Not explicitly implemented
- **Connection pool cleanup**: Not explicitly implemented
- **Lifespan management**: Not integrated with FastAPI lifespan

### Health Check
- **Implementation**: Not found in database.py
- **DSN leakage**: N/A
- **Sanitization**: N/A

### Test Coverage
- **PostgreSQL tests**: Not found in database.py
- **SQLite tests**: Tests use `sqlite+aiosqlite:///:memory:`
- **Test fixtures**: Not found in database.py

### Metrics Integration
- **Prometheus metrics**: `get_metrics()` from `metrics`
- **Pool state metrics**: `_record_pool_state()` tracks pool size, active, idle
- **Pool wait metrics**: Tracks connection checkout duration
- **Pool timeout metrics**: Tracks timeout errors
- **Privileged session metrics**: Tracked via `_privileged_db_session_metrics`
- **Tenant validation metrics**: Tracked via `_tenant_validation_metrics`

---

## Layer 5 (Ground Truth) - `services/layer5-ground-truth/src/layer5_ground_truth/database.py`

### PostgreSQL URL Handling
- **Schemes supported**: `postgresql+asyncpg://`, `postgresql://`, `postgres://`, `postgresql+psycopg://`
- **DSN parsing**: Uses `settings.database_url` from config
- **Async support**: Yes - uses async SQLAlchemy with asyncpg
- **URL source**: Environment variable `LAYER5_DATABASE_URL`
- **Production safety**: `_assert_rls_safe_database_url()` validates scheme and username in production
- **SQLite fallback**: Supports `sqlite://` for tests with UUID handling

### Engine/Session Setup
- **Engine type**: Async SQLAlchemy engine with `create_async_engine()`
- **Session factory**: `async_sessionmaker(class_=TenantEnforcedAsyncSession)`
- **Connection args**: `check_same_thread=False` for SQLite
- **Pool size**: From `settings.db_pool_size`
- **Max overflow**: From `settings.db_max_overflow`
- **Pool pre-ping**: From `settings.db_pool_pre_ping`
- **Pool recycle**: From `settings.db_pool_recycle`
- **Pool timeout**: From `settings.db_pool_timeout`
- **Echo**: From `settings.debug`
- **Future**: True

### Pool Configuration
- **Size**: From `settings.db_pool_size`
- **Max overflow**: From `settings.db_max_overflow`
- **Pre-ping**: From `settings.db_pool_pre_ping`
- **Recycle**: From `settings.db_pool_recycle`
- **Timeout**: From `settings.db_pool_timeout`
- **Explicit config**: Yes, via Pydantic settings
- **SQLite handling**: Special handling for SQLite UUID types

### Tenant/RLS Setup
- **RLS method**: `SET LOCAL app.tenant_id = :tenant_id` (text())
- **Validation**: Custom `validate_tenant_id()` with shared fallback
- **Reserved keywords**: `system`, `admin`, `internal`
- **Fail-safe mode**: Not configurable (always fail-safe)
- **Session marking**: `_mark_session_tenant_context()` / `_mark_session_tenant_bypass()`
- **Session enforcement**: `TenantEnforcedAsyncSession` blocks SQL before tenant context set
- **Flush enforcement**: Event listener enforces tenant context before flush

### Transaction Handling
- **Commit**: Manual via `await session.commit()`
- **Rollback**: Manual via `await session.rollback()` in except block
- **Context manager**: Async context managers in dependencies
- **Auto-commit**: False
- **Auto-flush**: False
- **Expire on commit**: False

### Session Lifecycle
- **FastAPI dependencies**: `get_db()`, `get_db_from_context()`, `get_db_with_optional_tenant()`
- **Context manager**: `db_session()` for non-FastAPI usage
- **Session closure**: Async context manager handles cleanup
- **Tenant enforcement**: `TenantEnforcedAsyncSession` with pre-execution checks
- **Deprecated dependencies**: `get_db()` (with warning)

### Shutdown/Engine Disposal
- **Engine disposal**: `close_db()` function exists
- **Connection pool cleanup**: `close_db()` calls `await engine.dispose()`
- **Lifespan management**: Not integrated with FastAPI lifespan (manual call required)

### Health Check
- **Implementation**: Not found in database.py
- **DSN leakage**: N/A
- **Sanitization**: N/A

### Test Coverage
- **PostgreSQL tests**: Not found in database.py
- **SQLite tests**: Tests use `sqlite+aiosqlite:///:memory:`
- **Test fixtures**: Not found in database.py
- **UUID handling**: `SQLiteUUID` type adapter for SQLite compatibility

### Metrics Integration
- **Prometheus metrics**: `_get_metrics()` from `metrics.prometheus_metrics` (optional)
- **Pool state metrics**: `_record_pool_state()` tracks pool size, active, idle
- **Pool wait metrics**: Tracks connection checkout duration
- **Pool timeout metrics**: Tracks timeout errors
- **Privileged session metrics**: Tracked via `_privileged_db_session_metrics`

---

## Layer 6 (Benchmarks) - `services/layer6-benchmarks/src/database.py`

### PostgreSQL URL Handling
- **Schemes supported**: N/A (uses Neo4j, not PostgreSQL)
- **DSN parsing**: N/A
- **Async support**: Yes - uses Neo4j async driver
- **URL source**: Environment variable `NEO4J_URI`
- **Production safety**: N/A

### Engine/Session Setup
- **Engine type**: Neo4j AsyncDriver
- **Session factory**: N/A (Neo4j session API)
- **Connection args**: N/A
- **Pool size**: Configurable via `neo4j_max_pool_size`
- **Connection timeout**: 10.0 seconds
- **Retry logic**: Exponential backoff (max 5 attempts)

### Pool Configuration
- **Size**: From `settings.neo4j_max_pool_size`
- **Connection timeout**: 10.0 seconds
- **Explicit config**: Yes, via Pydantic settings
- **Retry logic**: Built-in driver retry with exponential backoff

### Tenant/RLS Setup
- **RLS method**: N/A (Neo4j doesn't use PostgreSQL RLS)
- **Validation**: N/A
- **Reserved keywords**: N/A
- **Fail-safe mode**: N/A
- **Session marking**: N/A
- **Session enforcement**: N/A

### Transaction Handling
- **Commit**: N/A (Neo4j transaction API)
- **Rollback**: N/A (Neo4j transaction API)
- **Context manager**: N/A
- **Auto-commit**: N/A
- **Auto-flush**: N/A

### Session Lifecycle
- **FastAPI dependencies**: N/A
- **Context manager**: N/A
- **Session closure**: N/A
- **Tenant enforcement**: N/A

### Shutdown/Engine Disposal
- **Engine disposal**: `close_driver()` function exists
- **Connection pool cleanup**: `close_driver()` calls `await driver.close()`
- **Lifespan management**: Not integrated with FastAPI lifespan (manual call required)

### Health Check
- **Implementation**: `health_check()` function
- **DSN leakage**: Returns URI in response (potential issue)
- **Sanitization**: Returns status and URI, no error details

### Test Coverage
- **PostgreSQL tests**: N/A (Neo4j)
- **SQLite tests**: N/A (Neo4j)
- **Test fixtures**: N/A

### Metrics Integration
- **Prometheus metrics**: N/A
- **Pool state metrics**: N/A
- **Pool wait metrics**: N/A
- **Pool timeout metrics**: N/A
- **Privileged session metrics**: N/A

---

## Summary of Patterns

### Common Patterns
- All services use environment variables for database configuration
- L4 and L5 use async SQLAlchemy with similar patterns
- L4 and L5 use `TenantEnforcedAsyncSession` for tenant enforcement
- L4 and L5 have similar pool configuration via Pydantic settings
- L4 and L5 track privileged session metrics
- L4 and L5 have similar transaction handling (manual commit/rollback)

### Divergences
- L1 uses sync SQLAlchemy, L4/L5 use async
- L1 has statement timeout configuration, L4/L5 do not
- L5 has explicit pool recycle/timeout settings, L4 does not
- L5 has engine disposal function, L4 does not
- L6 uses Neo4j (completely different pattern)
- L1 has metrics integration, L4/L5 have optional metrics
- L5 has SQLite UUID handling, L4 does not

### Production-Readiness Gaps
- **Engine disposal**: L4 lacks explicit engine disposal
- **Health checks**: L1, L4, L5 lack health check implementations
- **DSN leakage**: L6 health check returns URI (potential issue)
- **Lifespan management**: None integrate with FastAPI lifespan
- **PostgreSQL tests**: None have explicit PostgreSQL integration tests
- **Pool timeout**: L4 lacks explicit pool timeout configuration
