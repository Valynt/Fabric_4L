from __future__ import annotations

import asyncio

import pytest

from layer4_agents.messaging.bus import RedisMessageBus, create_message_bus
from layer4_agents.messaging.types import AgentMessage, MessagePriority, MessageType


class PubSub:
    def __init__(self, messages=()):
        self.messages = list(messages)
        self.subscribed = []
        self.unsubscribed = self.closed = 0

    async def subscribe(self, channel):
        self.subscribed.append(channel)

    async def unsubscribe(self):
        self.unsubscribed += 1

    async def close(self):
        self.closed += 1

    async def listen(self):
        for message in self.messages:
            if isinstance(message, BaseException):
                raise message
            yield message


class Redis:
    def __init__(self, pubsub):
        self.value = pubsub
        self.published = []
        self.closed = 0

    def pubsub(self):
        return self.value

    async def publish(self, channel, value):
        self.published.append((channel, value))

    async def close(self):
        self.closed += 1


@pytest.mark.asyncio
async def test_redis_subscription_publication_and_unsubscription() -> None:
    pubsub = PubSub()
    redis = Redis(pubsub)
    bus = RedisMessageBus(node_id="node")
    bus._redis = redis
    bus._pubsub = pubsub

    def handler(_message):
        return None

    await bus.subscribe("receiver", MessageType.STATUS_UPDATE, handler)
    assert pubsub.subscribed == ["vf:agent:status_update"]
    message_id = await bus.publish(
        "sender",
        MessageType.STATUS_UPDATE,
        {"status": "ready"},
        recipient_id="receiver",
        correlation_id="correlation",
        priority=MessagePriority.HIGH,
    )
    assert message_id and redis.published[0][0] == "vf:agent:status_update"
    assert redis.published[0][1].recipient_id == "receiver"
    assert await bus.broadcast("sender", MessageType.COORDINATION, {"all": True})
    await bus.unsubscribe("receiver", MessageType.STATUS_UPDATE)
    assert MessageType.STATUS_UPDATE not in bus._subscriptions["receiver"]
    await bus.subscribe("receiver", MessageType.STATUS_UPDATE, handler)
    await bus.unsubscribe("receiver")
    assert "receiver" not in bus._subscriptions

    bus._closed = True
    with pytest.raises(RuntimeError, match="closed"):
        await bus.subscribe("x", MessageType.STATUS_UPDATE, handler)
    with pytest.raises(RuntimeError, match="closed"):
        await bus.publish("x", MessageType.STATUS_UPDATE, {})
    await bus.unsubscribe("x")


@pytest.mark.asyncio
async def test_local_delivery_filters_and_isolates_handler_failures() -> None:
    bus = RedisMessageBus()
    received = []

    async def async_handler(message):
        received.append(("async", message.payload))

    def sync_handler(message):
        received.append(("sync", message.payload))

    def failing_handler(_message):
        raise RuntimeError("handler failed")

    bus._subscriptions["receiver"][MessageType.TASK_RESULT] = [
        async_handler,
        failing_handler,
        sync_handler,
    ]
    bus._subscriptions["sender"][MessageType.TASK_RESULT] = [sync_handler]
    bus._subscriptions["other"][MessageType.STATUS_UPDATE] = [sync_handler]
    targeted = AgentMessage(
        message_type=MessageType.TASK_RESULT,
        sender_id="sender",
        recipient_id="receiver",
        payload={"result": 1},
    )
    await bus._deliver_locally(targeted)
    assert received == [("async", {"result": 1}), ("sync", {"result": 1})]


@pytest.mark.asyncio
async def test_listener_deserializes_messages_and_ignores_invalid_entries(monkeypatch) -> None:
    valid = AgentMessage(
        message_type=MessageType.COORDINATION,
        sender_id="sender",
        payload={"value": 1},
    )
    pubsub = PubSub(
        [
            {"type": "subscribe", "data": None},
            {"type": "message", "data": {"bad": "data"}},
            {"type": "message", "data": valid.to_dict()},
        ]
    )
    bus = RedisMessageBus()
    bus._pubsub = pubsub
    delivered = []

    async def deliver(message):
        delivered.append(message)

    monkeypatch.setattr(bus, "_deliver_locally", deliver)
    await bus._listen()
    assert [message.message_id for message in delivered] == [valid.message_id]
    bus._pubsub = None
    await bus._listen()


@pytest.mark.asyncio
async def test_close_and_factory_contracts() -> None:
    pubsub = PubSub()
    redis = Redis(pubsub)
    bus = RedisMessageBus()
    bus._redis = redis
    bus._pubsub = pubsub
    bus._listener_task = asyncio.create_task(asyncio.sleep(60))
    await bus.close()
    assert bus._closed and pubsub.unsubscribed == 1 and pubsub.closed == 1 and redis.closed == 1
    assert (await create_message_bus("memory")).__class__.__name__ == "InMemoryMessageBus"
    assert isinstance(await create_message_bus("redis", "redis://example"), RedisMessageBus)
    with pytest.raises(ValueError, match="redis_url"):
        await create_message_bus("redis")
    with pytest.raises(ValueError, match="Unknown backend"):
        await create_message_bus("other")
