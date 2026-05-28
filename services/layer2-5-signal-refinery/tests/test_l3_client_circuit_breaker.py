"""Tests for L2.5 L3 client circuit-breaker pilot (P1-014)."""

from unittest.mock import AsyncMock

import pytest

from layer2_5_signal_refinery.clients.l3_graph_client import L3GraphClient, _l3_circuit_breaker
from value_fabric.shared.resilience import CircuitBreakerOpen


@pytest.fixture(autouse=True)
def _reset_breaker():
    """Reset the shared breaker to closed before each test."""
    _l3_circuit_breaker.state = "closed"
    _l3_circuit_breaker.failures = 0
    _l3_circuit_breaker.last_failure_time = 0
    _l3_circuit_breaker.half_open_calls = 0
    yield


@pytest.mark.asyncio
async def test_push_signal_returns_false_when_circuit_open():
    client = L3GraphClient()
    # Force circuit open
    _l3_circuit_breaker.state = "open"
    _l3_circuit_breaker.last_failure_time = pytest.importorskip("time").time()

    result = await client.push_signal({"id": "sig-1"}, tenant_id="tenant-1")
    assert result is False


@pytest.mark.asyncio
async def test_push_signal_uses_circuit_breaker_on_failure(monkeypatch):
    client = L3GraphClient()
    monkeypatch.setattr(
        client._client,
        "post",
        AsyncMock(side_effect=ConnectionError("refused")),
    )

    # First failure
    result = await client.push_signal({"id": "sig-1"}, tenant_id="tenant-1")
    assert result is False

    # Second failure
    result = await client.push_signal({"id": "sig-2"}, tenant_id="tenant-1")
    assert result is False

    # Third failure should open the circuit (threshold=3)
    result = await client.push_signal({"id": "sig-3"}, tenant_id="tenant-1")
    assert result is False

    # Next call should be rejected by open circuit
    result = await client.push_signal({"id": "sig-4"}, tenant_id="tenant-1")
    assert result is False
