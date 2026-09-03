from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from value_fabric.shared.database import (
    create_postgresql_engine,
    create_session_maker,
    PostgresHealthProbe,
)
from value_fabric.shared.fastapi_framework.health import ProbeResult
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from .models import Base

logger = structlog.get_logger(__name__)

DATABASE_URL = os.getenv("LAYER7_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/layer7_billing")

engine = create_postgresql_engine(DATABASE_URL)
session_maker = create_session_maker(engine)

# SEC-P001: Async Redis client backing RateLimitMiddleware for billing endpoints.
# Imported by the API layer to wire RedisRateLimiter into GovernanceMiddleware.
# Resolves to None when the redis package is unavailable or REDIS_URL is unset, so
# the service still boots (rate limiting degrades to the limiter's local fallback).
try:
    import redis.asyncio as _redis_asyncio
except ImportError:  # pragma: no cover - redis is an optional runtime dependency
    _redis_asyncio = None  # type: ignore[assignment]

REDIS_URL = os.getenv("REDIS_URL")
redis_client_async = (
    _redis_asyncio.from_url(REDIS_URL, decode_responses=True)
    if (_redis_asyncio is not None and REDIS_URL)
    else None
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()


@asynccontextmanager
async def db_session_for_context(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    async with session_maker() as session:
        await session.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_from_context(
    ctx: RequestContext = Depends(require_authenticated),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a tenant-scoped DB session from authenticated context.

    P0-02 hardening: tenant_id is extracted from the canonical
    RequestContext set by GovernanceMiddleware, never from a raw header.
    """
    async with db_session_for_context(str(ctx.tenant_id)) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Layer 7 billing service", component="layer7-billing", version="0.1.0")
    await init_db()
    logger.info("Layer 7 billing database initialized", dependency="database", status="healthy")
    yield
    logger.info("Shutting down Layer 7 billing service", component="layer7-billing")
    await close_db()
    logger.info("Layer 7 billing database disconnected", dependency="database", status="disconnected")


async def health_probe() -> ProbeResult:
    probe = PostgresHealthProbe(engine)
    result = await probe.check()
    if result.healthy:
        logger.info("Layer 7 billing health check passed", dependency="database", status="healthy")
    else:
        logger.warning("Layer 7 billing health check failed", dependency="database", status="unhealthy", detail=result.detail)
    return result
