"""Comprehensive unit tests for the Webhook Dead-Letter Queue (DLQ).

Covers:
- DLQRecord creation, serialization, and secret-header scrubbing.
- WebhookDLQ enqueue, lookup, listing with filters and limits.
- FIFO eviction on capacity overflow.
- Resolution lifecycle (mark_resolved).
- Retry count progression (increment_retry).
- JSON export serialization.
- Global singleton lifecycle (get_webhook_dlq, reset_webhook_dlq).
- Thread-safe concurrent operations.
"""

from __future__ import annotations

import concurrent.futures
import json
import time

import pytest

from app.core.webhook_dlq import (
    DLQRecord,
    WebhookDLQ,
    get_webhook_dlq,
    reset_webhook_dlq,
)


@pytest.fixture(autouse=True)
def clean_dlq():
    """Ensure singleton is reset before and after each test."""
    reset_webhook_dlq()
    yield
    reset_webhook_dlq()


class TestDLQRecord:
    """Tests for DLQRecord data class and serialization."""

    def test_record_fields_and_defaults(self):
        record = DLQRecord(
            id="dlq_1234567890ab",
            event_id="evt_01",
            event_type="user.created",
            payload={"user_id": "usr_999"},
            headers={"svix-id": "msg_123", "content-type": "application/json"},
            error_reason="Connection error to auth directory",
            received_at=1700000000.0,
        )
        assert record.id == "dlq_1234567890ab"
        assert record.event_id == "evt_01"
        assert record.event_type == "user.created"
        assert record.payload == {"user_id": "usr_999"}
        assert record.headers == {"svix-id": "msg_123", "content-type": "application/json"}
        assert record.error_reason == "Connection error to auth directory"
        assert record.received_at == 1700000000.0
        assert record.retry_count == 0
        assert record.resolved is False

    def test_to_dict_scrubs_secret_and_sensitive_headers_case_insensitively(self):
        record = DLQRecord(
            id="dlq_abc",
            event_id="evt_02",
            event_type="organization.created",
            payload={"org_id": "org_111"},
            headers={
                "svix-id": "msg_456",
                "svix-timestamp": "1700000000",
                "content-type": "application/json",
                "Webhook-Secret": "whsec_supersecret123",
                "X-CLERK-SECRET-KEY": "sk_test_sensitive",
                "Authorization": "Bearer sensitive_token_xyz",
                "Cookie": "vf_session=secret_cookie_val",
                "X-API-Key": "my-api-key-123",
                "custom-secret-hdr": "hidden_value",
            },
            error_reason="Invalid payload structure",
            received_at=1700000000.0,
            retry_count=2,
            resolved=True,
        )
        d = record.to_dict()
        assert d["id"] == "dlq_abc"
        assert d["event_id"] == "evt_02"
        assert d["event_type"] == "organization.created"
        assert d["payload"] == {"org_id": "org_111"}
        assert d["error_reason"] == "Invalid payload structure"
        assert d["received_at"] == 1700000000.0
        assert d["retry_count"] == 2
        assert d["resolved"] is True

        # Non-sensitive headers are preserved
        assert d["headers"]["svix-id"] == "msg_456"
        assert d["headers"]["svix-timestamp"] == "1700000000"
        assert d["headers"]["content-type"] == "application/json"

        # All sensitive headers (secrets, auth, cookies, api-keys) must be stripped
        assert "Webhook-Secret" not in d["headers"]
        assert "X-CLERK-SECRET-KEY" not in d["headers"]
        assert "custom-secret-hdr" not in d["headers"]
        assert "Authorization" not in d["headers"]
        assert "Cookie" not in d["headers"]
        assert "X-API-Key" not in d["headers"]

