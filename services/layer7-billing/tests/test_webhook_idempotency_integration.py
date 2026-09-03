"""
Integration tests for webhook idempotency.

Tests the idempotency logic used by the webhook endpoint.
"""

from __future__ import annotations

import json

import pytest

from value_fabric.shared.idempotency import (
    IdempotencyRecord,
    IdempotencyRequest,
    IdempotencyService,
    InMemoryIdempotencyStore,
    build_request_fingerprint,
)


class TestWebhookIdempotencyIntegration:
    """Integration tests for webhook idempotency logic."""

    def test_webhook_duplicate_returns_cached_response(self):
        """Duplicate webhook requests return cached response."""
        service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=60)

        event = {"id": "evt_test_duplicate_123", "type": "payment.created", "data": {"amount": 1000}}
        event_id = event["id"]
        request_fingerprint = build_request_fingerprint("POST", "/webhook", event)

        req = IdempotencyRequest(
            tenant_id="stripe",
            endpoint_key="POST:/webhook",
            idempotency_key=event_id,
            request_fingerprint=request_fingerprint,
        )

        # First request - no cached response
        cached = service.check_replay(req)
        assert cached is None

        # Store response
        service.store_response(req, IdempotencyRecord(status_code=200, body={"received": True, "event_id": event_id}, headers={}))

        # Duplicate request with same event_id returns cached response
        cached = service.check_replay(req)
        assert cached is not None
        assert cached.body == {"received": True, "event_id": event_id}

    def test_webhook_with_idempotency_key(self):
        """Webhook respects explicit Idempotency-Key header."""
        service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=60)

        event = {"id": "evt_test_key_123", "type": "payment.created", "data": {"amount": 1000}}
        idempotency_key = "idemp_test_abc123"
        request_fingerprint = build_request_fingerprint("POST", "/webhook", event)

        req = IdempotencyRequest(
            tenant_id="stripe",
            endpoint_key="POST:/webhook",
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
        )

        # First request with Idempotency-Key
        service.store_response(req, IdempotencyRecord(status_code=200, body={"processed": True}, headers={}))

        # Second request with same Idempotency-Key returns cached response
        cached = service.check_replay(req)
        assert cached is not None
        assert cached.body == {"processed": True}

    def test_webhook_replay_attack_prevented(self):
        """Webhook replay attacks are prevented via idempotency."""
        service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=60)

        event = {"id": "evt_test_replay_123", "type": "payment.created", "data": {"amount": 1000}}
        request_fingerprint = build_request_fingerprint("POST", "/webhook", event)

        req = IdempotencyRequest(
            tenant_id="stripe",
            endpoint_key="POST:/webhook",
            idempotency_key=event["id"],
            request_fingerprint=request_fingerprint,
        )

        # First legitimate request
        service.store_response(req, IdempotencyRecord(status_code=200, body={"processed": True}, headers={}))

        # Attacker's replay attempt (same event_id)
        cached = service.check_replay(req)
        assert cached is not None
        assert cached.body == {"processed": True}
        # Replay returns cached response instead of re-processing

    def test_webhook_different_events_processed_independently(self):
        """Different webhook events are processed independently."""
        service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=60)

        event1 = {"id": "evt_test_1", "type": "payment.created", "data": {"amount": 1000}}
        event2 = {"id": "evt_test_2", "type": "payment.created", "data": {"amount": 2000}}

        req1 = IdempotencyRequest(
            tenant_id="stripe",
            endpoint_key="POST:/webhook",
            idempotency_key=event1["id"],
            request_fingerprint=build_request_fingerprint("POST", "/webhook", event1),
        )

        req2 = IdempotencyRequest(
            tenant_id="stripe",
            endpoint_key="POST:/webhook",
            idempotency_key=event2["id"],
            request_fingerprint=build_request_fingerprint("POST", "/webhook", event2),
        )

        service.store_response(req1, IdempotencyRecord(status_code=200, body={"event_id": "evt_test_1"}, headers={}))
        service.store_response(req2, IdempotencyRecord(status_code=200, body={"event_id": "evt_test_2"}, headers={}))

        # Each event should return its own cached response
        cached1 = service.check_replay(req1)
        cached2 = service.check_replay(req2)

        assert cached1.body == {"event_id": "evt_test_1"}
        assert cached2.body == {"event_id": "evt_test_2"}

    def test_webhook_string_tenant_id_accepted(self):
        """String tenant_id like 'stripe' is accepted by idempotency service."""
        service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=60)

        event = {"id": "evt_test_tenant_123", "type": "payment.created"}
        req = IdempotencyRequest(
            tenant_id="stripe",  # String tenant_id for tenant-agnostic webhooks
            endpoint_key="POST:/webhook",
            idempotency_key=event["id"],
            request_fingerprint=build_request_fingerprint("POST", "/webhook", event),
        )

        # Should not raise error when tenant_id parameter is not passed
        cached = service.check_replay(req)
        assert cached is None

        service.store_response(req, IdempotencyRecord(status_code=200, body={"ok": True}, headers={}))
        cached = service.check_replay(req)
        assert cached is not None

    def test_webhook_in_memory_store_fallback(self):
        """InMemoryIdempotencyStore works when Redis is unavailable."""
        service = IdempotencyService(store=InMemoryIdempotencyStore(), ttl_seconds=60)

        event = {"id": "evt_test_fallback_123", "type": "payment.created"}
        req = IdempotencyRequest(
            tenant_id="stripe",
            endpoint_key="POST:/webhook",
            idempotency_key=event["id"],
            request_fingerprint=build_request_fingerprint("POST", "/webhook", event),
        )

        # First request - no cache
        assert service.check_replay(req) is None

        # Store response
        service.store_response(req, IdempotencyRecord(status_code=200, body={"fallback": True}, headers={}))

        # Second request - should return cached from in-memory store
        cached = service.check_replay(req)
        assert cached is not None
        assert cached.body == {"fallback": True}
