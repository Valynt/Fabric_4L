"""Phase 2 tests for the in-memory CheckpointPort adapter.

Covers tenant-scoped save/load/list semantics, deep-copy isolation, and the
fail-closed behavior required by the runtime checkpoint contract.
"""

from __future__ import annotations

from typing import Any

import pytest

from layer4_agents.runtime import (
    Checkpoint,
    InMemoryCheckpointAdapter,
    TenantRequiredError,
)
from layer4_agents.runtime.ports import CheckpointPort

pytestmark = pytest.mark.unit


def _checkpoint(**overrides: Any) -> Checkpoint:
    values: dict[str, Any] = {
        "checkpoint_id": "run-1:state:abc12345",
        "run_id": "run-1",
        "thread_id": "thread-1",
        "tenant_id": "tenant-a",
        "state_hash": "ab" * 32,
        "metadata": {"workflow_type": "demo", "status": "paused"},
    }
    values.update(overrides)
    return Checkpoint(**values)


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tenant_id": "tenant-a",
        "workflow_id": "wf-1",
        "run_id": "run-1",
        "trace_id": "trace-1",
        "workflow_type": "roi_calculator",
        "status": "interrupted",
        "input_data": {"prospect_id": "acme"},
        "output_data": {"start": {"ok": True}},
    }
    payload.update(overrides)
    return payload


def test_inmemory_checkpoint_adapter_satisfies_checkpoint_port() -> None:
    adapter = InMemoryCheckpointAdapter()
    assert isinstance(adapter, CheckpointPort)


@pytest.mark.asyncio
async def test_save_and_load_round_trip() -> None:
    adapter = InMemoryCheckpointAdapter()
    checkpoint = _checkpoint()
    payload = _payload()

    await adapter.save(checkpoint, payload)
    loaded = await adapter.load("run-1", "thread-1", "tenant-a")

    assert loaded is not None
    loaded_checkpoint, loaded_payload = loaded
    assert loaded_checkpoint.checkpoint_id == checkpoint.checkpoint_id
    assert loaded_checkpoint.tenant_id == "tenant-a"
    assert loaded_checkpoint.state_hash == checkpoint.state_hash
    assert loaded_payload["tenant_id"] == "tenant-a"
    assert loaded_payload["status"] == "interrupted"
    assert loaded_payload["input_data"]["prospect_id"] == "acme"


@pytest.mark.asyncio
async def test_load_returns_deep_copies_not_store_references() -> None:
    adapter = InMemoryCheckpointAdapter()
    await adapter.save(_checkpoint(), _payload())

    first = await adapter.load("run-1", "thread-1", "tenant-a")
    assert first is not None
    first_checkpoint, first_payload = first
    first_checkpoint.metadata = {"mutated": True}  # type: ignore[union-attr]
    first_payload["status"] = "completed"
    first_payload["input_data"]["prospect_id"] = "mutated"

    second = await adapter.load("run-1", "thread-1", "tenant-a")
    assert second is not None
    _checkpoint2, payload2 = second
    assert payload2["status"] == "interrupted"
    assert payload2["input_data"]["prospect_id"] == "acme"


@pytest.mark.asyncio
async def test_save_requires_tenant_and_fails_closed() -> None:
    adapter = InMemoryCheckpointAdapter()
    checkpoint = _checkpoint(tenant_id="")

    with pytest.raises(TenantRequiredError) as exc_info:
        await adapter.save(checkpoint, _payload())

    assert exc_info.value.code == "TENANT_REQUIRED"


@pytest.mark.asyncio
async def test_load_without_checkpoint_id_returns_latest_for_thread() -> None:
    adapter = InMemoryCheckpointAdapter()
    await adapter.save(_checkpoint(checkpoint_id="run-1:state:aaaaaaaa", state_hash="aa" * 32), _payload())
    await adapter.save(_checkpoint(checkpoint_id="run-1:state:bbbbbbbb", state_hash="bb" * 32), _payload())

    loaded = await adapter.load("run-1", "thread-1", "tenant-a")

    assert loaded is not None
    checkpoint, _payload2 = loaded
    assert checkpoint.checkpoint_id == "run-1:state:bbbbbbbb"
    assert checkpoint.state_hash == "bb" * 32


@pytest.mark.asyncio
async def test_load_by_checkpoint_id() -> None:
    adapter = InMemoryCheckpointAdapter()
    await adapter.save(_checkpoint(checkpoint_id="run-1:state:aaaaaaaa", state_hash="aa" * 32), _payload())
    await adapter.save(_checkpoint(checkpoint_id="run-1:state:bbbbbbbb", state_hash="bb" * 32), _payload())

    loaded = await adapter.load(
        "run-1", "thread-1", "tenant-a", checkpoint_id="run-1:state:aaaaaaaa"
    )

    assert loaded is not None
    checkpoint, _payload2 = loaded
    assert checkpoint.checkpoint_id == "run-1:state:aaaaaaaa"


@pytest.mark.asyncio
async def test_load_scoped_by_thread() -> None:
    adapter = InMemoryCheckpointAdapter()
    await adapter.save(_checkpoint(thread_id="thread-1"), _payload())
    await adapter.save(_checkpoint(thread_id="thread-2"), _payload())

    loaded = await adapter.load("run-1", "thread-1", "tenant-a")

    assert loaded is not None
    checkpoint, _payload2 = loaded
    assert checkpoint.thread_id == "thread-1"


@pytest.mark.asyncio
async def test_list_returns_checkpoints_in_save_order() -> None:
    adapter = InMemoryCheckpointAdapter()
    await adapter.save(_checkpoint(checkpoint_id="run-1:state:aaaaaaaa"), _payload())
    await adapter.save(_checkpoint(checkpoint_id="run-1:state:bbbbbbbb"), _payload())

    checkpoints = await adapter.list("run-1", "tenant-a")

    assert [c.checkpoint_id for c in checkpoints] == [
        "run-1:state:aaaaaaaa",
        "run-1:state:bbbbbbbb",
    ]


@pytest.mark.asyncio
async def test_cross_tenant_read_fails_closed() -> None:
    adapter = InMemoryCheckpointAdapter()
    await adapter.save(_checkpoint(), _payload())

    # A different tenant must not see the run at all (no data leak).
    assert await adapter.list("run-1", "tenant-b") == []
    assert await adapter.load("run-1", "thread-1", "tenant-b") is None
