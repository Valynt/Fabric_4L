from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
)

from layer1_ingestion.shared.exceptions import TenantContextError

INTENTIONAL_DB_ADAPTER_BYPASS = True

"""Database engine and session management.

P0-08: Supports PostgreSQL Row-Level Security via SET LOCAL app.tenant_id
SECURITY: Fail-safe tenant isolation - tenant context is mandatory

Public FastAPI dependencies (use these in route handlers):
  - get_db_from_context   — canonical replacement for get_db_with_tenant
  - get_db_with_tenant    — deprecated; use get_db_from_context instead
  - get_db_from_context_sync — sync variant for GovernanceMiddlewareSync paths
"""

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from urllib.parse import urlparse
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from value_fabric.shared.redis_ha import create_async_redis_client, create_sync_redis_client

from ..metrics.prometheus_metrics import get_metrics
from .config import settings

# Database connection pool configuration from environment
# P1-02: Tune pool sizes for higher concurrency
# Tune these based on your load: pool_size + max_overflow = max concurrent connections
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))  # Increased from 5 to 20
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "30"))  # Increased from 10 to 30
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
# P0-05: Configurable statement timeout (default 5 minutes for long-running operations)
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "300000"))  # 5 minutes default
logger = logging.getLogger(__name__)
_RLS_SUPPORTED_SCHEMES = frozenset(
    {"postgresql", "postgres", "postgresql+asyncpg", "postgresql+psycopg"}
)
_RLS_SUPERUSER_NAMES = frozenset(
    {"postgres", "rdsadmin", "cloudsqladmin", "azure_superuser"}
)
_PRIVILEGED_REASON_HEADER = "X-Privileged-Reason"
_TENANT_CONTEXT_STATE_KEY = "tenant_context_state"
_TENANT_CONTEXT_VALUE_KEY = "tenant_context_value"
_TENANT_BYPASS_REASON_KEY = "tenant_context_bypass_reason"


def _is_production_like_runtime() -> bool:
    return bool(getattr(settings, "is_production_like", False))


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


_assert_rls_safe_database_url(settings.database_url, source="Layer 1 database URL")

