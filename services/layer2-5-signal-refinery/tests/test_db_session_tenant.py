import pytest

from layer2_5_signal_refinery import database as db_module
from layer2_5_signal_refinery.database import db_session


class _FakeSession:
    """Stand-in session so the acceptance test does not require PostgreSQL RLS."""

    async def execute(self, *args, **kwargs):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass


class _FakeSessionContext:
    async def __aenter__(self):
        return _FakeSession()

    async def __aexit__(self, *args):
        return False


class _FakeSessionFactory:
    def __call__(self):
        return _FakeSessionContext()


async def test_db_session_rejects_none_tenant():
    with pytest.raises(ValueError, match="tenant_id is required"):
        async with db_session(tenant_id=None):
            pass  # pragma: no cover


async def test_db_session_accepts_valid_tenant(monkeypatch):
    # SQLite does not support PostgreSQL SET LOCAL RLS syntax, so we substitute
    # a fake session factory for this unit test. Full RLS behavior is covered by
    # integration tests against PostgreSQL.
    monkeypatch.setattr(db_module, "get_session_factory", lambda: _FakeSessionFactory())

    async with db_session(tenant_id="tenant-123") as session:
        assert session is not None
