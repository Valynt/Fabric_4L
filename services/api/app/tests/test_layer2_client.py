"""Regression tests for the gateway Layer2Client adapter.

These prove the adapter delegates to the canonical shared transport with the
correct ``ExtractRequest`` payload and the corrected status path.  A 4xx/5xx
upstream response must surface as the gateway's ``HTTPException(502)``.
"""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi import HTTPException

from app.clients.layer2_client import Layer2Client


class _Recorder:
    """Captures every outbound request for assertion."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []


def _handler(capture: _Recorder, *, extract_status: int = 200) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        capture.requests.append(request)
        if request.url.path == "/v1/extract":
            if extract_status >= 400:
                return httpx.Response(extract_status, text="upstream broke")
            return httpx.Response(
                200,
                json={"extraction_job_id": "job-1", "status": "queued", "message": "ok"},
            )
        if request.url.path == "/v1/extract/status/job-1":
            return httpx.Response(
                200,
                json={
                    "job_id": "job-1",
                    "overall_status": "COMPLETED",
                    "extraction_status": "COMPLETED",
                    "ingestion_status": "COMPLETED",
                    "entities_extracted": 5,
                    "relationships_extracted": 3,
                    "completed_at": "2026-01-01T00:00:00Z",
                },
            )
        return httpx.Response(404)

    return handler


@pytest.fixture
def patched_async_client(monkeypatch):
    """Route httpx.AsyncClient to a MockTransport driven by a captured handler."""

    def _patch(handler) -> None:
        original_async_client = httpx.AsyncClient

        def _patched_async_client(*args, **kwargs):
            kwargs.pop("timeout", None)
            transport = httpx.MockTransport(handler)
            return original_async_client(transport=transport, timeout=1.0)

        monkeypatch.setattr("httpx.AsyncClient", _patched_async_client)

    return _patch


@pytest.fixture
def capture() -> _Recorder:
    return _Recorder()


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content.decode("utf-8"))


@pytest.mark.asyncio
async def test_extract_sends_canonical_extract_request(capture, patched_async_client) -> None:
    patched_async_client(_handler(capture))
    client = Layer2Client(base_url="http://layer2", timeout=1.0)

    result = await client.extract(
        tenant_id="tenant-1",
        content_id="cid-1",
        source_url="https://example.com/doc",
        markdown_content="# Heading\nBody text",
        extraction_config={"entity_types": ["person"]},
    )

    assert result["extraction_job_id"] == "job-1"
    request = capture.requests[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/extract"
    assert request.headers.get("X-Tenant-ID") == "tenant-1"
    assert _body(request) == {
        "content_id": "cid-1",
        "source_url": "https://example.com/doc",
        "markdown_content": "# Heading\nBody text",
        "extraction_config": {"entity_types": ["person"]},
    }


@pytest.mark.asyncio
async def test_extract_omits_config_when_absent(capture, patched_async_client) -> None:
    patched_async_client(_handler(capture))
    client = Layer2Client(base_url="http://layer2", timeout=1.0)

    await client.extract(
        tenant_id="tenant-1",
        content_id="cid-1",
        source_url="https://example.com",
        markdown_content="body",
    )

    assert _body(capture.requests[0]) == {
        "content_id": "cid-1",
        "source_url": "https://example.com",
        "markdown_content": "body",
    }


@pytest.mark.asyncio
async def test_get_job_status_uses_correct_path(capture, patched_async_client) -> None:
    patched_async_client(_handler(capture))
    client = Layer2Client(base_url="http://layer2", timeout=1.0)

    result = await client.get_job_status(tenant_id="tenant-1", job_id="job-1")

    request = capture.requests[0]
    assert request.method == "GET"
    # Corrected path: /v1/extract/status/{job_id} (not the legacy /v1/extractions/{job_id}).
    assert request.url.path == "/v1/extract/status/job-1"
    assert result["overall_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_upstream_4xx_raises_gateway_502(capture, patched_async_client) -> None:
    patched_async_client(_handler(capture, extract_status=500))
    client = Layer2Client(base_url="http://layer2", timeout=1.0)

    with pytest.raises(HTTPException) as excinfo:
        await client.extract(
            tenant_id="tenant-1",
            content_id="cid-1",
            source_url="https://example.com",
            markdown_content="body",
        )

    assert excinfo.value.status_code == 502
    assert "upstream broke" in str(excinfo.value.detail)
