"""Reusable FastAPI application assembly helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ..error_handling.handlers import register_exception_handlers

from .health import (
    HealthCheckProbe,
    ProbeResult,
    aggregate_probes,
    build_readiness_payload,
)
from .logging import StructuredLoggingConfig, configure_structlog
from .middleware import (
    CorsPolicy,
    add_cors_middleware,
    add_idempotency_middleware,
    add_rate_limit_middleware,
    add_request_id_middleware,
    add_tenant_enforcement_middleware,
)


class EnforcementMode(StrEnum):
    """Rollout mode for security and governance controls."""

    OFF = "off"
    AUDIT = "audit"
    ENFORCE = "enforce"


class ExceptionHandlerRegistrationMode(StrEnum):
    """Exception handler registration strategies for shared app assembly."""

    DEFAULT = "default"
    SKIP = "skip"


@dataclass(frozen=True)
class EnforcementControlConfig:
    """Control-level rollout configuration for a single enforcement concern."""

    mode: EnforcementMode = EnforcementMode.AUDIT


@dataclass(frozen=True)
class HealthChecksConfig:
    """Health/readiness endpoint behavior configuration."""

    mode: EnforcementMode = EnforcementMode.AUDIT
    route_opt_out_paths: frozenset[str] = field(
        default_factory=lambda: frozenset({"/health", "/health/detailed", "/ready", "/readiness"})
    )


@dataclass(frozen=True)
class FrameworkRateLimitConfig:
    """Framework-level rate limit configuration.

    The factory is deferred so the shared framework does not import Redis at
    module load. When ``mode != OFF`` and ``rate_limiter_factory`` is provided,
    :func:`create_fabric_app` installs the rate-limit middleware.
    """

    mode: EnforcementMode = EnforcementMode.AUDIT
    rate_limiter_factory: Callable[[], Any] | None = None
    exempt_paths: tuple[str, ...] = (
        "/health",
        "/ready",
        "/metrics",
        "/docs",
        "/openapi.json",
    )


@dataclass(frozen=True)
class FrameworkIdempotencyConfig:
    """Framework-level idempotency configuration.

    ``service_factory`` should return a configured ``IdempotencyService`` (or
    compatible object) when called. Idempotency is applied only for the listed
    methods.
    """

    mode: EnforcementMode = EnforcementMode.AUDIT
    service_factory: Callable[[], Any] | None = None
    methods: frozenset[str] = field(
        default_factory=lambda: frozenset({"POST", "PUT", "PATCH", "DELETE"})
    )
    header_name: str = "Idempotency-Key"


@dataclass(frozen=True)
class EnforcementRolloutConfig:
    """Top-level progressive enforcement configuration attached to app.state."""

    tenant_enforcement: EnforcementControlConfig = field(default_factory=EnforcementControlConfig)
    rate_limiting: EnforcementControlConfig = field(default_factory=EnforcementControlConfig)
    idempotency: EnforcementControlConfig = field(default_factory=EnforcementControlConfig)
    health_checks: HealthChecksConfig = field(default_factory=HealthChecksConfig)


@dataclass
class EnforcementCounters:
    """Structured counters for rollout observability."""

    blocked_total: int = 0
    bypass_total: int = 0
    false_positive_candidate_total: int = 0


def mark_route_enforcement_opt_out(
    handler: Callable[..., Any],
    *,
    reason: str,
) -> Callable[..., Any]:
    """Mark a route handler as enforcement-opt-out for safe internal/public routes."""

    setattr(handler, "_vf_enforcement_opt_out", True)
    setattr(handler, "_vf_enforcement_opt_out_reason", reason)
    return handler


def _is_route_opted_out(path: str, config: EnforcementRolloutConfig) -> bool:
    return path in config.health_checks.route_opt_out_paths


def record_enforcement_decision(
    app: FastAPI,
    *,
    control: str,
    violation: str,
    route: str,
    tenant_id: str | None,
    actor_id: str | None,
    logger: Any | None = None,
) -> bool:
    """Apply rollout semantics and emit structured audit context.

    Returns ``True`` when request processing should continue, ``False`` when the
    caller should block the request in enforce mode.
    """

    config: EnforcementRolloutConfig = getattr(app.state, "enforcement_rollout", EnforcementRolloutConfig())
    counters: EnforcementCounters = getattr(app.state, "enforcement_counters", EnforcementCounters())
    app.state.enforcement_counters = counters

    if _is_route_opted_out(route, config):
        counters.bypass_total += 1
        if logger is not None:
            logger.info(
                "enforcement.opt_out",
                extra={
                    "control": control,
                    "route": route,
                    "tenant_id": tenant_id,
                    "actor_id": actor_id,
                    "violation": violation,
                    "mode": "bypass",
                },
            )
        return True

    mode = getattr(config, control, EnforcementControlConfig()).mode
    if mode == EnforcementMode.OFF:
        counters.bypass_total += 1
        return True

    if mode == EnforcementMode.AUDIT:
        counters.false_positive_candidate_total += 1
        if logger is not None:
            logger.warning(
                "enforcement.audit_violation",
                extra={
                    "control": control,
                    "route": route,
                    "tenant_id": tenant_id,
                    "actor_id": actor_id,
                    "violation": violation,
                    "mode": mode.value,
                },
            )
        return True

    counters.blocked_total += 1
    if logger is not None:
        logger.warning(
            "enforcement.blocked",
            extra={
                "control": control,
                "route": route,
                "tenant_id": tenant_id,
                "actor_id": actor_id,
                "violation": violation,
                "mode": mode.value,
            },
        )
    return False


def init_telemetry(service_name: str, *, endpoint: str | None = None) -> Any | None:
    """Install process tracing via the shared observability platform client."""
    from value_fabric.shared.observability.platform import configure_platform

    return configure_platform(service_name, endpoint=endpoint).provider


def instrument_fastapi_app(app: FastAPI, *, enabled: bool) -> bool:
    from value_fabric.shared.observability.platform import (
        instrument_fastapi_app as instrument_platform_app,
    )

    return instrument_platform_app(app, enabled=enabled)


def build_health_response(
    *,
    service_name: str,
    status: str = "ok",
    version: str | None = None,
    timestamp: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "status": status,
        "service": service_name,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }
    if version is not None:
        response["version"] = version
    response.update(extra)
    return response


def register_health_endpoint(
    app: FastAPI,
    *,
    service_name: str,
    path: str = "/health",
    include_in_schema: bool = True,
    handler: Callable[..., Any] | None = None,
) -> None:
    if handler is None:

        async def default_handler() -> dict[str, Any]:
            return build_health_response(service_name=service_name)

        route_handler = default_handler
    else:
        route_handler = handler

    mark_route_enforcement_opt_out(route_handler, reason="health_or_readiness")

    app.add_api_route(
        path,
        route_handler,
        methods=["GET"],
        include_in_schema=include_in_schema,
        tags=["health"],
    )

    # Alias /health/live for Kubernetes livenessProbe compatibility
    if path == "/health":
        app.add_api_route(
            "/health/live",
            route_handler,
            methods=["GET"],
            include_in_schema=include_in_schema,
            tags=["health"],
        )


def register_readiness_endpoint(
    app: FastAPI,
    *,
    service_name: str,
    probes: list[HealthCheckProbe],
    path: str = "/ready",
    include_in_schema: bool = True,
    version: str | None = None,
    timeout_seconds: float = 2.0,
    cache_ttl_seconds: float = 5.0,
) -> None:
    """Register a readiness endpoint that fans out to pluggable probes.

    Results are cached for ``cache_ttl_seconds`` to protect downstream
    dependencies from synthetic load by aggressive orchestrators.
    """

    state: dict[str, Any] = {"expires_at": 0.0, "payload": None, "healthy": False}
    _lock = asyncio.Lock()

    async def readiness_handler() -> JSONResponse:
        import time

        now = time.monotonic()
        async with _lock:
            if state["payload"] is not None and now < state["expires_at"]:
                payload = state["payload"]
                healthy = state["healthy"]
            else:
                healthy, results = await aggregate_probes(probes, timeout_seconds=timeout_seconds)
                payload = build_readiness_payload(
                    service_name=service_name,
                    healthy=healthy,
                    probe_results=results,
                    version=version,
                )
                state["payload"] = payload
                state["healthy"] = healthy
                state["expires_at"] = now + cache_ttl_seconds

        return JSONResponse(
            status_code=200 if healthy else 503,
            content=payload,
        )

    mark_route_enforcement_opt_out(readiness_handler, reason="health_or_readiness")
    app.add_api_route(
        path,
        readiness_handler,
        methods=["GET"],
        include_in_schema=include_in_schema,
        tags=["health"],
    )


def install_metrics_middleware(
    app: FastAPI,
    *,
    metrics: Any | None,
    middleware_factory: Callable[[Any], Any],
    logger: Any | None = None,
) -> Any | None:
    """Attach a service metrics instance and install its HTTP middleware once."""

    if metrics is None:
        return None

    app.state.metrics = metrics
    if getattr(app.state, "_metrics_middleware_installed", False):
        return metrics

    app.middleware("http")(middleware_factory(metrics))
    app.state._metrics_middleware_installed = True
    if logger is not None:
        logger.info("Metrics middleware installed")

    return metrics


def create_fabric_app(
    *,
    service_name: str,
    title: str,
    version: str,
    description: str,
    lifespan: Callable[..., Any] | None = None,
    cors_policy: CorsPolicy | dict[str, Any] | None = None,
    register_default_exception_handlers: bool = True,
    exception_handler_registration_mode: ExceptionHandlerRegistrationMode = ExceptionHandlerRegistrationMode.DEFAULT,
    include_request_id_middleware: bool = True,
    pre_core_middleware_hook: Callable[[FastAPI], None] | None = None,
    post_core_middleware_hook: Callable[[FastAPI], None] | None = None,
    health_readiness_augmentation_hook: Callable[[FastAPI], None] | None = None,
    telemetry_service_name: str | None = None,
    instrument_telemetry: bool = False,
    enforcement_rollout: EnforcementRolloutConfig | None = None,
    rate_limit: FrameworkRateLimitConfig | None = None,
    idempotency: FrameworkIdempotencyConfig | None = None,
    structured_logging: StructuredLoggingConfig | None = None,
    health_probes: list[HealthCheckProbe] | None = None,
    readiness_path: str = "/ready",
    enforce_tenant_context: bool = True,
    audit_worker_db_factory: Callable | None = None,
    **fastapi_kwargs: Any,
) -> FastAPI:
    """Create a FastAPI application with Value Fabric defaults.

    This factory centralizes the common bootstrap concerns that are repeated
    across service entrypoints without constraining service-specific startup
    dependencies or router composition.

    Extension hooks are inert by default:
    - Middleware hooks run only when explicitly provided by a service.
    - Exception handler mode defaults to current shared behavior.
    - Health/readiness augmentation runs only when explicitly provided.

    Service-owned lifecycle behavior remains authoritative: this factory must
    not open/close DB sessions automatically, and must not own DB engine/session
    lifecycle. Session lifecycle remains in each service's startup/shutdown and
    dependency wiring. Any future shared DB helper must be explicit opt-in and
    validated per service before adoption.
    """

    app = FastAPI(
        title=title,
        version=version,
        description=description,
        lifespan=lifespan,
        **fastapi_kwargs,
    )
    app.state.service_name = service_name
    app.state.telemetry_provider = None
    app.state.enforcement_rollout = enforcement_rollout or EnforcementRolloutConfig()
    app.state.enforcement_counters = EnforcementCounters()
    app.state.rate_limit_config = rate_limit
    app.state.idempotency_config = idempotency
    app.state.health_probes = list(health_probes) if health_probes else []

    # P1-005: Wrap lifespan to start/stop AuditWorker when a DB factory is provided.
    if lifespan is not None and audit_worker_db_factory is not None:
        from contextlib import asynccontextmanager

        from value_fabric.shared.audit.worker import AuditWorker

        original_lifespan = lifespan

        @asynccontextmanager
        async def _wrapped_lifespan(app: FastAPI):
            worker = AuditWorker(audit_worker_db_factory)
            worker.start()
            async with original_lifespan(app):
                yield
            worker.stop()
            if worker._task is not None:
                try:
                    await asyncio.wait_for(worker._task, timeout=10.0)
                except asyncio.TimeoutError:
                    worker._task.cancel()

        lifespan = _wrapped_lifespan

    if structured_logging is not None:
        applied = configure_structlog(structured_logging)
        app.state.structlog_configured = applied

    # P1-004: Sentry error tracking uses the centralized scrubbed initializer
    # and remains a no-op when SENTRY_DSN is unset.
    try:
        from value_fabric.shared.observability.sentry_init import init_sentry

        app.state.sentry_enabled = init_sentry(
            service_name=service_name,
            release=version,
        )
    except Exception:
        app.state.sentry_enabled = False

    if telemetry_service_name is not None:
        from value_fabric.shared.observability.platform import (
            configure_platform,
            instrument_fastapi_app as instrument_platform_app,
        )

        telemetry = configure_platform(
            telemetry_service_name,
            service_version=version,
        )
        app.state.telemetry_provider = telemetry.provider
        if instrument_telemetry:
            instrument_platform_app(app, enabled=telemetry.provider is not None)

    if pre_core_middleware_hook is not None:
        pre_core_middleware_hook(app)

    if cors_policy is not None:
        policy = cors_policy if isinstance(cors_policy, CorsPolicy) else CorsPolicy(**cors_policy)
        add_cors_middleware(app, policy)

    if include_request_id_middleware:
        add_request_id_middleware(app)

    if post_core_middleware_hook is not None:
        post_core_middleware_hook(app)

    should_register_handlers = register_default_exception_handlers
    if exception_handler_registration_mode == ExceptionHandlerRegistrationMode.SKIP:
        should_register_handlers = False

    if should_register_handlers:
        register_exception_handlers(app)

    if enforce_tenant_context:
        add_tenant_enforcement_middleware(app)

    if rate_limit is not None and rate_limit.rate_limiter_factory is not None:
        add_rate_limit_middleware(
            app,
            rate_limiter_factory=rate_limit.rate_limiter_factory,
            mode=rate_limit.mode,
            exempt_paths=list(rate_limit.exempt_paths),
        )

    if idempotency is not None and idempotency.service_factory is not None:
        add_idempotency_middleware(
            app,
            service_factory=idempotency.service_factory,
            mode=idempotency.mode,
            methods=idempotency.methods,
            header_name=idempotency.header_name,
        )

    if health_probes:
        register_readiness_endpoint(
            app,
            service_name=service_name,
            probes=list(health_probes),
            path=readiness_path,
            version=version,
        )

    if health_readiness_augmentation_hook is not None:
        health_readiness_augmentation_hook(app)

    return app
