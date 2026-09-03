from __future__ import annotations

"""Durable Postgres ``CheckpointPort`` adapter tests (SQLite-backed).

Exercises ``PostgresCheckpointAdapter`` against a file-backed SQLite database —
the adapter opens a session per operation, so an in-memory ``:memory:`` engine
would not share data across sessions. No external Postgres required in CI.

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

from layer4_agents.runtime.adapters import PostgresCheckpointAdapter
from layer4_agents.runtime.errors import TenantRequiredError
from layer4_agents.runtime.models import Checkpoint
from layer4_agents.runtime.orm import Base, RuntimeCheckpointRow
from layer4_agents.runtime.ports import CheckpointPort


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

    db_path = tmp_path / "runtime_checkpoints.db"
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
                tables=[RuntimeCheckpointRow.__table__],
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


def _adapter(session_factory) -> PostgresCheckpointAdapter:
    return PostgresCheckpointAdapter(session_factory)


def _checkpoint(
    checkpoint_id: str = "cp-1",
    *,
    run_id: str = "run-1",
    thread_id: str = "thread-1",
    tenant_id: str = "tenant-a",
    state_hash: str = "hash-1",
    created_at: str = "2026-08-26T00:00:00+00:00",
    metadata: dict | None = None,
) -> Checkpoint:
    return Checkpoint(
        checkpoint_id=checkpoint_id,
        run_id=run_id,
        thread_id=thread_id,
        tenant_id=tenant_id,
        state_hash=state_hash,
        created_at=created_at,
        metadata=metadata,
    )


class TestPostgresCheckpointAdapter:
    async def test_port_conformance(self, session_factory):
        assert isinstance(_adapter(session_factory), CheckpointPort)

    async def test_save_load_round_trip(self, session_factory):
        adapter = _adapter(session_factory)
        checkpoint = _checkpoint(metadata={"note": "first"})
        await adapter.save(checkpoint, {"step": 1})
        loaded = await adapter.load("run-1", "thread-1", "tenant-a")
        assert loaded is not None
        ckpt, state = loaded
        assert ckpt == checkpoint
        assert state == {"step": 1}

    async def test_save_replace_by_composite_key(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save(_checkpoint(state_hash="hash-1"), {"v": 1})
        await adapter.save(_checkpoint(state_hash="hash-2"), {"v": 2})
        loaded = await adapter.load("run-1", "thread-1", "tenant-a")
        assert loaded is not None
        ckpt, state = loaded
        assert ckpt.state_hash == "hash-2"
        assert state == {"v": 2}

    async def test_load_latest_when_multiple_thread_checkpoints(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save(_checkpoint(checkpoint_id="cp-1", state_hash="h1"), {"v": 1})
        await adapter.save(_checkpoint(checkpoint_id="cp-2", state_hash="h2"), {"v": 2})
        loaded = await adapter.load("run-1", "thread-1", "tenant-a")
        assert loaded is not None
        ckpt, _ = loaded
        assert ckpt.checkpoint_id == "cp-2"

    async def test_load_by_checkpoint_id(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save(_checkpoint(checkpoint_id="cp-1"), {"v": 1})
        await adapter.save(_checkpoint(checkpoint_id="cp-2"), {"v": 2})
        loaded = await adapter.load("run-1", "thread-1", "tenant-a", checkpoint_id="cp-1")
        assert loaded is not None
        ckpt, state = loaded
        assert ckpt.checkpoint_id == "cp-1"
        assert state == {"v": 1}

    async def test_load_absent_returns_none(self, session_factory):
        adapter = _adapter(session_factory)
        assert await adapter.load("run-1", "thread-1", "tenant-a") is None

    async def test_list_save_order(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save(_checkpoint(checkpoint_id="cp-2"), {"v": 2})
        await adapter.save(_checkpoint(checkpoint_id="cp-1"), {"v": 1})
        checkpoints = await adapter.list("run-1", "tenant-a")
        assert [c.checkpoint_id for c in checkpoints] == ["cp-2", "cp-1"]

    async def test_cross_tenant_invisible(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save(_checkpoint(), {"v": 1})
        assert await adapter.load("run-1", "thread-1", "tenant-b") is None
        assert await adapter.list("run-1", "tenant-b") == []

    async def test_missing_tenant_save_fails_closed(self, session_factory):
        adapter = _adapter(session_factory)
        with pytest.raises(TenantRequiredError):
            await adapter.save(_checkpoint(tenant_id=""), {"v": 1})

    async def test_metadata_and_created_at_round_trip(self, session_factory):
        adapter = _adapter(session_factory)
        checkpoint = _checkpoint(
            created_at="2026-01-02T03:04:05+00:00",
            metadata={"source": "unit-test", "n": 1},
        )
        await adapter.save(checkpoint, {"v": 1})
        loaded = await adapter.load("run-1", "thread-1", "tenant-a")
        assert loaded is not None
        ckpt, _ = loaded
        assert ckpt.created_at == "2026-01-02T03:04:05+00:00"
        assert ckpt.metadata == {"source": "unit-test", "n": 1}

    async def test_state_deep_copy_isolation(self, session_factory):
        adapter = _adapter(session_factory)
        await adapter.save(_checkpoint(), {"nested": {"k": "v"}})
        first = await adapter.load("run-1", "thread-1", "tenant-a")
        assert first is not None
        _, state = first
        state["nested"]["k"] = "mutated"
        second = await adapter.load("run-1", "thread-1", "tenant-a")
        assert second is not None
        _, state2 = second
        assert state2 == {"nested": {"k": "v"}}
