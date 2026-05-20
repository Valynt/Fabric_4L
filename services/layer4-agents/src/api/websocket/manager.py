"""WebSocket connection manager for real-time workflow streaming.

Provides pub/sub-style event broadcasting to connected clients with
connection resilience, last-event-ID replay, and workflow-scoped channels.

Security (OBS-L4-009):
- Tenant ownership of workflow_id is enforced at connect time.
- Cross-tenant access denials emit ``security_websocket_tenant_mismatch_total``
  and a structured WARNING log with actor_tenant_id, workflow_id, and
  correlation_id for BOLA/IDOR alerting.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import WebSocket
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..schemas.workflow_progress import normalize_workflow_progress

try:
    from ...metrics.prometheus_metrics import PrometheusMetrics as _PrometheusMetrics

    _METRICS_AVAILABLE = True
except ImportError:
    _METRICS_AVAILABLE = False
    _PrometheusMetrics = None  # type: ignore[assignment,misc]


class WorkflowWebSocketManager__summarize_outputResult(TypedDictModel):
    pass

logger = logging.getLogger(__name__)


@dataclass
class EventStore:
    """Ring buffer for event replay on reconnection."""

    max_events: int = 100
    events: list[dict[str, Any]] = field(default_factory=list)

    def add(self, event: dict[str, Any]) -> None:
        """Add event to buffer, maintaining max size."""
        event["_stored_at"] = datetime.now(UTC).isoformat()
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events.pop(0)

    def get_since(self, last_event_id: str | None = None) -> list[dict[str, Any]]:
        """Get events since a specific event ID."""
        if not last_event_id:
            return self.events[-10:]  # Return last 10 events by default

        for i, event in enumerate(self.events):
            if event.get("event_id") == last_event_id:
                return self.events[i + 1 :]
        return []


@dataclass
class WorkflowConnection:
    """Represents a WebSocket connection tracking its state.

    Multi-tenancy (Task 2.2):
    - tenant_id: Tenant identifier for connection authorization
    - user_id: User identifier for ownership verification
    """

    websocket: WebSocket
    workflow_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_event_id: str | None = None
    is_alive: bool = True
    _conn_id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)

    # Multi-tenancy context (Task 2.2)
    tenant_id: str | None = None
    user_id: str | None = None
    correlation_id: str | None = None

    def __hash__(self) -> int:
        return hash(self._conn_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkflowConnection):
            return NotImplemented
        return self._conn_id == other._conn_id

    async def send_event(self, event: dict[str, Any]) -> bool:
        """Send event to this connection. Returns success status."""
        if not self.is_alive:
            return False
        try:
            if self.correlation_id and "correlation_id" not in event:
                event["correlation_id"] = self.correlation_id
            await self.websocket.send_json(event)
            self.last_event_id = event.get("event_id")
            return True
        except Exception as e:
            logger.warning(f"Failed to send event to workflow {self.workflow_id}: {e}")
            self.is_alive = False
            return False


class WorkflowWebSocketManager:
    """Manages WebSocket connections for workflow streaming.

    Features:
    - Workflow-scoped channels (subscribe to specific workflow events)
    - Connection resilience with automatic cleanup
    - Last-event-ID replay for reconnection recovery
    - Heartbeat/ping-pong for connection health
    - Event persistence in memory (configurable Redis backend)
    - Tenant ownership enforcement with BOLA/IDOR probe detection (OBS-L4-009)
    """

    def __init__(self, redis_client=None, metrics=None):
        """Initialize WebSocket manager.

        Args:
            redis_client: Optional Redis client for cross-instance pub/sub
            metrics: Optional PrometheusMetrics instance for security counters
        """
        self.redis = redis_client
        self._metrics = metrics
        # workflow_id -> set of connections
        self._workflow_connections: dict[str, set[WorkflowConnection]] = {}
        # workflow_id -> event history for replay
        self._event_stores: dict[str, EventStore] = {}
        # workflow_id -> owning tenant_id (populated on first broadcast)
        self._workflow_tenant_registry: dict[str, str] = {}
        # Global connection lock
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None

    def record_workflow_tenant(self, workflow_id: str, tenant_id: str) -> None:
        """Register the owning tenant for a workflow.

        Call this when a workflow is created or first receives events so that
        subsequent WebSocket subscriptions can be validated against the owner.

        Args:
            workflow_id: Workflow instance ID.
            tenant_id: Tenant that owns the workflow.
        """
        self._workflow_tenant_registry[workflow_id] = tenant_id

    def _emit_tenant_mismatch(
        self,
        *,
        actor_tenant_id: str,
        workflow_id: str,
        workflow_owner_tenant_id: str,
        correlation_id: str | None,
    ) -> None:
        """Emit metric + structured log for a cross-tenant access denial (OBS-L4-009).

        The log payload includes all fields required for BOLA/IDOR alerting:
        actor_tenant_id, workflow_id, workflow_owner_tenant_id, and correlation_id.
        """
        logger.warning(
            "security.websocket.tenant_mismatch: cross-tenant WebSocket access denied "
            "actor_tenant_id=%s workflow_id=%s owner_tenant_id=%s correlation_id=%s",
            actor_tenant_id,
            workflow_id,
            workflow_owner_tenant_id,
            correlation_id,
            extra={
                "event": "security.websocket.tenant_mismatch",
                "actor_tenant_id": actor_tenant_id,
                "workflow_id": workflow_id,
                "owner_tenant_id": workflow_owner_tenant_id,
                "correlation_id": correlation_id,
                "security_signal": "BOLA_IDOR_PROBE",
            },
        )
        if self._metrics is not None:
            try:
                self._metrics.increment_ws_tenant_mismatch(actor_tenant_id)
            except Exception:
                pass  # Never let metric emission break the security path

    async def start(self) -> None:
        """Start background tasks for connection management."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop background tasks and close all connections."""
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        # Close all connections gracefully
        async with self._lock:
            for workflow_id, connections in self._workflow_connections.items():
                for conn in connections:
                    try:
                        await conn.websocket.close(code=1001, reason="Server shutting down")
                    except Exception:
                        pass
            self._workflow_connections.clear()
            self._event_stores.clear()

        logger.info("WebSocket manager stopped")

    async def connect(
        self,
        websocket: WebSocket,
        workflow_id: str,
        last_event_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Accept a new WebSocket connection for a workflow.

        Enforces tenant ownership: if the workflow is registered to a different
        tenant, the connection is rejected and a security metric is emitted
        (OBS-L4-009).

        Args:
            websocket: FastAPI WebSocket instance
            workflow_id: Workflow to subscribe to
            last_event_id: Optional last seen event ID for replay
            tenant_id: Tenant identifier for authorization
            user_id: User identifier for ownership verification
            correlation_id: X-Request-ID for structured log correlation
        """
        # --- Tenant ownership enforcement (OBS-L4-009) ----------------------
        owner_tenant_id = self._workflow_tenant_registry.get(workflow_id)
        if owner_tenant_id and tenant_id and owner_tenant_id != tenant_id:
            self._emit_tenant_mismatch(
                actor_tenant_id=tenant_id,
                workflow_id=workflow_id,
                workflow_owner_tenant_id=owner_tenant_id,
                correlation_id=correlation_id,
            )
            await websocket.close(code=4403, reason="Access denied")
            return

        await websocket.accept()

        conn = WorkflowConnection(
            websocket=websocket,
            workflow_id=workflow_id,
            last_event_id=last_event_id,
            tenant_id=tenant_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        async with self._lock:
            if workflow_id not in self._workflow_connections:
                self._workflow_connections[workflow_id] = set()
            if workflow_id not in self._event_stores:
                self._event_stores[workflow_id] = EventStore()

            self._workflow_connections[workflow_id].add(conn)

            # Send missed events if reconnecting (inside lock to prevent race
            # with cleanup_workflow removing the event store)
            missed_events = []
            if last_event_id:
                event_store = self._event_stores.get(workflow_id)
                if event_store:
                    missed_events = event_store.get_since(last_event_id)

        for event in missed_events:
            await conn.send_event(event)

        # Send connection established event
        now = datetime.now(UTC)
        await conn.send_event(
            {
                "event_id": f"conn-{now.timestamp()}-{uuid.uuid4().hex[:8]}",
                "event_type": "connection_established",
                "timestamp": now.isoformat(),
                "workflow_id": workflow_id,
                "message": f"Subscribed to workflow {workflow_id}",
                "replay_count": len(missed_events) if last_event_id else 0,
            }
        )

        logger.info(f"WebSocket connected for workflow {workflow_id}")

    async def disconnect(self, websocket: WebSocket, workflow_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if workflow_id in self._workflow_connections:
                # Find and remove the connection
                conn_to_remove = None
                for conn in self._workflow_connections[workflow_id]:
                    if conn.websocket == websocket:
                        conn_to_remove = conn
                        break

                if conn_to_remove:
                    conn_to_remove.is_alive = False
                    self._workflow_connections[workflow_id].discard(conn_to_remove)

                    # Cleanup connections but keep event store for replay
                    if not self._workflow_connections[workflow_id]:
                        del self._workflow_connections[workflow_id]
                        # Note: we keep _event_stores[workflow_id] for reconnection replay

        logger.info(f"WebSocket disconnected for workflow {workflow_id}")

    async def cleanup_workflow(self, workflow_id: str) -> None:
        """Remove event store and tenant registry entry for completed workflows.

        Call this when a workflow completes and no longer needs replay capability.
        """
        async with self._lock:
            # Only clean up if no active connections
            if workflow_id in self._workflow_connections:
                logger.warning(f"Cannot cleanup workflow {workflow_id}: has active connections")
                return

            if workflow_id in self._event_stores:
                del self._event_stores[workflow_id]
                logger.info(f"Cleaned up event store for workflow {workflow_id}")

            self._workflow_tenant_registry.pop(workflow_id, None)

    async def broadcast_to_workflow(
        self,
        workflow_id: str,
        event_type: str,
        payload: dict[str, Any],
        message: str | None = None,
        tenant_id: str | None = None,
    ) -> int:
        """Broadcast an event to all connections for a workflow.

        Args:
            workflow_id: Target workflow.
            event_type: Event type string.
            payload: Event payload dict.
            message: Human-readable message (defaults to event_type).
            tenant_id: Owning tenant — registers workflow ownership on first
                       broadcast so subsequent connect() calls can enforce it.

        Returns:
            Number of successful deliveries.
        """
        # Register workflow ownership on first broadcast (OBS-L4-009)
        if tenant_id and workflow_id not in self._workflow_tenant_registry:
            self.record_workflow_tenant(workflow_id, tenant_id)

        event = {
            "event_id": f"evt-{datetime.now(UTC).timestamp()}-{uuid.uuid4().hex[:8]}",
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "workflow_id": workflow_id,
            "message": message or event_type,
            "payload": payload,
        }

        # Store for replay and get connections atomically under lock
        async with self._lock:
            # Ensure event store exists
            if workflow_id not in self._event_stores:
                self._event_stores[workflow_id] = EventStore()
            self._event_stores[workflow_id].add(event)

            # Get connections under same lock to prevent race with disconnect
            if workflow_id not in self._workflow_connections:
                return 0
            connections = list(self._workflow_connections[workflow_id])

        # Broadcast to all connections (outside lock to avoid blocking)
        delivered = 0
        dead_connections: list[WorkflowConnection] = []

        for conn in connections:
            success = await conn.send_event(event)
            if success:
                delivered += 1
            else:
                dead_connections.append(conn)

        # Cleanup dead connections
        if dead_connections:
            async with self._lock:
                if workflow_id in self._workflow_connections:
                    for conn in dead_connections:
                        self._workflow_connections[workflow_id].discard(conn)
                    # Clean up empty workflow entry
                    if not self._workflow_connections[workflow_id]:
                        del self._workflow_connections[workflow_id]

        return delivered

    async def broadcast_state_update(
        self,
        workflow_id: str,
        status: str,
        current_node: str | None = None,
        progress_percentage: float = 0.0,
        output_data: dict | None = None,
        pause_point: dict | None = None,
    ) -> int:
        """Broadcast a workflow state update event.

        This is the primary method for streaming workflow progress.
        """
        payload = {
            "status": status,
            "current_node": current_node,
            "progress_percentage": progress_percentage,
        }
        payload["normalized_progress"] = normalize_workflow_progress(
            status=payload,
            message=f"Workflow status: {status}",
        ).model_dump()

        if output_data:
            payload["output_snapshot"] = self._summarize_output(output_data)

        if pause_point:
            payload["pause_point"] = {
                "title": pause_point.get("title"),
                "reason": pause_point.get("reason"),
                "severity": pause_point.get("severity"),
            }

        return await self.broadcast_to_workflow(
            workflow_id=workflow_id,
            event_type="state_update",
            payload=payload,
            message=f"Workflow status: {status}",
        )

    async def broadcast_node_transition(
        self, workflow_id: str, from_node: str | None, to_node: str, node_output: dict | None = None
    ) -> int:
        """Broadcast a node transition event."""
        return await self.broadcast_to_workflow(
            workflow_id=workflow_id,
            event_type="node_transition",
            payload={
                "from_node": from_node,
                "to_node": to_node,
                "node_output_preview": self._summarize_output(node_output) if node_output else None,
            },
            message=f"Transitioned from {from_node or 'start'} to {to_node}",
        )

    async def broadcast_pause_point(self, workflow_id: str, pause_point: dict[str, Any]) -> int:
        """Broadcast a human-in-the-loop pause point."""
        return await self.broadcast_to_workflow(
            workflow_id=workflow_id,
            event_type="pause_point",
            payload={"pause_point": pause_point, "requires_action": True, "can_resume": True},
            message=f"Workflow paused: {pause_point.get('title', 'Action required')}",
        )

    async def broadcast_completion(
        self,
        workflow_id: str,
        status: str,
        final_output: dict | None = None,
        errors: list[str] | None = None,
    ) -> int:
        """Broadcast workflow completion event."""
        return await self.broadcast_to_workflow(
            workflow_id=workflow_id,
            event_type="workflow_complete",
            payload={
                "status": status,
                "final_output": final_output,
                "errors": errors or [],
                "completion_time": datetime.now(UTC).isoformat(),
            },
            message=f"Workflow {status}",
        )

    def _summarize_output(self, output: dict, max_keys: int = 5) -> dict:
        """Create a summarized version of output for streaming."""
        if not output:
            return WorkflowWebSocketManager__summarize_outputResult.model_validate({})

        summary = {}
        for i, (key, value) in enumerate(output.items()):
            if i >= max_keys:
                summary["_additional_keys"] = len(output) - max_keys
                break

            # Truncate large values
            if isinstance(value, (list, dict)):
                summary[key] = f"<{type(value).__name__} len={len(value)}>"
            elif isinstance(value, str) and len(value) > 100:
                summary[key] = value[:100] + "..."
            else:
                summary[key] = value

        return summary

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of stale connections."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_stale_connections(self) -> None:
        """Remove connections that haven't responded."""
        stale_threshold = timedelta(minutes=5)
        now = datetime.now(UTC)
        dead_connections = []

        async with self._lock:
            for workflow_id, connections in self._workflow_connections.items():
                for conn in connections:
                    if now - conn.connected_at > stale_threshold and not conn.is_alive:
                        dead_connections.append((workflow_id, conn))

        for workflow_id, conn in dead_connections:
            await self.disconnect(conn.websocket, workflow_id)
            logger.debug(f"Cleaned up stale connection for workflow {workflow_id}")

    async def _heartbeat_loop(self) -> None:
        """Send periodic pings to keep connections alive."""
        while True:
            try:
                await asyncio.sleep(30)  # Ping every 30 seconds
                await self._send_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _send_heartbeats(self) -> None:
        """Send ping to all connections and check health."""
        dead_connections = []

        async with self._lock:
            for workflow_id, connections in self._workflow_connections.items():
                for conn in connections:
                    try:
                        await conn.websocket.send_json(
                            {
                                "event_type": "ping",
                                "timestamp": datetime.now(UTC).isoformat(),
                                "correlation_id": conn.correlation_id,
                            }
                        )
                    except Exception:
                        conn.is_alive = False
                        dead_connections.append((workflow_id, conn))

        # Cleanup dead connections
        for workflow_id, conn in dead_connections:
            await self.disconnect(conn.websocket, workflow_id)

    async def handle_client_message(
        self, websocket: WebSocket, workflow_id: str, message: dict[str, Any]
    ) -> None:
        """Handle messages from client (acknowledgments, ping responses, etc.)."""
        msg_type = message.get("type")

        if msg_type == "pong":
            # Client responded to ping, mark connection alive
            async with self._lock:
                if workflow_id in self._workflow_connections:
                    for conn in self._workflow_connections[workflow_id]:
                        if conn.websocket == websocket:
                            conn.is_alive = True
                            break

        elif msg_type == "ack":
            # Client acknowledged event receipt
            event_id = message.get("event_id")
            logger.debug(f"Client acknowledged event {event_id} for workflow {workflow_id}")

        elif msg_type == "subscribe_history":
            # Client requesting full history
            async with self._lock:
                event_store = self._event_stores.get(workflow_id)
                events = event_store.events if event_store else []
            await websocket.send_json(
                {
                    "event_type": "history_response",
                    "events": events[-50:],  # Send last 50 events
                    "correlation_id": next(
                        (
                            conn.correlation_id
                            for conn in self._workflow_connections.get(workflow_id, set())
                            if conn.websocket == websocket
                        ),
                        None,
                    ),
                }
            )

        elif msg_type == "workflow_complete_ack":
            # Client acknowledged workflow completion - safe to cleanup
            logger.debug(f"Client acknowledged completion for workflow {workflow_id}")
            # Schedule cleanup after a delay to allow other clients to reconnect
            asyncio.create_task(self._delayed_cleanup(workflow_id, delay_seconds=300))

    async def _delayed_cleanup(self, workflow_id: str, delay_seconds: int) -> None:
        """Schedule cleanup of workflow event store after a delay."""
        await asyncio.sleep(delay_seconds)
        await self.cleanup_workflow(workflow_id)


# Global singleton instance
_ws_manager: WorkflowWebSocketManager | None = None


def get_ws_manager(redis_client=None) -> WorkflowWebSocketManager:
    """Get or create the global WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WorkflowWebSocketManager(redis_client)
    return _ws_manager
