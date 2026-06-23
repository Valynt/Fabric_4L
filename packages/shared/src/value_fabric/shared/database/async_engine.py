"""Shared async SQLAlchemy engine and session management.

Provides a reusable pattern for creating async database engines
with configurable connection pooling across all Value Fabric services.

Singleton Pattern Limitations:
- This module uses module-level global singletons for engine and session factory
- The first caller's parameters (database_url, pool_size, etc.) become locked in
- All subsequent calls reuse the same engine with the original configuration
- This pattern is suitable for single-database applications but may cause issues
  in multi-tenant scenarios requiring different database configurations
- If multi-database support is needed, consider implementing a keyed cache pattern
  where each database_url gets its own engine instance

Usage:
    # In application startup
    from value_fabric.shared.database import get_async_engine, async_db_session

    # Get engine (creates on first call, reuses on subsequent calls)
    engine = get_async_engine(database_url="postgresql+asyncpg://...")

    # Use context manager for sessions
    async with async_db_session(database_url="postgresql+asyncpg://...") as session:
        await session.execute(...)
"""

import logging
import os
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

# Module-level singleton - shared across the process
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_engine_lock = threading.Lock()
_RLS_SUPPORTED_SCHEMES = frozenset({"postgresql", "postgres", "postgresql+asyncpg", "postgresql+psycopg"})
_RLS_SUPERUSER_NAMES = frozenset({"postgres", "rdsadmin", "cloudsqladmin", "azure_superuser"})


def _is_strict_runtime() -> bool:
    from value_fabric.shared.security.config import is_strict_environment
    return is_strict_environment()


def _assert_rls_safe_database_url(database_url: str) -> None:
    if not _is_strict_runtime():
        return

    parsed = urlparse(database_url)
    scheme = (parsed.scheme or "").lower()
    username = (parsed.username or "").lower()

    if scheme not in _RLS_SUPPORTED_SCHEMES:
        raise RuntimeError(
            "Protected environments must use PostgreSQL with RLS-capable tenant isolation."
        )

    if username in _RLS_SUPERUSER_NAMES:
        raise RuntimeError(
            f"Protected environments must not use PostgreSQL superuser role '{username}'."
        )


def get_async_engine(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> AsyncEngine:
    """
    Get or create a shared async database engine.

    Args:
        database_url: Database connection URL (must use async driver like asyncpg)
        pool_size: Number of connections to maintain in the pool
        max_overflow: Maximum overflow connections beyond pool_size
        pool_pre_ping: Test connections before using them
        echo: Log SQL statements (debug mode)

    Returns:
        Shared AsyncEngine instance

    Raises:
        ValueError: If database_url is empty or invalid
    """
    global _engine
    if not database_url or not database_url.strip():
        raise ValueError("database_url cannot be empty")
    _assert_rls_safe_database_url(database_url)

    with _engine_lock:
        if _engine is None:
            _engine = create_async_engine(
                database_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=pool_pre_ping,
                echo=echo,
                future=True,
            )
            logger.info(
                "Created async engine: pool_size=%s, max_overflow=%s",
                pool_size,
                max_overflow,
            )
    return _engine


def get_async_session_factory(
    engine: AsyncEngine | None = None,
    autocommit: bool = False,
    autoflush: bool = False,
    expire_on_commit: bool = False,
) -> async_sessionmaker[AsyncSession]:
    """
    Get or create a shared async session factory.

    Args:
        engine: AsyncEngine instance (uses global engine if None)
        autocommit: Enable autocommit mode
        autoflush: Enable autoflush mode
        expire_on_commit: Expire objects on commit

    Returns:
        Shared async session factory

    Raises:
        ValueError: If engine is None on first call
    """
    global _session_factory
    if _session_factory is None:
        if engine is None:
            raise ValueError("Engine must be provided on first call")
        _session_factory = async_sessionmaker(
            bind=engine,
            autocommit=autocommit,
            autoflush=autoflush,
            expire_on_commit=expire_on_commit,
        )
        logger.info("Created async session factory")
    return _session_factory


async def close_async_engine() -> None:
    """Dispose the global engine connection pool.

    Should be called from application shutdown handlers.
    """
    global _engine, _session_factory
    with _engine_lock:
        if _engine is not None:
            await _engine.dispose()
            _engine = None
            _session_factory = None
            logger.info("Closed async engine")


@asynccontextmanager
async def async_db_session(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    **engine_kwargs: Any,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for async database sessions with automatic cleanup.

    Creates an engine and session factory on first use, reuses on subsequent calls.
    Commits on success, rolls back on exception.

    Args:
        database_url: Database connection URL
        pool_size: Connection pool size
        max_overflow: Maximum overflow connections
        **engine_kwargs: Additional arguments for create_async_engine

    Yields:
        AsyncSession instance
    """
    engine = get_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        **engine_kwargs,
    )
    factory = get_async_session_factory(engine)

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
