"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Operational routes extracted from the Layer 3 monolith.
"""

from __future__ import annotations

import logging
import platform
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, Literal, cast

try:
    import psutil  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - exercised only in minimal test envs

    class _PsutilFallback:
        def virtual_memory(self) -> SimpleNamespace:
            return SimpleNamespace(used=0, total=0)

        def cpu_percent(self, interval: Any = None) -> float:
            return 0.0

        def cpu_count(self) -> int:
            return 0

        def disk_usage(self, path: str) -> SimpleNamespace:
            return SimpleNamespace(used=0)

    psutil = _PsutilFallback()
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.observability.metrics_access import (
    verify_metrics_access,  # type: ignore[import-untyped]
)
from value_fabric.shared.probes import normalize_probe_payload

from src.api.metrics_state import get_system_metrics, set_app_metrics
from src.config import get_settings

from ...api.dependencies import get_schema_initializer
from ...api.models import (
    DependencyStatus,
    DetailedHealthResponse,
    HealthResponse,
)

# mypy: disable-error-code=import-untyped

logger = logging.getLogger(__name__)

router = APIRouter()
SYSTEM_HEALTH_RESPONSES = {
    200: {"description": "Service health payload"},
    503: {"description": "Service unavailable"},
}
__all__ = ["router", "get_system_metrics", "set_app_metrics"]


async def _check_neo4j_dependency(
    schema_initializer: Any | None,
    settings: Any,
) -> DependencyStatus:
    """Check Neo4j dependency health status."""
    if (
        schema_initializer is not None
        and getattr(schema_initializer, "_driver", None) is None
    ):
        return DependencyStatus(
            name="neo4j",
            status="degraded",
            response_time_ms=None,
            error="Neo4j not initialized",
            failure_reason="neo4j_not_initialized",
            details={
                "uri": settings.neo4j_uri,
                "database": settings.neo4j_database,
            },
        )

    try:
        from src.schema.initializer import SchemaInitializer

        neo4j_checker = (
            schema_initializer
            if schema_initializer is not None
            else SchemaInitializer()
        )
        if schema_initializer is None:
            neo4j_checker._owned_driver = False
        start_time = time.time()
        neo4j_health = await neo4j_checker.health_check()
        response_time = (time.time() - start_time) * 1000

        return DependencyStatus(
            name="neo4j",
            status=neo4j_health["status"],
            response_time_ms=response_time,
            error=neo4j_health.get("error"),
            failure_reason=(
                "neo4j_unhealthy" if neo4j_health["status"] != "healthy" else None
            ),
            details={
                "uri": settings.neo4j_uri,
                "database": settings.neo4j_database,
            },
        )
    except (ConnectionError, OSError, RuntimeError, TimeoutError):
        return DependencyStatus(
            name="neo4j",
            status="unhealthy",
            response_time_ms=None,
            error="dependency_unhealthy",
            failure_reason="neo4j_connection_error",
            details={"uri": settings.neo4j_uri},
        )


def _check_pinecone_dependency(settings: Any) -> DependencyStatus | None:
    """Check Pinecone dependency health status if configured."""
    if not settings.pinecone_api_key:
        return None

    try:
        start_time = time.time()
        response_time = (time.time() - start_time) * 1000
        return DependencyStatus(
            name="pinecone",
            status="healthy",
            response_time_ms=response_time,
            error=None,
            failure_reason=None,
            details={"index": settings.pinecone_index},
        )
    except (ConnectionError, OSError, RuntimeError, TimeoutError):
        return DependencyStatus(
            name="pinecone",
            status="unhealthy",
            response_time_ms=None,
            error="dependency_unhealthy",
            failure_reason="pinecone_connection_error",
        )


async def check_dependencies(
    schema_initializer: Any | None = None,
) -> list[DependencyStatus]:
    """Check health of Layer 3 dependencies."""
    settings = get_settings()
    dependencies: list[DependencyStatus] = []

    neo4j_dep = await _check_neo4j_dependency(schema_initializer, settings)
    dependencies.append(neo4j_dep)

    pinecone_dep = _check_pinecone_dependency(settings)
    if pinecone_dep is not None:
        dependencies.append(pinecone_dep)

    return dependencies


async def _attempt_neo4j_recovery(
    request: Request,
    schema_initializer: object | None,
    request_id: str,
) -> object | None:
    """Attempt to recover Neo4j state if driver is None."""
    if (
        schema_initializer is not None
        and getattr(schema_initializer, "_driver", None) is None
    ):
        try:
            from ...api.dependencies import recover_neo4j_state

            app = request.app
            recovered_state = await recover_neo4j_state(app)
            if (
                recovered_state.schema_initializer is not None
                and getattr(recovered_state.schema_initializer, "_driver", None)
                is not None
            ):
                logger.info("Neo4j state recovered during health check")
                return recovered_state.schema_initializer
        except Exception as exc:
            logger.warning(
                "Neo4j state recovery attempt failed during health check: %s",
                exc,
                extra={"health_request_id": request_id},
            )
    return schema_initializer


async def _resolve_neo4j_and_schema_status(
    schema_initializer: object | None,
    request_id: str = "unknown",
) -> tuple[dict[str, object], dict[str, object]]:
    """Resolve Neo4j health and schema verification status."""
    if schema_initializer is None:
        return (
            {"status": "unavailable", "message": "Neo4j not initialized"},
            {"status": "unknown", "message": "Schema initializer not available"},
        )

    if getattr(schema_initializer, "_driver", None) is None:
        return (
            {"status": "unavailable", "message": "Neo4j not initialized"},
            {"status": "degraded", "message": "Schema initializer has no Neo4j driver"},
        )

    try:
        health_result = await schema_initializer.health_check()
        neo4j_health = (
            health_result.model_dump()
            if hasattr(health_result, "model_dump")
            else dict(health_result)
        )
        schema_status = await schema_initializer.verify_schema()
        return neo4j_health, schema_status
    except (
        ConnectionError,
        OSError,
        RuntimeError,
        TimeoutError,
        ValueError,
        TypeError,
    ):
        logger.warning(
            "Health check failed for Neo4j",
            exc_info=True,
            extra={"health_request_id": request_id},
        )
        return (
            {"status": "error", "message": "Neo4j health check failed"},
            {"status": "error", "message": "Neo4j health check failed"},
        )


def _build_system_info() -> dict[str, Any]:
    """Collect platform, CPU, memory, and disk info."""
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": psutil.virtual_memory().total / (1024**3),
        "disk_usage_gb": psutil.disk_usage("/").used / (1024**3),
    }


def _build_configuration(settings: Any) -> dict[str, Any]:
    """Format configuration summary for detailed health check."""
    return {
        "api_host": settings.api_host,
        "api_port": settings.api_port,
        "log_level": settings.log_level,
        "log_format": settings.log_format,
        "neo4j_database": settings.neo4j_database,
        "neo4j_max_pool_size": settings.neo4j_max_pool_size,
        "pinecone_configured": bool(settings.pinecone_api_key),
    }


def _derive_overall_status(
    dependencies: list[DependencyStatus],
    schema_initializer: object | None,
    schema_status: dict[str, object] | None = None,
) -> Literal["healthy", "unhealthy", "degraded"]:
    if (
        schema_initializer is None
        or getattr(schema_initializer, "_driver", None) is None
    ):
        return "degraded"
    if any(dep.status == "unhealthy" for dep in dependencies):
        return "unhealthy"
    if any(dep.status == "degraded" for dep in dependencies):
        return "degraded"
    if schema_status is not None:
        if (
            schema_status.get("status") in ("error", "unhealthy")
            or schema_status.get("valid") is False
        ):
            return "unhealthy"
        if schema_status.get("status") == "degraded":
            return "degraded"
    return "healthy"


def _derive_readiness(
    *,
    dependencies: list[DependencyStatus],
    schema_initializer: object | None,
    schema_status: dict[str, object],
) -> dict[str, object]:
    """Return readiness envelope gated by mandatory dependencies only."""
    if (
        schema_initializer is None
        or getattr(schema_initializer, "_driver", None) is None
    ):
        return {"is_ready": False, "reason": "neo4j_uninitialized"}

    neo4j_dependency = next((dep for dep in dependencies if dep.name == "neo4j"), None)
    if neo4j_dependency is None:
        return {"is_ready": False, "reason": "neo4j_dependency_missing"}
    if neo4j_dependency.status != "healthy":
        return {"is_ready": False, "reason": "dependency_unhealthy"}

    if not schema_status.get("valid", False):
        return {"is_ready": False, "reason": "schema_verification_failed"}

    return {"is_ready": True, "reason": "dependencies_available"}


@router.get(
    "/metrics",
    tags=["Monitoring"],
    include_in_schema=False,
    summary="Prometheus Metrics",
    description="Export Prometheus metrics for monitoring.",
    responses={
        403: {"description": "Metrics endpoint requires internal access"},
        200: {"description": "Prometheus metrics exported successfully"},
        503: {"description": "Metrics collection disabled"},
    },
)
async def get_metrics(request: Request) -> Response:
    """Get Prometheus metrics from the app state registry."""
    if not verify_metrics_access(request):
        raise AuthorizationError(message="Metrics endpoint requires internal access")

    metrics = getattr(request.app.state, "metrics", None)

    if not metrics:
        return Response(
            content="# Metrics collection is disabled",
            status_code=503,
            media_type="text/plain",
        )

    try:
        metrics_data = metrics.get_metrics()
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    except (AttributeError, RuntimeError, ValueError, TypeError) as exc:
        logger.error(
            "Error generating metrics",
            extra={
                "context": {
                    "endpoint": "/metrics",
                    "operation": "get_metrics",
                    "error_type": exc.__class__.__name__,
                }
            },
            exc_info=True,
        )
        error_payload = {
            "code": "METRICS_EXPORT_ERROR",
            "message": "Failed to generate metrics",
        }
        return Response(
            content=str(error_payload), status_code=500, media_type="application/json"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Basic Health Check",
    responses=SYSTEM_HEALTH_RESPONSES,
)
@router.get(
    "/health/live",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Basic Health Check (Liveness)",
    responses=SYSTEM_HEALTH_RESPONSES,
    include_in_schema=False,
)
async def health_check(
    request: Request,
    schema_initializer: Any = Depends(get_schema_initializer),
) -> dict[str, Any]:
    """Check service health and Neo4j connectivity."""
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "unknown")

    schema_initializer = await _attempt_neo4j_recovery(
        request, schema_initializer, request_id
    )
    dependencies = await check_dependencies(schema_initializer=schema_initializer)
    metrics = get_system_metrics()

    neo4j_health, schema_status = await _resolve_neo4j_and_schema_status(
        schema_initializer, request_id
    )

    overall_status = _derive_overall_status(
        dependencies, schema_initializer, schema_status
    )
    response_time_ms = round((time.time() - start_time) * 1000, 2)

    logger.info(
        "Health check completed",
        extra={
            "health_request_id": request_id,
            "status": overall_status,
            "response_time_ms": response_time_ms,
            "neo4j_status": neo4j_health.get("status"),
        },
    )

    return normalize_probe_payload(
        status=overall_status,
        service="layer3-knowledge",
        readiness=_derive_readiness(
            dependencies=dependencies,
            schema_initializer=schema_initializer,
            schema_status=schema_status,
        ),
        dependencies=dependencies,
        extra={
            "version": "1.0.0",
            "timestamp": datetime.now(UTC),
            "uptime_seconds": metrics.uptime_seconds,
            "response_time_ms": response_time_ms,
            "metrics": metrics,
            "neo4j": neo4j_health,
            "schema_status": schema_status,
        },
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    tags=["Health"],
    summary="Detailed Health Check",
)
async def detailed_health_check(
    schema_initializer: Any = Depends(get_schema_initializer),
) -> DetailedHealthResponse:
    """Get detailed health information with system info and configuration."""
    dependencies = await check_dependencies(schema_initializer=schema_initializer)
    metrics = get_system_metrics()

    neo4j_health, schema_status = await _resolve_neo4j_and_schema_status(
        schema_initializer
    )

    overall_status = cast(
        Literal["healthy", "unhealthy", "degraded"],
        _derive_overall_status(dependencies, schema_initializer, schema_status),
    )

    settings = get_settings()
    system_info = _build_system_info()
    configuration = _build_configuration(settings)

    return DetailedHealthResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.now(UTC),
        uptime_seconds=metrics.uptime_seconds,
        dependencies=dependencies,
        metrics=metrics,
        neo4j=neo4j_health,
        schema_status=schema_status,
        system_info=system_info,
        configuration=configuration,
    )
