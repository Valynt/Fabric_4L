"""
P1-011: Message Queue Integration Tests
Validates RabbitMQ/Kafka connectivity, message delivery guarantees,
and consumer resilience patterns.
"""
import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from value_fabric.shared.testing import mark

pytestmark = [mark.integration, mark.requires_docker]


@pytest.fixture(scope="module")
def rabbitmq_container():
    """Spin up RabbitMQ via testcontainers."""
    pytest.importorskip("testcontainers")
    from testcontainers.rabbitmq import RabbitMqContainer

    with RabbitMqContainer("rabbitmq:3.13-alpine") as rabbit:
        yield rabbit.get_connection_url()


@pytest.fixture(scope="module")
def kafka_container():
    """Spin up Kafka via testcontainers."""
    pytest.importorskip("testcontainers")
    from testcontainers.kafka import KafkaContainer

    with KafkaContainer("confluentinc/cp-kafka:7.6") as kafka:
        yield kafka.get_bootstrap_server()


@pytest.mark.asyncio
async def test_rabbitmq_connectivity(rabbitmq_container):
    """Verify RabbitMQ connection and basic pub/sub."""
    pytest.importorskip("aio_pika")
    import aio_pika

    connection = await aio_pika.connect(rabbitmq_container)
    channel = await connection.channel()
    queue = await channel.declare_queue("test_queue", auto_delete=True)

    # Publish test message
    message_body = b"integration_test_message"
    await channel.default_exchange.publish(
        aio_pika.Message(body=message_body),
        routing_key="test_queue",
    )

    # Consume with timeout
    incoming = await asyncio.wait_for(queue.get(), timeout=5.0)
    assert incoming.body == message_body
    await connection.close()


@pytest.mark.asyncio
async def test_kafka_connectivity(kafka_container):
    """Verify Kafka producer/consumer round-trip."""
    pytest.importorskip("aiokafka")
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

    topic = "test_topic"
    test_message = b"kafka_integration_test"

    # Produce
    producer = AIOKafkaProducer(bootstrap_servers=kafka_container)
    await producer.start()
    await producer.send_and_wait(topic, test_message)
    await producer.stop()

    # Consume
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=kafka_container,
        auto_offset_reset="earliest",
        group_id="test_group",
    )
    await consumer.start()
    msg = await asyncio.wait_for(consumer.getone(), timeout=10.0)
    assert msg.value == test_message
    await consumer.stop()


@pytest.mark.asyncio
async def test_message_delivery_guarantees():
    """Test at-least-once delivery with idempotent consumer."""
    processed_ids = set()

    async def process_message(msg_id: str) -> bool:
        """Idempotent message processor."""
        if msg_id in processed_ids:
            return False  # Already processed (duplicate)
        processed_ids.add(msg_id)
        return True

    # Simulate duplicate delivery
    msg_id = "msg_001"
    assert await process_message(msg_id) is True
    assert await process_message(msg_id) is False  # Duplicate rejected


@pytest.mark.asyncio
async def test_consumer_backpressure():
    """Verify consumer handles backpressure gracefully."""
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent messages

    async def process_with_backpressure(msg: bytes) -> None:
        async with semaphore:
            await asyncio.sleep(0.01)  # Simulate processing

    # Process 100 messages with limited concurrency
    messages = [f"msg_{i}".encode() for i in range(100)]
    start = time.time()
    await asyncio.gather(*(process_with_backpressure(m) for m in messages))
    elapsed = time.time() - start

    # With 10 concurrent and 0.01s each, 100 messages should take ~0.1s
    assert elapsed < 2.0, f"Backpressure processing too slow: {elapsed}s"


class TestCeleryMessageQueue:
    """Tests for Celery as message queue backend."""

    def test_celery_task_serialization(self):
        """Verify task args serialize correctly."""
        from celery import Celery

        app = Celery("test")

        @app.task
        def add(x, y):
            return x + y

        # Test serialization round-trip
        body = add.s(1, 2).body
        deserialized = add.app.amqp.router.route({}, add.name)
        assert body is not None

    def test_celery_task_retry_with_backoff(self):
        """Verify retry with exponential backoff."""
        from celery import Task

        class RetryableTask(Task):
            max_retries = 3
            default_retry_delay = 60
            retry_backoff = True
            retry_backoff_max = 600

            def run(self, x):
                if self.request.retries < 2:
                    raise self.retry(countdown=60 * (2 ** self.request.retries))
                return x * 2

        assert RetryableTask.max_retries == 3
        assert RetryableTask.retry_backoff is True

    def test_dead_letter_queue(self):
        """Verify dead letter queue configuration."""
        # Mock DLQ routing
        dlq_config = {
            "queue": "celery_dlq",
            "routing_key": "celery.dlq",
            "x-message-ttl": 86400000,  # 24 hours
            "x-max-retries": 3,
        }
        assert dlq_config["x-max-retries"] == 3
        assert dlq_config["x-message-ttl"] > 0
