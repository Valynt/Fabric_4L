"""Canonical PostgreSQL runtime helpers for shared async SQLAlchemy usage."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


@dataclass(frozen=True)
class PostgresPoolConfig:
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: float = 30.0
    pool_recycle: int = 1800
    pool_pre_ping: bool = True
    echo: bool = False


T = TypeVar("T")


def validate_postgresql_dsn(dsn: str) -> str:
    if not dsn or not dsn.strip():
        raise ValueError("Database DSN cannot be empty")

    url = make_url(dsn)
    if not url.drivername.startswith("postgresql"):
        raise ValueError(f"Expected PostgreSQL DSN, got '{url.drivername}'")
    return dsn


def resolve_runtime_dsn(*env_vars: str, fallback: str | None = None) -> str:
    for env_name in env_vars:
        value = os.getenv(env_name)
        if value:
            return validate_postgresql_dsn(value)
    if fallback:
        return validate_postgresql_dsn(fallback)
    raise RuntimeError(f"No database DSN configured in env vars: {', '.join(env_vars)}")


def create_postgresql_engine(dsn: str, *, pool: PostgresPoolConfig | None = None, **kwargs: Any) -> AsyncEngine:
    pool_cfg = pool or PostgresPoolConfig()
    return create_async_engine(
        validate_postgresql_dsn(dsn),
        pool_size=pool_cfg.pool_size,
        max_overflow=pool_cfg.max_overflow,
        pool_timeout=pool_cfg.pool_timeout,
        pool_recycle=pool_cfg.pool_recycle,
        pool_pre_ping=pool_cfg.pool_pre_ping,
        echo=pool_cfg.echo,
        future=True,
        **kwargs,
    )


def create_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


async def health_probe(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


async def shutdown_engine(engine: AsyncEngine | None) -> None:
    if engine is not None:
        await engine.dispose()


@asynccontextmanager
async def session_scope(session_maker: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def transactional(
    session_maker: async_sessionmaker[AsyncSession],
    fn: Callable[[AsyncSession], Awaitable[T]],
) -> T:
    async with session_scope(session_maker) as session:
        return await fn(session)


async def get_db_session(session_maker: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    async with session_scope(session_maker) as session:
        yield session
