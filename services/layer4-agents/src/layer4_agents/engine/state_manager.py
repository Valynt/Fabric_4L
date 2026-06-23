from __future__ import annotations

"""State manager for workflow state persistence using Redis."""
import asyncio
import json
import logging
import re
from collections import OrderedDict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from pydantic import TypeAdapter, ValidationError

from ..models.agent_state import AgentState, WorkflowStatus

if TYPE_CHECKING:
    from ..contexts.api_surface.public import WorkflowWebSocketManager

logger = logging.getLogger(__name__)
_SECRET_KEY_PATTERN = re.compile(
    r"(secret|token|password|api[_-]?key|authorization|credential|private[_-]?key)",
    re.IGNORECASE,
)

# Redis key constants
_WORKFLOW_KEY_PREFIX = "layer4:workflow"
_HISTORY_KEY_SUFFIX = ":history"


class StateManager:
    """Manages workflow state persistence using Redis.

    Provides:
    - State storage and retrieval
    - Workflow status tracking
    - History recording
    - Real-time WebSocket broadcasting
    - LRU eviction for in-memory fallback (max 10K entries)

    Example:
        manager = StateManager(redis_client)
        await manager.save_state(workflow_id, state)
        state = await manager.load_state(workflow_id)
    """

    DEFAULT_MAX_MEMORY_ENTRIES = 10000  # P0-26: Bounded memory store

    def __init__(
        self,
        redis_client=None,
        ws_manager: WorkflowWebSocketManager | None = None,
        max_memory_entries: int = DEFAULT_MAX_MEMORY_ENTRIES,
    ):
        """Initialize state manager.

        Args:
            redis_client: Redis client instance (optional)
            ws_manager: WebSocket manager for real-time streaming (optional)
            max_memory_entries: Maximum entries for in-memory LRU cache (default 10K)
        """
        self.redis = redis_client
        # P0-26: LRU cache with maxlen to prevent unbounded growth
        self._memory_store: OrderedDict[str, Any] = OrderedDict()
        self._max_memory_entries = max_memory_entries
        self._ws_manager: WorkflowWebSocketManager | None = ws_manager

    @property
    def redis_client(self):
        """Return the configured Redis client for compatibility with startup integrations."""
        return self.redis

    def _get_key(self, workflow_id: str) -> str:
        """Generate Redis key for workflow state."""
        return f"{_WORKFLOW_KEY_PREFIX}:{workflow_id}"

    def _get_history_key(self, workflow_id: str) -> str:
        """Generate Redis key for workflow history."""
        return f"{_WORKFLOW_KEY_PREFIX}:{workflow_id}{_HISTORY_KEY_SUFFIX}"

    def set_ws_manager(self, ws_manager: WorkflowWebSocketManager) -> None:
        """Set WebSocket manager for real-time broadcasting."""
        self._ws_manager = ws_manager

    async def save_state(
        self,
        workflow_id: str,
        state: AgentState,
        ttl_seconds: int = 86400,  # 24 hours default
    ) -> None:
        """Save workflow state and broadcast update.

        Args:
            workflow_id: Workflow identifier
            state: Current workflow state
            ttl_seconds: Time to live for Redis key
        """
        key = self._get_key(workflow_id)

        # Serialize state
        state_dict = self._redact_secrets(state.model_dump())
        state_json = json.dumps(state_dict, default=str)

        if self.redis:
            await self.redis.setex(key, ttl_seconds, state_json)
        else:
            # P0-26: LRU eviction - remove oldest if at capacity
            if len(self._memory_store) >= self._max_memory_entries and key not in self._memory_store:
                oldest_key = next(iter(self._memory_store))
                del self._memory_store[oldest_key]
                logger.info(f"LRU eviction: removed workflow state for {oldest_key}")
            self._memory_store[key] = {
                "data": state_dict,
                "expires": datetime.now(UTC).timestamp() + ttl_seconds,
            }

        # Broadcast state update via WebSocket
        if self._ws_manager:
            try:
                await self._ws_manager.broadcast_state_update(
                    workflow_id=workflow_id,
                    status=state.status.value
                    if hasattr(state.status, "value")
                    else str(state.status),
                    current_node=state.current_node,
                    progress_percentage=self._calculate_progress(state),
                    output_data=state_dict.get("output_data"),
                    pause_point=state_dict.get("pause_point"),
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Failed to broadcast state update: {e}")

    def _calculate_progress(self, state: AgentState) -> float:
        """Calculate workflow progress percentage."""
        # Simple heuristic: if completed, 100%; if failed, 0%;
        # otherwise estimate based on status
        status = state.status
        if status == WorkflowStatus.COMPLETED:
            return 100.0
        elif status == WorkflowStatus.FAILED:
            return 0.0
        elif status == WorkflowStatus.PAUSED:
            # Estimate based on whether we have output
            return 50.0 if state.output_data else 25.0
        elif status == WorkflowStatus.RUNNING:
            return 10.0
        else:
            return 0.0

    def _redact_secrets(self, value: Any) -> Any:
        """Recursively redact secret-bearing keys before checkpoint persistence."""
        if isinstance(value, dict):
            redacted: dict[str, Any] = {}
            for key, item in value.items():
                if _SECRET_KEY_PATTERN.search(str(key)):
                    redacted[key] = "[redacted]"
                else:
                    redacted[key] = self._redact_secrets(item)
            return redacted
        if isinstance(value, list):
            return [self._redact_secrets(item) for item in value]
        return value

    async def load_state(self, workflow_id: str) -> AgentState | None:
        """Load workflow state.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Workflow state or None if not found
        """
        key = self._get_key(workflow_id)

        if self.redis:
            data = await self.redis.get(key)
            if data:
                try:
                    # CONTRACT §2.5: Use Pydantic TypeAdapter for schema validation
                    state_adapter = TypeAdapter(dict[str, Any])
                    state_dict = state_adapter.validate_json(data)
                    return self._deserialize_state(state_dict)
                except (ValidationError, ValueError) as e:
                    logger.error(f"Failed to deserialize state for workflow {workflow_id}: {e}")
                    return None
        else:
            stored = self._memory_store.get(key)
            if stored and stored["expires"] > datetime.now(UTC).timestamp():
                # P0-26: Refresh LRU order on access
                self._memory_store.move_to_end(key)
                return self._deserialize_state(stored["data"])

        return None

    def _deserialize_state(self, state_dict: dict[str, Any]) -> AgentState:
        """Deserialize state dict to appropriate state type."""
        from ..models.agent_state import (
            BusinessCaseAgentState,
            OrchestratorAgentState,
            ROIAgentState,
            WhitespaceAgentState,
        )

        workflow_type = state_dict.get("workflow_type")
        if not isinstance(workflow_type, str):
            raise ValueError(f"Invalid workflow_type for state deserialization: {workflow_type}")

        # Map to correct state type
        type_map = {
            "roi_calculator": ROIAgentState,
            "whitespace_analysis": WhitespaceAgentState,
            "business_case": BusinessCaseAgentState,
            "orchestrator": OrchestratorAgentState,
        }

        state_class = type_map.get(workflow_type)
        if state_class is None:
            raise ValueError(f"Unknown workflow_type for state deserialization: {workflow_type}")

        # Parse datetime fields.
        # NOTE: _deserialize_state may raise ValidationError for malformed persisted
        # data (e.g. corrupted datetime strings). load_state() catches this and
        # returns None, treating the workflow as non-resumable.
        for field in ["started_at", "completed_at", "extracted_at"]:
            if state_dict.get(field) and isinstance(state_dict[field], str):
                try:
                    state_dict[field] = datetime.fromisoformat(
                        state_dict[field].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

        return cast(ROIAgentState | WhitespaceAgentState | BusinessCaseAgentState | OrchestratorAgentState, state_class(**state_dict))

    async def delete_state(self, workflow_id: str) -> None:
        """Delete workflow state."""
        key = self._get_key(workflow_id)

        if self.redis:
            await self.redis.delete(key)
        else:
            self._memory_store.pop(key, None)

    async def list_workflows(self) -> list[str]:
        """List all persisted workflow IDs without changing recovery semantics.

        ``list_active_workflows`` is intentionally status-filtered for pod
        recovery. This method supports tenant-scoped API listing where completed
        validation workflows must remain visible through canonical state.
        """
        workflow_ids: list[str] = []
        prefix = f"{_WORKFLOW_KEY_PREFIX}:"

        if self.redis:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=f"{prefix}*",
                    count=100,
                )
                for key in keys:
                    key_text = key.decode("utf-8") if isinstance(key, bytes | bytearray) else str(key)
                    if _HISTORY_KEY_SUFFIX in key_text or not key_text.startswith(prefix):
                        continue
                    workflow_ids.append(key_text.removeprefix(prefix))
                if cursor == 0:
                    break
        else:
            now = datetime.now(UTC).timestamp()
            for key, stored in list(self._memory_store.items()):
                if _HISTORY_KEY_SUFFIX in key or not key.startswith(prefix):
                    continue
                if stored.get("expires", 0) <= now:
                    continue
                workflow_ids.append(key.removeprefix(prefix))

        return sorted(set(workflow_ids))

    async def record_history(
        self, workflow_id: str, node_id: str, input_data: dict, output_data: dict, duration_ms: int
    ) -> None:
        """Record node execution history.

        Args:
            workflow_id: Workflow identifier
            node_id: Node that executed
            input_data: Node input
            output_data: Node output
            duration_ms: Execution duration
        """
        key = self._get_history_key(workflow_id)

        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "node_id": node_id,
            "input_summary": self._summarize(input_data),
            "output_summary": self._summarize(output_data),
            "duration_ms": duration_ms,
        }

        if self.redis:
            await self.redis.lpush(key, json.dumps(entry))
            await self.redis.ltrim(key, 0, 99)  # Keep last 100
        else:
            history_key = f"{workflow_id}{_HISTORY_KEY_SUFFIX}"
            if history_key not in self._memory_store:
                self._memory_store[history_key] = []
            self._memory_store[history_key].insert(0, entry)
            self._memory_store[history_key] = self._memory_store[history_key][:100]

    def _summarize(self, data: dict, max_length: int = 200) -> str:
        """Create summary of data for history."""
        text = json.dumps(data, default=str)
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    async def get_history(self, workflow_id: str, limit: int = 50) -> list:
        """Get execution history for workflow."""
        key = self._get_history_key(workflow_id)

        if self.redis:
            data = await self.redis.lrange(key, 0, limit - 1)
            history = []
            for d in data:
                try:
                    # CONTRACT §2.5: Use Pydantic validation for history entries
                    history_adapter = TypeAdapter(dict[str, Any])
                    history.append(history_adapter.validate_json(d))
                except ValidationError as e:
                    logger.warning(f"Failed to validate history entry for workflow {workflow_id}: {e}")
                    continue
            return history
        else:
            history_key = f"{workflow_id}{_HISTORY_KEY_SUFFIX}"
            history: list[Any] = self._memory_store.get(history_key, [])  # type: ignore[no-redef]
            return history[:limit]

    async def list_active_workflows(self) -> list[str]:
        """List workflow IDs with RUNNING or PENDING status.
        
        Used on startup to identify workflows that may have been
        orphaned by a pod restart.
        
        Note: This scans all workflow keys in Redis. For large deployments,
        consider using a Redis set to track active workflows.
        """
        active_ids = []
        active_statuses = {WorkflowStatus.RUNNING.value, WorkflowStatus.PENDING.value, WorkflowStatus.PAUSED.value}
        
        if self.redis:
            # Scan for workflow keys (prefix:* without history suffix)
            # This is a simple scan; production may want to use a secondary index
            pattern = f"{_WORKFLOW_KEY_PREFIX}:*"
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                for key in keys:
                    key_text = key.decode("utf-8") if isinstance(key, bytes | bytearray) else str(key)
                    # Skip history keys
                    if _HISTORY_KEY_SUFFIX in key_text or not key_text.startswith(f"{_WORKFLOW_KEY_PREFIX}:"):
                        continue
                    
                    workflow_id = key_text.removeprefix(f"{_WORKFLOW_KEY_PREFIX}:")
                    try:
                        state = await self.load_state(workflow_id)
                        if state and state.status.value in active_statuses:
                            active_ids.append(workflow_id)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning(f"Failed to check state for {workflow_id}: {e}")
                
                if cursor == 0:
                    break
        else:
            # In-memory fallback: scan _memory_store
            for key in self._memory_store:
                if key.startswith(f"{_WORKFLOW_KEY_PREFIX}:") and _HISTORY_KEY_SUFFIX not in key:
                    workflow_id = key.replace(f"{_WORKFLOW_KEY_PREFIX}:", "")
                    try:
                        state = await self.load_state(workflow_id)
                        if state and state.status.value in active_statuses:
                            active_ids.append(workflow_id)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning(f"Failed to check state for {workflow_id}: {e}")
        
        return active_ids
