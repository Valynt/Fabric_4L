from __future__ import annotations

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.rate_limiting import RateLimitConfig, RateLimitScope
from value_fabric.shared.rate_limiting.http_middleware import RateLimitKeyStrategy, build_rate_limit_key


def test_tenant_scope_key_always_includes_tenant_id_when_disabled_in_strategy() -> None:
    key = build_rate_limit_key(
        request=None,  # type: ignore[arg-type]
        ctx=RequestContext(tenant_id="tenant-a"),
        config=RateLimitConfig(requests_per_minute=10, burst_size=2, scope=RateLimitScope.TENANT),
        endpoint_class="read",
        key_strategy=RateLimitKeyStrategy(include_tenant=False, include_caller=False, include_route_class=False),
    )

    assert key == "ratelimit:tenant:tenant-a"


def test_user_scope_key_always_includes_tenant_id_when_disabled_in_strategy() -> None:
    key = build_rate_limit_key(
        request=None,  # type: ignore[arg-type]
        ctx=RequestContext(tenant_id="tenant-a", user_id="user-1"),
        config=RateLimitConfig(requests_per_minute=10, burst_size=2, scope=RateLimitScope.USER),
        endpoint_class="read",
        key_strategy=RateLimitKeyStrategy(include_tenant=False, include_caller=True, include_route_class=False),
    )

    assert key == "ratelimit:user:tenant-a:user-1"
