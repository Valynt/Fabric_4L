from __future__ import annotations

"""Durable Postgres ``MemoryPort`` adapter tests (SQLite-backed).

Exercises ``PostgresMemoryAdapter`` against a file-backed SQLite database — the
adapter opens a session per operation, so an in-memory ``:memory:`` engine would
not share data across sessions. No external Postgres required in CI.

The ``before_flush`` tenant-enforcement listener registered by
``layer4_agents.database`` fires on every flush with no tenant context set, so
the fixture removes it for the duration of each test and restores it afterward
(same pattern as ``test_harness_persistence.py``).
"""

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from layer4_agents.runtime.adapters import PostgresMemoryAdapter
from layer4_agents.runtime.errors import TenantRequiredError
from layer4_agents.runtime.orm import (
    Base,
    RuntimeLongTermMemoryRow,
    RuntimeThreadStateRow,
)
from layer4_agents.runtime.ports import MemoryPort


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    """File SQLite engine + session factory, with the tenant listener removed."""
    _removed: list = []
    try:
        clslevel = Session.dispatch.before_flush._clslevel
        for fn in list(clslevel.get(Session, [])):
            try:
                event.remove(Session, "before_flush", fn)
                _removed.append(fn)
            except Exception:
                pass
    except Exception:
        pass

    db_path = tmp_path / "runtime_memory.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 30.0},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    RuntimeThreadStateRow.__table__,
                    RuntimeLongTermMemoryRow.__table__,
                ],
            )
        )
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()

    for fn in _removed:
        try:
            if not event.contains(Session, "before_flush", fn):
                event.listen(Session, "before_flush", fn)
        except Exception:
            pass


def _adapter(session_factory) -> PostgresMemoryAdapter:
    return PostgresMemoryAdapter(session_factory)


class TestPostgresMemoryAdapter:
    async def test_port_conformance(self, session_factory):
        assert isinstance(_adapter(session_factory), MemoryPort)

    async def test_thread_state_round_trip(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save_thread_state("thread-1", "tenant-a", {"step": 1, "notes": ["x"]})
        state = await adapter.get_thread_state("thread-1", "tenant-a")
        assert state == {"step": 1, "notes": ["x"]}

    async def test_thread_state_latest_write_wins(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save_thread_state("thread-1", "tenant-a", {"v": 1})
        await adapter.save_thread_state("thread-1", "tenant-a", {"v": 2})
        assert await adapter.get_thread_state("thread-1", "tenant-a") == {"v": 2}

    async def test_thread_state_absent_returns_none(self, session_factory):
        adapter = _adapter(session_factory)
        assert await adapter.get_thread_state("missing", "tenant-a") is None

    async def test_thread_state_cross_tenant_invisible(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save_thread_state("thread-1", "tenant-a", {"v": 1})
        assert await adapter.get_thread_state("thread-1", "tenant-b") is None

    async def test_thread_state_deep_copy_isolation(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save_thread_state("thread-1", "tenant-a", {"nested": {"k": "v"}})
        first = await adapter.get_thread_state("thread-1", "tenant-a")
        assert first is not None
        first["nested"]["k"] = "mutated"
        second = await adapter.get_thread_state("thread-1", "tenant-a")
        assert second == {"nested": {"k": "v"}}

    async def test_missing_tenant_fails_closed(self, session_factory):
        adapter = _adapter(session_factory)
        with pytest.raises(TenantRequiredError):
            await adapter.get_thread_state("thread-1", "")
        with pytest.raises(TenantRequiredError):
            await adapter.save_thread_state("thread-1", "", {"v": 1})
        with pytest.raises(TenantRequiredError):
            await adapter.search_long_term("q", "")

    async def test_search_long_term_case_insensitive_substring(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.add_long_term("tenant-a", {"text": "Hello World"})
        await adapter.add_long_term("tenant-a", {"text": "unrelated"})
        results = await adapter.search_long_term("hello", "tenant-a")
        assert results == [{"text": "Hello World"}]

    async def test_search_long_term_tenant_scoped(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.add_long_term("tenant-a", {"text": "shared needle"})
        await adapter.add_long_term("tenant-b", {"text": "shared needle"})
        results = await adapter.search_long_term("needle", "tenant-a")
        assert results == [{"text": "shared needle"}]
        assert len(results) == 1

    async def test_search_long_term_most_recent_first_and_limit(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.add_long_term("tenant-a", {"i": 1, "text": "needle"})
        await adapter.add_long_term("tenant-a", {"i": 2, "text": "needle"})
        await adapter.add_long_term("tenant-a", {"i": 3, "text": "needle"})
        results = await adapter.search_long_term("needle", "tenant-a", limit=2)
        assert results == [{"i": 3, "text": "needle"}, {"i": 2, "text": "needle"}]

    async def test_search_long_term_zero_limit_returns_empty(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.add_long_term("tenant-a", {"text": "needle"})
        assert await adapter.search_long_term("needle", "tenant-a", limit=0) == []

    async def test_add_long_term_fails_closed(self, session_factory):
        adapter = _adapter(session_factory)
        with pytest.raises(TenantRequiredError):
            await adapter.add_long_term("", {"text": "x"})
