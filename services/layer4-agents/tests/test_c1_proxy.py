from __future__ import annotations

"""Tests for the C1 streaming proxy route."""


from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We build a minimal FastAPI app that only includes the C1 router so that
# test setup does not require the full L4 application (DB, LangGraph, etc.).
from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import c1 as c1_route

C1Message = c1_route.C1Message
C1StreamRequest = c1_route.C1StreamRequest
router = c1_route.router

_app = FastAPI()
register_exception_handlers(_app)
_app.include_router(router, prefix="/v1")
_app.dependency_overrides[c1_route.require_authenticated] = lambda: RequestContext(
    tenant_id="tenant-c1-test",
    user_id="user-c1-test",
)


@pytest.fixture()
def client():
    return TestClient(_app)


# ---------------------------------------------------------------------------
# Pydantic model validation
# ---------------------------------------------------------------------------


class TestC1StreamRequest:
    def test_valid_request(self):
        req = C1StreamRequest(
            messages=[C1Message(role="user", content="hello")],
            business_case_id="bc-1",
        )
        assert len(req.messages) == 1
        assert req.business_case_data is None

    def test_rejects_empty_messages(self):
        with pytest.raises(ValueError):
            C1StreamRequest(messages=[], business_case_id="bc-1")

    def test_rejects_empty_business_case_id(self):
        with pytest.raises(ValueError):
            C1StreamRequest(
                messages=[C1Message(role="user", content="hello")],
                business_case_id="",
            )


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class TestStreamC1Endpoint:
    """Tests for POST /v1/c1/stream."""

    _VALID_BODY = {
        "messages": [{"role": "user", "content": "What if cost doubles?"}],
        "business_case_id": "bc-42",
        "business_case_data": {"total_value": 500000},
    }

    def test_returns_503_when_api_key_not_set(self, client: TestClient):
        """Without THESYS_API_KEY the endpoint should return 503."""
        with patch.dict("os.environ", {"THESYS_API_KEY": ""}, clear=False), patch("layer4_agents.services.thesys_provider.THESYS_API_KEY", ""):
            resp = client.post("/v1/c1/stream", json=self._VALID_BODY)
        assert resp.status_code == 503
        assert "not configured" in resp.json()["error"]["message"]

    def test_returns_422_on_invalid_body(self, client: TestClient):
        """Missing required fields should trigger validation error."""
        resp = client.post("/v1/c1/stream", json={"messages": []})
        assert resp.status_code == 422

    def test_streams_sse_from_thesys(self, client: TestClient):
        """Happy path: proxy streams SSE chunks from Thesys."""
        # Simulate Thesys returning two SSE lines
        sse_lines = [
            'data: {"type":"component","data":{"type":"MetricCard","props":{"label":"ROI","value":2.5}}}',
            'data: {"type":"done"}',
        ]

        mock_response = AsyncMock()
        mock_response.status_code = 200
        # aiter_lines must be a regular method returning an async iterator
        mock_response.aiter_lines = lambda: _async_iter(sse_lines)
        mock_response.aread = AsyncMock(return_value=b"")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client_instance = AsyncMock()
        mock_client_instance.stream = MagicMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("layer4_agents.services.thesys_provider.THESYS_API_KEY", "test-key"),
            patch("layer4_agents.services.thesys_provider.httpx.AsyncClient", return_value=mock_client_instance),
        ):
            resp = client.post("/v1/c1/stream", json=self._VALID_BODY)

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        # The body should contain the forwarded SSE lines plus a done sentinel
        body = resp.text
        assert "component" in body, "Expected 'component' in SSE stream"
        assert "done" in body, "Expected 'done' sentinel in SSE stream"

    def test_handles_thesys_error_status(self, client: TestClient):
        """Non-200 from Thesys should yield an error SSE chunk."""
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.aread = AsyncMock(return_value=b"Unauthorized")
        mock_response.aiter_lines = lambda: _async_iter([])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client_instance = AsyncMock()
        mock_client_instance.stream = MagicMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("layer4_agents.services.thesys_provider.THESYS_API_KEY", "test-key"),
            patch("layer4_agents.services.thesys_provider.httpx.AsyncClient", return_value=mock_client_instance),
        ):
            resp = client.post("/v1/c1/stream", json=self._VALID_BODY)

        assert resp.status_code == 200  # SSE always 200; error is in the stream
        assert "error" in resp.text

    def test_handles_connection_error(self, client: TestClient):
        """ConnectError from httpx should yield a friendly error event."""
        import httpx as _httpx

        mock_client_instance = AsyncMock()
        mock_client_instance.stream = MagicMock(side_effect=_httpx.ConnectError("fail"))
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("layer4_agents.services.thesys_provider.THESYS_API_KEY", "test-key"),
            patch("layer4_agents.services.thesys_provider.httpx.AsyncClient", return_value=mock_client_instance),
        ):
            resp = client.post("/v1/c1/stream", json=self._VALID_BODY)

        assert resp.status_code == 200
        assert "error" in resp.text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _async_iter(items):
    """Convert a list into an async iterator."""
    for item in items:
        yield item
