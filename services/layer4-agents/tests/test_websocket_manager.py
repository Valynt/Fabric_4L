from __future__ import annotations

"""Tests for WebSocket manager workflow streaming.

Tests the pub/sub-style event broadcasting system with connection resilience,
event replay, and workflow-scoped channels.
"""


from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import WebSocket

from layer4_agents.api.websocket.manager import (
    EventStore,
    WorkflowConnection,
    WorkflowWebSocketManager,
    get_ws_manager,
)

# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def ws_manager() -> AsyncGenerator[WorkflowWebSocketManager, None]:
    """Provide a fresh WebSocket manager instance."""
    manager = WorkflowWebSocketManager()
    yield manager
    # Cleanup
    await manager.stop()


@pytest_asyncio.fixture
async def started_manager(ws_manager) -> AsyncGenerator[WorkflowWebSocketManager, None]:
    """Provide a started WebSocket manager."""
    await ws_manager.start()
    yield ws_manager
    await ws_manager.stop()


@pytest.fixture
def mock_websocket() -> WebSocket:
    """Create a mock WebSocket with common methods."""
    ws = MagicMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


# ============================================================================
# EventStore Tests
# ============================================================================

class TestEventStore:
    """Test event storage and replay functionality."""
    
    def test_adds_event_with_timestamp(self):
        """Event storage should add _stored_at timestamp to events."""
        # Arrange
        store = EventStore(max_events=10)
        event = {"event_id": "evt-1", "data": "test"}
        
        # Act
        store.add(event)
        
        # Assert
        assert len(store.events) == 1
        assert "_stored_at" in store.events[0]
        assert store.events[0]["event_id"] == "evt-1"
    
    def test_maintains_max_size_as_ring_buffer(self):
        """Event store should act as ring buffer, dropping oldest events."""
        # Arrange
        store = EventStore(max_events=3)
        
        # Act - add 5 events to 3-slot buffer
        for i in range(5):
            store.add({"event_id": f"evt-{i}"})
        
        # Assert - only last 3 events remain
        assert len(store.events) == 3
        assert store.events[0]["event_id"] == "evt-2"
        assert store.events[2]["event_id"] == "evt-4"
    
    def test_get_since_returns_events_after_event_id(self):
        """Should return all events after the specified event ID."""
        # Arrange
        store = EventStore()
        for i in range(5):
            store.add({"event_id": f"evt-{i}"})
        
        # Act
        result = store.get_since("evt-2")
        
        # Assert
        assert len(result) == 2
        assert result[0]["event_id"] == "evt-3"
        assert result[1]["event_id"] == "evt-4"
    
    def test_get_since_returns_empty_for_unknown_id(self):
        """Should return empty list if event ID not found."""
        # Arrange
        store = EventStore()
        store.add({"event_id": "evt-1"})
        
        # Act
        result = store.get_since("unknown-id")
        
        # Assert
        assert result == []
    
    def test_get_since_returns_last_10_by_default(self):
        """Should return last 10 events when no last_event_id provided."""
        # Arrange
        store = EventStore(max_events=100)
        for i in range(20):
            store.add({"event_id": f"evt-{i}"})
        
        # Act
        result = store.get_since(None)
        
        # Assert
        assert len(result) == 10
        assert result[0]["event_id"] == "evt-10"


# ============================================================================
# WorkflowConnection Tests
# ============================================================================

class TestWorkflowConnection:
    """Test WebSocket connection wrapper."""
    
    @pytest.mark.asyncio
    async def test_send_event_success_updates_last_event_id(self, mock_websocket):
        """Successful send should update last_event_id tracking."""
        # Arrange
        conn = WorkflowConnection(
            websocket=mock_websocket,
            workflow_id="wf-1",
            last_event_id=None
        )
        event = {"event_id": "evt-123"}
        
        # Act
        result = await conn.send_event(event)
        
        # Assert
        assert result is True
        assert conn.last_event_id == "evt-123"
        mock_websocket.send_json.assert_called_once_with(event)
    
    @pytest.mark.asyncio
    async def test_send_event_failure_marks_connection_dead(self, mock_websocket):
        """Failed send should mark connection as not alive."""
        # Arrange
        conn = WorkflowConnection(
            websocket=mock_websocket,
            workflow_id="wf-1"
        )
        mock_websocket.send_json.side_effect = Exception("Connection broken")
        
        # Act
        result = await conn.send_event({"event_id": "evt-1"})
        
        # Assert
        assert result is False
        assert conn.is_alive is False
    
    @pytest.mark.asyncio
    async def test_send_event_to_dead_connection_returns_false(self, mock_websocket):
        """Sending to already-dead connection should return False immediately."""
        # Arrange
        conn = WorkflowConnection(
            websocket=mock_websocket,
            workflow_id="wf-1",
            is_alive=False
        )
        
        # Act
        result = await conn.send_event({"event_id": "evt-1"})
        
        # Assert
        assert result is False
        mock_websocket.send_json.assert_not_called()


