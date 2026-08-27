"""Gateway adapter tests for the Layer 5 client.

These tests pin the gateway's contract after the L5 consolidation slice:
the adapter must keep the exact public surface, tenant header propagation,
and ``HTTPException(502)`` error translation while delegating endpoint and
transport knowledge to ``value_fabric.shared.clients.layer5``.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import HTTPException

from app.clients.layer5_client import Layer5Client


def _mock_transport():
    """MockTransport handler mirroring the Layer 5 OpenAPI surface."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v1/truths" and request.method == "GET":
            return httpx.Response(200, json={"items": [], "total": 0})
        if path == "/api/v1/truths" and request.method == "POST":
            return httpx.Response(201, json={"truth_id": "t-1"})
        if path == "/api/v1/truths/t-1":
            return httpx.Response(200, json={"truth_id": "t-1"})
        if path == "/api/v1/truths/t-1/validate":
            return httpx.Response(200, json={"truth_id": "t-1", "status": "approved"})
        if path == "/api/v1/truths/sync-kg":
            return httpx.Response(200, json={"synced": 1, "failed": 0})
        if path == "/api/v1/truths/freshness-summary":
            return httpx.Response(200, json={"fresh": 1, "stale": 0})
        if path == "/api/v1/maturity-ladder":
            return httpx.Response(200, json={"levels": []})
        return httpx.Response(404, text="not found")

    return httpx.MockTransport(handler)


@pytest.fixture
def patched_async_client(monkeypatch):
    transport = _mock_transport()
    original = httpx.AsyncClient

    def _patched(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original(transport=transport, timeout=1.0)

    monkeypatch.setattr("httpx.AsyncClient", _patched)
    return transport


@pytest.mark.asyncio
async def test_gateway_client_public_surface(monkeypatch, patched_async_client) -> None:
    monkeypatch.setenv("SERVICE_AUTH_SECRET", "s" * 32)
    client = Layer5Client(base_url="http://layer5", timeout=1.0)

    assert (await client.list_truths("tenant-1"))["total"] == 0
    assert (await client.get_truth("tenant-1", "t-1"))["truth_id"] == "t-1"
    created = await client.submit_truth("tenant-1", claim="c", claim_type="other", confidence=0.9)
    assert created["truth_id"] == "t-1"
    validated = await client.validate_truth("tenant-1", "t-1", action="approve", actor="bot")
    assert validated["status"] == "approved"
    assert (await client.sync_kg("tenant-1"))["synced"] == 1
    assert (await client.get_freshness_summary("tenant-1"))["stale"] == 0
    assert (await client.get_maturity_ladder("tenant-1"))["levels"] == []


@pytest.mark.asyncio
async def test_gateway_client_sends_tenant_and_service_auth(monkeypatch) -> None:
    host = None

    def capture(request: httpx.Request) -> httpx.Response:
        nonlocal host
        host = (request.headers.get("X-Tenant-ID"), request.headers.get("X-Service-Auth"))
        return httpx.Response(200, json={})

    monkeypatch.setenv("SERVICE_AUTH_SECRET", "fixed-service-secret")
    transport = httpx.MockTransport(capture)
    original = httpx.AsyncClient

    def _patched(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original(transport=transport, timeout=1.0)

    monkeypatch.setattr("httpx.AsyncClient", _patched)
    await Layer5Client(base_url="http://layer5", timeout=1.0).get_freshness_summary("t-abc")
    assert host == ("t-abc", "fixed-service-secret")


@pytest.mark.asyncio
async def test_gateway_client_raises_502_with_upstream_detail(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="validation failed")

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def _patched(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original(transport=transport, timeout=1.0)

    monkeypatch.setattr("httpx.AsyncClient", _patched)
    client = Layer5Client(base_url="http://layer5", timeout=1.0)

    with pytest.raises(HTTPException) as excinfo:
        await client.submit_truth("tenant-1", claim="c", claim_type="other", confidence=0.1)
    assert excinfo.value.status_code == 502
    assert excinfo.value.detail == "validation failed"


@pytest.mark.asyncio
async def test_gateway_client_raises_502_generic_when_no_body(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def _patched(*args, **kwargs):
        kwargs.pop("timeout", None)
        return original(transport=transport, timeout=1.0)

    monkeypatch.setattr("httpx.AsyncClient", _patched)
    client = Layer5Client(base_url="http://layer5", timeout=1.0)

    with pytest.raises(HTTPException) as excinfo:
        await client.sync_kg("tenant-1")
    assert excinfo.value.status_code == 502
    assert excinfo.value.detail == "Layer 5 request failed (500)"
