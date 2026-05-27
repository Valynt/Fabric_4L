from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Request

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.rate_limiting import RateLimitConfig, RateLimitScope


DEFAULT_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/health",
    "/metrics",
    "/internal/health",
    "/internal/metrics",
)


@dataclass(frozen=True)
class RateLimitKeyStrategy:
    include_tenant: bool = True
    include_caller: bool = True
    include_route_class: bool = True

    @classmethod
    def from_env(cls) -> "RateLimitKeyStrategy":
        return cls(
            include_tenant=_read_bool("RATE_LIMIT_KEY_INCLUDE_TENANT", True),
            include_caller=_read_bool("RATE_LIMIT_KEY_INCLUDE_CALLER", True),
            include_route_class=_read_bool("RATE_LIMIT_KEY_INCLUDE_ROUTE", True),
        )


@dataclass(frozen=True)
class SharedRateLimitMiddlewareConfig:
    exempt_prefixes: tuple[str, ...]
    key_strategy: RateLimitKeyStrategy

    @classmethod
    def from_env(cls) -> "SharedRateLimitMiddlewareConfig":
        raw = os.getenv("RATE_LIMIT_EXEMPT_PATH_PREFIXES")
        prefixes = tuple(p.strip() for p in raw.split(",") if p.strip()) if raw else DEFAULT_EXEMPT_PREFIXES
        return cls(exempt_prefixes=prefixes, key_strategy=RateLimitKeyStrategy.from_env())


def should_skip_rate_limit(path: str, *, config: SharedRateLimitMiddlewareConfig) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in config.exempt_prefixes)


def build_rate_limit_key(
    *,
    ctx: RequestContext,
    config: RateLimitConfig,
    endpoint_class: str,
    key_strategy: RateLimitKeyStrategy,
) -> str:
    parts = ["ratelimit", config.scope.value]
    # Tenant dimension is non-optional for tenant- and user-scoped limits.
    # This prevents cross-tenant key collisions when env flags are misconfigured.
    if config.scope in {RateLimitScope.TENANT, RateLimitScope.USER}:
        parts.append(str(ctx.tenant_id))

    if key_strategy.include_caller:
        if config.scope == RateLimitScope.API_KEY and ctx.api_key_id:
            parts.append(str(ctx.api_key_id))
        elif config.scope == RateLimitScope.USER and ctx.user_id:
            parts.append(str(ctx.user_id))

    if key_strategy.include_route_class:
        parts.append(endpoint_class)
    return ":".join(parts)


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
