"""
Async SQLAlchemy engine and session management for Layer 5.

Uses asyncpg for production and aiosqlite for tests (via DATABASE_URL override).
Follows the same pattern as Layer 1's database.py but with async support.
"""

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import event
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.types import CHAR, TypeDecorator

from .config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional metrics support
# ---------------------------------------------------------------------------


def _get_metrics():
    """
    Get the metrics module if available.

    Prometheus metrics are optional - if the module is not installed,
    this returns None gracefully. This allows the database layer to
    function in environments without monitoring dependencies.

    Returns:
        Metrics object or None if not available.
    """
    try:
        from metrics.prometheus_metrics import get_metrics
        return get_metrics()
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# SQLite UUID type adapter
# ---------------------------------------------------------------------------


class SQLiteUUID(TypeDecorator):
    """
    Platform-independent UUID type.

    Uses PostgreSQL's UUID type when available, otherwise stores as CHAR(32).
    This is needed because SQLite doesn't have native UUID support and
    SQLAlchemy's UUID(as_uuid=True) stores as integers which causes issues.
    """

    impl = CHAR
    cache_ok = True

    def __init__(self):
        super().__init__(length=32)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value.hex
        return str(value).replace("-", "")

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, int):
            # Convert integer to UUID bytes then to UUID
            return uuid.UUID(int=value)
        if isinstance(value, str):
            if len(value) == 32:
                return uuid.UUID(value)
            return uuid.UUID(value)
        return value


# ---------------------------------------------------------------------------
# Engine — created once at import time, reused across requests
# ---------------------------------------------------------------------------

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker["TenantEnforcedAsyncSession"] | None = None
_TENANT_CONTEXT_STATE_KEY = "tenant_context_state"
_TENANT_CONTEXT_VALUE_KEY = "tenant_context_value"
_TENANT_BYPASS_REASON_KEY = "tenant_context_bypass_reason"
_PRIVILEGED_REASON_HEADER = "X-Privileged-Reason"
_RLS_SUPPORTED_SCHEMES = frozenset({"postgresql", "postgres", "postgresql+asyncpg", "postgresql+psycopg"})
_RLS_SUPERUSER_NAMES = frozenset({"postgres", "rdsadmin", "cloudsqladmin", "azure_superuser"})
logger = logging.getLogger(__name__)
_privileged_db_session_metrics = {
    "activations_total": 0,
    "denials_total": 0,
    "missing_reason_total": 0,
}


def _record_pool_state(engine: AsyncEngine) -> None:
    metrics = _get_metrics()
    if metrics is None:
        return
    try:
        pool = engine.sync_engine.pool
        active = int(pool.checkedout())
        size = int(pool.size())
        idle = max(size - active, 0)
        metrics.set_db_pool_state(pool_size=size, active=active, idle=idle)
    except Exception:
        logger.debug("DB pool state metric emission failed", exc_info=True)


def _setup_sqlite_uuid_handling(url: str) -> None:
    """
    Configure SQLite to handle UUIDs properly.

    SQLite doesn't have native UUID support. When SQLAlchemy's UUID(as_uuid=True)
    is used with SQLite, UUIDs get stored as integers which causes retrieval issues.
    This patches the behavior to store UUIDs as strings instead.
    """
    if "sqlite" not in url.lower():
        return

    import sqlite3

    # Register adapter to convert UUID to string when storing
    sqlite3.register_adapter(uuid.UUID, lambda u: str(u))

    # Register converter to convert string back to UUID when retrieving
    sqlite3.register_converter(
        "UUID",
        lambda val: uuid.UUID(val.decode() if isinstance(val, bytes) else str(val)),
    )


def _is_production_like_runtime() -> bool:
    env = get_settings().effective_environment if hasattr(get_settings(), "effective_environment") else ""
    value = str(env or "").strip().lower()
    return value not in {"", "local", "dev", "development", "test", "testing", "ci"}


