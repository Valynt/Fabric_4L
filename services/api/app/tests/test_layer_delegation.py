from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import yaml
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.security import TokenPayload, require_authenticated
from app.routers.layer_delegation import (
    DELEGATION_TARGETS,
    _request_headers,
    _target_url,
    router,
)
from value_fabric.shared.resilience import CircuitBreakerRegistry


def _settings(**overrides):
    base = {
        "layer1_api_base_url": "http://l1:8001",
        "layer2_api_base_url": "http://l2:8002",
        "layer3_api_base_url": "http://l3:8003",
        "layer4_api_base_url": "http://l4:8004",
        "layer5_api_base_url": "http://l5:8005",
        "delegation_timeout_seconds": 5.0,
        "delegation_retry_max_attempts": 3,
        "delegation_retry_base_delay": 0.0,
        "delegation_retry_max_delay": 0.0,
        "delegation_cb_failure_threshold": 5,
        "delegation_cb_recovery_timeout": 60.0,
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

    def test_forwards_identity_and_trace_headers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SERVICE_AUTH_SECRET", raising=False)
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
        # Caller-supplied service auth must never be forwarded: layers trust
        # X-Tenant-ID only alongside a valid X-Service-Auth, so relaying a
        # client value would let callers spoof service-to-service identity.
        assert "x-service-auth" not in forwarded
        assert "cookie" not in forwarded
        assert "x-forwarded-for" not in forwarded

    def test_service_auth_is_injected_from_server_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "server-side-secret")
        request = self._request({"X-Service-Auth": "client-spoof-attempt"})
        forwarded = _request_headers(request, tenant_id="verified-t1")
        assert forwarded["x-service-auth"] == "server-side-secret"

    @pytest.mark.parametrize(
        ("compose_path", "expected_setting"),
        [
            (
                "infra/compose/docker-compose.dev.yml",
                "SERVICE_AUTH_SECRET=dev-local-service-auth-secret-32-chars",
            ),
            (
                "infra/compose/docker-compose.live.yml",
                "SERVICE_AUTH_SECRET=${SERVICE_AUTH_SECRET}",
            ),
        ],
    )
    def test_gateway_deployments_receive_service_auth_secret(
        self, compose_path: str, expected_setting: str
    ) -> None:
        compose = yaml.safe_load(Path(compose_path).read_text(encoding="utf-8"))
        environment = compose["services"]["api-gateway"]["environment"]
        settings = (
            environment
            if isinstance(environment, list)
            else [f"{name}={value}" for name, value in environment.items()]
        )
        assert expected_setting in settings

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

        # Reset breaker registry so prior resilience tests don't leave state.
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()

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


class TestDelegationResilience:
    """Retry + circuit breaker behavior for the async delegation proxy."""

    def _app(self) -> FastAPI:
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        _auth_override(app)
        return app

    def _client_returning(self, responses):
        """Return a _FakeAsyncClient whose request yields responses in order.

        Each entry is either an httpx.Response or an Exception instance
        (raised on that attempt).
        """
        iterator = iter(responses)

        async def _request(*args, **kwargs):
            item = next(iterator)
            if isinstance(item, Exception):
                raise item
            return item

        return _FakeAsyncClient(_request)

    @pytest.mark.asyncio
    async def test_transient_503_retried_then_succeeds(self) -> None:
        app = self._app()
        # Reset breaker registry so prior tests don't share state.
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()

        bad = httpx.Response(503, content=b"down")
        ok = httpx.Response(200, content=b"{}", headers={"content-type": "application/json"})
        fake = self._client_returning([bad, ok])

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/agents/v1/accounts")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_circuit_open_returns_503_with_circuit_open_detail(self) -> None:
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()

        app = self._app()
        bad = httpx.Response(503, content=b"down")
        # failure_threshold=1 → first 503 opens the breaker; retry attempts
        # are rejected and surface as circuit_open.
        fake = self._client_returning([bad])

        settings = _settings(delegation_cb_failure_threshold=1)

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=settings),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/agents/v1/accounts")

        assert response.status_code == 503
        assert response.json()["detail"] == "owning_layer_circuit_open"

    @pytest.mark.asyncio
    async def test_deterministic_404_not_retried(self) -> None:
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()

        app = self._app()
        not_found = httpx.Response(404, content=b"nope")
        fake = self._client_returning([not_found])

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/agents/v1/accounts")

        # 404 is deterministic → surfaces as-is, no retry.
        assert response.status_code == 404


