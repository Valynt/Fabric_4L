from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from value_fabric.shared.database import (
    create_postgresql_engine,
    create_session_maker,
    PostgresHealthProbe,
)
from value_fabric.shared.fastapi_framework.health import ProbeResult

from .models import Base

DATABASE_URL = os.getenv("LAYER7_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/layer7_billing")

engine = create_postgresql_engine(DATABASE_URL)
session_maker = create_session_maker(engine)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()


@asynccontextmanager
async def db_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    async with session_maker() as session:
        await session.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db(
    x_tenant_id: str = Header(...),
) -> AsyncGenerator[AsyncSession, None]:
    async with db_session(x_tenant_id) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


async def health_probe() -> ProbeResult:
    probe = PostgresHealthProbe(engine)
    return await probe.check()
