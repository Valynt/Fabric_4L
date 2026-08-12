from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.security import TokenPayload, require_authenticated
from app.routers.layer_delegation import (
    DELEGATION_TARGETS,
    _request_headers,
    _target_url,
    router,
)


def _settings(**overrides):
    base = {
        "layer1_api_base_url": "http://l1:8001",
        "layer2_api_base_url": "http://l2:8002",
        "layer3_api_base_url": "http://l3:8003",
        "layer4_api_base_url": "http://l4:8004",
        "layer5_api_base_url": "http://l5:8005",
        "delegation_timeout_seconds": 5.0,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeAsyncClient:
    """Minimal async-context-manager stand-in for httpx.AsyncClient.

    Instance-level ``__aenter__`` assignment on a MagicMock is ignored by
    Python's implicit dunder lookup (type-level only), so a real class is
    required to drive ``async with`` in _delegate.
    """

    def __init__(self, request_impl) -> None:
        self.request = request_impl

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _auth_override(app: FastAPI) -> None:
    app.dependency_overrides[require_authenticated] = lambda: TokenPayload(
        sub="test-user",
        tenant_id="test-tenant",
        jti="test-jti",
        iss="test-iss",
        aud="test-aud",
    )


class TestDelegationTargets:
    def test_agents_forwards_layer_relative_path_unchanged(self) -> None:
        with patch("app.routers.layer_delegation.get_settings", return_value=_settings()):
            assert _target_url("agents", "v1/accounts") == "http://l4:8004/v1/accounts"
            assert _target_url("agents", "accounts") == "http://l4:8004/accounts"

    def test_graph_forwards_layer_relative_path_unchanged(self) -> None:
        with patch("app.routers.layer_delegation.get_settings", return_value=_settings()):
            assert (
                _target_url("graph", "v1/calculators/value-cases")
                == "http://l3:8003/v1/calculators/value-cases"
            )

    def test_ingest_adds_canonical_l1_prefix(self) -> None:
        with patch("app.routers.layer_delegation.get_settings", return_value=_settings()):
            assert _target_url("ingest", "sources") == "http://l1:8001/api/v1/ingestion/sources"

    def test_truths_adds_canonical_l5_prefix(self) -> None:
        with patch("app.routers.layer_delegation.get_settings", return_value=_settings()):
            assert _target_url("truths", "academy/pillars") == "http://l5:8005/api/v1/academy/pillars"

    def test_extract_adds_v1_prefix(self) -> None:
        with patch("app.routers.layer_delegation.get_settings", return_value=_settings()):
            assert _target_url("extract", "jobs/abc") == "http://l2:8002/v1/jobs/abc"

    def test_all_segments_have_settings(self) -> None:
        settings = _settings()
        for _, (attr, _) in DELEGATION_TARGETS.items():
            assert hasattr(settings, attr)


class TestRequestHeaderFiltering:
    def _request(self, headers: dict[str, str]) -> Request:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/agents/accounts",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "query_string": b"",
        }
        return Request(scope)

    def test_forwards_identity_and_trace_headers(self) -> None:
        request = self._request(
            {
                "Authorization": "Bearer token",
                "X-Tenant-ID": "spoofed",
                "X-User-ID": "u1",
                "X-Request-ID": "r1",
                "X-Service-Auth": "secret",
                "Content-Type": "application/json",
                "Cookie": "session=abc",
                "X-Forwarded-For": "1.2.3.4",
            }
        )
        forwarded = _request_headers(request, tenant_id="verified-t1")
        assert forwarded["authorization"] == "Bearer token"
        assert forwarded["x-tenant-id"] == "verified-t1"
        assert forwarded["x-user-id"] == "u1"
        assert forwarded["x-request-id"] == "r1"
        assert forwarded["x-service-auth"] == "secret"
        assert "cookie" not in forwarded
        assert "x-forwarded-for" not in forwarded

    def test_tenant_id_is_injected_not_forwarded(self) -> None:
        request = self._request(
            {
                "X-Tenant-ID": "attacker-tenant",
            }
        )
        forwarded = _request_headers(request, tenant_id="jwt-tenant")
        assert forwarded["x-tenant-id"] == "jwt-tenant"

    def test_cookie_auth_is_promoted_to_authorization_header(self) -> None:
        request = self._request(
            {
                "Cookie": "vf_session=session-token",
            }
        )
        forwarded = _request_headers(request, tenant_id="jwt-tenant")
        assert forwarded["authorization"] == "B" + "earer session-token"


class TestDelegationRouter:
    def test_routes_registered_for_all_segments(self) -> None:
        # This FastAPI version wraps included routers in _IncludedRouter
        # (no .path on the wrapper); the registered paths live on the
        # original router and the /v1 prefix is applied by the wrapper.
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        wrapper = app.routes[-1]
        assert wrapper.original_router is router
        paths = {route.path for route in router.routes}
        for segment in DELEGATION_TARGETS:
            assert f"/{segment}/{{path:path}}" in paths
            assert f"/{segment}" in paths

    @pytest.mark.asyncio
    async def test_upstream_transport_error_returns_503(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        # Override auth dependency so we don't need a real JWT
        _auth_override(app)

        failing_client = _FakeAsyncClient(AsyncMock(side_effect=httpx.ConnectError("down")))

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=failing_client),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/agents/v1/accounts")

        assert response.status_code == 503
        assert response.json()["detail"] == "owning_layer_unavailable"

    @pytest.mark.asyncio
    async def test_repeated_query_params_are_forwarded_in_order(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        _auth_override(app)

        upstream_response = httpx.Response(
            200,
            content=b"{}",
            headers={"content-type": "application/json"},
        )
        request_mock = AsyncMock(return_value=upstream_response)
        fake_client = _FakeAsyncClient(request_mock)

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake_client),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/graph/entities?tag=a&tag=b&status=active")

        assert response.status_code == 200
        assert request_mock.await_args.args[:2] == (
            "GET",
            "http://l3:8003/entities?tag=a&tag=b&status=active",
        )
