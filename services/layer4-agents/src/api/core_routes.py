from __future__ import annotations

"""Core Layer 4 API endpoints registered by the app factory."""


import time
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import Response
from value_fabric.shared.models.typed_dict import TypedDictModel

try:
    from value_fabric.shared.observability.metrics_access import verify_metrics_access

    _shared_verify_metrics_access = verify_metrics_access

    def verify_metrics_access(request: Request) -> tuple[bool, str | None]:
        access_result = _shared_verify_metrics_access(request)
        if isinstance(access_result, tuple):
            return access_result
        return access_result, None

    METRICS_ACCESS_AVAILABLE = True
except ImportError:
    METRICS_ACCESS_AVAILABLE = False
    verify_metrics_access = None

from .startup import runtime_state


class health_checkResult(TypedDictModel):
    dependencies: Any
    executor_ready: bool
    metrics: dict[str, Any]
    service: str
    status: Any
    timestamp: Any
    uptime_seconds: Any
    version: str


class rootResult(TypedDictModel):
    documentation: str
    health: str
    metrics: str
    service: str
    version: str


def register_core_routes(app: FastAPI) -> None:
    app_start_time = time.time()

    @app.get("/health")
    async def health_check():
        import psutil

        uptime = time.time() - app_start_time
        memory_info = psutil.virtual_memory()

        dependencies = []
        overall_status = "healthy"

        try:
            if runtime_state.checkpoint_saver is not None and getattr(
                runtime_state.checkpoint_saver, "conn", None
            ):
                await runtime_state.checkpoint_saver.conn.execute("SELECT 1")
                dependencies.append(
                    {
                        "name": "postgres",
                        "status": "healthy",
                        "response_time_ms": None,
                        "error": None,
                        "failure_reason": None,
                    }
                )
            else:
                dependencies.append(
                    {
                        "name": "postgres",
                        "status": "degraded",
                        "response_time_ms": None,
                        "error": "Checkpointing not configured",
                        "failure_reason": "checkpointing_not_configured",
                    }
                )
                overall_status = "degraded"
        except Exception as exc:
            dependencies.append(
                {
                    "name": "postgres",
                    "status": "unhealthy",
                    "response_time_ms": None,
                    "error": "PostgreSQL health check failed",
                    "error_code": "POSTGRES_HEALTH_ERROR",
                }
            )
            overall_status = "degraded"

        try:
            if runtime_state.state_manager is not None and getattr(
                runtime_state.state_manager, "redis_client", None
            ):
                await runtime_state.state_manager.redis_client.ping()
                dependencies.append(
                    {"name": "redis", "status": "healthy", "response_time_ms": None, "error": None, "failure_reason": None}
                )
            else:
                dependencies.append(
                    {
                        "name": "redis",
                        "status": "degraded",
                        "response_time_ms": None,
                        "error": "Redis not configured",
                        "failure_reason": "redis_not_configured",
                    }
                )
        except Exception as exc:
            dependencies.append(
                {"name": "redis", "status": "unhealthy", "response_time_ms": None, "error": "Redis health check failed", "error_code": "REDIS_HEALTH_ERROR"}
            )

        return health_checkResult.model_validate({
            "status": overall_status,
            "service": "layer4-agents",
            "version": "0.2.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "executor_ready": runtime_state.workflow_executor is not None,
            "uptime_seconds": uptime,
            "dependencies": dependencies,
            "metrics": {
                "memory_usage_mb": memory_info.used / (1024 * 1024),
                "cpu_percent": psutil.cpu_percent(),
                "active_connections": 0,
                "total_requests": 0,
            },
        })

    @app.get("/metrics")
    async def metrics_endpoint(request: Request):
        if METRICS_ACCESS_AVAILABLE and verify_metrics_access:
            is_authorized, error_message = verify_metrics_access(request)
            if not is_authorized:
                return Response(
                    content=error_message or "Unauthorized",
                    status_code=401,
                    media_type="text/plain",
                )

        metrics = getattr(request.app.state, "metrics", None)
        if not metrics:
            return Response(
                content="Metrics collection is disabled", status_code=503, media_type="text/plain"
            )
        try:
            return Response(
                content=metrics.get_metrics(),
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )
        except Exception as exc:
            return Response(content=f"Error generating metrics: {exc}", status_code=500, media_type="text/plain")

    @app.get("/")
    async def root():
        return rootResult.model_validate({
            "service": "Layer 4: Agentic Workflow Engine",
            "version": "0.2.0",
            "documentation": "/docs",
            "health": "/health",
            "metrics": "/metrics",
        })
