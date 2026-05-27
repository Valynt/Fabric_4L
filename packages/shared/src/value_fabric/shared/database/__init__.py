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
from .tenant_validation import TenantContextError, validate_tenant_id
from .tenant_validation import MissingTenantContextError, require_tenant_context

__all__ = [
    "get_async_engine",
    "get_async_session_factory",
    "close_async_engine",
    "async_db_session",
    "validate_tenant_id",
    "TenantContextError",
    "MissingTenantContextError",
    "require_tenant_context",
    "DatabaseAdapterConfig",
    "RuntimeDatabaseAdapter",
    "is_production_mode_from_env",
    "normalize_sqlalchemy_url_scheme",
]

from .runtime_adapter import (
    DatabaseAdapterConfig,
    RuntimeDatabaseAdapter,
    is_production_mode_from_env,
    normalize_sqlalchemy_url_scheme,
)
