"""pytest configuration and shared fixtures for Layer 7 Billing tests.

Uses an in-memory SQLite database (via aiosqlite) for fast, isolated tests.
The DATABASE_URL is overridden before any imports touch the engine.

Fixture hierarchy:
  engine (function-scoped) →  fresh in-memory DB per test
  db     (function-scoped) →  session with a nested transaction rolled back after each test
"""

import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Override DATABASE_URL before any application code imports the engine
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["APP_ENV"] = "test"


@pytest.fixture(scope="function")
async def engine():
    """Create a fresh in-memory database engine for each test."""
    from layer7_billing.models import Base

    engine = create_async_engine(TEST_DB_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session with transaction rollback for isolation."""
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Set tenant context for the session
        await session.execute(
            "SELECT set_config('app.tenant_id', 'test-tenant', true)"
        )
        
        yield session
        
        # Rollback to isolate test changes
        await session.rollback()
