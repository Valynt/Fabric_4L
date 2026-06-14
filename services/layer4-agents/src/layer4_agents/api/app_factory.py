from __future__ import annotations

"""Layer 4 FastAPI application factory."""


import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
from value_fabric.shared.fastapi_framework import create_fabric_app
from value_fabric.shared.fastapi_framework.health import CallableProbe, ProbeResult
from value_fabric.shared.observability import configure_observability
from value_fabric.shared.security import validate_production_safety

from ..config.settings import get_settings

logger = logging.getLogger(__name__)
from ..metrics import initialize_metrics
from .core_routes import register_core_routes
from .middleware import configure_middleware
from .routers import register_routers
from .startup import build_lifespan, runtime_state, start_optional_integrations


def init_telemetry() -> TracerProvider | None:
    import os

    if not get_settings().otel_exporter_endpoint:
        return None
    sample_ratio = float(os.getenv("OTEL_SAMPLE_RATIO", "0.01"))
    resource = Resource.create({SERVICE_NAME: "layer4-agents"})
    sampler = ParentBasedTraceIdRatio(sample_ratio)
    provider = TracerProvider(resource=resource, sampler=sampler)
    exporter = OTLPSpanExporter(endpoint=f"{get_settings().otel_exporter_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


async def _postgres_probe() -> ProbeResult:
    try:
        saver = runtime_state.checkpoint_saver
        if saver is not None:
            # AsyncPostgresSaver stores the psycopg connection either as a public
            # `conn` attribute or keeps the reference we attached privately. Probe
            # both locations so readiness reflects actual DB reachability rather
            # than an implementation detail of the saver.
            conn = getattr(saver, "conn", None) or getattr(saver, "_conn", None)
            if conn is not None:
                await conn.execute("SELECT 1")
                return ProbeResult(name="postgres", healthy=True)
            return ProbeResult(name="postgres", healthy=False, detail="checkpoint_connection_not_found")
        return ProbeResult(name="postgres", healthy=False, detail="checkpointing_not_configured")
    except Exception as exc:
        import logging

        logging.getLogger("fabric.health").warning("Postgres readiness probe failed", exc_info=exc)
        return ProbeResult(name="postgres", healthy=False, detail="postgres:unavailable")


async def _redis_probe() -> ProbeResult:
    try:
        sm = runtime_state.state_manager
        redis_client = getattr(sm, "redis_client", None) if sm else None
        if redis_client is not None:
            await redis_client.ping()
            return ProbeResult(name="redis", healthy=True)
        return ProbeResult(name="redis", healthy=False, detail="redis_not_configured")
    except Exception as exc:
        import logging

        logging.getLogger("fabric.health").warning("Redis readiness probe failed", exc_info=exc)
        return ProbeResult(name="redis", healthy=False, detail="redis:unavailable")


async def _executor_probe() -> ProbeResult:
    try:
        if runtime_state.workflow_executor is not None:
            return ProbeResult(name="executor", healthy=True)
        return ProbeResult(name="executor", healthy=False, detail="executor_not_initialized")
    except Exception as exc:
        import logging

        logging.getLogger("fabric.health").warning("Executor readiness probe failed", exc_info=exc)
        return ProbeResult(name="executor", healthy=False, detail="executor:unavailable")


def create_app() -> FastAPI:
    app = create_fabric_app(
        service_name="layer4-agents",
        title="Layer 4: Agentic Workflow Orchestrator",
        description="LangGraph-powered workflow orchestration for Value Fabric with multi-agent support",
        version="0.2.0",
        lifespan=build_lifespan(
            validate_production_safety=validate_production_safety,
            init_telemetry=init_telemetry,
            configure_optional_integrations=start_optional_integrations,
        ),
        health_probes=[
            CallableProbe(name="postgres", fn=_postgres_probe),
            CallableProbe(name="redis", fn=_redis_probe),
            CallableProbe(name="executor", fn=_executor_probe),
        ],
        readiness_path="/ready",
    )

    if get_settings().otel_exporter_endpoint:
        FastAPIInstrumentor.instrument_app(app)

    app.state.metrics = initialize_metrics()
    configure_observability(
        app,
        service_name="layer4-agents",
        metrics_provider=lambda: app.state.metrics.get_metrics() if getattr(app.state, "metrics", None) else "",
        readiness_check=lambda: True,
    )
    configure_middleware(app)

    register_core_routes(app)
    register_routers(app)
    return app