# ============================================================================
# WorkflowWebSocketManager Tests
# ============================================================================

class TestManagerLifecycle:
    """Test manager start/stop lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_creates_background_tasks(self, ws_manager):
        """Starting manager should create cleanup and heartbeat tasks."""
        # Act
        await ws_manager.start()
        
        # Assert
        assert ws_manager._cleanup_task is not None
        assert ws_manager._heartbeat_task is not None
        assert not ws_manager._cleanup_task.done()
        assert not ws_manager._heartbeat_task.done()
    
    @pytest.mark.asyncio
    async def test_stop_cancels_background_tasks(self, started_manager):
        """Stopping manager should cancel background tasks."""
        # Act
        await started_manager.stop()
        
        # Assert
        assert started_manager._cleanup_task is None or started_manager._cleanup_task.done()
        assert started_manager._heartbeat_task is None or started_manager._heartbeat_task.done()
    
    @pytest.mark.asyncio
    async def test_stop_closes_all_connections(self, started_manager, mock_websocket):
        """Stopping should gracefully close all active connections."""
        # Arrange - connect a client
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Act
        await started_manager.stop()
        
        # Assert
        mock_websocket.close.assert_called_once_with(
            code=1001,
            reason="Server shutting down"
        )
        assert len(started_manager._workflow_connections) == 0


class TestConnectionManagement:
    """Test WebSocket connect/disconnect functionality."""
    
    @pytest.mark.asyncio
    async def test_connect_accepts_websocket_and_stores_connection(
        self, started_manager, mock_websocket
    ):
        """Connect should accept WebSocket and track the connection."""
        # Act
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Assert
        mock_websocket.accept.assert_called_once()
        assert "wf-1" in started_manager._workflow_connections
        assert len(started_manager._workflow_connections["wf-1"]) == 1
    
    @pytest.mark.asyncio
    async def test_connect_sends_connection_established_event(
        self, started_manager, mock_websocket
    ):
        """Connect should send connection established event to client."""
        # Act
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Assert
        calls = mock_websocket.send_json.call_args_list
        # First call should be connection_established
        first_call = calls[0][0][0]
        assert first_call["event_type"] == "connection_established"
        assert first_call["workflow_id"] == "wf-1"
        assert "replay_count" in first_call
        assert "trace_id" in first_call
        assert "correlation_id" in first_call
        assert "request_id" in first_call
        assert "x_request_id" in first_call
        assert "connection_trace_id" in first_call

    @pytest.mark.asyncio
    async def test_connect_includes_trace_metadata_when_provided(
        self, started_manager, mock_websocket
    ):
        await started_manager.connect(mock_websocket, "wf-1", x_request_id="req-999")
        first_call = mock_websocket.send_json.call_args_list[0][0][0]
        assert first_call["trace_id"] == "req-999"
        assert first_call["x_request_id"] == "req-999"
        assert first_call["connection_trace_id"] == "req-999"
        assert first_call["correlation_id"] == "req-999"
        assert first_call["request_id"] == "req-999"
    
    @pytest.mark.asyncio
    async def test_connect_replays_missed_events_on_reconnect(
        self, started_manager, mock_websocket
    ):
        """Connect with last_event_id should replay missed events."""
        # Arrange - add some events to store
        started_manager._event_stores["wf-1"] = EventStore()
        for i in range(5):
            started_manager._event_stores["wf-1"].add({"event_id": f"evt-{i}"})
        
        # Act - reconnect with last seen event
        await started_manager.connect(mock_websocket, "wf-1", last_event_id="evt-2")
        
        # Assert - should replay evt-3 and evt-4
        calls = mock_websocket.send_json.call_args_list
        # First calls should be replayed events
        event_ids = [call[0][0].get("event_id") for call in calls[:-1]]  # Exclude connection_established
        assert "evt-3" in event_ids
        assert "evt-4" in event_ids
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, started_manager, mock_websocket):
        """Disconnect should remove connection from tracking."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Act
        await started_manager.disconnect(mock_websocket, "wf-1")
        
        # Assert - connections removed but event store preserved for replay
        assert "wf-1" not in started_manager._workflow_connections
        assert "wf-1" in started_manager._event_stores  # Kept for reconnection replay
    
    @pytest.mark.asyncio
    async def test_multiple_connections_same_workflow(self, started_manager, mock_websocket):
        """Multiple clients can connect to same workflow."""
        # Arrange
        ws2 = MagicMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        
        # Act
        await started_manager.connect(mock_websocket, "wf-1")
        await started_manager.connect(ws2, "wf-1")
        
        # Assert
        assert len(started_manager._workflow_connections["wf-1"]) == 2


