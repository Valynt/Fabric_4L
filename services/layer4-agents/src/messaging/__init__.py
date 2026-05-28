from __future__ import annotations

"""Multi-agent messaging system for Layer 4.

Provides pub/sub messaging, message routing, and inter-agent communication.
"""


from .bus import InMemoryMessageBus, MessageBus, RedisMessageBus
from .router import MessageRouter
from .signal_events import (
    BaseSignalEvent,
    ErrorCategory,
    SignalCompletedEvent,
    SignalDiscoveredEvent,
    SignalEvent,
    SignalEventType,
    SignalFailedEvent,
    SignalStreamCompleteEvent,
    create_signal_completed_event,
    create_signal_discovered_event,
    create_signal_failed_event,
    create_stream_complete_event,
)
from .types import AgentMessage, MessagePriority, MessageType

__all__ = [
    "MessageType",
    "AgentMessage",
    "MessagePriority",
    "MessageBus",
    "InMemoryMessageBus",
    "RedisMessageBus",
    "MessageRouter",
    # Signal Events
    "BaseSignalEvent",
    "SignalDiscoveredEvent",
    "SignalCompletedEvent",
    "SignalFailedEvent",
    "SignalStreamCompleteEvent",
    "SignalEvent",
    "SignalEventType",
    "ErrorCategory",
    "create_signal_discovered_event",
    "create_signal_completed_event",
    "create_signal_failed_event",
    "create_stream_complete_event",
]
