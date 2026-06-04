"""Authentication endpoint rate-limit regression tests."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from layer4_agents.tenants.api.routes import oidc
from value_fabric.shared.identity.middleware import GovernanceMiddleware
from value_fabric.shared.identity.rate_limiter import RateLimitResult
from value_fabric.shared.identity.rate_limiting import RateLimitConfig, RateLimitScope


def _request(path: str = "/auth/oidc/acme/login", host: str = "203.0.113.20") -> SimpleNamespace:
    return SimpleNamespace(
        url=SimpleNamespace(path=path),
        method="GET",
        client=SimpleNamespace(host=host),
        state=SimpleNamespace(),
    )


def test_oidc_preauth_rate_limit_fails_closed_after_repeated_login_attempts() -> None:
    oidc._auth_preauth_buckets.clear()
    request = _request(host="203.0.113.21")

    for _ in range(oidc.AUTH_PREAUTH_MAX_ATTEMPTS):
        oidc._check_preauth_rate_limit(request, "login", "tenant-a")

    with pytest.raises(Exception) as exc:
        oidc._check_preauth_rate_limit(request, "login", "tenant-a")

    assert getattr(exc.value, "status_code", None) == 429
    assert getattr(exc.value, "headers", {}).get("Retry-After")
    assert getattr(exc.value, "headers", {}).get("X-RateLimit-Policy") == "oidc_preauth"


def test_oidc_callback_and_login_have_separate_rate_limit_buckets() -> None:
    oidc._auth_preauth_buckets.clear()
    request = _request(host="203.0.113.22")

    for _ in range(oidc.AUTH_PREAUTH_MAX_ATTEMPTS):
        oidc._check_preauth_rate_limit(request, "login", "tenant-a")

    oidc._check_preauth_rate_limit(request, "callback", "state-a")

    with pytest.raises(Exception) as exc:
        oidc._check_preauth_rate_limit(request, "login", "tenant-a")
    assert getattr(exc.value, "status_code", None) == 429


def test_oidc_preauth_rate_limit_uses_socket_peer_not_forwarded_headers() -> None:
    oidc._auth_preauth_buckets.clear()
    request = SimpleNamespace(
        url=SimpleNamespace(path="/auth/oidc/acme/login"),
        method="GET",
        client=SimpleNamespace(host="198.51.100.23"),
        headers={"X-Forwarded-For": "10.0.0.1"},
        state=SimpleNamespace(),
    )

    oidc._check_preauth_rate_limit(request, "login", "tenant-a")

    assert any(key.startswith("auth:login:198.51.100.23:tenant-a") for key in oidc._auth_preauth_buckets)
    assert not any("10.0.0.1" in key for key in oidc._auth_preauth_buckets)


def test_governance_middleware_classifies_auth_endpoints_as_auth_scope() -> None:
    middleware = GovernanceMiddleware(app=SimpleNamespace(), rate_limiter=None)

    assert middleware._classify_endpoint(_request("/auth/oidc/acme/login")) == "auth"
    assert middleware._classify_endpoint(_request("/auth/oidc/callback")) == "auth"


class _Limiter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, RateLimitConfig]] = []

    async def check(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        self.calls.append((key, config))
        return RateLimitResult(allowed=False, remaining=0, reset_at=123.0, retry_after=60)


@pytest.mark.asyncio
async def test_authenticated_auth_scope_rate_limit_key_uses_tenant_and_user_dimension() -> None:
    limiter = _Limiter()
    middleware = GovernanceMiddleware(app=SimpleNamespace(), rate_limiter=limiter)
    tenant_id = uuid4()
    user_id = uuid4()
    ctx = SimpleNamespace(
        tenant_id=tenant_id,
        user_id=user_id,
        api_key_id=None,
        roles=["analyst"],
        source="jwt",
        has_any_role=lambda *_roles: False,
    )
    request = _request("/auth/oidc/refresh")
    config = RateLimitConfig(requests_per_minute=2, burst_size=1, scope=RateLimitScope.USER)
    request.state.rate_limit_config = config
    request.state.rate_limit_policy = "test"

    key = middleware._build_rate_limit_key(request, ctx, config)

    assert key == f"ratelimit:user:{tenant_id}:{user_id}:auth"
