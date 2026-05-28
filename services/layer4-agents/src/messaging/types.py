from __future__ import annotations

"""Message types and structures for inter-agent communication.

Based on the specification's agent messaging patterns.
"""


from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from value_fabric.shared.models.typed_dict import TypedDictModel


class AgentMessage_to_dictResult(TypedDictModel):
    correlation_id: Any
    message_id: Any
    message_type: Any
    payload: Any
    priority: Any
    recipient_id: Any
    sender_id: Any
    timestamp: Any
    ttl_seconds: Any

class TaskAssignment_to_dictResult(TypedDictModel):
    capability: Any
    deadline: Any
    parameters: Any
    task_id: Any
    tenant_id: Any

class TaskResult_to_dictResult(TypedDictModel):
    error: Any
    execution_time_ms: Any
    result: Any
    success: Any
    task_id: Any

class StatusUpdate_to_dictResult(TypedDictModel):
    agent_id: Any
    current_task: Any
    metadata: Any
    progress_percent: Any
    status: Any

class ErrorNotification_to_dictResult(TypedDictModel):
    context: Any
    error_id: Any
    message: Any
    severity: Any
    stack_trace: Any

class ProvenanceEvent_to_dictResult(TypedDictModel):
    activity_id: Any
    agent_id: Any
    attributes: Any
    entity_id: Any
    event_type: Any
    timestamp: Any


class MessageType(Enum):
    """Types of messages passed between agents.

    From spec:
    - TASK_ASSIGNMENT: Assign a task to an agent
    - TASK_RESULT: Return result from task execution
    - STATUS_UPDATE: Agent status change notification
    - ERROR_NOTIFICATION: Error occurred during execution
    - COORDINATION: Coordination between agents
    - PROVENANCE_EVENT: Provenance tracking event
    """

    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    STATUS_UPDATE = "status_update"
    ERROR_NOTIFICATION = "error_notification"
    COORDINATION = "coordination"
    PROVENANCE_EVENT = "provenance_event"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    WORKFLOW_EVENT = "workflow_event"


class MessagePriority(Enum):
    """Message priority levels."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class AgentMessage:
    """Message passed between agents.

    From spec section 1.4 Inter-Agent Communication Patterns:
    - message_id: Unique identifier
    - message_type: Type of message
    - sender_id: Sending agent ID
    - recipient_id: Target agent ID (None for broadcast)
    - timestamp: When message was sent
    - payload: Message content
    - correlation_id: For request/response correlation
    - priority: Message priority

    Attributes:
        message_id: Unique message identifier
        message_type: Type of message
        sender_id: ID of sending agent
        recipient_id: ID of recipient agent (None for broadcast)
        timestamp: UTC datetime when message was created
        payload: Message content (dict)
        correlation_id: For tracing request/response pairs
        priority: Message priority level
        ttl_seconds: Time-to-live for message expiration
    """

    message_type: MessageType
    sender_id: str
    payload: dict[str, Any]
    recipient_id: str | None = None
    message_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None
    priority: MessagePriority = MessagePriority.NORMAL
    ttl_seconds: int = 300

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return AgentMessage_to_dictResult.model_validate({
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "ttl_seconds": self.ttl_seconds,
        })


    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentMessage:
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender_id=data["sender_id"],
            recipient_id=data.get("recipient_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            payload=data["payload"],
            correlation_id=data.get("correlation_id"),
            priority=MessagePriority(data.get("priority", 3)),
            ttl_seconds=data.get("ttl_seconds", 300),
        )

    def is_expired(self) -> bool:
        """Check if message has expired based on TTL."""
        elapsed = (datetime.now(UTC) - self.timestamp).total_seconds()
        return elapsed > self.ttl_seconds

    def is_broadcast(self) -> bool:
        """Check if message is a broadcast (no specific recipient)."""
        return self.recipient_id is None


@dataclass
class TaskAssignment:
    """Task assignment message payload.

    Attributes:
        task_id: Unique task identifier
        capability: Capability to execute
        parameters: Task parameters
        deadline: Optional deadline
        tenant_id: Tenant context
    """

    task_id: str
    capability: str
    parameters: dict[str, Any]
    deadline: datetime | None = None
    tenant_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return TaskAssignment_to_dictResult.model_validate({
            "task_id": self.task_id,
            "capability": self.capability,
            "parameters": self.parameters,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "tenant_id": self.tenant_id,
        })


@dataclass
class TaskResult:
    """Task result message payload.

    Attributes:
        task_id: Task identifier from assignment
        success: Whether task succeeded
        result: Result data (if success)
        error: Error message (if failed)
        execution_time_ms: Time taken to execute
    """

    task_id: str
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return TaskResult_to_dictResult.model_validate({
            "task_id": self.task_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        })


@dataclass
class StatusUpdate:
    """Status update message payload.

    Attributes:
        agent_id: Agent reporting status
        status: Current status (IDLE, RUNNING, COMPLETED, etc.)
        current_task: What the agent is doing
        progress_percent: Completion percentage (0-100)
        metadata: Additional status info
    """

    agent_id: str
    status: str
    current_task: str | None = None
    progress_percent: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return StatusUpdate_to_dictResult.model_validate({
            "agent_id": self.agent_id,
            "status": self.status,
            "current_task": self.current_task,
            "progress_percent": self.progress_percent,
            "metadata": self.metadata,
        })


@dataclass
class ErrorNotification:
    """Error notification message payload.

    Attributes:
        error_id: Unique error identifier
        severity: Error severity (WARNING, ERROR, CRITICAL)
        message: Error message
        stack_trace: Optional stack trace
        context: Error context
    """

    error_id: str
    severity: str
    message: str
    stack_trace: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return ErrorNotification_to_dictResult.model_validate({
            "error_id": self.error_id,
            "severity": self.severity,
            "message": self.message,
            "stack_trace": self.stack_trace,
            "context": self.context,
        })


@dataclass
class ProvenanceEvent:
    """Provenance tracking event payload.

    Attributes:
        event_type: Type of provenance event
        activity_id: Activity being tracked
        entity_id: Entity being tracked
        agent_id: Agent responsible
        timestamp: When event occurred
        attributes: Additional provenance attributes
    """

    event_type: str
    activity_id: str
    entity_id: str
    agent_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return ProvenanceEvent_to_dictResult.model_validate({
            "event_type": self.event_type,
            "activity_id": self.activity_id,
            "entity_id": self.entity_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "attributes": self.attributes,
        })


