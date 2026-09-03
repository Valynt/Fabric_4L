from __future__ import annotations

"""Tests for L4 messaging types, bus, and router."""


import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from _wait_utils import wait_for_background_tasks, wait_until

from layer4_agents.messaging.bus import InMemoryMessageBus, create_message_bus
from layer4_agents.messaging.router import MessageRouter
from layer4_agents.messaging.types import (
    AgentMessage,
    ErrorNotification,
    MessagePriority,
    MessageType,
    ProvenanceEvent,
    StatusUpdate,
    TaskAssignment,
    TaskResult,
)

# ═══════════════════════════════════════════════════════════════════════════
# Message types
# ═══════════════════════════════════════════════════════════════════════════


class TestMessageType:
    def test_values_are_strings(self):
        assert MessageType.TASK_ASSIGNMENT.value == "task_assignment"
        assert MessageType.TASK_RESULT.value == "task_result"

    def test_all_unique(self):
        values = [m.value for m in MessageType]
        assert len(values) == len(set(values))


class TestMessagePriority:
    def test_ordering(self):
        assert MessagePriority.CRITICAL.value < MessagePriority.HIGH.value
        assert MessagePriority.HIGH.value < MessagePriority.NORMAL.value
        assert MessagePriority.NORMAL.value < MessagePriority.LOW.value
        assert MessagePriority.LOW.value < MessagePriority.BACKGROUND.value


class TestAgentMessage:
    def test_creation_defaults(self):
        msg = AgentMessage(
            message_type=MessageType.TASK_ASSIGNMENT,
            sender_id="agent-1",
            payload={"task": "extract"},
        )
        assert msg.sender_id == "agent-1"
        assert msg.recipient_id is None
        assert msg.priority == MessagePriority.NORMAL
        assert msg.ttl_seconds == 300
        assert msg.message_id is not None

    def test_to_dict_roundtrip(self):
        msg = AgentMessage(
            message_type=MessageType.TASK_RESULT,
            sender_id="agent-1",
            payload={"result": "done"},
            recipient_id="agent-2",
            correlation_id="corr-1",
            priority=MessagePriority.HIGH,
        )
        d = msg.to_dict()
        restored = AgentMessage.from_dict(d)
        assert restored.sender_id == msg.sender_id
        assert restored.recipient_id == msg.recipient_id
        assert restored.message_type == msg.message_type
        assert restored.correlation_id == msg.correlation_id
        assert restored.priority == msg.priority

    def test_is_broadcast(self):
        broadcast = AgentMessage(
            message_type=MessageType.STATUS_UPDATE,
            sender_id="agent-1",
            payload={},
        )
        assert broadcast.is_broadcast() is True

        targeted = AgentMessage(
            message_type=MessageType.TASK_ASSIGNMENT,
            sender_id="agent-1",
            payload={},
            recipient_id="agent-2",
        )
        assert targeted.is_broadcast() is False

    def test_is_expired(self):
        expired = AgentMessage(
            message_type=MessageType.TASK_ASSIGNMENT,
            sender_id="agent-1",
            payload={},
            timestamp=datetime.now(UTC) - timedelta(seconds=500),
            ttl_seconds=300,
        )
        assert expired.is_expired() is True

        fresh = AgentMessage(
            message_type=MessageType.TASK_ASSIGNMENT,
            sender_id="agent-1",
            payload={},
            ttl_seconds=300,
        )
        assert fresh.is_expired() is False


class TestTaskAssignment:
    def test_to_dict(self):
        ta = TaskAssignment(
            task_id="task-1",
            capability="document_parsing",
            parameters={"url": "https://example.com"},
            tenant_id="tenant-1",
        )
        d = ta.to_dict()
        assert d["task_id"] == "task-1"
        assert d["capability"] == "document_parsing"
        assert d["tenant_id"] == "tenant-1"

    def test_deadline_serialization(self):
        now = datetime.now(UTC)
        ta = TaskAssignment(
            task_id="task-1",
            capability="test",
            parameters={},
            deadline=now,
        )
        d = ta.to_dict()
        assert d["deadline"] == now.isoformat()


class TestTaskResult:
    def test_success(self):
        tr = TaskResult(task_id="task-1", success=True, result={"value": 42})
        d = tr.to_dict()
        assert d["success"] is True
        assert d["result"] == {"value": 42}

    def test_failure(self):
        tr = TaskResult(task_id="task-1", success=False, error="Timeout")
        d = tr.to_dict()
        assert d["success"] is False
        assert d["error"] == "Timeout"


class TestStatusUpdate:
    def test_to_dict(self):
        su = StatusUpdate(
            agent_id="agent-1",
            status="RUNNING",
            current_task="extraction",
            progress_percent=45.5,
        )
        d = su.to_dict()
        assert d["agent_id"] == "agent-1"
        assert d["progress_percent"] == 45.5


class TestErrorNotification:
    def test_to_dict(self):
        en = ErrorNotification(
            error_id="err-1",
            severity="CRITICAL",
            message="Out of memory",
            context={"node": "worker-3"},
        )
        d = en.to_dict()
        assert d["severity"] == "CRITICAL"
        assert d["context"]["node"] == "worker-3"


