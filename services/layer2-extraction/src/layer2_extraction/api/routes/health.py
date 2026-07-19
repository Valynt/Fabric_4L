"""Health check routes for Layer 2 extraction service."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter
from value_fabric.shared.fastapi_framework.health import ProbeResult
from value_fabric.shared.probes import normalize_probe_payload

router = APIRouter()

LAYER3_SKIP_ERROR = (
    "Release-smoke readiness skips downstream Layer 3 probe; live smoke tests validate "
    "cross-service contracts after startup"
)
LAYER3_SKIP_FAILURE_REASON = "layer3_probe_skipped"
LAYER3_HEALTH_CHECK_ERROR_CODE = "L3_HEALTH_CHECK_ERROR"


def should_skip_layer3_probe() -> bool:
    return os.getenv("LAYER2_HEALTH_SKIP_LAYER3", "").lower() in {"1", "true", "yes"}


async def pending_ingestion_probe(pending_ingestion_store: Any) -> ProbeResult:
    """Return readiness for the pending-ingestion store."""
    try:
        await pending_ingestion_store.get_due(datetime.now(UTC))
    except Exception as exc:
        return ProbeResult(name="pending_ingestion_store", healthy=False, detail=type(exc).__name__)
    return ProbeResult(name="pending_ingestion_store", healthy=True)


async def quarantine_probe(quarantine_store: Any) -> ProbeResult:
    """Return readiness for the quarantine store using a synthetic tenant scope."""
    try:
        await quarantine_store.list(tenant_id="__health_probe__")
    except Exception as exc:
        return ProbeResult(name="quarantine_store", healthy=False, detail=type(exc).__name__)
    return ProbeResult(name="quarantine_store", healthy=True)


def collect_metrics_counts(metrics: Any) -> tuple[int, int]:
    """Return total request and active connection counters from the metrics registry."""
    total_requests = 0
    active_connections = 0

    if not metrics or not metrics.config.enabled:
        return total_requests, active_connections

    try:
        requests_counter = metrics._metrics.get("requests_total", {})
        total_requests = (
            sum(
                v._value.get() if hasattr(v._value, "get") else v._value
                for method_dict in requests_counter._metrics.values()
                for endpoint_dict in method_dict.values()
                for v in endpoint_dict.values()
            )
            if hasattr(requests_counter, "_metrics")
            else 0
        )
    except (AttributeError, TypeError):
        total_requests = 0

    try:
        active_connections = int(metrics._metrics.get("active_connections", {}).get("total", {}).get("_value", 0))
    except (AttributeError, TypeError):
        active_connections = 0

    return total_requests, active_connections


async def layer3_dependency_status(
    *,
    skip_layer3_probe: bool,
    layer3_client_factory: Any,
) -> tuple[dict[str, Any], bool]:
    """Return the Layer 3 dependency health record and whether it is healthy."""
    if skip_layer3_probe:
        return (
            {
                "name": "layer3_knowledge",
                "status": "degraded",
                "response_time_ms": None,
                "error": LAYER3_SKIP_ERROR,
                "failure_reason": LAYER3_SKIP_FAILURE_REASON,
            },
            False,
        )

    try:
        l3_start = time.time()
        l3_client = layer3_client_factory()
        l3_healthy = await l3_client.health_check()
        l3_response_ms = round((time.time() - l3_start) * 1000, 2)
        await l3_client.close()

        return (
            {
                "name": "layer3_knowledge",
                "status": "healthy" if l3_healthy else "unhealthy",
                "response_time_ms": l3_response_ms,
                "error": None if l3_healthy else "Layer 3 returned unhealthy status",
                "failure_reason": None if l3_healthy else "dependency_unhealthy",
            },
            bool(l3_healthy),
        )
    except Exception:
        return (
            {
                "name": "layer3_knowledge",
                "status": "unhealthy",
                "response_time_ms": None,
                "error": "Layer 3 health check failed",
                "error_code": LAYER3_HEALTH_CHECK_ERROR_CODE,
                "failure_reason": "dependency_probe_error",
            },
            False,
        )


def build_system_metrics(
    *,
    active_connections: int,
    total_requests: int,
    psutil_module: Any,
) -> dict[str, Any]:
    system_metrics: dict[str, Any] = {
        "active_connections": active_connections,
        "total_requests": total_requests,
    }
    if psutil_module:
        memory_info = psutil_module.virtual_memory()
        system_metrics["memory_usage_mb"] = memory_info.used / (1024 * 1024)
        system_metrics["cpu_percent"] = psutil_module.cpu_percent()
    return system_metrics


async def build_health_payload(
    *,
    app_start_time: float,
    metrics: Any,
    layer3_client_factory: Any,
    psutil_module: Any,
    skip_layer3_probe: bool | None = None,
) -> dict[str, Any]:
    """Build the Layer 2 health payload without depending on FastAPI app globals."""
    start_time = time.time()
    uptime = time.time() - app_start_time

    total_requests, active_connections = collect_metrics_counts(metrics)
    dependency, l3_dep_healthy = await layer3_dependency_status(
        skip_layer3_probe=should_skip_layer3_probe() if skip_layer3_probe is None else skip_layer3_probe,
        layer3_client_factory=layer3_client_factory,
    )
    dependencies = [dependency]
    overall_status = "healthy" if l3_dep_healthy else "degraded"

    total_response_ms = round((time.time() - start_time) * 1000, 2)

    if metrics:
        metrics.set_health_status(overall_status == "healthy", component="api")
        metrics.set_health_status(l3_dep_healthy, component="layer3")

    return cast(dict[str, Any], normalize_probe_payload(
        status=overall_status,
        service="layer2-extraction",
        dependencies=dependencies,
        extra={
            "version": "1.0.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_seconds": uptime,
            "response_time_ms": total_response_ms,
            "metrics": build_system_metrics(
                active_connections=active_connections,
                total_requests=total_requests,
                psutil_module=psutil_module,
            ),
        },
    ))