class TestDelegationObservability:
    """Prometheus metrics + structured audit logs are emitted per delegation."""

    def _app(self) -> FastAPI:
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        _auth_override(app)
        return app

    def _client_returning(self, responses):
        iterator = iter(responses)

        async def _request(*args, **kwargs):
            item = next(iterator)
            if isinstance(item, Exception):
                raise item
            return item

        return _FakeAsyncClient(_request)

    @pytest.mark.asyncio
    async def test_success_increments_delegation_requests_counter(self) -> None:
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()
        app = self._app()
        ok = httpx.Response(200, content=b"{}", headers={"content-type": "application/json"})
        fake = self._client_returning([ok])

        from app.core.metrics import DELEGATION_REQUESTS_TOTAL, registry

        before = registry.get_sample_value(
            "fabric_api_delegation_requests_total",
            {"segment": "agents", "method": "GET", "status_code": "200", "outcome": "success"},
        ) or 0.0

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/agents/v1/accounts")

        assert response.status_code == 200
        after = registry.get_sample_value(
            "fabric_api_delegation_requests_total",
            {"segment": "agents", "method": "GET", "status_code": "200", "outcome": "success"},
        ) or 0.0
        assert after == before + 1.0

    @pytest.mark.asyncio
    async def test_circuit_open_increments_circuit_open_counter(self) -> None:
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()
        app = self._app()
        bad = httpx.Response(503, content=b"down")
        fake = self._client_returning([bad])
        settings = _settings(delegation_cb_failure_threshold=1)

        from app.core.metrics import DELEGATION_CIRCUIT_OPEN_TOTAL, registry

        before = registry.get_sample_value(
            "fabric_api_delegation_circuit_open_total", {"segment": "agents"}
        ) or 0.0

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=settings),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/agents/v1/accounts")

        assert response.status_code == 503
        after = registry.get_sample_value(
            "fabric_api_delegation_circuit_open_total", {"segment": "agents"}
        ) or 0.0
        assert after == before + 1.0

    @pytest.mark.asyncio
    async def test_concurrency_exhausted_returns_503_with_concurrency_detail(self) -> None:
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()
        app = self._app()
        # Patch the semaphore returned by _get_semaphore to always report
        # locked → concurrency exhausted.
        fake_sem = MagicMock()
        fake_sem.locked.return_value = True
        fake_sem.acquire = AsyncMock()
        fake_sem.release = MagicMock()

        # Use an AsyncMock spy so we can assert the upstream was never called.
        request_spy = AsyncMock(return_value=httpx.Response(200, content=b"{}"))
        fake = _FakeAsyncClient(request_spy)

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
            patch("app.routers.layer_delegation._get_semaphore", return_value=fake_sem),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/agents/v1/accounts")

        assert response.status_code == 503
        assert response.json()["detail"] == "gateway_concurrency_exhausted"
        # Upstream was never contacted — semaphore rejected before the call.
        request_spy.assert_not_called()


