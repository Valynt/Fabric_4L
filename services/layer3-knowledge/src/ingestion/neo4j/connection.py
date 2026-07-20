from __future__ import annotations

from neo4j import AsyncDriver

from ...config import Settings, get_settings
from ...db.driver import get_driver


class Neo4jConnectionManager:
    """Owns Neo4j driver lifecycle and yields async sessions."""

    def __init__(
        self,
        driver: AsyncDriver | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self._driver = driver
        self._owned_driver = driver is None

    async def get_driver(self) -> AsyncDriver:
        """Get or create Neo4j driver via the shared singleton factory."""
        if self._driver is None:
            self._driver = await get_driver(self.settings)
        return self._driver

    def session(self, database: str | None = None):
        """Return an async context manager for a Neo4j session.

        The caller is responsible for `async with`.
        """
        db = database or self.settings.neo4j_database
        return _SessionContext(self, db)

    async def close(self) -> None:
        """Close Neo4j driver if owned."""
        if self._owned_driver and self._driver:
            await self._driver.close()
            self._driver = None


class _SessionContext:
    """Helper to make `session()` await-free and async-context-manageable."""

    def __init__(self, manager: Neo4jConnectionManager, database: str):
        self._manager = manager
        self._database = database
        self._session = None

    async def __aenter__(self):
        driver = await self._manager.get_driver()
        self._session = driver.session(database=self._database)
        return await self._session.__aenter__()

    async def __aexit__(self, exc_type, exc, tb):
        return await self._session.__aexit__(exc_type, exc, tb)
