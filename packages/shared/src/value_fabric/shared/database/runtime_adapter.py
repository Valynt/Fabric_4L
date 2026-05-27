"""Canonical shared runtime database adapter.

Defines a single interface for async SQLAlchemy runtime services:
- engine/session creation
- URL scheme validation by runtime mode
- tenant/RLS session hook
- pooled/retry-friendly defaults
- health check semantics
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

PRODUCTION_ALLOWED_SCHEMES = frozenset({"postgresql", "postgresql+asyncpg", "postgresql+psycopg"})
TEST_ALLOWED_SCHEMES = frozenset({"sqlite+aiosqlite", "sqlite"})
RLS_SUPERUSER_NAMES = frozenset({"postgres", "rdsadmin", "cloudsqladmin", "azure_superuser"})


@dataclass(frozen=True)
class DatabaseAdapterConfig:
    database_url: str
    service_name: str
    production_mode: bool
    allow_test_sqlite: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_pre_ping: bool = True
    pool_recycle: int = 1800
    pool_timeout: int = 30
    echo: bool = False


class RuntimeDatabaseAdapter:
    """Canonical shared async DB adapter for runtime SQL services."""

    def __init__(self, config: DatabaseAdapterConfig):
        self.config = config
        self._validate_url_policy()
        self._engine = create_async_engine(
            self.config.database_url,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_pre_ping=self.config.pool_pre_ping,
            pool_recycle=self.config.pool_recycle,
            pool_timeout=self.config.pool_timeout,
            echo=self.config.echo,
            future=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    async def apply_tenant_rls(self, session: AsyncSession, tenant_id: str) -> None:
        await session.execute(text("SET LOCAL app.tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        session.info["tenant_context_state"] = "set"
        session.info["tenant_context_value"] = tenant_id

    async def health_check(self) -> dict[str, str]:
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "healthy", "service": self.config.service_name}
        except Exception as exc:  # noqa: BLE001
            return {"status": "unhealthy", "service": self.config.service_name, "error": str(exc)}

    async def close(self) -> None:
        await self._engine.dispose()

    def _validate_url_policy(self) -> None:
        parsed = urlparse(self.config.database_url)
        scheme = (parsed.scheme or "").lower()
        username = (parsed.username or "").lower()

        if self.config.production_mode:
            if scheme not in PRODUCTION_ALLOWED_SCHEMES:
                raise RuntimeError(
                    f"{self.config.service_name}: production runtime requires PostgreSQL driver; got '{scheme}'."
                )
            if username in RLS_SUPERUSER_NAMES:
                raise RuntimeError(
                    f"{self.config.service_name}: production runtime forbids superuser role '{username}'."
                )
            return

        if scheme in PRODUCTION_ALLOWED_SCHEMES:
            return
        if self.config.allow_test_sqlite and scheme in TEST_ALLOWED_SCHEMES:
            return
        raise RuntimeError(
            f"{self.config.service_name}: non-production runtime URL scheme '{scheme}' is not allowed."
        )


def is_production_mode_from_env() -> bool:
    value = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "").strip().lower()
    return value not in {"", "local", "dev", "development", "test", "testing", "ci"}


def normalize_sqlalchemy_url_scheme(database_url: str) -> str:
    return make_url(database_url).drivername.lower()
