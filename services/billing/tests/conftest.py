"""Pytest configuration and fixtures for billing service tests."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from billing.models import Base


@pytest_asyncio.fixture()
async def db_session():
    """Provide an in-memory SQLite async session for unit tests.

    Uses SQLite + aiosqlite so tests run without a real Postgres instance.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session

    await engine.dispose()
