"""Atomic converging-upsert behavior for the durable runtime adapters.

``PostgresMemoryAdapter.save_thread_state`` and ``PostgresCheckpointAdapter.save``
must converge on a single row per composite key under both the native
``ON CONFLICT DO UPDATE`` path (SQLite/PostgreSQL) and the dialect-agnostic
INSERT-then-UPDATE fallback. The composite UNIQUE constraint guarantees a
duplicate row is unrepresentable, so concurrent saves converge instead of
racing (the legacy SELECT-then-INSERT could abort a writer on IntegrityError).
"""

from __future__ import annotations

import asyncio

import pytest_asyncio
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from layer4_agents.runtime.adapters import PostgresCheckpointAdapter, PostgresMemoryAdapter
from layer4_agents.runtime.models import Checkpoint
from layer4_agents.runtime.orm import (
    Base,
    RuntimeCheckpointRow,
    RuntimeThreadStateRow,
)


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

    db_path = tmp_path / "runtime_upsert.db"
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
                tables=[RuntimeThreadStateRow.__table__, RuntimeCheckpointRow.__table__],
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


async def _count_thread_states(session_factory, tenant_id: str, thread_id: str) -> int:
    async with session_factory() as session:
        scalar = await session.scalar(
            select(func.count())
            .select_from(RuntimeThreadStateRow)
            .where(
                RuntimeThreadStateRow.tenant_id == tenant_id,
                RuntimeThreadStateRow.thread_id == thread_id,
            )
        )
        return int(scalar or 0)


async def _count_checkpoints(session_factory, tenant_id: str, run_id: str) -> int:
    async with session_factory() as session:
        scalar = await session.scalar(
            select(func.count())
            .select_from(RuntimeCheckpointRow)
            .where(
                RuntimeCheckpointRow.tenant_id == tenant_id,
                RuntimeCheckpointRow.run_id == run_id,
            )
        )
        return int(scalar or 0)


def _checkpoint(checkpoint_id: str = "cp-1", state_hash: str = "hash-1") -> Checkpoint:
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        run_id="run-1",
        thread_id="thread-1",
        tenant_id="tenant-a",
        state_hash=state_hash,
        created_at="2026-01-01T00:00:00+00:00",
        metadata={"k": "v"},
    )


class TestThreadStateUpsert:
    async def test_repeated_saves_converge_on_one_row(self, session_factory):
        adapter = PostgresMemoryAdapter(session_factory)
        await adapter.save_thread_state("thread-1", "tenant-a", {"v": 1})
        await adapter.save_thread_state("thread-1", "tenant-a", {"v": 2})

        assert await _count_thread_states(session_factory, "tenant-a", "thread-1") == 1
        state = await adapter.get_thread_state("thread-1", "tenant-a")
        assert state == {"v": 2}

    async def test_concurrent_saves_converge_on_one_row(self, session_factory):
        adapter = PostgresMemoryAdapter(session_factory)
        await asyncio.gather(
            *(adapter.save_thread_state("thread-1", "tenant-a", {"v": i}) for i in range(8))
        )

        assert await _count_thread_states(session_factory, "tenant-a", "thread-1") == 1
        state = await adapter.get_thread_state("thread-1", "tenant-a")
        assert state is not None and state["v"] in set(range(8))

    async def test_fallback_dialect_still_converges(self, session_factory, monkeypatch):
        monkeypatch.setattr(
            "layer4_agents.runtime.adapters._upsert._dialect_name",
            lambda session: "mysql",
        )
        adapter = PostgresMemoryAdapter(session_factory)
        await adapter.save_thread_state("thread-1", "tenant-a", {"v": 1})
        await adapter.save_thread_state("thread-1", "tenant-a", {"v": 2})

        assert await _count_thread_states(session_factory, "tenant-a", "thread-1") == 1
        state = await adapter.get_thread_state("thread-1", "tenant-a")
        assert state == {"v": 2}

    async def test_preexisting_row_is_updated_not_duplicated(self, session_factory):
        # Seed the row with a raw Core insert, then let the adapter upsert onto it.
        from sqlalchemy import insert

        async with session_factory() as session:
            async with session.begin():
                await session.execute(
                    insert(RuntimeThreadStateRow.__table__).values(
                        tenant_id="tenant-a",
                        thread_id="thread-1",
                        state={"seeded": True},
                    )
                )

        adapter = PostgresMemoryAdapter(session_factory)
        await adapter.save_thread_state("thread-1", "tenant-a", {"v": 9})

        assert await _count_thread_states(session_factory, "tenant-a", "thread-1") == 1
        state = await adapter.get_thread_state("thread-1", "tenant-a")
        assert state == {"v": 9}


class TestCheckpointUpsert:
    async def test_repeated_saves_converge_on_one_row(self, session_factory):
        adapter = PostgresCheckpointAdapter(session_factory)
        await adapter.save(_checkpoint(state_hash="hash-1"), {"v": 1})
        await adapter.save(_checkpoint(state_hash="hash-2"), {"v": 2})

        assert await _count_checkpoints(session_factory, "tenant-a", "run-1") == 1
        loaded = await adapter.load("run-1", "thread-1", "tenant-a")
        assert loaded is not None
        checkpoint, state = loaded
        assert checkpoint.state_hash == "hash-2"
        assert state == {"v": 2}

    async def test_fallback_dialect_still_converges(self, session_factory, monkeypatch):
        monkeypatch.setattr(
            "layer4_agents.runtime.adapters._upsert._dialect_name",
            lambda session: "mysql",
        )
        adapter = PostgresCheckpointAdapter(session_factory)
        await adapter.save(_checkpoint(state_hash="hash-1"), {"v": 1})
        await adapter.save(_checkpoint(state_hash="hash-2"), {"v": 2})

        assert await _count_checkpoints(session_factory, "tenant-a", "run-1") == 1
        loaded = await adapter.load("run-1", "thread-1", "tenant-a")
        assert loaded is not None
        checkpoint, state = loaded
        assert checkpoint.state_hash == "hash-2"
        assert state == {"v": 2}

    async def test_preexisting_row_is_updated_not_duplicated(self, session_factory):
        from sqlalchemy import insert

        async with session_factory() as session:
            async with session.begin():
                await session.execute(
                    insert(RuntimeCheckpointRow.__table__).values(
                        checkpoint_id="cp-1",
                        run_id="run-1",
                        thread_id="thread-1",
                        tenant_id="tenant-a",
                        state_hash="seeded-hash",
                        state={"seeded": True},
                        metadata={"seed": 1},
                        created_at="2026-01-01T00:00:00+00:00",
                    )
                )

        adapter = PostgresCheckpointAdapter(session_factory)
        await adapter.save(_checkpoint(state_hash="hash-9"), {"v": 9})

        assert await _count_checkpoints(session_factory, "tenant-a", "run-1") == 1
        loaded = await adapter.load("run-1", "thread-1", "tenant-a")
        assert loaded is not None
        checkpoint, state = loaded
        assert checkpoint.state_hash == "hash-9"
        assert checkpoint.metadata == {"k": "v"}
        assert state == {"v": 9}
