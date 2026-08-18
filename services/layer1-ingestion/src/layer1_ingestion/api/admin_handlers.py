"""Health, metrics, cleanup, and proxy-pool route handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis
import structlog
from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.observability.metrics_access import verify_metrics_access
from value_fabric.shared.probes import normalize_probe_payload

from ..metrics import get_metrics
from ..shared.config import settings
from ..shared.database import get_db_from_context_sync
from ..shared.models import JobStatus, ScrapingJob, create_proxy_pool
from ._task_fallback import UnavailableTask, _build_task_unavailable_detail
from .dependencies import get_tenant_id
from .schemas.admin_schemas import (
    ComponentHealth,
    CreateProxyPoolRequest,
    HealthCheckResponse,
    ProxyPoolResponse,
)

logger = structlog.get_logger()


class trigger_cleanupResult(TypedDictModel):
    message: str
    status: str


class legacy_health_checkResult(TypedDictModel):
    dependencies: Any
    note: str
    status: Any


try:
    from ..shared.otel_celery import build_celery_options
    from ..shared.tasks import cleanup_old_content
except ImportError as exc:
    build_celery_options = None  # type: ignore[assignment]
    cleanup_old_content = UnavailableTask("cleanup_old_content", exc)


async def health_check(db: Session = Depends(get_db_from_context_sync)):
    """Enhanced health check endpoint."""
    components = {}

    try:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
        components["database"] = ComponentHealth(status="healthy", latency_ms=0)
    except Exception as e:
        logger.error(
            "health_check_database_failed", error_code="DB_HEALTH_ERROR", error=repr(e)
        )
        components["database"] = ComponentHealth(
            status="unhealthy", message="Database connection failed"
        )

    try:
        from ..shared.database import redis_client

        if redis_client is None:
            raise ConnectionError("Redis client not configured")
        redis_client.ping()
        components["queue"] = ComponentHealth(status="healthy", latency_ms=0)
    except (redis.RedisError, ConnectionError) as e:
        logger.warning("redis_ping_failed", error=str(e))
        components["queue"] = ComponentHealth(
            status="degraded", message="Redis not available"
        )

    active_jobs = (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.status.in_(
                [
                    JobStatus.QUEUED.value,
                    JobStatus.VALIDATING.value,
                    JobStatus.BROWSER_ACQUIRING.value,
                    JobStatus.NAVIGATING.value,
                    JobStatus.EXTRACTING.value,
                    JobStatus.TRANSFORMING.value,
                    JobStatus.STORING.value,
                ]
            )
        )
        .count()
    )

    queued_jobs = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.status == JobStatus.QUEUED.value)
        .count()
    )

    started_jobs = db.query(ScrapingJob).all()
    wait_times_ms = [
        int((job.started_at - job.created_at).total_seconds() * 1000)
        for job in started_jobs
        if job.started_at and job.created_at
    ]
    average_wait_time_ms = (
        int(sum(wait_times_ms) / len(wait_times_ms)) if wait_times_ms else None
    )

    metrics = {
        "active_jobs": active_jobs,
        "queued_jobs": queued_jobs,
        "available_browsers": None,
        "available_browsers_metadata": {
            "status": "unknown",
            "reason": "Browser pool telemetry is not yet wired in Layer 1",
        },
        "average_wait_time_ms": average_wait_time_ms,
        "average_wait_time_ms_metadata": {
            "status": "unknown" if average_wait_time_ms is None else "measured",
            "reason": (
                "No started jobs available to calculate queue wait time"
                if average_wait_time_ms is None
                else None
            ),
        },
    }

    if any(c.status == "unhealthy" for c in components.values()):
        overall_status = "unhealthy"
    elif any(c.status == "degraded" for c in components.values()):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        timestamp=datetime.now(UTC),
        components={k: v.dict() for k, v in components.items()},
        metrics=metrics,
    )


async def metrics_endpoint(request: Request):
    """Prometheus-compatible metrics endpoint."""
    if not verify_metrics_access(request):
        raise AuthorizationError(message="Metrics endpoint requires internal access")

    metrics = get_metrics()

    if not metrics:
        return Response(
            content="Metrics collection is disabled",
            status_code=503,
            media_type="text/plain",
        )

    try:
        metrics_data = metrics.get_metrics()
        return Response(
            content=metrics_data, media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        return Response(
            content=f"Error generating metrics: {e}",
            status_code=500,
            media_type="text/plain",
        )


async def trigger_cleanup(
    days: int = Query(default=30, ge=1, le=365),
    org_id: UUID = Depends(get_tenant_id),
):
    """Trigger content cleanup for old data."""
    cleanup_old_content.apply_async(
        args=[days, str(org_id)],
        **(build_celery_options() or {}),
    )
    return trigger_cleanupResult.model_validate(
        {
            "message": f"Cleanup initiated for content older than {days} days",
            "status": "processing",
        }
    )


async def create_proxy_pool_endpoint(
    request: CreateProxyPoolRequest,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Create a proxy pool."""
    pool = create_proxy_pool(
        tenant_id=org_id,
        name=request.name,
        proxies=request.proxies,
        rotation_strategy=request.rotation_strategy,
    )

    db.add(pool)
    db.commit()
    db.refresh(pool)

    return ProxyPoolResponse(
        id=pool.id,
        name=pool.name,
        proxy_count=len(pool.proxies) if pool.proxies else 0,
        rotation_strategy=pool.rotation_strategy,
        created_at=pool.created_at,
    )


async def legacy_health_check():
    """Legacy-compatible health check with dependency status."""
    from ..shared.database import _new_session, redis_client

    dependencies = []
    overall_status = "healthy"

    db = _new_session()
    try:
        from sqlalchemy import text

        db.execute(text("SELECT 1"))
        dependencies.append({"name": "database", "status": "healthy", "error": None})
    except Exception as e:
        logger.error(
            "health_check_database_failed", error_code="DB_HEALTH_ERROR", error=repr(e)
        )
        dependencies.append(
            {
                "name": "database",
                "status": "unhealthy",
                "error": "Database connection failed",
            }
        )
        overall_status = "degraded"
    finally:
        db.close()

    try:
        if redis_client is None:
            dependencies.append(
                {
                    "name": "redis",
                    "status": "degraded",
                    "error": "Redis client not configured",
                }
            )
            overall_status = "degraded"
        else:
            redis_client.ping()
            dependencies.append({"name": "redis", "status": "healthy", "error": None})
    except Exception as e:
        logger.error(
            "health_check_redis_failed", error_code="REDIS_HEALTH_ERROR", error=repr(e)
        )
        dependencies.append(
            {"name": "redis", "status": "degraded", "error": "Redis connection failed"}
        )
        overall_status = "degraded"

    payload = normalize_probe_payload(
        status=overall_status,
        service="layer1-ingestion",
        dependencies=dependencies,
        extra={
            "note": "Legacy endpoint; use /api/v1/ingestion/health for full schema response",
        },
    )
    return legacy_health_checkResult.model_validate(payload)


async def legacy_metrics():
    """Legacy-compatible metrics endpoint."""
    content = "# HELP layer1_ingestion_metrics_legacy placeholder\n# TYPE layer1_ingestion_metrics_legacy gauge\nlayer1_ingestion_metrics_legacy 0\n"
    return Response(
        content=content, media_type="text/plain; version=0.0.4; charset=utf-8"
    )
