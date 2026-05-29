from __future__ import annotations

"""Unit tests for StateManager (in-memory path).

Tests state persistence, LRU eviction, history recording, progress
calculation, and the list_active_workflows helper — all without Redis.
"""


import time

import pytest
from pydantic import ValidationError

from layer4_agents.engine.state_manager import StateManager
from layer4_agents.models.agent_state import (
    ROIAgentState,
    WorkflowStatus,
    WorkflowType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _roi_state(workflow_id: str, status: WorkflowStatus = WorkflowStatus.PENDING) -> ROIAgentState:
    """Create a minimal ROIAgentState for testing."""
    state = ROIAgentState(tenant_id="test-tenant", 
        workflow_id=workflow_id,
        workflow_type=WorkflowType.ROI_CALCULATOR,
    )
    state.status = status
    return state


# ============================================================================
# StateManager – basic save / load / delete
# ============================================================================

class TestStateManagerSaveAndLoad:
    """Tests for core save / load / delete operations."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(self):
        """State saved to memory can be retrieved with load_state()."""
        manager = StateManager()
        state = _roi_state("wf-roundtrip", WorkflowStatus.RUNNING)

        await manager.save_state("wf-roundtrip", state)
        loaded = await manager.load_state("wf-roundtrip")

        assert loaded is not None
        assert loaded.workflow_id == "wf-roundtrip"
        assert loaded.status == WorkflowStatus.RUNNING

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_load_nonexistent_workflow_returns_none(self):
        """load_state() returns None for an unknown workflow ID."""
        manager = StateManager()
        result = await manager.load_state("does-not-exist")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_removes_state(self):
        """delete_state() removes the persisted state."""
        manager = StateManager()
        state = _roi_state("wf-delete")

        await manager.save_state("wf-delete", state)
        await manager.delete_state("wf-delete")
        result = await manager.load_state("wf-delete")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_noop(self):
        """delete_state() on an unknown workflow does not raise."""
        manager = StateManager()
        await manager.delete_state("phantom-wf")  # should not raise

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_save_overwrites_existing_state(self):
        """save_state() replaces the previously persisted state."""
        manager = StateManager()
        state_v1 = _roi_state("wf-overwrite", WorkflowStatus.PENDING)
        state_v2 = _roi_state("wf-overwrite", WorkflowStatus.COMPLETED)

        await manager.save_state("wf-overwrite", state_v1)
        await manager.save_state("wf-overwrite", state_v2)
        loaded = await manager.load_state("wf-overwrite")

        assert loaded is not None
        assert loaded.status == WorkflowStatus.COMPLETED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_workflows_are_independent(self):
        """Different workflow IDs do not interfere with each other."""
        manager = StateManager()
        state_a = _roi_state("wf-a", WorkflowStatus.RUNNING)
        state_b = _roi_state("wf-b", WorkflowStatus.PAUSED)

        await manager.save_state("wf-a", state_a)
        await manager.save_state("wf-b", state_b)

        loaded_a = await manager.load_state("wf-a")
        loaded_b = await manager.load_state("wf-b")

        assert loaded_a is not None and loaded_a.status == WorkflowStatus.RUNNING
        assert loaded_b is not None and loaded_b.status == WorkflowStatus.PAUSED


# ============================================================================
# StateManager – TTL / expiry
# ============================================================================

class TestStateManagerTTL:
    """Tests for TTL-based expiry of in-memory entries."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_expired_state_returns_none(self):
        """State saved with TTL of -1 second is treated as expired."""
        manager = StateManager()
        state = _roi_state("wf-expired")

        # Save normally, then manually expire the entry
        await manager.save_state("wf-expired", state, ttl_seconds=3600)
        key = manager._get_key("wf-expired")
        # Force expiry by backdating the 'expires' timestamp
        manager._memory_store[key]["expires"] = time.time() - 1.0

        result = await manager.load_state("wf-expired")
        assert result is None


# ============================================================================
# StateManager – LRU eviction
# ============================================================================

class TestStateManagerLRUEviction:
    """Tests for LRU eviction when capacity is exceeded."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lru_eviction_removes_oldest_entry(self):
        """When max capacity is reached, the LRU entry is evicted."""
        manager = StateManager(max_memory_entries=3)

        for i in range(3):
            await manager.save_state(f"wf-{i}", _roi_state(f"wf-{i}"))

        # Verify all 3 are present
        for i in range(3):
            key = manager._get_key(f"wf-{i}")
            assert key in manager._memory_store

        # Add a 4th entry – the oldest (wf-0) should be evicted
        await manager.save_state("wf-3", _roi_state("wf-3"))

        assert manager._get_key("wf-0") not in manager._memory_store
        # The three newest entries remain
        for i in range(1, 4):
            assert manager._get_key(f"wf-{i}") in manager._memory_store

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lru_access_refreshes_order(self):
        """Accessing a stored entry refreshes it so it is not evicted first."""
        manager = StateManager(max_memory_entries=3)

        for i in range(3):
            await manager.save_state(f"wf-{i}", _roi_state(f"wf-{i}"))

        # Access wf-0 to refresh its LRU position
        await manager.load_state("wf-0")

        # Add a 4th entry – wf-1 (the new oldest) should be evicted instead
        await manager.save_state("wf-3", _roi_state("wf-3"))

        assert manager._get_key("wf-0") in manager._memory_store
        assert manager._get_key("wf-1") not in manager._memory_store

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_re_saving_existing_key_does_not_trigger_eviction(self):
        """Updating an existing entry does not count as a new entry for LRU capacity."""
        manager = StateManager(max_memory_entries=2)

        await manager.save_state("wf-a", _roi_state("wf-a"))
        await manager.save_state("wf-b", _roi_state("wf-b"))

        # Re-save wf-a (update, not new)
        await manager.save_state("wf-a", _roi_state("wf-a", WorkflowStatus.COMPLETED))

        # Both should still exist
        assert manager._get_key("wf-a") in manager._memory_store
        assert manager._get_key("wf-b") in manager._memory_store


# ============================================================================
# StateManager – progress calculation
# ============================================================================

class TestStateManagerProgress:
    """Tests for _calculate_progress()."""

    @pytest.mark.unit
    def test_completed_progress_is_100(self):
        manager = StateManager()
        state = _roi_state("wf", WorkflowStatus.COMPLETED)
        assert manager._calculate_progress(state) == 100.0

    @pytest.mark.unit
    def test_failed_progress_is_0(self):
        manager = StateManager()
        state = _roi_state("wf", WorkflowStatus.FAILED)
        assert manager._calculate_progress(state) == 0.0

    @pytest.mark.unit
    def test_running_progress_is_10(self):
        manager = StateManager()
        state = _roi_state("wf", WorkflowStatus.RUNNING)
        assert manager._calculate_progress(state) == 10.0

    @pytest.mark.unit
    def test_paused_without_output_is_25(self):
        manager = StateManager()
        state = _roi_state("wf", WorkflowStatus.PAUSED)
        state.output_data = {}
        assert manager._calculate_progress(state) == 25.0

    @pytest.mark.unit
    def test_paused_with_output_is_50(self):
        manager = StateManager()
        state = _roi_state("wf", WorkflowStatus.PAUSED)
        state.output_data = {"node1": {"result": "done"}}
        assert manager._calculate_progress(state) == 50.0

    @pytest.mark.unit
    def test_pending_progress_is_0(self):
        manager = StateManager()
        state = _roi_state("wf", WorkflowStatus.PENDING)
        assert manager._calculate_progress(state) == 0.0


# ============================================================================
# StateManager – history
# ============================================================================

class TestStateManagerHistory:
    """Tests for record_history() and get_history()."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_record_and_retrieve_history(self):
        """History entries can be saved and retrieved."""
        manager = StateManager()

        await manager.record_history(
            workflow_id="wf-hist",
            node_id="node-start",
            input_data={"key": "value"},
            output_data={"result": "ok"},
            duration_ms=42,
        )

        history = await manager.get_history("wf-hist")
        assert len(history) == 1
        entry = history[0]
        assert entry["node_id"] == "node-start"
        assert entry["duration_ms"] == 42

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_history_respects_limit(self):
        """get_history() returns at most `limit` entries."""
        manager = StateManager()

        for i in range(10):
            await manager.record_history(
                workflow_id="wf-limit",
                node_id=f"node-{i}",
                input_data={},
                output_data={},
                duration_ms=i,
            )

        history = await manager.get_history("wf-limit", limit=5)
        assert len(history) == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_history_is_empty_for_unknown_workflow(self):
        """get_history() returns an empty list for unknown workflow IDs."""
        manager = StateManager()
        history = await manager.get_history("unknown-wf")
        assert history == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_history_capped_at_100_entries(self):
        """In-memory history is capped at 100 entries per workflow."""
        manager = StateManager()

        for i in range(120):
            await manager.record_history(
                workflow_id="wf-cap",
                node_id=f"n{i}",
                input_data={},
                output_data={},
                duration_ms=0,
            )

        history = await manager.get_history("wf-cap", limit=200)
        assert len(history) <= 100


# ============================================================================
# StateManager – list_active_workflows
# ============================================================================

class TestStateManagerActiveWorkflows:
    """Tests for list_active_workflows() using the in-memory store."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_running_workflow_is_active(self):
        """RUNNING workflow IDs appear in list_active_workflows()."""
        manager = StateManager()
        await manager.save_state("wf-active", _roi_state("wf-active", WorkflowStatus.RUNNING))

        active = await manager.list_active_workflows()
        assert "wf-active" in active

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_completed_workflow_is_not_active(self):
        """COMPLETED workflows do not appear in list_active_workflows()."""
        manager = StateManager()
        await manager.save_state("wf-done", _roi_state("wf-done", WorkflowStatus.COMPLETED))

        active = await manager.list_active_workflows()
        assert "wf-done" not in active

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_paused_workflow_is_active(self):
        """PAUSED workflows are included in list_active_workflows()."""
        manager = StateManager()
        await manager.save_state("wf-paused", _roi_state("wf-paused", WorkflowStatus.PAUSED))

        active = await manager.list_active_workflows()
        assert "wf-paused" in active

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pending_workflow_is_active(self):
        """PENDING workflows are included in list_active_workflows()."""
        manager = StateManager()
        await manager.save_state("wf-pending", _roi_state("wf-pending", WorkflowStatus.PENDING))

        active = await manager.list_active_workflows()
        assert "wf-pending" in active

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_store_returns_empty_list(self):
        """list_active_workflows() returns [] when nothing is stored."""
        manager = StateManager()
        assert await manager.list_active_workflows() == []


# ============================================================================
# StateManager – secret redaction (security invariant)
# ============================================================================

class TestStateManagerSecretRedaction:
    """Tests for _redact_secrets — secrets must never be persisted in state."""

    @pytest.mark.unit
    def test_redacts_password_key(self):
        manager = StateManager()
        payload = {"username": "alice", "password": "super-secret"}
        result = manager._redact_secrets(payload)
        assert result["password"] == "[redacted]"
        assert result["username"] == "alice"

    @pytest.mark.unit
    def test_redacts_api_key_variant(self):
        manager = StateManager()
        payload = {"api_key": "sk-live-123", "api-key": "sk-live-456"}
        result = manager._redact_secrets(payload)
        assert result["api_key"] == "[redacted]"
        assert result["api-key"] == "[redacted]"

    @pytest.mark.unit
    def test_redacts_nested_secrets(self):
        manager = StateManager()
        payload = {
            "config": {
                "secret_token": "tok",
                "authorization": "Bearer xyz",
                "public_value": "ok",
            },
            "items": [
                {"private_key": "pk", "name": "item1"},
            ],
        }
        result = manager._redact_secrets(payload)
        assert result["config"]["secret_token"] == "[redacted]"
        assert result["config"]["authorization"] == "[redacted]"
        assert result["config"]["public_value"] == "ok"
        assert result["items"][0]["private_key"] == "[redacted]"
        assert result["items"][0]["name"] == "item1"

    @pytest.mark.unit
    def test_redacts_case_insensitive(self):
        manager = StateManager()
        payload = {"SECRET": "hidden", "Token": "t", "PassWord": "pw"}
        result = manager._redact_secrets(payload)
        assert result["SECRET"] == "[redacted]"
        assert result["Token"] == "[redacted]"
        assert result["PassWord"] == "[redacted]"

    @pytest.mark.unit
    def test_leaves_primitives_and_non_dicts_untouched(self):
        manager = StateManager()
        assert manager._redact_secrets("plain-string") == "plain-string"
        assert manager._redact_secrets(42) == 42
        assert manager._redact_secrets(None) is None


# ============================================================================
# StateManager – deserialization type guard
# ============================================================================

class TestStateManagerDeserializeState:
    """Tests for _deserialize_state — strict type dispatch and validation."""

    @pytest.mark.unit
    def test_deserialize_roi_calculator(self):
        manager = StateManager()
        state_dict = {
            "workflow_type": "roi_calculator",
            "tenant_id": "t1",
            "workflow_id": "wf-1",
            "status": "running",
        }
        state = manager._deserialize_state(state_dict)
        assert isinstance(state, ROIAgentState)

    @pytest.mark.unit
    def test_rejects_non_string_workflow_type(self):
        manager = StateManager()
        with pytest.raises(ValueError, match="Invalid workflow_type"):
            manager._deserialize_state({"workflow_type": 123})

    @pytest.mark.unit
    def test_rejects_unknown_workflow_type(self):
        manager = StateManager()
        with pytest.raises(ValueError, match="Unknown workflow_type"):
            manager._deserialize_state({"workflow_type": "malicious_type"})

    @pytest.mark.unit
    def test_parses_iso_datetime_strings(self):
        manager = StateManager()
        from datetime import datetime

        state_dict = {
            "workflow_type": "roi_calculator",
            "tenant_id": "t1",
            "workflow_id": "wf-1",
            "status": "running",
            "started_at": "2024-01-15T10:30:00Z",
            "completed_at": "2024-01-15T11:00:00+00:00",
        }
        state = manager._deserialize_state(state_dict)
        assert isinstance(state.started_at, datetime)
        assert isinstance(state.completed_at, datetime)

    @pytest.mark.unit
    def test_malformed_datetime_raises_validation_error(self):
        """Malformed datetime strings propagate as ValidationError (caught by load_state)."""
        manager = StateManager()
        state_dict = {
            "workflow_type": "roi_calculator",
            "tenant_id": "t1",
            "workflow_id": "wf-1",
            "status": "running",
            "started_at": "not-a-date",
        }
        with pytest.raises(ValidationError):
            manager._deserialize_state(state_dict)


# ============================================================================
# StateManager – list_workflows (all workflows, not just active)
# ============================================================================

class TestStateManagerListWorkflows:
    """Tests for list_workflows — includes completed, filters expired/history."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_includes_completed_workflows(self):
        manager = StateManager()
        await manager.save_state("wf-done", _roi_state("wf-done", WorkflowStatus.COMPLETED))
        ids = await manager.list_workflows()
        assert "wf-done" in ids

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_excludes_expired_workflows(self):
        manager = StateManager()
        await manager.save_state("wf-expired", _roi_state("wf-expired"), ttl_seconds=3600)
        # Force expiry
        key = manager._get_key("wf-expired")
        manager._memory_store[key]["expires"] = time.time() - 1.0
        ids = await manager.list_workflows()
        assert "wf-expired" not in ids

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_excludes_history_keys(self):
        manager = StateManager()
        await manager.record_history("wf-h", "node", {}, {}, 0)
        ids = await manager.list_workflows()
        # History entries should not appear as workflow IDs
        assert all("history" not in i for i in ids)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_sorted_unique_ids(self):
        manager = StateManager()
        await manager.save_state("wf-b", _roi_state("wf-b"))
        await manager.save_state("wf-a", _roi_state("wf-a"))
        await manager.save_state("wf-a", _roi_state("wf-a", WorkflowStatus.RUNNING))  # overwrite
        ids = await manager.list_workflows()
        assert ids == sorted(set(ids))
        assert "wf-a" in ids
        assert "wf-b" in ids


# ============================================================================
# StateManager – key generation helpers
# ============================================================================

class TestStateManagerKeys:
    """Tests for Redis key generation helpers."""

    @pytest.mark.unit
    def test_get_key_format(self):
        manager = StateManager()
        key = manager._get_key("my-workflow")
        assert key == "layer4:workflow:my-workflow"

    @pytest.mark.unit
    def test_get_history_key_format(self):
        manager = StateManager()
        key = manager._get_history_key("my-workflow")
        assert key == "layer4:workflow:my-workflow:history"

    @pytest.mark.unit
    def test_summarize_short_data(self):
        manager = StateManager()
        data = {"key": "value"}
        summary = manager._summarize(data)
        assert "key" in summary
        assert "value" in summary

    @pytest.mark.unit
    def test_summarize_truncates_long_data(self):
        manager = StateManager()
        data = {"long": "x" * 500}
        summary = manager._summarize(data, max_length=50)
        assert len(summary) <= 53  # 50 + "..."
        assert summary.endswith("...")
