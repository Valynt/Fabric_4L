"""Shared database configuration and utilities for Value Fabric services.

Provides common database engine and session management patterns
to reduce code duplication across services.
"""

from .async_engine import (
    async_db_session,
    close_async_engine,
    get_async_engine,
    get_async_session_factory,
)
from .lifespan import PgRuntime, PostgresHealthProbe, pg_lifespan
from .postgresql import (
    PostgresPoolConfig,
    create_postgresql_engine,
    create_session_maker,
    get_db_session,
    get_db_session_dependency,
    health_probe,
    normalize_async_postgresql_dsn,
    resolve_runtime_dsn,
    session_scope,
    shutdown_engine,
    transactional,
    validate_postgresql_dsn,
)
from .runtime_adapter import (
    DatabaseAdapterConfig,
    RuntimeDatabaseAdapter,
    is_production_mode_from_env,
    normalize_sqlalchemy_url_scheme,
)
from .tenant_validation import (
    MissingTenantContextError,
    TenantContextError,
    require_tenant_context,
    validate_tenant_id,
)

__all__ = [
    "get_async_engine",
    "get_async_session_factory",
    "close_async_engine",
    "async_db_session",
    "validate_tenant_id",
    "TenantContextError",
    "MissingTenantContextError",
    "require_tenant_context",
    "PostgresPoolConfig",
    "create_postgresql_engine",
    "create_session_maker",
    "get_db_session",
    "get_db_session_dependency",
    "health_probe",
    "normalize_async_postgresql_dsn",
    "resolve_runtime_dsn",
    "session_scope",
    "shutdown_engine",
    "transactional",
    "validate_postgresql_dsn",
    "DatabaseAdapterConfig",
    "RuntimeDatabaseAdapter",
    "is_production_mode_from_env",
    "normalize_sqlalchemy_url_scheme",
    "PgRuntime",
    "PostgresHealthProbe",
    "pg_lifespan",
]
