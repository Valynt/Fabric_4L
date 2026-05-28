"""Shared async PostgreSQL lifespan helpers.

Provides a canonical FastAPI-friendly context manager that:

- Resolves a DSN from env vars (with normalization to an async driver).
- Creates an :class:`AsyncEngine` and ``async_sessionmaker``.
- Exposes a :class:`PostgresHealthProbe` for the framework readiness endpoint.
- Disposes the engine on shutdown.

The helpers are deliberately small and dependency-free so services can adopt
them incrementally without restructuring their own lifespan callables.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from .postgresql import (
    PostgresPoolConfig,
    create_postgresql_engine,
    create_session_maker,
    health_probe,
    resolve_runtime_dsn,
    shutdown_engine,
)

from ..fastapi_framework.health import ProbeResult


@dataclass
class PgRuntime:
    """Runtime handles owned by :func:`pg_lifespan`."""

    engine: AsyncEngine
    session_maker: async_sessionmaker[AsyncSession]
    dsn: str


class PostgresHealthProbe:
    """:class:`HealthCheckProbe` adapter backed by :func:`health_probe`."""

    def __init__(self, engine: AsyncEngine, *, name: str = "postgres") -> None:
        self.name = name
        self._engine = engine

    async def check(self) -> ProbeResult:
        try:
            ok = await health_probe(self._engine)
        except Exception:  # noqa: BLE001 — expected operational failures must not raise
            return ProbeResult(name=self.name, healthy=False, detail="health_check_failed")
        return ProbeResult(name=self.name, healthy=ok, detail=None if ok else "select_1_failed")


@asynccontextmanager
async def pg_lifespan(
    *env_vars: str,
    fallback: str | None = None,
    pool: PostgresPoolConfig | None = None,
) -> AsyncIterator[PgRuntime]:
    """Async context manager that owns engine + session_maker lifecycle.

    Example::

        async with pg_lifespan("DATABASE_URL") as pg:
            app.state.db_engine = pg.engine
            app.state.session_maker = pg.session_maker
            yield
    """

    dsn = resolve_runtime_dsn(*env_vars, fallback=fallback)
    engine = create_postgresql_engine(dsn, pool=pool)
    session_maker = create_session_maker(engine)
    try:
        yield PgRuntime(engine=engine, session_maker=session_maker, dsn=dsn)
    finally:
        await shutdown_engine(engine)
