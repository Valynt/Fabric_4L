"""Phase 3 tests for the in-memory MemoryPort adapter.

Covers tenant-scoped thread-state save/get semantics, deep-copy isolation, the
long-term search seam, and the fail-closed behavior required by the runtime
memory contract.
"""

from __future__ import annotations

from typing import Any

import pytest

from layer4_agents.runtime import InMemoryMemoryAdapter, TenantRequiredError
from layer4_agents.runtime.ports import MemoryPort

pytestmark = pytest.mark.unit


def _thread_state(**overrides: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "run_id": "run-1",
        "workflow_id": "wf-1",
        "workflow_type": "demo",
        "tenant_id": "tenant-a",
        "status": "interrupted",
        "turn": 2,
    }
    state.update(overrides)
    return state


def _record(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_id": "rec-1",
        "kind": "roi",
        "summary": "Acme prospect ROI analysis",
        "topics": ["roi", "manufacturing"],
    }
    record.update(overrides)
    return record


def test_inmemory_memory_adapter_satisfies_memory_port() -> None:
    adapter = InMemoryMemoryAdapter()
    assert isinstance(adapter, MemoryPort)


@pytest.mark.asyncio
async def test_save_and_get_thread_state_round_trip() -> None:
    adapter = InMemoryMemoryAdapter()
    await adapter.save_thread_state("thread-1", "tenant-a", _thread_state())

    state = await adapter.get_thread_state("thread-1", "tenant-a")

    assert state is not None
    assert state["run_id"] == "run-1"
    assert state["workflow_type"] == "demo"
    assert state["status"] == "interrupted"
    assert state["turn"] == 2


@pytest.mark.asyncio
async def test_get_thread_state_returns_deep_copy_not_store_reference() -> None:
    adapter = InMemoryMemoryAdapter()
    await adapter.save_thread_state("thread-1", "tenant-a", _thread_state())

    first = await adapter.get_thread_state("thread-1", "tenant-a")
    assert first is not None
    first["status"] = "completed"
    first["nested"] = {"mutated": True}

    second = await adapter.get_thread_state("thread-1", "tenant-a")
    assert second is not None
    assert second["status"] == "interrupted"
    assert "nested" not in second


@pytest.mark.asyncio
async def test_get_thread_state_is_scoped_by_thread() -> None:
    adapter = InMemoryMemoryAdapter()
    await adapter.save_thread_state("thread-1", "tenant-a", _thread_state(run_id="run-1"))
    await adapter.save_thread_state("thread-2", "tenant-a", _thread_state(run_id="run-2"))

    assert await adapter.get_thread_state("thread-1", "tenant-a") is not None
    state = await adapter.get_thread_state("thread-2", "tenant-a")
    assert state is not None and state["run_id"] == "run-2"


@pytest.mark.asyncio
async def test_save_thread_state_latest_write_wins_per_thread() -> None:
    adapter = InMemoryMemoryAdapter()
    await adapter.save_thread_state("thread-1", "tenant-a", _thread_state(status="running"))
    await adapter.save_thread_state("thread-1", "tenant-a", _thread_state(status="completed"))

    state = await adapter.get_thread_state("thread-1", "tenant-a")

    assert state is not None and state["status"] == "completed"


@pytest.mark.asyncio
async def test_save_thread_state_requires_tenant_and_fails_closed() -> None:
    adapter = InMemoryMemoryAdapter()

    with pytest.raises(TenantRequiredError) as exc_info:
        await adapter.save_thread_state("thread-1", "", _thread_state())

    assert exc_info.value.code == "TENANT_REQUIRED"


@pytest.mark.asyncio
async def test_cross_tenant_thread_state_is_invisible() -> None:
    adapter = InMemoryMemoryAdapter()
    await adapter.save_thread_state("thread-1", "tenant-a", _thread_state())

    # A different tenant must not see the thread at all (no data leak).
    assert await adapter.get_thread_state("thread-1", "tenant-b") is None


@pytest.mark.asyncio
async def test_search_long_term_matches_tenant_scoped_records() -> None:
    adapter = InMemoryMemoryAdapter()
    await adapter.add_long_term("tenant-a", _record())
    await adapter.add_long_term("tenant-a", _record(record_id="rec-2", summary="Beta planning for Acme expansion"))
    await adapter.add_long_term("tenant-b", _record(record_id="rec-3", summary="Acme confidential"))

    hits = await adapter.search_long_term("Acme", "tenant-a")

    assert [r["record_id"] for r in hits] == ["rec-2", "rec-1"]
    # tenant-b's matching record is never visible to tenant-a.
    assert all(r["record_id"] != "rec-3" for r in hits)


@pytest.mark.asyncio
async def test_search_long_term_respects_limit_and_most_recent_first() -> None:
    adapter = InMemoryMemoryAdapter()
    for index in range(5):
        await adapter.add_long_term(
            "tenant-a", _record(record_id=f"rec-{index}", summary=f"Acme analysis {index}")
        )

    hits = await adapter.search_long_term("Acme", "tenant-a", limit=2)

    assert [r["record_id"] for r in hits] == ["rec-4", "rec-3"]


@pytest.mark.asyncio
async def test_search_long_term_returns_deep_copies() -> None:
    adapter = InMemoryMemoryAdapter()
    await adapter.add_long_term("tenant-a", _record(topics=["roi"]))

    hits = await adapter.search_long_term("roi", "tenant-a")
    assert hits
    hits[0]["topics"].append("mutated")

    hits2 = await adapter.search_long_term("roi", "tenant-a")
    assert hits2 and hits2[0]["topics"] == ["roi"]


@pytest.mark.asyncio
async def test_search_long_term_requires_tenant_and_fails_closed() -> None:
    adapter = InMemoryMemoryAdapter()

    with pytest.raises(TenantRequiredError) as exc_info:
        await adapter.search_long_term("Acme", "")

    assert exc_info.value.code == "TENANT_REQUIRED"


@pytest.mark.asyncio
async def test_add_long_term_requires_tenant_and_fails_closed() -> None:
    adapter = InMemoryMemoryAdapter()

    with pytest.raises(TenantRequiredError):
        await adapter.add_long_term("", _record())