class TestWebhookDLQ:
    """Tests for WebhookDLQ buffer operations."""

    def test_enqueue_generates_id_and_returns_record(self):
        dlq = WebhookDLQ(max_records=10)
        start_time = time.time()
        record = dlq.enqueue(
            event_id="evt_test_01",
            event_type="user.updated",
            payload={"id": "usr_123"},
            headers={"svix-id": "evt_test_01"},
            error_reason="DB lock timeout",
        )

        assert record.id.startswith("dlq_")
        assert len(record.id) > 4
        assert record.event_id == "evt_test_01"
        assert record.event_type == "user.updated"
        assert record.payload == {"id": "usr_123"}
        assert record.headers == {"svix-id": "evt_test_01"}
        assert record.error_reason == "DB lock timeout"
        assert record.received_at >= start_time
        assert record.retry_count == 0
        assert record.resolved is False

    def test_get_existing_and_nonexistent_record(self):
        dlq = WebhookDLQ()
        rec = dlq.enqueue(
            event_id="evt_100",
            event_type="session.created",
            payload={},
            headers={},
            error_reason="Network error",
        )
        found = dlq.get(rec.id)
        assert found == rec

        missing = dlq.get("dlq_nonexistent")
        assert missing is None

    def test_fifo_eviction_when_capacity_exceeded(self):
        dlq = WebhookDLQ(max_records=3)
        r1 = dlq.enqueue(event_id="e1", event_type="t1", payload={}, headers={}, error_reason="r1")
        r2 = dlq.enqueue(event_id="e2", event_type="t2", payload={}, headers={}, error_reason="r2")
        r3 = dlq.enqueue(event_id="e3", event_type="t3", payload={}, headers={}, error_reason="r3")

        assert dlq.get(r1.id) is not None
        assert dlq.get(r2.id) is not None
        assert dlq.get(r3.id) is not None

        # Adding 4th item should evict r1 (oldest)
        r4 = dlq.enqueue(event_id="e4", event_type="t4", payload={}, headers={}, error_reason="r4")

        assert dlq.get(r1.id) is None
        assert dlq.get(r2.id) is not None
        assert dlq.get(r3.id) is not None
        assert dlq.get(r4.id) is not None

        all_records = dlq.list_records(unresolved_only=False)
        assert len(all_records) == 3
        assert [r.id for r in all_records] == [r2.id, r3.id, r4.id]

    def test_list_records_filtering_and_limits(self):
        dlq = WebhookDLQ(max_records=10)
        r1 = dlq.enqueue(event_id="e1", event_type="t1", payload={}, headers={}, error_reason="r1")
        r2 = dlq.enqueue(event_id="e2", event_type="t2", payload={}, headers={}, error_reason="r2")
        r3 = dlq.enqueue(event_id="e3", event_type="t3", payload={}, headers={}, error_reason="r3")
        r4 = dlq.enqueue(event_id="e4", event_type="t4", payload={}, headers={}, error_reason="r4")

        # Mark r2 resolved
        dlq.mark_resolved(r2.id)

        # Default: unresolved only
        unresolved = dlq.list_records()
        assert [r.id for r in unresolved] == [r1.id, r3.id, r4.id]

        # All records
        all_records = dlq.list_records(unresolved_only=False)
        assert [r.id for r in all_records] == [r1.id, r2.id, r3.id, r4.id]

        # Limit parameter (returns most recent N items)
        limited = dlq.list_records(limit=2, unresolved_only=False)
        assert [r.id for r in limited] == [r3.id, r4.id]

        limited_unresolved = dlq.list_records(limit=2, unresolved_only=True)
        assert [r.id for r in limited_unresolved] == [r3.id, r4.id]

    def test_mark_resolved(self):
        dlq = WebhookDLQ()
        r1 = dlq.enqueue(event_id="e1", event_type="t1", payload={}, headers={}, error_reason="r1")

        assert r1.resolved is False
        assert dlq.mark_resolved(r1.id) is True

        updated = dlq.get(r1.id)
        assert updated is not None
        assert updated.resolved is True

        # Nonexistent record returns False
        assert dlq.mark_resolved("dlq_unknown") is False

    def test_increment_retry(self):
        dlq = WebhookDLQ()
        r1 = dlq.enqueue(event_id="e1", event_type="t1", payload={}, headers={}, error_reason="r1")

        assert r1.retry_count == 0
        assert dlq.increment_retry(r1.id) == 1
        assert dlq.increment_retry(r1.id) == 2
        assert dlq.increment_retry(r1.id) == 3

        record = dlq.get(r1.id)
        assert record is not None
        assert record.retry_count == 3

        # Nonexistent record returns 0
        assert dlq.increment_retry("dlq_missing") == 0

    def test_export_json(self):
        dlq = WebhookDLQ()
        dlq.enqueue(
            event_id="e1",
            event_type="t1",
            payload={"data": "test"},
            headers={"secret_header": "xxx", "svix-id": "e1"},
            error_reason="failed",
        )
        dlq.enqueue(
            event_id="e2",
            event_type="t2",
            payload={"data": "test2"},
            headers={"svix-id": "e2"},
            error_reason="timeout",
        )

        json_str = dlq.export_json()
        data = json.loads(json_str)

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["event_id"] == "e1"
        assert "secret_header" not in data[0]["headers"]
        assert data[0]["headers"]["svix-id"] == "e1"
        assert data[1]["event_id"] == "e2"

    def test_clear(self):
        dlq = WebhookDLQ()
        dlq.enqueue(event_id="e1", event_type="t1", payload={}, headers={}, error_reason="r1")
        dlq.enqueue(event_id="e2", event_type="t2", payload={}, headers={}, error_reason="r2")

        assert len(dlq.list_records(unresolved_only=False)) == 2
        dlq.clear()
        assert len(dlq.list_records(unresolved_only=False)) == 0


class TestSingletonLifecycle:
    """Tests for singleton getter and reset helper."""

    def test_get_webhook_dlq_returns_singleton(self):
        d1 = get_webhook_dlq()
        d2 = get_webhook_dlq()
        assert d1 is d2

        d1.enqueue(event_id="s1", event_type="test", payload={}, headers={}, error_reason="err")
        assert len(d2.list_records(unresolved_only=False)) == 1

    def test_reset_webhook_dlq_clears_singleton(self):
        dlq = get_webhook_dlq()
        dlq.enqueue(event_id="s1", event_type="test", payload={}, headers={}, error_reason="err")
        assert len(dlq.list_records(unresolved_only=False)) == 1

        reset_webhook_dlq()
        assert len(dlq.list_records(unresolved_only=False)) == 0


class TestConcurrency:
    """Tests for thread safety under concurrent enqueue and update operations."""

    def test_concurrent_enqueues_and_evictions(self):
        dlq = WebhookDLQ(max_records=50)
        total_workers = 10
        ops_per_worker = 20

        def worker(w_id: int):
            records = []
            for i in range(ops_per_worker):
                rec = dlq.enqueue(
                    event_id=f"worker_{w_id}_evt_{i}",
                    event_type="test.event",
                    payload={"worker": w_id, "index": i},
                    headers={"svix-id": f"worker_{w_id}_evt_{i}"},
                    error_reason="concurrent test",
                )
                records.append(rec)
                if i % 2 == 0:
                    dlq.increment_retry(rec.id)
                if i % 4 == 0:
                    dlq.mark_resolved(rec.id)
            return records

        with concurrent.futures.ThreadPoolExecutor(max_workers=total_workers) as executor:
            futures = [executor.submit(worker, w) for w in range(total_workers)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        # Buffer size should not exceed max_records
        all_stored = dlq.list_records(unresolved_only=False)
        assert len(all_stored) == 50