def _assert_rls_safe_database_url(database_url: str, *, source: str) -> None:
    if not _is_production_like_runtime():
        return

    parsed = urlparse(database_url)
    scheme = (parsed.scheme or "").lower()
    username = (parsed.username or "").lower()

    if scheme not in _RLS_SUPPORTED_SCHEMES:
        raise RuntimeError(
            f"{source} must use PostgreSQL with RLS-capable tenant isolation in protected environments."
        )

    if username in _RLS_SUPERUSER_NAMES:
        raise RuntimeError(
            f"{source} must not use PostgreSQL superuser role '{username}' in protected environments."
        )


def _statement_sets_tenant_context(statement: object) -> bool:
    sql = str(statement).lower()
    return "app.tenant_id" in sql and ("set_config" in sql or "set local" in sql)


def _mark_session_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    session.info[_TENANT_CONTEXT_STATE_KEY] = "set"
    session.info[_TENANT_CONTEXT_VALUE_KEY] = tenant_id
    session.info.pop(_TENANT_BYPASS_REASON_KEY, None)


def _mark_session_tenant_bypass(session: AsyncSession, *, reason: str) -> None:
    session.info[_TENANT_CONTEXT_STATE_KEY] = "bypass"
    session.info[_TENANT_CONTEXT_VALUE_KEY] = None
    session.info[_TENANT_BYPASS_REASON_KEY] = reason


def _assert_session_has_tenant_context(session: AsyncSession, *, operation: str) -> None:
    state = session.info.get(_TENANT_CONTEXT_STATE_KEY)
    if state in {"set", "bypass"}:
        return
    raise TenantContextError(
        f"Tenant database session context must be established before {operation}."
    )


class TenantEnforcedAsyncSession(AsyncSession):
    """AsyncSession that fails closed if SQL executes before tenant context is set."""

    async def execute(self, statement, params=None, /, **kwargs):  # type: ignore[override]
        if not _statement_sets_tenant_context(statement):
            _assert_session_has_tenant_context(self, operation="statement execution")
        try:
            return await super().execute(statement, params, **kwargs)
        except SATimeoutError:
            metrics = _get_metrics()
            if metrics is not None:
                try:
                    metrics.increment_db_pool_timeout()
                except Exception:
                    logger.debug("DB pool timeout metric emission failed", exc_info=True)
            raise


@event.listens_for(TenantEnforcedAsyncSession.sync_session_class, "before_flush")
def _enforce_tenant_context_before_flush(session, flush_context, instances) -> None:
    _assert_session_has_tenant_context(session, operation="flush")


