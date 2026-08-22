from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI, Request

from layer4_agents.integration.layer2_client import Layer2ExtractionClient

# TracingMiddleware lives in services/layer3-knowledge/src — importing it here
# requires layer3's internal bare imports to resolve without colliding with
# layer4's own `config` package.  Skip gracefully when not available.
try:
    from tracing.middleware import TracingMiddleware

    _LAYER3_TRACING_AVAILABLE = True
except (ImportError, Exception):
    TracingMiddleware = None  # type: ignore[assignment,misc]
    _LAYER3_TRACING_AVAILABLE = False

from value_fabric.shared.observability.trace_context import (
    CANONICAL_TRACE_HEADER,
    TRACE_HEADER_ALIASES,
)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _LAYER3_TRACING_AVAILABLE,
    reason="layer3 tracing.middleware not importable in layer4 test env (cross-service namespace collision)",
)
@pytest.mark.parametrize("legacy_header", TRACE_HEADER_ALIASES)
async def test_layer3_handler_reads_legacy_trace_headers_and_emits_canonical_only(legacy_header: str) -> None:
    app = FastAPI()
    app.add_middleware(TracingMiddleware)

    @app.get("/trace-check")
    async def trace_check(request: Request):
        return {"trace_id": request.state.trace_context.trace_id}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/trace-check",
            headers={legacy_header: "legacy-trace-001", "X-Span-Id": "span-001"},
        )

    assert response.status_code == 200
    assert response.json()["trace_id"] == "legacy-trace-001"
    assert response.headers.get(CANONICAL_TRACE_HEADER) == "legacy-trace-001"
    for alias in TRACE_HEADER_ALIASES:
        assert alias not in response.headers


@pytest.mark.asyncio
async def test_layer4_layer2_client_writes_canonical_trace_header_to_downstream_handler() -> None:
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"ok": True})

    client = Layer2ExtractionClient(base_url="http://layer2.test")
    client.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://layer2.test")

    try:
        result = await client.extract_operational_signals(
            prospect_data={"company": "Acme"},
            trace_id="canonical-trace-123",
        )
    finally:
        await client.close()

    assert result["ok"] is True
    assert captured["headers"].get(CANONICAL_TRACE_HEADER.lower()) == "canonical-trace-123"
    for alias in TRACE_HEADER_ALIASES:
        assert alias.lower() not in captured["headers"]
