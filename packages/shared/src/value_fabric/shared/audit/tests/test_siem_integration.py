from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from ..models import AuditAction, AuditEvent
from ..siem_integration import SIEMAuditSink, SIEMDeliveryConfig


class _Resp:
    def __init__(self, code: int):
        self.status_code = code


class _Client:
    def __init__(self, responses, collector):
        self._responses = responses
        self._collector = collector

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, headers):
        self._collector.append({"url": url, "json": json, "headers": headers})
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return _Resp(response)


def _event(**kwargs):
    return AuditEvent(
        action=AuditAction.USER_LOGIN,
        tenant_id=uuid4(),
        user_id="u1",
        details={"password": "hidden", "safe": "ok"},
        **kwargs,
    )


@pytest.mark.asyncio
async def test_webhook_success_and_headers():
    calls = []
    responses = [200]
    sink = SIEMAuditSink(
        SIEMDeliveryConfig(endpoint="https://siem.example/events", auth_header="Bearer t", signature_secret="sig"),
        client_factory=lambda: _Client(responses, calls),
    )
    ok = await sink.deliver(_event())
    assert ok is True
    assert sink.metrics.delivered_total == 1
    assert calls[0]["headers"]["Idempotency-Key"] == calls[0]["json"]["event_id"]
    assert "X-Signature-SHA256" in calls[0]["headers"]


@pytest.mark.asyncio
async def test_retry_and_dead_letter_on_failure():
    calls = []
    responses = [500, 502, 503]
    sleeps = []

    async def _sleep(s):
        sleeps.append(s)

    sink = SIEMAuditSink(
        SIEMDeliveryConfig(endpoint="https://siem.example/events", max_retries=2, backoff_seconds=0.01),
        client_factory=lambda: _Client(responses, calls),
        sleeper=_sleep,
    )
    ok = await sink.deliver(_event())
    assert ok is False
    assert len(calls) == 3
    assert sleeps == [0.01, 0.02]
    assert sink.metrics.failed_total == 1
    assert len(sink.dead_letter_queue) == 1


@pytest.mark.asyncio
async def test_duplicate_suppression():
    calls = []
    responses = [200]
    event = _event()
    sink = SIEMAuditSink(SIEMDeliveryConfig(endpoint="https://siem.example/events"), client_factory=lambda: _Client(responses, calls))
    assert await sink.deliver(event) is True
    assert await sink.deliver(event) is True
    assert len(calls) == 1
    assert sink.metrics.duplicate_suppressed_total == 1


@pytest.mark.asyncio
async def test_redacts_sensitive_fields_and_slo_breach_metric():
    calls = []
    responses = [200]
    old_ts = datetime.now(timezone.utc) - timedelta(minutes=6)
    sink = SIEMAuditSink(
        SIEMDeliveryConfig(endpoint="https://siem.example/events", slo_seconds=300),
        client_factory=lambda: _Client(responses, calls),
        now_fn=lambda: old_ts.timestamp() + 360,
    )
    await sink.deliver(_event(timestamp=old_ts))
    assert calls[0]["json"]["details"]["password"] == "[REDACTED]"
    assert sink.metrics.slo_breaches_total == 1