def get_engine() -> AsyncEngine:
    """Return (or lazily create) the shared async engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _assert_rls_safe_database_url(settings.database_url, source="Layer 5 database URL")
        engine_kwargs: dict[str, Any] = {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_pre_ping": settings.db_pool_pre_ping,
            "pool_recycle": settings.db_pool_recycle,
            "pool_timeout": settings.db_pool_timeout,
            "echo": settings.debug,
            "future": True,
        }
        # SQLite requires check_same_thread=False for connection pooling
        if settings.database_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_async_engine(
            settings.database_url,
            **engine_kwargs,
        )
        _record_pool_state(_engine)

        @event.listens_for(_engine.sync_engine.pool, "checkout")
        def _on_pool_checkout(dbapi_conn, connection_record, connection_proxy) -> None:
            connection_record.info["pool_checkout_start"] = time.perf_counter()
            _record_pool_state(_engine)

        @event.listens_for(_engine.sync_engine.pool, "checkin")
        def _on_pool_checkin(dbapi_conn, connection_record) -> None:
            start = connection_record.info.pop("pool_checkout_start", None)
            if start is not None:
                metrics = _get_metrics()
                if metrics is not None:
                    try:
                        metrics.observe_db_pool_wait(time.perf_counter() - start)
                    except Exception:
                        logger.debug("DB pool wait metric emission failed", exc_info=True)
            _record_pool_state(_engine)
        _setup_sqlite_uuid_handling(settings.database_url)
    return _engine


def get_session_factory() -> async_sessionmaker[TenantEnforcedAsyncSession]:
    """Return (or lazily create) the shared session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=TenantEnforcedAsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Internal-only FastAPI dependency that yields an async database session.

    .. warning::

        INTERNAL ONLY — Use ``get_db_from_context`` for all tenant routes.
        This dependency does NOT set ``SET LOCAL app.tenant_id``, so RLS
        policies will block all rows.  It is retained only for the
        ``init_db`` / health-check paths that run before tenant context
        is available.

    Usage::

        @router.get("/truths/{id}")
        async def get_truth(id: UUID, db: AsyncSession = Depends(get_db_from_context)):
            ...
    """
    import warnings

    context = get_request_context() if SHARED_IDENTITY_AVAILABLE else None
    if context is not None and context.tenant_id is not None:
        raise RuntimeError(
            "Unsafe get_db() usage detected with tenant request context. "
            "Tenant-scoped routes must depend on get_db_from_context()."
        )

    warnings.warn(
        "get_db() does not enforce RLS tenant context. "
        "Use get_db_from_context() for tenant-scoped queries.",
        DeprecationWarning,
        stacklevel=2,
    )
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Context manager for non-FastAPI usage (services, background tasks)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def db_session(tenant_id: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for use outside of FastAPI request lifecycle.

    Args:
        tenant_id: UUID string of the tenant.  When provided, the session
            executes ``SET LOCAL app.tenant_id`` so that PostgreSQL RLS
            policies are enforced.  Omitting ``tenant_id`` is only valid
            for system-level operations (migrations, health checks).

    Raises:
        TenantContextError: If ``tenant_id`` is provided but invalid.
    """
    factory = get_session_factory()
    async with factory() as session:
        if tenant_id is not None:
            validated = validate_tenant_id(tenant_id)
            await session.execute(
                text("SET LOCAL app.tenant_id = :tid"),
                {"tid": validated},
            )
            _mark_session_tenant_context(session, validated)
        else:
            _mark_session_tenant_bypass(session, reason="system_operation")
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Lifecycle helpers (called from FastAPI lifespan)
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create all tables if they do not exist (dev/test convenience)."""
    from .models import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine connection pool on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


# ---------------------------------------------------------------------------
# Sprint 5: Context-aware database session for async layers (Task 5.2.2)
# ---------------------------------------------------------------------------

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text

try:
    from metrics.prometheus_metrics import get_metrics
except ImportError:
    get_metrics = None  # type: ignore

try:
    from value_fabric.shared.identity.context import RequestContext, get_request_context
    SHARED_IDENTITY_AVAILABLE = True
except ImportError:
    SHARED_IDENTITY_AVAILABLE = False
    RequestContext = None  # type: ignore

    def get_request_context():  # type: ignore
        """Fail-closed fallback used when the shared identity package is unavailable."""
        return None

try:
    from value_fabric.shared.database import TenantContextError, validate_tenant_id
    SHARED_DATABASE_AVAILABLE = True
except ImportError:
    SHARED_DATABASE_AVAILABLE = False

    class TenantContextError(Exception):  # type: ignore
        """Fallback when shared database module is unavailable."""

        pass

    def validate_tenant_id(tenant_id: UUID | str | None) -> str:  # type: ignore
        """Fallback validation when shared database module is unavailable."""
        if tenant_id is None:
            raise TenantContextError(
                "Tenant context is mandatory. "
                "Use explicit admin role context for system operations."
            )

        normalized = str(tenant_id).strip()
        if not normalized:
            raise TenantContextError("Empty tenant_id is not allowed.")

        # Validate UUID format
        if normalized.lower() not in ("system", "admin", "internal"):
            try:
                UUID(normalized)
            except ValueError:
                raise TenantContextError(f"Invalid tenant_id format: {normalized}")

        return normalized


async def get_db_from_context(
    context: "RequestContext" = Depends(get_request_context),  # type: ignore
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for DB session with tenant from RequestContext (Sprint 5).

    SECURITY: Uses RequestContext set by GovernanceMiddleware.
    Fail-safe: Rejects requests without explicit tenant identification.

    Usage::

        @router.get("/items")
        async def list_items(
            db: AsyncSession = Depends(get_db_from_context),
            context: RequestContext = Depends(get_request_context)
        ):
            ...

    Raises:
        HTTPException: 400 if tenant context is missing
    """
    if not SHARED_IDENTITY_AVAILABLE:
        raise RuntimeError(
            "shared.identity required for get_db_from_context"
        )

    if not context or not context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required. Ensure request passed through GovernanceMiddleware.",
        )

    try:
        tenant_id = validate_tenant_id(context.tenant_id)
    except TenantContextError as e:
        logger.warning("Tenant context validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant context",
        ) from e

    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            text("SET LOCAL app.tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        _mark_session_tenant_context(session, tenant_id)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_with_optional_tenant(
    request: Request,
    context: "RequestContext" = Depends(get_request_context),  # type: ignore
) -> AsyncGenerator[AsyncSession, None]:
    """DB session with optional tenant for super-admin operations (Sprint 5).

    SECURITY: Must be combined with privileged access checks.
    Super-admins can bypass tenant context for cross-tenant operations.

    Usage::

        @router.get("/admin/all-tenants")
        async def get_all_tenants(
            db: AsyncSession = Depends(get_db_with_optional_tenant),
            context: RequestContext = Depends(require_request_context)
        ):
            ...

    Raises:
        HTTPException: 400 if non-super-admin without tenant context
    """
    if not SHARED_IDENTITY_AVAILABLE:
        raise RuntimeError(
            "shared.identity required for get_db_with_optional_tenant"
        )

    factory = get_session_factory()
    async with factory() as session:
        if context.tenant_id:
            try:
                tenant_id = validate_tenant_id(context.tenant_id)
            except TenantContextError as e:
                logger.warning("Tenant context validation failed: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid tenant context",
                ) from e
            await session.execute(
                text("SET LOCAL app.tenant_id = :tenant_id"),
                {"tenant_id": tenant_id}
            )
            _mark_session_tenant_context(session, tenant_id)
        elif context.is_super_admin():
            reason = _require_privileged_cross_tenant_reason(request, context)
            _mark_session_tenant_bypass(session, reason=f"privileged_cross_tenant:{reason}")
            _record_privileged_db_session_activation(
                context,
                mode="cross_tenant_admin",
                reason=reason,
            )
        else:
            _privileged_db_session_metrics["denials_total"] += 1
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-tenant database access requires super admin role.",
            )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_privileged_db_session_metrics() -> dict[str, int]:
    return _privileged_db_session_metrics.copy()