class TestProvenanceEvent:
    def test_to_dict(self):
        pe = ProvenanceEvent(
            event_type="entity_generated",
            activity_id="act-1",
            entity_id="ent-1",
            agent_id="agent-1",
        )
        d = pe.to_dict()
        assert d["event_type"] == "entity_generated"
        assert "timestamp" in d


# ═══════════════════════════════════════════════════════════════════════════
# InMemoryMessageBus
# ═══════════════════════════════════════════════════════════════════════════


class TestInMemoryMessageBus:
    @pytest.fixture
    def bus(self):
        return InMemoryMessageBus()

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, bus):
        received = []

        async def handler(msg):
            received.append(msg)

        await bus.subscribe("agent-2", MessageType.TASK_ASSIGNMENT, handler)
        await bus.publish(
            agent_id="agent-1",
            event_type=MessageType.TASK_ASSIGNMENT,
            payload={"task": "test"},
            recipient_id="agent-2",
        )
        # Signal-based wait for the background delivery to complete.
        await wait_until(
            lambda: len(received) == 1,
            description="message delivered to subscriber",
        )
        assert received[0].payload == {"task": "test"}

    @pytest.mark.asyncio
    async def test_publish_skips_sender(self, bus):
        received = []

        async def handler(msg):
            received.append(msg)

        await bus.subscribe("agent-1", MessageType.STATUS_UPDATE, handler)
        tasks_before = {t for t in asyncio.all_tasks()}
        await bus.publish(
            agent_id="agent-1",
            event_type=MessageType.STATUS_UPDATE,
            payload={"status": "busy"},
        )
        # Flush the background delivery, then assert the sender got nothing.
        await wait_for_background_tasks(
            tasks_before, description="status update delivery"
        )
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_broadcast(self, bus):
        received_a = []
        received_b = []

        async def handler_a(msg):
            received_a.append(msg)

        async def handler_b(msg):
            received_b.append(msg)

        await bus.subscribe("agent-2", MessageType.STATUS_UPDATE, handler_a)
        await bus.subscribe("agent-3", MessageType.STATUS_UPDATE, handler_b)

        await bus.broadcast(
            agent_id="agent-1",
            event_type=MessageType.STATUS_UPDATE,
            payload={"status": "starting"},
        )
        await wait_until(
            lambda: len(received_a) == 1 and len(received_b) == 1,
            description="broadcast delivered to both subscribers",
        )

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        received = []

        async def handler(msg):
            received.append(msg)

        await bus.subscribe("agent-2", MessageType.TASK_ASSIGNMENT, handler)
        await bus.unsubscribe("agent-2", MessageType.TASK_ASSIGNMENT)

        tasks_before = {t for t in asyncio.all_tasks()}
        await bus.publish(
            agent_id="agent-1",
            event_type=MessageType.TASK_ASSIGNMENT,
            payload={},
            recipient_id="agent-2",
        )
        # Flush the background delivery, then assert nothing was received.
        await wait_for_background_tasks(
            tasks_before, description="delivery after unsubscribe"
        )
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_all(self, bus):
        received = []

        async def handler(msg):
            received.append(msg)

        await bus.subscribe("agent-2", MessageType.TASK_ASSIGNMENT, handler)
        await bus.subscribe("agent-2", MessageType.STATUS_UPDATE, handler)
        await bus.unsubscribe("agent-2")  # Unsubscribe from all

        tasks_before = {t for t in asyncio.all_tasks()}
        await bus.publish(
            agent_id="agent-1",
            event_type=MessageType.TASK_ASSIGNMENT,
            payload={},
            recipient_id="agent-2",
        )
        # Flush the background delivery, then assert nothing was received.
        await wait_for_background_tasks(
            tasks_before, description="delivery after unsubscribe-all"
        )
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_close_prevents_publish(self, bus):
        await bus.close()
        with pytest.raises(RuntimeError, match="closed"):
            await bus.publish(
                agent_id="agent-1",
                event_type=MessageType.TASK_ASSIGNMENT,
                payload={},
            )

    @pytest.mark.asyncio
    async def test_close_prevents_subscribe(self, bus):
        await bus.close()
        with pytest.raises(RuntimeError, match="closed"):
            await bus.subscribe("agent-1", MessageType.TASK_ASSIGNMENT, lambda m: None)

    @pytest.mark.asyncio
    async def test_targeted_message_not_delivered_to_others(self, bus):
        received_target = []
        received_other = []

        async def target_handler(msg):
            received_target.append(msg)

        async def other_handler(msg):
            received_other.append(msg)

        await bus.subscribe("agent-2", MessageType.TASK_ASSIGNMENT, target_handler)
        await bus.subscribe("agent-3", MessageType.TASK_ASSIGNMENT, other_handler)

        await bus.publish(
            agent_id="agent-1",
            event_type=MessageType.TASK_ASSIGNMENT,
            payload={"for": "agent-2 only"},
            recipient_id="agent-2",
        )
        await wait_until(
            lambda: len(received_target) == 1,
            description="targeted message delivered to recipient",
        )
        assert len(received_other) == 0