class TestBroadcasting:
    """Test event broadcasting to workflow connections."""
    
    @pytest.mark.asyncio
    async def test_broadcast_to_workflow_delivers_to_all_connections(
        self, started_manager, mock_websocket
    ):
        """Broadcast should deliver event to all connected clients."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Act
        delivered = await started_manager.broadcast_to_workflow(
            workflow_id="wf-1",
            event_type="test_event",
            payload={"data": "test"}
        )
        
        # Assert
        assert delivered == 1
        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event_type"] == "test_event"
        assert call_args["payload"]["data"] == "test"
    
    @pytest.mark.asyncio
    async def test_broadcast_stores_event_for_replay(self, started_manager, mock_websocket):
        """Broadcast should store event for future replay."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Act
        await started_manager.broadcast_to_workflow(
            workflow_id="wf-1",
            event_type="state_update",
            payload={"status": "running"}
        )
        
        # Assert
        assert "wf-1" in started_manager._event_stores
        store = started_manager._event_stores["wf-1"]
        assert len(store.events) == 1
        assert store.events[0]["event_type"] == "state_update"
    
    @pytest.mark.asyncio
    async def test_broadcast_returns_zero_for_unknown_workflow(self, started_manager):
        """Broadcast to non-existent workflow should return 0."""
        # Act
        delivered = await started_manager.broadcast_to_workflow(
            workflow_id="unknown-wf",
            event_type="test",
            payload={}
        )
        
        # Assert
        assert delivered == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_cleans_up_dead_connections(
        self, started_manager, mock_websocket
    ):
        """Broadcast should remove dead connections and not count them."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        # Make connection fail on next send
        mock_websocket.send_json.side_effect = Exception("Connection dead")
        
        # Act
        delivered = await started_manager.broadcast_to_workflow(
            workflow_id="wf-1",
            event_type="test",
            payload={}
        )
        
        # Assert
        assert delivered == 0
        # Connection should be cleaned up (empty workflow entry removed entirely)
        assert "wf-1" not in started_manager._workflow_connections
    
    @pytest.mark.asyncio
    async def test_broadcast_state_update_sends_formatted_event(
        self, started_manager, mock_websocket
    ):
        """Broadcast state update should send properly formatted event."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Act
        await started_manager.broadcast_state_update(
            workflow_id="wf-1",
            status="running",
            current_node="extract_data",
            progress_percentage=50.0
        )
        
        # Assert
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event_type"] == "state_update"
        assert call_args["payload"]["status"] == "running"
        assert call_args["payload"]["current_node"] == "extract_data"
        assert call_args["payload"]["progress_percentage"] == 50.0
    
    @pytest.mark.asyncio
    async def test_broadcast_node_transition(self, started_manager, mock_websocket):
        """Broadcast node transition should send transition event."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Act
        await started_manager.broadcast_node_transition(
            workflow_id="wf-1",
            from_node="start",
            to_node="process",
            node_output={"result": "success"}
        )
        
        # Assert
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event_type"] == "node_transition"
        assert call_args["payload"]["from_node"] == "start"
        assert call_args["payload"]["to_node"] == "process"
    
    @pytest.mark.asyncio
    async def test_broadcast_pause_point(self, started_manager, mock_websocket):
        """Broadcast pause point should send pause event with action info."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Act
        await started_manager.broadcast_pause_point(
            workflow_id="wf-1",
            pause_point={
                "title": "Review Required",
                "reason": "Human validation needed",
                "severity": "high"
            }
        )
        
        # Assert
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event_type"] == "pause_point"
        assert call_args["payload"]["requires_action"] is True
        assert call_args["payload"]["can_resume"] is True
    
    @pytest.mark.asyncio
    async def test_broadcast_completion(self, started_manager, mock_websocket):
        """Broadcast completion should send workflow complete event."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        
        # Act
        await started_manager.broadcast_completion(
            workflow_id="wf-1",
            status="completed",
            final_output={"result": "success"},
            errors=[]
        )
        
        # Assert
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event_type"] == "workflow_complete"
        assert call_args["payload"]["status"] == "completed"
        assert call_args["payload"]["errors"] == []


class TestOutputSummarization:
    """Test output summarization for streaming."""
    
    def test_summarize_output_truncates_large_values(self, ws_manager):
        """Should truncate large string values."""
        # Arrange
        output = {"key": "x" * 200}
        
        # Act
        result = ws_manager._summarize_output(output)
        
        # Assert
        assert len(result["key"]) <= 103  # 100 + "..."
        assert result["key"].endswith("...")
    
    def test_summarize_output_summarizes_collections(self, ws_manager):
        """Should summarize list/dict values with type and length."""
        # Arrange
        output = {
            "items": [1, 2, 3, 4, 5],
            "nested": {"a": 1, "b": 2}
        }
        
        # Act
        result = ws_manager._summarize_output(output)
        
        # Assert
        assert result["items"] == "<list len=5>"
        assert result["nested"] == "<dict len=2>"
    
    def test_summarize_output_limits_keys(self, ws_manager):
        """Should limit number of keys in summary."""
        # Arrange
        output = {f"key_{i}": f"value_{i}" for i in range(10)}
        
        # Act
        result = ws_manager._summarize_output(output, max_keys=5)
        
        # Assert
        assert len(result) == 6  # 5 keys + _additional_keys
        assert result["_additional_keys"] == 5
    
    def test_summarize_output_handles_empty(self, ws_manager):
        """Should handle empty output gracefully."""
        # Act
        result = ws_manager._summarize_output({})
        
        # Assert
        assert dict(result) == {}
    
    def test_summarize_output_handles_none(self, ws_manager):
        """Should handle None output gracefully."""
        # Act
        result = ws_manager._summarize_output(None)
        
        # Assert
        assert dict(result) == {}

    @pytest.mark.asyncio
    async def test_broadcast_cross_tenant_isolation(self, started_manager, mock_websocket):
        """Events scoped to Tenant A should never be delivered to Tenant B connection."""
        ws_b = MagicMock(spec=WebSocket)
        ws_b.accept = AsyncMock()
        ws_b.send_json = AsyncMock()
        ws_b.close = AsyncMock()

        # Connect Tenant A
        await started_manager.connect(mock_websocket, "wf-shared", tenant_id="tenant-a")
        # Connect second socket with different tenant
        conn_b = WorkflowConnection(
            websocket=ws_b,
            workflow_id="wf-shared",
            tenant_id="tenant-b",
        )
        started_manager._workflow_connections["wf-shared"].add(conn_b)

        # Broadcast event specifically for tenant-a
        delivered = await started_manager.broadcast_to_workflow(
            workflow_id="wf-shared",
            event_type="tenant_event",
            payload={"secret": "alpha"},
            tenant_id="tenant-a",
        )

        assert delivered == 1
        # mock_websocket received the event (plus connection_established)
        sent_events_a = [call[0][0]["event_type"] for call in mock_websocket.send_json.call_args_list]
        assert "tenant_event" in sent_events_a

        # ws_b should NOT receive the tenant_event
        sent_events_b = [call[0][0]["event_type"] for call in ws_b.send_json.call_args_list]
        assert "tenant_event" not in sent_events_b


class TestClientMessageHandling:
    """Test handling of messages from clients."""
    
    @pytest.mark.asyncio
    async def test_handle_pong_marks_connection_alive(self, started_manager, mock_websocket):
        """Pong message should mark connection as alive."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        # Mark as potentially dead
        for conn in started_manager._workflow_connections["wf-1"]:
            conn.is_alive = False
        
        # Act
        await started_manager.handle_client_message(
            mock_websocket, "wf-1", {"type": "pong"}
        )
        
        # Assert
        for conn in started_manager._workflow_connections["wf-1"]:
            assert conn.is_alive is True
    
    @pytest.mark.asyncio
    async def test_handle_ack_logs_debug(self, started_manager, mock_websocket):
        """Ack message should log debug information."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1", trace_id="trace-ack-1")

        # Act & Assert (no error)
        with patch("layer4_agents.api.websocket.manager.logger") as mock_logger:
            await started_manager.handle_client_message(
                mock_websocket,
                "wf-1",
                {"type": "ack", "event_id": "evt-123"},
                trace_id="trace-ack-1",
            )
            mock_logger.debug.assert_called_once()
            extra = mock_logger.debug.call_args.kwargs["extra"]
            assert extra["trace_id"] == "trace-ack-1"
            assert extra["correlation_id"] == "trace-ack-1"
            assert extra["request_id"] == "trace-ack-1"
            assert extra["x_request_id"] == "trace-ack-1"
    
    @pytest.mark.asyncio
    async def test_handle_subscribe_history_sends_events(
        self, started_manager, mock_websocket
    ):
        """Subscribe history should send last 50 events."""
        # Arrange
        await started_manager.connect(mock_websocket, "wf-1")
        # Add some events
        for i in range(10):
            started_manager._event_stores["wf-1"].add({"event_id": f"evt-{i}"})
        
        # Act
        await started_manager.handle_client_message(
            mock_websocket, "wf-1", {"type": "subscribe_history"}
        )
        
        # Assert
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["event_type"] == "history_response"
        assert len(call_args["events"]) == 10


class TestSingleton:
    """Test global singleton instance."""
    
    def test_get_ws_manager_returns_same_instance(self):
        """Should return same manager instance on multiple calls."""
        # Act
        manager1 = get_ws_manager()
        manager2 = get_ws_manager()
        
        # Assert
        assert manager1 is manager2
    
    def test_get_ws_manager_creates_new_if_none(self):
        """Should create new instance if none exists."""
        # Arrange - reset singleton
        import layer4_agents.api.websocket.manager as manager_module
        manager_module._ws_manager = None
        
        # Act
        manager = get_ws_manager()
        
        # Assert
        assert manager is not None
        assert isinstance(manager, WorkflowWebSocketManager)


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegrationScenarios:
    """End-to-end integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle_connect_broadcast_disconnect(
        self, started_manager, mock_websocket
    ):
        """Complete lifecycle: connect -> broadcast -> disconnect."""
        # Arrange & Act - Connect
        await started_manager.connect(mock_websocket, "wf-integration")
        
        # Broadcast several events
        for i in range(3):
            await started_manager.broadcast_state_update(
                workflow_id="wf-integration",
                status="running",
                progress_percentage=i * 33
            )
        
        # Disconnect
        await started_manager.disconnect(mock_websocket, "wf-integration")
        
        # Assert - connection cleaned up
        assert "wf-integration" not in started_manager._workflow_connections
        # But event store should persist (for replay to new connections)
        assert "wf-integration" in started_manager._event_stores
    
    @pytest.mark.asyncio
    async def test_reconnect_receives_missed_events(
        self, started_manager, mock_websocket
    ):
        """Client reconnecting should receive events missed while offline."""
        # Arrange - First client connects and receives events
        await started_manager.connect(mock_websocket, "wf-reconnect")
        
        # Clear mocks to track only new events
        mock_websocket.send_json.reset_mock()
        
        # Simulate some events while "offline"
        for i in range(3):
            await started_manager.broadcast_state_update(
                workflow_id="wf-reconnect",
                status="running",
                progress_percentage=i * 50
            )
        
        # Remember last event ID
        last_event = started_manager._event_stores["wf-reconnect"].events[-1]
        last_event_id = last_event["event_id"]
        
        # New client connects with last_event_id
        ws2 = MagicMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        
        await started_manager.connect(ws2, "wf-reconnect", last_event_id=last_event_id)
        
        # Assert - should receive connection_established with replay_count = 0
        # (since we asked for events after the last one we have)
        calls = ws2.send_json.call_args_list
        first_event = calls[0][0][0]
        assert first_event["event_type"] == "connection_established"
        assert first_event["replay_count"] == 0  # No new events since last_event_id


