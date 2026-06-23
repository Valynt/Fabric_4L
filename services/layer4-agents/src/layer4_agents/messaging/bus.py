from __future__ import annotations

"""Message bus implementations for inter-agent communication.

Provides pub/sub messaging with support for:
- In-memory messaging (for single-node deployments)
- Redis-based messaging (for distributed deployments)
- Message filtering and routing
- Subscription management
"""


import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .types import AgentMessage, MessagePriority, MessageType

logger = logging.getLogger(__name__)


class MessageBus(ABC):
    """Abstract base class for message bus implementations.

    The message bus enables publish/subscribe communication between agents.
    Agents can subscribe to specific message types or broadcast to all listeners.

    Example:
        bus = InMemoryMessageBus()

        # Subscribe to messages
        await bus.subscribe("agent-1", MessageType.TASK_ASSIGNMENT, handler)

        # Publish message
        await bus.publish(
            agent_id="agent-1",
            event_type=MessageType.TASK_RESULT,
            payload={"result": "success"}
        )
    """

    @abstractmethod
    async def subscribe(
        self,
        subscriber_id: str,
        message_type: MessageType,
        handler: Callable[[AgentMessage], Any],
    ) -> None:
        """Subscribe to a message type.

        Args:
            subscriber_id: Unique identifier for subscriber
            message_type: Type of messages to receive
            handler: Callback function for received messages
        """
        pass

    @abstractmethod
    async def unsubscribe(
        self,
        subscriber_id: str,
        message_type: MessageType | None = None,
    ) -> None:
        """Unsubscribe from messages.

        Args:
            subscriber_id: Subscriber to remove
            message_type: Specific type to unsubscribe (None = all types)
        """
        pass

    @abstractmethod
    async def publish(
        self,
        agent_id: str,
        event_type: MessageType,
        payload: dict[str, Any],
        recipient_id: str | None = None,
        correlation_id: str | None = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> str:
        """Publish a message to the bus.

        Args:
            agent_id: ID of sending agent
            event_type: Type of event
            payload: Message content
            recipient_id: Specific recipient (None for broadcast)
            correlation_id: For request/response correlation
            priority: Message priority

        Returns:
            message_id: ID of published message
        """
        pass

    @abstractmethod
    async def broadcast(
        self,
        agent_id: str,
        event_type: MessageType,
        payload: dict[str, Any],
    ) -> str:
        """Broadcast message to all subscribers.

        Args:
            agent_id: ID of sending agent
            event_type: Type of event
            payload: Message content

        Returns:
            message_id: ID of broadcast message
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the message bus and clean up resources."""
        pass


class InMemoryMessageBus(MessageBus):
    """In-memory message bus implementation.

    Suitable for single-node deployments or testing.
    Uses asyncio for async message delivery.
    """

    def __init__(self):
        """Initialize in-memory message bus."""
        # subscriber_id -> {message_type -> [handlers]}
        self._subscriptions: dict[str, dict[MessageType, list[Callable]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # message_type -> {subscriber_id -> [handlers]}
        self._type_subscribers: dict[MessageType, dict[str, list[Callable]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._lock = asyncio.Lock()
        self._closed = False

    async def subscribe(
        self,
        subscriber_id: str,
        message_type: MessageType,
        handler: Callable[[AgentMessage], Any],
    ) -> None:
        """Subscribe to a message type."""
        async with self._lock:
            if self._closed:
                raise RuntimeError("Message bus is closed")

            self._subscriptions[subscriber_id][message_type].append(handler)
            self._type_subscribers[message_type][subscriber_id].append(handler)

            logger.debug(f"Subscribed {subscriber_id} to {message_type.value}")

    async def unsubscribe(
        self,
        subscriber_id: str,
        message_type: MessageType | None = None,
    ) -> None:
        """Unsubscribe from messages."""
        async with self._lock:
            if self._closed:
                return

            if message_type is None:
                # Unsubscribe from all types
                for msg_type in list(self._subscriptions[subscriber_id].keys()):
                    handlers = self._subscriptions[subscriber_id][msg_type]
                    for handler in handlers:
                        self._type_subscribers[msg_type][subscriber_id].remove(handler)
                    del self._subscriptions[subscriber_id][msg_type]
            else:
                # Unsubscribe from specific type
                if message_type in self._subscriptions[subscriber_id]:
                    handlers = self._subscriptions[subscriber_id][message_type]
                    for handler in handlers:
                        self._type_subscribers[message_type][subscriber_id].remove(handler)
                    del self._subscriptions[subscriber_id][message_type]

            logger.debug(
                f"Unsubscribed {subscriber_id} from {message_type.value if message_type else 'all'}"
            )

    async def publish(
        self,
        agent_id: str,
        event_type: MessageType,
        payload: dict[str, Any],
        recipient_id: str | None = None,
        correlation_id: str | None = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> str:
        """Publish a message."""
        async with self._lock:
            if self._closed:
                raise RuntimeError("Message bus is closed")

            message = AgentMessage(
                message_type=event_type,
                sender_id=agent_id,
                recipient_id=recipient_id,
                payload=payload,
                correlation_id=correlation_id,
                priority=priority,
            )

            # Deliver message asynchronously
            asyncio.create_task(self._deliver_message(message))

            return message.message_id

    async def broadcast(
        self,
        agent_id: str,
        event_type: MessageType,
        payload: dict[str, Any],
    ) -> str:
        """Broadcast message to all subscribers."""
        return await self.publish(
            agent_id=agent_id,
            event_type=event_type,
            payload=payload,
            recipient_id=None,  # Broadcast = no specific recipient
        )

    async def _deliver_message(self, message: AgentMessage) -> None:
        """Deliver message to all appropriate subscribers."""
        message_type = message.message_type
        recipient_id = message.recipient_id

        # Get subscribers for this message type
        subscribers = self._type_subscribers.get(message_type, {})

        delivery_tasks = []

        for subscriber_id, handlers in subscribers.items():
            # Skip if message is for specific recipient and this isn't it
            if recipient_id is not None and subscriber_id != recipient_id:
                continue

            # Skip sender (don't deliver to self)
            if subscriber_id == message.sender_id:
                continue

            for handler in handlers:
                # Create delivery task
                task = asyncio.create_task(self._safe_deliver(handler, message))
                delivery_tasks.append(task)

        # Wait for all deliveries to complete
        if delivery_tasks:
            await asyncio.gather(*delivery_tasks, return_exceptions=True)

    async def _safe_deliver(
        self,
        handler: Callable[[AgentMessage], Any],
        message: AgentMessage,
    ) -> None:
        """Safely deliver message to handler."""
        try:
            result = handler(message)
            # If handler returns a coroutine, await it
            if asyncio.iscoroutine(result):
                await result
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error delivering message {message.message_id}: {e}")

    async def close(self) -> None:
        """Close the message bus."""
        async with self._lock:
            self._closed = True
            self._subscriptions.clear()
            self._type_subscribers.clear()
            logger.info("InMemoryMessageBus closed")


class RedisMessageBus(MessageBus):
    """Redis-backed message bus for distributed deployments.

    Uses Redis pub/sub for message distribution across multiple nodes.
    Requires redis-py and a running Redis server.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        node_id: str | None = None,
    ):
        """Initialize Redis message bus.

        Args:
            redis_url: Redis connection URL
            node_id: Unique identifier for this node
        """
        self.redis_url = redis_url
        self.node_id = node_id or f"node-{id(self)}"
        self._redis = None
        self._pubsub = None
        self._subscriptions: dict[str, dict[MessageType, list[Callable]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._listener_task: asyncio.Task | None = None
        self._closed = False

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            import redis.asyncio as redis

            self._redis = await redis.from_url(self.redis_url)
        return self._redis

    async def subscribe(
        self,
        subscriber_id: str,
        message_type: MessageType,
        handler: Callable[[AgentMessage], Any],
    ) -> None:
        """Subscribe to a message type via Redis."""
        if self._closed:
            raise RuntimeError("Message bus is closed")

        self._subscriptions[subscriber_id][message_type].append(handler)

        # Subscribe to Redis channel for this message type
        redis = await self._get_redis()
        channel = f"vf:agent:{message_type.value}"

        if self._pubsub is None:
            self._pubsub = redis.pubsub()
            await self._pubsub.subscribe(channel)
            # Start listener task
            self._listener_task = asyncio.create_task(self._listen())
        else:
            await self._pubsub.subscribe(channel)

        logger.debug(f"Subscribed {subscriber_id} to {message_type.value} via Redis")

    async def unsubscribe(
        self,
        subscriber_id: str,
        message_type: MessageType | None = None,
    ) -> None:
        """Unsubscribe from messages."""
        if self._closed:
            return

        if message_type is None:
            if subscriber_id in self._subscriptions:
                del self._subscriptions[subscriber_id]
        else:
            if subscriber_id in self._subscriptions:
                if message_type in self._subscriptions[subscriber_id]:
                    del self._subscriptions[subscriber_id][message_type]

    async def publish(
        self,
        agent_id: str,
        event_type: MessageType,
        payload: dict[str, Any],
        recipient_id: str | None = None,
        correlation_id: str | None = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> str:
        """Publish message via Redis."""
        if self._closed:
            raise RuntimeError("Message bus is closed")

        message = AgentMessage(
            message_type=event_type,
            sender_id=agent_id,
            recipient_id=recipient_id,
            payload=payload,
            correlation_id=correlation_id,
            priority=priority,
        )

        redis = await self._get_redis()
        channel = f"vf:agent:{event_type.value}"

        # Serialize and publish
        message_json = message.to_dict()
        await redis.publish(channel, message_json)

        return message.message_id

    async def broadcast(
        self,
        agent_id: str,
        event_type: MessageType,
        payload: dict[str, Any],
    ) -> str:
        """Broadcast message via Redis."""
        return await self.publish(
            agent_id=agent_id,
            event_type=event_type,
            payload=payload,
            recipient_id=None,
        )

    async def _listen(self) -> None:
        """Listen for Redis messages."""
        if self._pubsub is None:
            return

        try:
            async for message in self._pubsub.listen():
                if self._closed:
                    break

                if message["type"] == "message":
                    # Deserialize and deliver
                    try:
                        data = message["data"]
                        agent_message = AgentMessage.from_dict(data)
                        await self._deliver_locally(agent_message)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if not self._closed:
                logger.error(f"Redis listener error: {e}")

    async def _deliver_locally(self, message: AgentMessage) -> None:
        """Deliver message to local subscribers."""
        message_type = message.message_type
        recipient_id = message.recipient_id

        for subscriber_id, handlers in self._subscriptions.items():
            if message_type not in handlers:
                continue

            # Skip if message is for specific recipient
            if recipient_id is not None and subscriber_id != recipient_id:
                continue

            # Skip sender
            if subscriber_id == message.sender_id:
                continue

            for handler in handlers[message_type]:
                try:
                    result = handler(message)
                    if asyncio.iscoroutine(result):
                        await result
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error delivering message to {subscriber_id}: {e}")

    async def close(self) -> None:
        """Close Redis connections."""
        self._closed = True

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()

        if self._redis:
            await self._redis.close()

        logger.info("RedisMessageBus closed")


async def create_message_bus(
    backend: str = "memory",
    redis_url: str | None = None,
) -> MessageBus:
    """Factory function to create appropriate message bus.

    Args:
        backend: "memory" or "redis"
        redis_url: Redis URL (required if backend="redis")

    Returns:
        Configured MessageBus instance
    """
    if backend == "memory":
        return InMemoryMessageBus()
    elif backend == "redis":
        if not redis_url:
            raise ValueError("redis_url required for Redis backend")
        return RedisMessageBus(redis_url=redis_url)
    else:
        raise ValueError(f"Unknown backend: {backend}")