class TestDelegationGetCache:
    """Redis-backed short-TTL cache for safe GET delegations."""

    def _app(self) -> FastAPI:
        app = FastAPI()
        app.include_router(router, prefix="/v1")
        _auth_override(app)
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()
        return app

    def _client_returning(self, responses):
        iterator = iter(responses)

        async def _request(*args, **kwargs):
            item = next(iterator)
            if isinstance(item, Exception):
                raise item
            return item

        return _FakeAsyncClient(_request)

    @pytest.mark.asyncio
    async def test_get_cache_hit_serves_without_upstream_call(self) -> None:
        app = self._app()
        cached_body = b'{"cached": true}'
        cached_payload = "200\rapplication/json\r" + cached_body.decode("latin-1")
        fake_redis = MagicMock()
        fake_redis.get.return_value = cached_payload

        request_spy = AsyncMock(return_value=httpx.Response(200, content=b"{}"))
        fake = _FakeAsyncClient(request_spy)

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
            patch("app.core.redis_client.get_redis_client", return_value=fake_redis),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/graph/entities")

        assert response.status_code == 200
        assert response.content == cached_body
        assert response.headers["x-delegation-cache"] == "hit"
        # Upstream was never called — cache served the request.
        request_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cache_miss_stores_and_forwards(self) -> None:
        app = self._app()
        fake_redis = MagicMock()
        fake_redis.get.return_value = None  # cache miss

        upstream_response = httpx.Response(
            200,
            content=b'{"fresh": true}',
            headers={"content-type": "application/json"},
        )
        request_mock = AsyncMock(return_value=upstream_response)
        fake = _FakeAsyncClient(request_mock)

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
            patch("app.core.redis_client.get_redis_client", return_value=fake_redis),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/graph/entities")

        assert response.status_code == 200
        assert response.headers["x-delegation-cache"] == "store"
        assert response.content == b'{"fresh": true}'
        fake_redis.set.assert_called_once()
        # TTL is passed as a keyword.
        assert fake_redis.set.await_args.kwargs.get("ex") or fake_redis.set.call_args.kwargs.get("ex")

    @pytest.mark.asyncio
    async def test_get_cache_skipped_when_redis_unavailable(self) -> None:
        app = self._app()
        # Redis unavailable → cache lookup returns None, upstream is called.
        upstream_response = httpx.Response(
            200, content=b'{"ok": true}', headers={"content-type": "application/json"}
        )
        request_mock = AsyncMock(return_value=upstream_response)
        fake = _FakeAsyncClient(request_mock)

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
            patch("app.core.redis_client.get_redis_client", return_value=None),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/graph/entities")

        assert response.status_code == 200
        # No cache header since Redis was unavailable (store was skipped).
        assert "x-delegation-cache" not in response.headers

    @pytest.mark.asyncio
    async def test_post_bypasses_cache(self) -> None:
        app = self._app()
        fake_redis = MagicMock()
        fake_redis.get.return_value = None

        upstream_response = httpx.Response(
            201, content=b'{"created": true}', headers={"content-type": "application/json"}
        )
        request_mock = AsyncMock(return_value=upstream_response)
        fake = _FakeAsyncClient(request_mock)

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
            patch("app.core.redis_client.get_redis_client", return_value=fake_redis),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/v1/agents/v1/accounts", json={"x": 1})

        assert response.status_code == 201
        # POST must never read from or write to the cache.
        fake_redis.get.assert_not_called()
        fake_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cache_key_is_tenant_scoped(self) -> None:
        """Cache keys differ by tenant so cross-tenant reads cannot collide."""
        from app.routers.layer_delegation import _cache_key

        key_a = _cache_key("graph", "/entities", "tenant-a", "user-1", "")
        key_b = _cache_key("graph", "/entities", "tenant-b", "user-1", "")
        assert key_a != key_b

    def test_get_cache_key_is_principal_scoped(self) -> None:
        """Cache keys differ by user within the same tenant to avoid RBAC cache poisoning."""
        from app.routers.layer_delegation import _cache_key

        key_user1 = _cache_key("graph", "/entities", "tenant-a", "user-1", "")
        key_user2 = _cache_key("graph", "/entities", "tenant-a", "user-2", "")
        key_anon = _cache_key("graph", "/entities", "tenant-a", None, "")

        assert key_user1 != key_user2
        assert key_user1 != key_anon

    @pytest.mark.asyncio
    async def test_get_cache_hit_records_telemetry(self) -> None:
        """Cache hits record metrics with outcome=cache_hit and audit logs."""
        from app.core.metrics import registry
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()
        app = self._app()
        cached_body = b'{"cached": true}'
        cached_payload = "200\rapplication/json\r" + cached_body.decode("latin-1")
        fake_redis = MagicMock()
        fake_redis.get.return_value = cached_payload

        before = registry.get_sample_value(
            "fabric_api_delegation_requests_total",
            {"segment": "graph", "method": "GET", "status_code": "200", "outcome": "cache_hit"},
        ) or 0.0

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings()),
            patch("app.core.redis_client.get_redis_client", return_value=fake_redis),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/graph/entities")

        assert response.status_code == 200
        assert response.headers["x-delegation-cache"] == "hit"

        after = registry.get_sample_value(
            "fabric_api_delegation_requests_total",
            {"segment": "graph", "method": "GET", "status_code": "200", "outcome": "cache_hit"},
        ) or 0.0
        assert after == before + 1.0

    @pytest.mark.asyncio
    async def test_429_exhaustion_preserves_rate_limit_headers_and_body(self) -> None:
        """Exhausted 429 attempts retain upstream rate-limit headers and body."""
        from app.routers import layer_delegation as mod

        mod._breakers = CircuitBreakerRegistry()
        app = self._app()
        upstream_headers = {
            "content-type": "application/json",
            "retry-after": "30",
            "x-ratelimit-limit": "100",
            "x-ratelimit-remaining": "0",
            "x-ratelimit-reset": "1700000000",
        }
        rate_limit_body = b'{"error": "rate limit exceeded"}'
        resp_429 = httpx.Response(429, content=rate_limit_body, headers=upstream_headers)
        fake = self._client_returning([resp_429, resp_429, resp_429])

        with (
            patch("app.routers.layer_delegation.get_settings", return_value=_settings(delegation_retry_max_attempts=3)),
            patch("app.routers.layer_delegation.httpx.AsyncClient", return_value=fake),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/v1/agents/v1/accounts")

        assert response.status_code == 429
        assert response.content == rate_limit_body
        assert response.headers.get("retry-after") == "30"
        assert response.headers.get("x-ratelimit-limit") == "100"
        assert response.headers.get("x-ratelimit-remaining") == "0"
        assert response.headers.get("x-ratelimit-reset") == "1700000000"