class TestTenantMismatchEnforcement:
    """Cross-tenant access denial and metric emission (OBS-L4-009)."""

    @pytest.mark.asyncio
    async def test_connect_denied_when_tenant_mismatch(self, ws_manager, mock_websocket):
        """Connection is rejected when actor tenant differs from workflow owner."""
        ws_manager.record_workflow_tenant("wf-owned", "tenant-owner")

        await ws_manager.connect(
            mock_websocket,
            "wf-owned",
            tenant_id="tenant-attacker",
            correlation_id="cid-001",
        )

        mock_websocket.close.assert_awaited_once_with(code=4403, reason="Access denied")
        mock_websocket.accept.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_allowed_for_correct_tenant(self, ws_manager, mock_websocket):
        """Connection proceeds when actor tenant matches workflow owner."""
        ws_manager.record_workflow_tenant("wf-owned", "tenant-owner")

        await ws_manager.connect(
            mock_websocket,
            "wf-owned",
            tenant_id="tenant-owner",
        )

        mock_websocket.accept.assert_awaited_once()
        mock_websocket.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_allowed_when_no_owner_registered(self, ws_manager, mock_websocket):
        """Connection proceeds when workflow has no registered owner (not yet broadcast)."""
        await ws_manager.connect(
            mock_websocket,
            "wf-unknown",
            tenant_id="tenant-any",
        )

        mock_websocket.accept.assert_awaited_once()
        mock_websocket.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_mismatch_emits_metric(self, ws_manager, mock_websocket):
        """Tenant mismatch increments the security metric."""
        mock_metrics = MagicMock()
        ws_manager._metrics = mock_metrics
        ws_manager.record_workflow_tenant("wf-owned", "tenant-owner")

        await ws_manager.connect(
            mock_websocket,
            "wf-owned",
            tenant_id="tenant-attacker",
            correlation_id="cid-002",
        )

        mock_metrics.increment_ws_tenant_mismatch.assert_called_once_with("tenant-attacker")

    @pytest.mark.asyncio
    async def test_mismatch_emits_structured_log(self, ws_manager, mock_websocket, caplog):
        """Tenant mismatch produces a structured WARNING with required fields."""
        import logging

        ws_manager.record_workflow_tenant("wf-owned", "tenant-owner")

        with caplog.at_level(logging.WARNING):
            await ws_manager.connect(
                mock_websocket,
                "wf-owned",
                tenant_id="tenant-attacker",
                correlation_id="cid-003",
            )

        assert "security.websocket.tenant_mismatch" in caplog.text
        assert "tenant-attacker" in caplog.text
        assert "wf-owned" in caplog.text
        assert "cid-003" in caplog.text

    @pytest.mark.asyncio
    async def test_broadcast_registers_workflow_tenant(self, ws_manager):
        """First broadcast to a workflow registers its owning tenant."""
        assert "wf-new" not in ws_manager._workflow_tenant_registry

        await ws_manager.broadcast_to_workflow(
            "wf-new", "state_update", {}, tenant_id="tenant-owner"
        )

        assert ws_manager._workflow_tenant_registry["wf-new"] == "tenant-owner"

    @pytest.mark.asyncio
    async def test_broadcast_does_not_overwrite_existing_owner(self, ws_manager):
        """Subsequent broadcasts do not change the registered owner."""
        ws_manager.record_workflow_tenant("wf-existing", "tenant-original")

        await ws_manager.broadcast_to_workflow(
            "wf-existing", "state_update", {}, tenant_id="tenant-other"
        )

        assert ws_manager._workflow_tenant_registry["wf-existing"] == "tenant-original"

    @pytest.mark.asyncio
    async def test_cleanup_removes_tenant_registry_entry(self, ws_manager):
        """cleanup_workflow removes the tenant registry entry."""
        ws_manager.record_workflow_tenant("wf-done", "tenant-owner")
        # No active connections — cleanup should proceed
        await ws_manager.cleanup_workflow("wf-done")

        assert "wf-done" not in ws_manager._workflow_tenant_registry

    @pytest.mark.asyncio
    async def test_metric_failure_does_not_break_rejection(self, ws_manager, mock_websocket):
        """A broken metrics instance must not prevent the security rejection."""
        broken_metrics = MagicMock()
        broken_metrics.increment_ws_tenant_mismatch.side_effect = RuntimeError("metrics down")
        ws_manager._metrics = broken_metrics
        ws_manager.record_workflow_tenant("wf-owned", "tenant-owner")

        # Should not raise — rejection still happens
        await ws_manager.connect(
            mock_websocket,
            "wf-owned",
            tenant_id="tenant-attacker",
        )

        mock_websocket.close.assert_awaited_once_with(code=4403, reason="Access denied")


