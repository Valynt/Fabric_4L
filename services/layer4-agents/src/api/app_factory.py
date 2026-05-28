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
from value_fabric.shared.fastapi_framework import create_fabric_app
from value_fabric.shared.observability import configure_observability
from value_fabric.shared.security import validate_production_safety

from ..config.settings import settings

logger = logging.getLogger(__name__)
from ..metrics import initialize_metrics
from .core_routes import register_core_routes
from .middleware import configure_middleware
from .routers import register_routers
from .startup import build_lifespan, start_optional_integrations


def init_telemetry() -> TracerProvider | None:
    if not settings.otel_exporter_endpoint:
        return None
    resource = Resource.create({SERVICE_NAME: "layer4-agents"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f"{settings.otel_exporter_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


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
    )

    if settings.otel_exporter_endpoint:
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