class TestCreateMessageBus:
    @pytest.mark.asyncio
    async def test_memory_backend(self):
        bus = await create_message_bus("memory")
        assert isinstance(bus, InMemoryMessageBus)
        await bus.close()

    @pytest.mark.asyncio
    async def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            await create_message_bus("kafka")

    @pytest.mark.asyncio
    async def test_redis_without_url_raises(self):
        with pytest.raises(ValueError, match="redis_url"):
            await create_message_bus("redis")


# ═══════════════════════════════════════════════════════════════════════════
# MessageRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestMessageRouter:
    @pytest.fixture
    def bus(self):
        return InMemoryMessageBus()

    @pytest.fixture
    def router(self, bus):
        return MessageRouter(bus)

    def test_register_agent(self, router):
        router.register_agent("agent-1", ["parsing", "ocr"])
        assert router.get_agent_capabilities("agent-1") == ["parsing", "ocr"]
        assert "agent-1" in router.get_agents_for_capability("parsing")
        assert "agent-1" in router.get_agents_for_capability("ocr")

    def test_unregister_agent(self, router):
        router.register_agent("agent-1", ["parsing"])
        router.unregister_agent("agent-1")
        assert router.get_agent_capabilities("agent-1") == []
        assert router.get_agents_for_capability("parsing") == []

    def test_unregister_nonexistent_agent_noop(self, router):
        router.unregister_agent("nonexistent")  # Should not raise

    def test_route_task_no_agents(self, router):
        result = router.route_task("parsing")
        assert result is None

    def test_route_task_load_balanced(self, router):
        router.register_agent("agent-1", ["parsing"])
        router.register_agent("agent-2", ["parsing"])
        router.update_agent_load("agent-1", 70)
        router.update_agent_load("agent-2", 30)
        result = router.route_task("parsing", strategy="load_balanced")
        assert result == "agent-2"

    def test_route_task_round_robin(self, router):
        router.register_agent("agent-1", ["parsing"])
        router.register_agent("agent-2", ["parsing"])
        result = router.route_task("parsing", strategy="round_robin")
        assert result == "agent-1"

    def test_route_task_random(self, router):
        router.register_agent("agent-1", ["parsing"])
        result = router.route_task("parsing", strategy="random")
        assert result == "agent-1"

    def test_route_task_unknown_strategy_raises(self, router):
        router.register_agent("agent-1", ["parsing"])
        with pytest.raises(ValueError, match="Unknown routing strategy"):
            router.route_task("parsing", strategy="magic")

    def test_overloaded_agents_fallback(self, router):
        router.register_agent("agent-1", ["parsing"])
        router.update_agent_load("agent-1", 95)
        # Only agent is overloaded, should still return it as fallback
        result = router.route_task("parsing")
        assert result == "agent-1"

    def test_update_agent_load_clamps(self, router):
        router.register_agent("agent-1", ["parsing"])
        router.update_agent_load("agent-1", 150)
        assert router.get_agent_load("agent-1") == 100
        router.update_agent_load("agent-1", -10)
        assert router.get_agent_load("agent-1") == 0
        # Unregistered agents report a load of 0
        assert router.get_agent_load("unknown-agent") == 0

    def test_get_all_capabilities(self, router):
        router.register_agent("agent-1", ["parsing", "ocr"])
        router.register_agent("agent-2", ["extraction"])
        caps = router.get_all_capabilities()
        assert set(caps) == {"parsing", "ocr", "extraction"}

    def test_cluster_health_no_agents(self, router):
        health = router.get_cluster_health()
        assert health["status"] == "unhealthy"
        assert health["total_agents"] == 0

    def test_cluster_health_healthy(self, router):
        router.register_agent("agent-1", ["parsing"])
        router.register_agent("agent-2", ["parsing"])
        router.update_agent_load("agent-1", 30)
        router.update_agent_load("agent-2", 40)
        health = router.get_cluster_health()
        assert health["status"] == "healthy"
        assert health["total_agents"] == 2

    def test_cluster_health_degraded(self, router):
        router.register_agent("agent-1", ["parsing"])
        router.register_agent("agent-2", ["parsing"])
        router.update_agent_load("agent-1", 85)
        router.update_agent_load("agent-2", 85)
        health = router.get_cluster_health()
        assert health["status"] == "critical"

    @pytest.mark.asyncio
    async def test_route_and_send(self, bus, router):
        received = []

        async def handler(msg):
            received.append(msg)

        router.register_agent("agent-2", ["parsing"])
        await bus.subscribe("agent-2", MessageType.TASK_ASSIGNMENT, handler)

        recipient = await router.route_and_send(
            sender_id="agent-1",
            capability="parsing",
            payload={"doc": "test.pdf"},
        )
        await wait_until(
            lambda: len(received) == 1,
            description="routed message delivered",
        )
        assert recipient == "agent-2"

    @pytest.mark.asyncio
    async def test_route_and_send_no_agent(self, bus, router):
        result = await router.route_and_send(
            sender_id="agent-1",
            capability="nonexistent",
            payload={},
        )
        assert result is None