class TestKillSwitch:
    """Real-time tenant suspension via WebSocket kill-switch."""

    @pytest.mark.asyncio
    async def test_connect_rejects_suspended_tenant(self, ws_manager, mock_websocket):
        """connect() must close with 4403 when tenant kill-switch is active."""
        with patch(
            "value_fabric.shared.tenant_kill_switch.TenantKillSwitch.is_suspended",
            new_callable=AsyncMock,
            return_value=True,
        ):
            await ws_manager.connect(
                mock_websocket,
                "wf-suspended",
                tenant_id="tenant-suspended",
            )

        mock_websocket.close.assert_awaited_once_with(code=4403, reason="Tenant suspended")
        mock_websocket.accept.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_connect_allows_active_tenant_when_kill_switch_inactive(self, ws_manager, mock_websocket):
        """connect() must proceed when tenant is not suspended."""
        with patch(
            "value_fabric.shared.tenant_kill_switch.TenantKillSwitch.is_suspended",
            new_callable=AsyncMock,
            return_value=False,
        ):
            await ws_manager.connect(
                mock_websocket,
                "wf-active",
                tenant_id="tenant-active",
            )

        mock_websocket.accept.assert_awaited_once()
        mock_websocket.close.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disconnect_tenant_closes_all_connections(self, ws_manager, mock_websocket):
        """disconnect_tenant() must forcibly close every connection for the tenant."""
        ws2 = MagicMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        ws2.close = AsyncMock()

        await ws_manager.connect(mock_websocket, "wf-1", tenant_id="tenant-a")
        await ws_manager.connect(ws2, "wf-2", tenant_id="tenant-a")

        closed = await ws_manager.disconnect_tenant("tenant-a")

        assert closed == 2
        mock_websocket.close.assert_awaited_once_with(code=4403, reason="Tenant suspended")
        ws2.close.assert_awaited_once_with(code=4403, reason="Tenant suspended")
        assert "wf-1" not in ws_manager._workflow_connections
        assert "wf-2" not in ws_manager._workflow_connections

    @pytest.mark.asyncio
    async def test_disconnect_tenant_skips_other_tenants(self, ws_manager, mock_websocket):
        """disconnect_tenant() must not affect connections from other tenants."""
        ws2 = MagicMock(spec=WebSocket)
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        ws2.close = AsyncMock()

        await ws_manager.connect(mock_websocket, "wf-1", tenant_id="tenant-a")
        await ws_manager.connect(ws2, "wf-2", tenant_id="tenant-b")

        closed = await ws_manager.disconnect_tenant("tenant-a")

        assert closed == 1
        mock_websocket.close.assert_awaited_once_with(code=4403, reason="Tenant suspended")
        ws2.close.assert_not_awaited()
        assert "wf-1" not in ws_manager._workflow_connections
        assert "wf-2" in ws_manager._workflow_connections

    @pytest.mark.asyncio
    async def test_disconnect_tenant_returns_zero_when_no_connections(self, ws_manager):
        """disconnect_tenant() must return 0 when tenant has no connections."""
        closed = await ws_manager.disconnect_tenant("tenant-none")
        assert closed == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
