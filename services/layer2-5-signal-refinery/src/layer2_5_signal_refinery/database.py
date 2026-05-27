"""Async SQLAlchemy engine and session management for L2.5 Signal Refinery.

Follows the same pattern as Layer 5's database.py:
- asyncpg for production, aiosqlite for tests
- RLS via SET LOCAL app.tenant_id
- get_db_from_context() as the canonical FastAPI dependency
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.types import CHAR, TypeDecorator
from value_fabric.shared.database import (
    DatabaseAdapterConfig,
    RuntimeDatabaseAdapter,
    is_production_mode_from_env,
)

from .config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_runtime_adapter: RuntimeDatabaseAdapter | None = None


# ---------------------------------------------------------------------------
# Cross-platform UUID type
# ---------------------------------------------------------------------------


class SQLiteUUID(TypeDecorator):
    """Platform-independent UUID — stores as CHAR(32) on SQLite, native UUID on PostgreSQL."""

    impl = CHAR
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(length=32)

    def process_bind_param(self, value: object, dialect: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value.hex
        return str(value).replace("-", "")

    def process_result_value(self, value: object, dialect: object) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, int):
            return uuid.UUID(int=value)
        if isinstance(value, str):
            if len(value) == 32:
                return uuid.UUID(hex=value)
            return uuid.UUID(str(value))
        return value  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Engine and session factory
# ---------------------------------------------------------------------------


def get_engine() -> AsyncEngine:
    global _engine, _runtime_adapter
    if _engine is None:
        settings = get_settings()
        _runtime_adapter = RuntimeDatabaseAdapter(
            DatabaseAdapterConfig(
                database_url=settings.database_url,
                service_name="layer2_5_signal_refinery",
                production_mode=is_production_mode_from_env(),
                allow_test_sqlite=True,
            )
        )
        _engine = _runtime_adapter.engine
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db() -> None:
    """Create all tables. Used at startup and in tests."""
    from .models.db_models import Base

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


# ---------------------------------------------------------------------------
# FastAPI dependency — canonical tenant-scoped session
# ---------------------------------------------------------------------------


def _get_request_context():
    """Import lazily to avoid circular imports."""
    try:
        from value_fabric.shared.identity.context import get_request_context
        return get_request_context()
    except ImportError:
        return None


async def get_db_from_context(
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: async DB session with tenant RLS from RequestContext.

    Fail-safe: rejects requests without tenant context.
    """
    ctx = _get_request_context()
    if ctx is None or not getattr(ctx, "tenant_id", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required.",
        )

    tenant_id = str(ctx.tenant_id)
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            text("SET LOCAL app.tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Context manager for non-FastAPI usage (background tasks, services)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def db_session(tenant_id: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        if tenant_id:
            await session.execute(
                text("SET LOCAL app.tenant_id = :tenant_id"),
                {"tenant_id": tenant_id},
            )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
