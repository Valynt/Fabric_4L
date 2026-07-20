import pytest

from src.ingestion.neo4j.connection import Neo4jConnectionManager


class _FakeSession:
    pass


class _FakeSessionContext:
    def __init__(self, driver, database):
        self.driver = driver
        self.database = database

    async def __aenter__(self):
        return _FakeSession()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeDriver:
    def __init__(self):
        self.closed = False
        self.session_database = None

    def session(self, database=None):
        self.session_database = database
        return _FakeSessionContext(self, database)

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_connection_manager_uses_injected_driver_and_does_not_close_it():
    injected = _FakeDriver()
    manager = Neo4jConnectionManager(driver=injected, settings=None)

    async with manager.session(database="neo4j") as session:
        assert isinstance(session, _FakeSession)
        assert injected.session_database == "neo4j"

    await manager.close()
    assert not injected.closed


@pytest.mark.asyncio
async def test_connection_manager_closes_owned_driver():
    owned_driver = _FakeDriver()
    manager = Neo4jConnectionManager(driver=None, settings=None)
    manager._driver = owned_driver

    await manager.close()
    assert owned_driver.closed
    assert manager._driver is None