def reset_privileged_db_session_metrics() -> None:
    _privileged_db_session_metrics.update({
        "activations_total": 0,
        "denials_total": 0,
        "missing_reason_total": 0,
    })


def _record_privileged_db_session_activation(
    context: "RequestContext",
    *,
    mode: str,
    reason: str,
) -> None:
    _privileged_db_session_metrics["activations_total"] += 1
    logger.warning(
        "Privileged cross-tenant DB session activated",
        extra={
            "request_id": getattr(context, "request_id", None),
            "actor_id": getattr(context, "user_id", None) or getattr(context, "api_key_id", None),
            "tenant_id": str(getattr(context, "tenant_id", None)) if getattr(context, "tenant_id", None) is not None else None,
            "mode": mode,
            "reason": reason,
        },
    )
    metrics = get_metrics()
    if metrics is not None:
        metrics.increment_privileged_db_session_activation(mode)


def _require_privileged_cross_tenant_reason(
    request: Request,
    context: "RequestContext",
) -> str:
    if not context.is_super_admin():
        _privileged_db_session_metrics["denials_total"] += 1
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant database access requires super admin role.",
        )

    reason = (request.headers.get(_PRIVILEGED_REASON_HEADER) or "").strip()
    if not reason:
        _privileged_db_session_metrics["missing_reason_total"] += 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cross-tenant database access requires {_PRIVILEGED_REASON_HEADER} header.",
        )
    return reason
