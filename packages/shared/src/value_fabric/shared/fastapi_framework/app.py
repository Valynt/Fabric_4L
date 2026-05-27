"""Reusable FastAPI application assembly helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from fastapi import FastAPI

from ..error_handling.handlers import register_exception_handlers

from .middleware import CorsPolicy, add_cors_middleware, add_request_id_middleware


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


def _is_route_opted_out(path: str, route_handler: Callable[..., Any], config: EnforcementRolloutConfig) -> bool:
    return path in config.health_checks.route_opt_out_paths or bool(
        getattr(route_handler, "_vf_enforcement_opt_out", False)
    )


def record_enforcement_decision(
    app: FastAPI,
    *,
    control: str,
    violation: str,
    route: str,
    tenant_id: str | None,
    actor_id: str | None,
    logger: Any | None = None,
    route_handler: Callable[..., Any] | None = None,
) -> bool:
    """Apply rollout semantics and emit structured audit context.

    Returns ``True`` when request processing should continue, ``False`` when the
    caller should block the request in enforce mode.
    """

    config: EnforcementRolloutConfig = getattr(app.state, "enforcement_rollout", EnforcementRolloutConfig())
    counters: EnforcementCounters = getattr(app.state, "enforcement_counters", EnforcementCounters())
    app.state.enforcement_counters = counters

    if route_handler is not None and _is_route_opted_out(route, route_handler, config):
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
    import os

    otel_endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otel_endpoint:
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return None

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f"{otel_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


def instrument_fastapi_app(app: FastAPI, *, enabled: bool) -> None:
    if not enabled:
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        return

    FastAPIInstrumentor.instrument_app(app)


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

    Service-owned lifecycle behavior remains authoritative; this factory does
    not create or manage DB/session lifecycle side effects.
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

    if telemetry_service_name is not None:
        app.state.telemetry_provider = init_telemetry(telemetry_service_name)
        if instrument_telemetry:
            instrument_fastapi_app(app, enabled=app.state.telemetry_provider is not None)

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

    if health_readiness_augmentation_hook is not None:
        health_readiness_augmentation_hook(app)

    return app