# Create engine with configurable pool settings
# P0-05: Add statement_timeout for query timeout protection (configurable via env var)
engine = create_engine(
    settings.database_url,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_timeout=DB_POOL_TIMEOUT,
    echo=settings.debug,
    connect_args={
        "options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
    }
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def close_db() -> None:
    """Dispose of the database engine and connection pool.

    Should be called during application shutdown to ensure clean connection cleanup.
    """
    global engine
    if engine is not None:
        engine.dispose()
        logger.info("Layer 1 database engine disposed")

# Redis client (used by health checks and Celery)
redis_client = None
# Async Redis client (used by rate limiter)
redis_client_async = None
REDIS_AVAILABLE = False
try:
    _redis_client = create_sync_redis_client(settings.redis_url, decode_responses=True)
    _redis_client.ping()
    redis_client = _redis_client
    redis_client_async = create_async_redis_client(settings.redis_url, decode_responses=True)
    REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    redis_client_async = None
    REDIS_AVAILABLE = False
    pass


# SECURITY: Fail-safe mode - require explicit tenant context
# Set to False only for admin/system operations with proper role validation
FAIL_SAFE_MODE = True

_privileged_db_session_metrics = {
    "activations_total": 0,
    "denials_total": 0,
    "missing_reason_total": 0,
}


def get_privileged_db_session_metrics() -> dict[str, int]:
    return _privileged_db_session_metrics.copy()


def reset_privileged_db_session_metrics() -> None:
    _privileged_db_session_metrics.update({
        "activations_total": 0,
        "denials_total": 0,
        "missing_reason_total": 0,
    })


def validate_tenant_id(tenant_id: UUID | str | None) -> str:
    """Validate tenant_id format and return normalized string.

    SECURITY: Strict validation to prevent tenant confusion attacks.

    Args:
        tenant_id: Tenant identifier to validate

    Returns:
        Normalized tenant ID string

    Raises:
        TenantContextError: If tenant_id is invalid or missing in fail-safe mode
    """
    if tenant_id is None:
        if FAIL_SAFE_MODE:
            raise TenantContextError(
                "Tenant context is mandatory in fail-safe mode. "
                "Use explicit admin role context for system operations."
            )
        return ""

    # Convert to string and normalize
    normalized = str(tenant_id).strip()

    # Fail-safe: empty tenant_id is not allowed
    if not normalized:
        raise TenantContextError(
            "Empty tenant_id is not allowed. Provide a valid tenant context."
        )

    # Validate UUID format for strict tenant isolation
    if normalized.lower() not in ('system', 'admin', 'internal'):
        try:
            UUID(normalized)
        except ValueError:
            raise TenantContextError(
                f"Invalid tenant_id format: {normalized}. Expected UUID."
            )

    return normalized


def set_tenant_context(session: Session, tenant_id: UUID | str | None) -> None:
    """P0-08: Set PostgreSQL app.tenant_id for RLS policies.

    SECURITY: Fail-safe semantics - tenant context is mandatory unless
    explicitly using admin bypass with proper role authentication.

    Executes SET LOCAL app.tenant_id = '...' which applies for the
    duration of the current transaction. RLS policies in PostgreSQL
    can reference current_setting('app.tenant_id') to filter rows.

    Args:
        session: SQLAlchemy session
        tenant_id: Tenant UUID or string identifier (whitespace is stripped)

    Raises:
        TenantContextError: If tenant_id is missing/invalid in fail-safe mode
    """
    # SECURITY: Validate tenant context with fail-safe semantics
    normalized_id = validate_tenant_id(tenant_id)

    # Set tenant context for RLS policies
    # Empty string only allowed for admin roles (enforced by RLS policy TO clause)
    session.execute(
        text("SET LOCAL app.tenant_id = :tenant_id"),
        {"tenant_id": normalized_id}
    )
    _mark_session_tenant_context(session, normalized_id)


def _mark_session_tenant_context(session: Session, tenant_id: str) -> None:
    session.info[_TENANT_CONTEXT_STATE_KEY] = "set"
    session.info[_TENANT_CONTEXT_VALUE_KEY] = tenant_id
    session.info.pop(_TENANT_BYPASS_REASON_KEY, None)


def _mark_session_tenant_bypass(session: Session, *, reason: str) -> None:
    session.info[_TENANT_CONTEXT_STATE_KEY] = "bypass"
    session.info[_TENANT_CONTEXT_VALUE_KEY] = None
    session.info[_TENANT_BYPASS_REASON_KEY] = reason


def _record_privileged_db_session_activation(context, *, mode: str, reason: str) -> None:
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


def _require_privileged_cross_tenant_reason(request: Request, context) -> str:
    if not context.is_super_admin():
        _privileged_db_session_metrics["denials_total"] += 1
        raise AuthorizationError(message = "Cross-tenant database access requires super admin role.")

    reason = (request.headers.get(_PRIVILEGED_REASON_HEADER) or "").strip()
    if not reason:
        _privileged_db_session_metrics["missing_reason_total"] += 1
        raise ValidationError(message = str(f"Cross-tenant database access requires {_PRIVILEGED_REASON_HEADER} header."))
    return reason


@contextmanager
def get_db_session(
    tenant_id: UUID | str | None = None,
    *,
    require_tenant: bool = True
) -> Generator[Session, None, None]:
    """Get a database session as a context manager.

    SECURITY: Fail-safe by default - tenant context is mandatory.

    Args:
        tenant_id: Tenant ID to set for RLS context (P0-08)
        require_tenant: If True (default), enforce mandatory tenant context.
                       Set to False only for admin/system operations with
                       proper role authentication.

    Raises:
        TenantContextError: If tenant_id is missing/invalid and require_tenant=True
    """
    # SECURITY: Enforce mandatory tenant context by default
    if require_tenant:
        # This will raise TenantContextError in fail-safe mode if tenant_id is invalid
        tenant_id = validate_tenant_id(tenant_id)
    elif tenant_id is not None:
        # Validate even when require_tenant=False, if a tenant_id was provided
        tenant_id = validate_tenant_id(tenant_id)
    # If require_tenant=False and tenant_id is None, this is a system-level bypass.
    # Emit metric for observability — all bypass usage must be alertable.
    if not require_tenant:
        metrics = get_metrics()
        if metrics:
            metrics.increment_privileged_db_session_activation(mode="bypass")

    session = SessionLocal()
    try:
        if tenant_id is not None:
            session.execute(
                text("SET LOCAL app.tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)}
            )
            _mark_session_tenant_context(session, str(tenant_id))
        else:
            _mark_session_tenant_bypass(session, reason="system_operation")
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions (without RLS).

    SECURITY: Use only for health checks or admin operations with proper
    role authentication. All production endpoints should use get_db_with_tenant.
    """
    session = SessionLocal()
    try:
        _mark_session_tenant_bypass(session, reason="system_operation")
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_with_tenant(
    request: Request,
) -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session with RLS tenant context.

    SECURITY: Mandatory tenant context from authenticated request context.
    Fail-safe: Rejects requests without validated tenant identification.

    Usage::

        @router.get("/jobs/{id}")
        async def get_job(id: UUID, db: Session = Depends(get_db_from_context)):
            ...

    Raises:
       : 401 if authenticated tenant context is missing

    .. deprecated:: Use get_db_from_context() instead (deadline: 2026-06-01).
    """
    ctx = getattr(request.state, "governance_context", None)
    if ctx is None or not getattr(ctx, "tenant_id", None):
        raise AuthenticationError(message = "Authentication required")
    try:
        tenant_id = validate_tenant_id(ctx.tenant_id)
    except TenantContextError as e:
        logger.warning("Tenant context validation failed: %s", e)
        raise ValidationError(message = "Invalid tenant context") from e

    session = SessionLocal()
    try:
        session.execute(
            text("SET LOCAL app.tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_from_context(
    request: Request,
) -> Generator[Session, None, None]:
    """FastAPI dependency for DB session with tenant from GovernanceMiddleware context.

    Replaces get_db_with_tenant(). Reads tenant from the canonical
    ``request.state.governance_context`` set by GovernanceMiddleware.

    SECURITY: Fail-safe — rejects requests without validated tenant context.

    Usage::

        @router.get("/jobs/{id}")
        async def get_job(id: UUID, db: Session = Depends(get_db_from_context)):
            ...

    Raises:
       : 401 if authenticated tenant context is missing
    """
    ctx = getattr(request.state, "governance_context", None)
    if ctx is None or not getattr(ctx, "tenant_id", None):
        raise AuthenticationError(message = "Authentication required")
    try:
        tenant_id = validate_tenant_id(ctx.tenant_id)
    except TenantContextError as e:
        logger.warning("Tenant context validation failed: %s", e)
        raise ValidationError(message = "Invalid tenant context") from e

    session = SessionLocal()
    try:
        session.execute(
            text("SET LOCAL app.tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_with_tenant_from_context(
    tenant_id: UUID | str
) -> Generator[Session, None, None]:
    """
    Context manager for database sessions with RLS tenant context.
    For use outside FastAPI request lifecycle (e.g., background tasks).

    SECURITY: Requires explicit tenant_id - fail-safe by default.

    Usage::

        with get_db_with_tenant_from_context(tenant_id=tenant_uuid) as db:
            ...

    Args:
        tenant_id: Required tenant UUID (cannot be None)

    Raises:
        TenantContextError: If tenant_id is missing or invalid
    """
    with get_db_session(tenant_id=tenant_id, require_tenant=True) as session:
        yield session


# ---------------------------------------------------------------------------
# Sprint 5: Context-aware database session for sync layers (Task 5.2.1)
# ---------------------------------------------------------------------------

try:
    from value_fabric.shared.identity.middleware_sync import (
        SyncRequestContext,
        get_request_context_sync,
        require_request_context_sync,
    )
    SYNC_IDENTITY_AVAILABLE = True
except ImportError:
    SYNC_IDENTITY_AVAILABLE = False
    SyncRequestContext = None  # type: ignore
    get_request_context_sync = None  # type: ignore
    require_request_context_sync = None  # type: ignore


def get_db_from_context_sync(
    context: "SyncRequestContext" = Depends(get_request_context_sync),  # type: ignore
) -> Generator[Session, None, None]:
    """FastAPI dependency for DB session with tenant from RequestContext (Sprint 5).

    SECURITY: Uses RequestContext set by GovernanceMiddlewareSync.
    Fail-safe: Rejects requests without explicit tenant identification.

    Usage::

        @router.get("/items")
        async def list_items(
            db: Session = Depends(get_db_from_context_sync),
            context: SyncRequestContext = Depends(get_request_context_sync)
        ):
            ...

    Raises:
       : 400 if tenant context is missing
    """
    if not SYNC_IDENTITY_AVAILABLE:
        raise RuntimeError(
            "shared.identity.middleware_sync required for get_db_from_context_sync"
        )

    if not context or not context.tenant_id:
        raise ValidationError(message = "Tenant context required. Ensure request passed through GovernanceMiddlewareSync.")

    # Validate tenant ID
    try:
        tenant_id = validate_tenant_id(context.tenant_id)
    except TenantContextError as e:
        logger.warning("Tenant context validation failed: %s", e)
        raise ValidationError(message = "Invalid tenant context") from e

    # Create session with RLS context
    session = SessionLocal()
    try:
        session.execute(
            text("SET LOCAL app.tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_with_optional_tenant_sync(
    request: Request,
    context: "SyncRequestContext" = Depends(get_request_context_sync),  # type: ignore
) -> Generator[Session, None, None]:
    """DB session with optional tenant for super-admin operations (Sprint 5).

    SECURITY: Must be combined with privileged access checks.
    Super-admins can bypass tenant context for cross-tenant operations.

    Usage::

        @router.get("/admin/all-tenants")
        async def get_all_tenants(
            db: Session = Depends(get_db_with_optional_tenant_sync),
            context: SyncRequestContext = Depends(require_request_context_sync)
        ):
            ...

    Raises:
       : 400 if non-super-admin without tenant context
    """
    if not SYNC_IDENTITY_AVAILABLE:
        raise RuntimeError(
            "shared.identity.middleware_sync required for get_db_with_optional_tenant_sync"
        )

    session = SessionLocal()
    try:
        if context.tenant_id:
            try:
                tenant_id = validate_tenant_id(context.tenant_id)
            except TenantContextError as e:
                logger.warning("Tenant context validation failed: %s", e)
                raise ValidationError(message = "Invalid tenant context") from e
            session.execute(
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
            raise AuthorizationError(message = "Cross-tenant database access requires super admin role.")
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
