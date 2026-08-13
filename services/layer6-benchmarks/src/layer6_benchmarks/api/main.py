# mypy: disallow-untyped-decorators=False, disable-error-code="no-untyped-def,arg-type"
"""Layer 6 Benchmark Service FastAPI application."""
from __future__ import annotations

import decimal
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, urlparse

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.responses import Response
from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from value_fabric.shared.identity.context import RequestContext, get_request_context
from value_fabric.shared.identity.policy_registry import authorize_action
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.startup import reject_insecure_bypass_in_production

logger = logging.getLogger(__name__)

try:
    from value_fabric.shared.environment import (
        get_service_environment,
        is_production_like_environment,
    )
    from value_fabric.shared.secrets import load_infisical_secrets

    load_infisical_secrets()
except Exception as exc:
    _secret_env = get_service_environment("layer6")
    logger.warning("Failed to load Infisical secrets (dev mode): %s", exc)
    if is_production_like_environment(_secret_env):
        raise RuntimeError("Failed to load Infisical secrets in production-like Layer 6 runtime")

from layer6_benchmarks.logging_config import configure_structured_logging

from ..database import close_driver, get_driver
from ..database import health_check as neo4j_health_check
from ..metrics import MetricsMiddleware, get_metrics, initialize_metrics
from ..models.benchmark_dataset import (
    FINANCIAL_SERVICES_BENCHMARK_SEED,
    HEALTHCARE_BENCHMARK_SEED,
    MANUFACTURING_BENCHMARK_SEED,
    SAAS_B2B_BENCHMARK_SEED,
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from ..repositories.benchmark_repository import BenchmarkRepository
from ..seed.load_benchmark_packs import load_default_benchmark_packs
from ..settings import Layer6Settings, validate_layer6_startup_settings
from ..shared_bootstrap import (
    SecurityConfig,
    add_security_middleware,
    build_health_response,
    create_fabric_app,
    install_metrics_middleware,
    register_health_endpoint,
    resolve_cors_policy,
    validate_production_safety,
    verify_metrics_access,
)
from .routes import benchmarks, system
from .schemas import (
    ComparisonRequestPayload,
    ComparisonResponse,
    DatasetDetail,
    DatasetSummary,
    DatasetUpsertPayload,
    ValidationRequestPayload,
    ValidationResponse,
)
from .startup_logging import emit_startup_metadata, runtime_metadata_from_env

# Configure structured logging
configure_structured_logging()
logger = structlog.get_logger(__name__)

SERVICE_NAME = "layer6-benchmarks"
SERVICE_VERSION = "1.0.0"
_SETTINGS: Layer6Settings = validate_layer6_startup_settings()
reject_insecure_bypass_in_production(service_name="layer6-benchmarks", settings=_SETTINGS)
_benchmark_repo: BenchmarkRepository | None = None
_neo4j_startup_error: str | None = None


class HealthCheckResult(TypedDictModel):
    response_time_ms: Any
    service: str
    status: str
    timestamp: Any
    version: str


class ListIndustriesResult(TypedDictModel):
    industries: Any


class ReadinessCheckResult(TypedDictModel):
    checks: dict[str, Any]
    service: str
    status: str
    timestamp: str
    version: str


def _public_startup_config() -> dict[str, Any]:
    db_url = urlparse(_SETTINGS.database_url)
    neo4j_url = urlparse(_SETTINGS.neo4j_uri)
    return {
        "environment": _SETTINGS.environment,
        "testing": _SETTINGS.testing,
        "auth_required": _SETTINGS.auth_required,
        "allow_insecure_dev_auth_bypass": _SETTINGS.allow_insecure_dev_auth_bypass,
        "allow_ephemeral_encryption": _SETTINGS.allow_ephemeral_encryption,
        "database_scheme": db_url.scheme,
        "database_host": db_url.hostname,
        "database_sslmode": parse_qs(db_url.query).get("sslmode", ["unset"])[0],
        "neo4j_scheme": neo4j_url.scheme,
        "neo4j_host": neo4j_url.hostname,
    }


def _record_compare_metric(*, industry: str, outcome: str) -> None:
    metrics = get_metrics()
    if metrics is not None:
        metrics.increment_dataset_comparisons(industry=industry, outcome=outcome)


def _build_dataset_from_seed(seed: dict[str, Any]) -> BenchmarkDataset:
    dataset = BenchmarkDataset(
        dataset_id=seed["dataset_id"],
        name=seed["name"],
        description=seed["description"],
        industry=seed["industry"],
        segment=seed["segment"],
        geography=seed["geography"],
        version=seed["version"],
        data_source=seed["data_source"],
        is_public=seed["is_public"],
        ownership_mode="global_system" if seed.get("is_public") else "tenant",
    )

    for metric_data in seed["metrics"].values():
        profile = StatisticalProfile.from_dict(metric_data["profile"])
        metric = BenchmarkMetric(
            name=metric_data["name"],
            unit=metric_data["unit"],
            description=metric_data["description"],
            profile=profile,
            lower_bound=(
                Decimal(metric_data.get("lower_bound", "0"))
                if "lower_bound" in metric_data
                else None
            ),
            upper_bound=(
                Decimal(metric_data.get("upper_bound", "0"))
                if "upper_bound" in metric_data
                else None
            ),
            is_higher_better=metric_data.get("is_higher_better", True),
        )
        dataset.add_metric(metric)

    return dataset


async def _init_seed_data() -> None:
    seeds = [
        MANUFACTURING_BENCHMARK_SEED,
        SAAS_B2B_BENCHMARK_SEED,
        HEALTHCARE_BENCHMARK_SEED,
        FINANCIAL_SERVICES_BENCHMARK_SEED,
    ]
    if _benchmark_repo is None:
        return
    for seed in seeds:
        await _benchmark_repo.save_dataset(_build_dataset_from_seed(seed))


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_production_safety()
    runtime_metadata = runtime_metadata_from_env(default_version=SERVICE_VERSION)
    emit_startup_metadata(
        service=runtime_metadata["service"],
        version=runtime_metadata["version"],
        build_sha=runtime_metadata["build_sha"],
        config=_public_startup_config(),
    )

    if app.state.telemetry_provider is not None:
        logger.info("L6: OpenTelemetry tracing initialized")

    # Validate the module-level Redis client (created for the governance
    # middleware above) so an unavailable Redis is logged at startup; the
    # tenant kill-switch fails closed either way.
    if _l6_redis_client is not None:
        try:
            await _l6_redis_client.ping()
            logger.info("L6: Redis client initialized for tenant kill-switch")
        except Exception:
            logger.warning("L6: Redis unavailable; tenant status checks will fail closed", exc_info=True)

    metrics = getattr(app.state, "metrics", None)
    if metrics is not None:
        logger.info("Prometheus metrics initialized")
        metrics.set_build_info(
            service=runtime_metadata["service"],
            version=runtime_metadata["version"],
            build_sha=runtime_metadata["build_sha"],
        )

    global _benchmark_repo, _neo4j_startup_error
    dataset_count = 0
    try:
        driver = await get_driver()
        _benchmark_repo = BenchmarkRepository(driver)
        await _init_seed_data()
        await load_default_benchmark_packs(_benchmark_repo)
        dataset_count = len(await _benchmark_repo.list_datasets(tenant_id="system"))
        _neo4j_startup_error = None
        logger.info("Layer 6 Benchmark Service started with %d datasets", dataset_count)
    except Exception as exc:  # pragma: no cover - exercised through readiness tests
        _benchmark_repo = None
        _neo4j_startup_error = "Neo4j benchmark store unavailable"
        logger.warning(
            "Layer 6 Benchmark Service starting degraded; Neo4j benchmark store unavailable",
            exc_info=exc,
        )

    yield
    await close_driver()
    _benchmark_repo = None


app = create_fabric_app(
    service_name=SERVICE_NAME,
    title="Value Fabric - Benchmark Service",
    description="Comparative intelligence and peer benchmarking API",
    version=SERVICE_VERSION,
    lifespan=lifespan,
    cors_policy=resolve_cors_policy(),
    telemetry_service_name=SERVICE_NAME,
    instrument_telemetry=True,
    enforce_tenant_context=True,
)

if app.state.telemetry_provider is not None:
    logger.info("L6: FastAPI instrumented with OpenTelemetry")

# Phase 1 Clerk integration: verify the Fabric4L internal AuthContext envelope.
# No-op when FABRIC_AUTH_PUBLIC_KEYS is unset.
from value_fabric.shared.identity.fabric_auth import register_fabric_auth_from_env  # noqa: E402

register_fabric_auth_from_env(app, service_name="layer6-benchmarks")

install_metrics_middleware(
    app,
    metrics=initialize_metrics(),
    middleware_factory=MetricsMiddleware,
    logger=logger,
)

_security_config_l6 = SecurityConfig.from_env(
    skip_validation_paths=frozenset({"/health", "/ready", "/metrics"}),
    strict_mode=True,
)
add_security_middleware(app, config=_security_config_l6)

# Register global exception handlers to prevent stack traces and sensitive data leaks
_l6_redis_client = None  # set below when GovernanceMiddleware wiring succeeds
try:
    from value_fabric.shared.error_handling import register_exception_handlers

    register_exception_handlers(app)
except ImportError:
    logger.warning("Shared error handling not available - exception handlers not registered")

try:
    from value_fabric.shared.identity.api_key_stub import reject_api_key_unsupported
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    from value_fabric.shared.identity.rate_limiter import RedisRateLimiter

    # The GovernanceMiddleware tenant kill-switch reads its Redis handle only
    # from the rate_limiter argument; without it every tenant-checked request
    # fails closed with 503 even when Redis is healthy (observed via the
    # Meridian certification journey, 2026-08-12). redis.from_url is lazy
    # (no connection at construction); the lifespan pings it and exposes it
    # on app.state.
    _l6_redis_url = os.getenv("REDIS_URL")
    _l6_redis_client = None
    if _l6_redis_url:
        import redis.asyncio as _redis_asyncio

        _l6_redis_client = _redis_asyncio.from_url(_l6_redis_url, decode_responses=True)

    app.add_middleware(
        GovernanceMiddleware,
        api_key_resolver=reject_api_key_unsupported,
        rate_limiter=RedisRateLimiter(_l6_redis_client) if _l6_redis_client is not None else None,
    )
    app.state.redis_client = _l6_redis_client
except ImportError as _gov_import_err:
    raise RuntimeError(
        "GovernanceMiddleware is required in all environments — "
        "shared.identity.middleware is not importable."
    ) from _gov_import_err


@app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
async def metrics_endpoint(request: Request):
    if not verify_metrics_access(request):
        raise AuthorizationError(message="Metrics endpoint requires internal access")

    metrics = get_metrics()
    if metrics is None:
        return Response(
            content="# Metrics collection is disabled",
            status_code=503,
            media_type="text/plain",
        )

    try:
        return Response(
            content=metrics.get_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    except Exception as exc:  # pragma: no cover - defensive only
        logger.error("Error generating metrics: %s", exc)
        return Response(
            content="# Error generating metrics exposition",
            status_code=500,
            media_type="text/plain",
        )


def _require_tenant_id(ctx: RequestContext | None) -> str:
    if ctx is None or not getattr(ctx, "tenant_id", None):
        raise AuthenticationError(message="Tenant context required")
    return str(ctx.tenant_id)


def _assert_global_benchmark_admin(ctx: RequestContext) -> None:
    if not (ctx.is_super_admin() or ctx.has_role("system")):
        raise AuthorizationError(message="Global benchmark baselines require privileged admin role")


async def health_check(request: Request):
    metrics = getattr(request.app.state, "metrics", None)
    if metrics is not None:
        metrics.set_health_status(True, service=SERVICE_NAME)
    return HealthCheckResult.model_validate(
        build_health_response(
            service_name=SERVICE_NAME,
            status="healthy",
            version=SERVICE_VERSION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            response_time_ms=0.0,
        )
    )


async def readiness_check() -> ReadinessCheckResult:
    checks: dict[str, dict[str, Any]] = {}

    try:
        validate_layer6_startup_settings()
        checks["config"] = {"status": "ok"}
    except Exception as exc:
        logger.error("Layer 6 startup settings validation failed: %s", exc)
        checks["config"] = {"status": "failed", "detail": "Configuration validation failed"}

    if _benchmark_repo is None and _neo4j_startup_error:
        neo4j_status = {"status": "unhealthy", "error": "Neo4j benchmark store unavailable"}
    else:
        neo4j_status = await neo4j_health_check()
    neo4j_ready = neo4j_status.get("status") == "healthy"
    checks["neo4j"] = {
        "status": "ok" if neo4j_ready else "failed",
        "detail": None if neo4j_ready else neo4j_status.get("error", "Neo4j health check failed"),
    }

    if _benchmark_repo is None:
        checks["benchmark_store"] = {
            "status": "failed",
            "detail": "Benchmark store not initialized",
        }
    else:
        try:
            dataset_count = len(await _benchmark_repo.list_datasets(tenant_id="system"))
            checks["benchmark_store"] = {
                "status": "ok" if dataset_count > 0 else "failed",
                "detail": None if dataset_count > 0 else "No benchmark datasets are loaded",
                "datasets_loaded": dataset_count,
            }
        except Exception as exc:
            logger.error("Benchmark store check failed: %s", exc)
            checks["benchmark_store"] = {
                "status": "failed",
                "detail": "Benchmark store check failed",
            }

    checks["startup"] = {
        "status": "ok" if _neo4j_startup_error is None else "failed",
        "detail": None if _neo4j_startup_error is None else "Neo4j benchmark store unavailable",
    }
    status = "ready" if all(check["status"] == "ok" for check in checks.values()) else "not_ready"
    return ReadinessCheckResult.model_validate(
        {
            "status": status,
            "service": SERVICE_NAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": SERVICE_VERSION,
            "checks": checks,
        }
    )


async def list_datasets(
    industry: str | None = None,
    segment: str | None = None,
    ctx: RequestContext = Depends(get_request_context),
):
    authorize_action("layer6.benchmarks.list", ctx)
    if _benchmark_repo is None:
        raise ServiceUnavailableError(message="Benchmark store not initialized")
    tenant_id = _require_tenant_id(ctx)
    datasets = await _benchmark_repo.list_datasets(
        industry=industry,
        segment=segment,
        tenant_id=tenant_id,
    )
    return [
        DatasetSummary(
            dataset_id=d.dataset_id,
            name=d.name,
            description=d.description,
            industry=d.industry,
            segment=d.segment,
            geography=d.geography,
            metrics=list(d.metrics.keys()),
            metric_count=len(d.metrics),
            version=d.version,
            data_source=d.data_source,
        )
        for d in datasets
    ]


async def get_dataset(dataset_id: str, ctx: RequestContext = Depends(get_request_context)):
    authorize_action("layer6.benchmarks.read", ctx)
    if _benchmark_repo is None:
        raise ServiceUnavailableError(message="Benchmark store not initialized")
    tenant_id = _require_tenant_id(ctx)
    dataset = await _benchmark_repo.get_dataset(dataset_id, tenant_id=tenant_id)
    if not dataset:
        raise NotFoundError(message="Dataset not found")

    return DatasetDetail(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        description=dataset.description,
        industry=dataset.industry,
        segment=dataset.segment,
        geography=dataset.geography,
        metrics={
            name: {
                "name": metric.name,
                "unit": metric.unit,
                "description": metric.description,
                "profile": metric.profile.to_dict(),
            }
            for name, metric in dataset.metrics.items()
        },
        version=dataset.version,
        data_source=dataset.data_source,
    )


async def compare(
    payload: ComparisonRequestPayload, ctx: RequestContext = Depends(get_request_context)
):
    authorize_action("layer6.benchmarks.compare", ctx)
    if _benchmark_repo is None:
        raise ServiceUnavailableError(message="Benchmark store not initialized")
    tenant_id = _require_tenant_id(ctx)
    dataset = await _benchmark_repo.get_dataset(payload.dataset_id, tenant_id=tenant_id)
    if not dataset:
        _record_compare_metric(industry=payload.industry, outcome="dataset_not_found")
        raise NotFoundError(message="Dataset not found")

    metric = dataset.get_metric(payload.metric)
    if not metric:
        _record_compare_metric(industry=dataset.industry, outcome="metric_not_found")
        raise NotFoundError(message=str(f"Metric '{payload.metric}' not found"))

    try:
        company_value = Decimal(payload.company_value)
    except (ValueError, decimal.InvalidOperation):
        _record_compare_metric(industry=dataset.industry, outcome="invalid_input")
        raise ValidationError(message="Invalid company_value format")

    profile = metric.profile
    if company_value <= profile.p10:
        distribution_percentile = 5
    elif company_value <= profile.p25:
        distribution_percentile = 17
    elif company_value <= profile.p50:
        distribution_percentile = 37
    elif company_value <= profile.p75:
        distribution_percentile = 62
    elif company_value <= profile.p90:
        distribution_percentile = 82
    else:
        distribution_percentile = 95

    # For lower-is-better metrics, invert the distribution percentile so the
    # percentile and bucket reflect performance rather than raw position.
    if metric.is_higher_better:
        percentile = distribution_percentile
    else:
        percentile = 100 - distribution_percentile

    if percentile >= 80:
        assessment = "top_performer"
    elif percentile >= 60:
        assessment = "above_average"
    elif percentile >= 40:
        assessment = "average"
    elif percentile >= 20:
        assessment = "below_average"
    else:
        assessment = "needs_improvement"

    if profile.sample_size >= 1000:
        confidence = "high"
    elif profile.sample_size >= 500:
        confidence = "medium"
    else:
        confidence = "low"

    _record_compare_metric(industry=dataset.industry, outcome="success")

    # Audit: benchmark comparison
    try:
        from value_fabric.shared.audit import AuditAction, emit_audit_event

        emit_audit_event(
            AuditAction.BENCHMARK_COMPARED,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            resource_type="BenchmarkDataset",
            resource_id=payload.dataset_id,
            outcome="success",
            details={
                "industry": dataset.industry,
                "metric": payload.metric,
                "company_value": str(payload.company_value),
                "percentile": percentile,
                "assessment": assessment,
            },
        )
    except Exception:
        logger.exception("Audit logging failed for benchmark compare")

    return ComparisonResponse(
        percentile=percentile,
        peer_median=str(profile.p50),
        peer_range=(str(profile.p10), str(profile.p90)),
        sample_size=profile.sample_size,
        confidence=confidence,
        assessment=assessment,
    )


async def validate(
    payload: ValidationRequestPayload, ctx: RequestContext = Depends(get_request_context)
):
    authorize_action("layer6.benchmarks.validate", ctx)
    if _benchmark_repo is None:
        raise ServiceUnavailableError(message="Benchmark store not initialized")
    tenant_id = _require_tenant_id(ctx)
    dataset = await _benchmark_repo.get_dataset(payload.dataset_id, tenant_id=tenant_id)
    if not dataset:
        raise NotFoundError(message="Dataset not found")

    metric = dataset.get_metric(payload.metric)
    if not metric:
        raise NotFoundError(message=str(f"Metric '{payload.metric}' not found"))

    try:
        value = Decimal(payload.value)
    except (ValueError, decimal.InvalidOperation):
        raise ValidationError(message="Invalid value format")

    profile = metric.profile
    tolerance_factor = Decimal(payload.tolerance_percent) / Decimal(100)
    range_min = profile.p10 * (Decimal(1) - tolerance_factor)
    range_max = profile.p90 * (Decimal(1) + tolerance_factor)
    is_valid = range_min <= value <= range_max

    median = profile.p50
    deviation_percent = 0.0 if value == median else float((value - median) / median * 100)
    if is_valid:
        severity = "info"
        message = f"Value {value} is within expected range ({range_min} - {range_max})"
    else:
        abs_deviation = abs(deviation_percent)
        if abs_deviation > 50:
            severity = "error"
            message = f"Value {value} significantly deviates from benchmark median ({median})"
        elif abs_deviation > 25:
            severity = "warning"
            message = f"Value {value} moderately deviates from benchmark median ({median})"
        else:
            severity = "info"
            message = f"Value {value} slightly outside tolerance range"

    # Audit: benchmark validation
    try:
        from value_fabric.shared.audit import AuditAction, emit_audit_event

        emit_audit_event(
            AuditAction.BENCHMARK_VALIDATED,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            resource_type="BenchmarkDataset",
            resource_id=payload.dataset_id,
            outcome="success",
            details={
                "industry": dataset.industry,
                "metric": payload.metric,
                "value": str(payload.value),
                "is_valid": is_valid,
                "severity": severity,
                "deviation_percent": deviation_percent,
            },
        )
    except Exception:
        logger.exception("Audit logging failed for benchmark validate")

    return ValidationResponse(
        is_valid=is_valid,
        expected_range=(str(range_min), str(range_max)),
        actual_value=str(value),
        deviation_percent=deviation_percent,
        severity=severity,
        message=message,
    )


async def list_industries(ctx: RequestContext = Depends(get_request_context)):
    authorize_action("layer6.benchmarks.industries", ctx)
    if _benchmark_repo is None:
        raise ServiceUnavailableError(message="Benchmark store not initialized")
    tenant_id = _require_tenant_id(ctx)
    datasets = await _benchmark_repo.list_datasets(tenant_id=tenant_id)
    return ListIndustriesResult.model_validate(
        {"industries": sorted({d.industry for d in datasets})}
    )


async def upsert_dataset(
    payload: DatasetUpsertPayload, ctx: RequestContext = Depends(get_request_context)
):
    authorize_action("layer6.benchmarks.write", ctx)
    if _benchmark_repo is None:
        raise ServiceUnavailableError(message="Benchmark store not initialized")
    tenant_id = _require_tenant_id(ctx)
    if payload.ownership_mode not in {"tenant", "global_system"}:
        raise ValidationError(message="ownership_mode must be one of: tenant, global_system")

    dataset_tenant_id = tenant_id
    if payload.ownership_mode == "global_system":
        _assert_global_benchmark_admin(ctx)
        dataset_tenant_id = "system"

    existing = await _benchmark_repo.get_dataset(payload.dataset_id, tenant_id=tenant_id)
    if existing and existing.ownership_mode == "global_system":
        _assert_global_benchmark_admin(ctx)

    dataset = BenchmarkDataset(
        dataset_id=payload.dataset_id,
        name=payload.name,
        description=payload.description,
        industry=payload.industry,
        segment=payload.segment,
        geography=payload.geography,
        version=payload.version,
        data_source=payload.data_source,
        is_public=payload.is_public,
        tenant_id=dataset_tenant_id,
        ownership_mode=payload.ownership_mode,
    )
    for metric_name, metric in payload.metrics.items():
        dataset.add_metric(
            BenchmarkMetric(
                name=metric.get("name", metric_name),
                unit=metric["unit"],
                description=metric["description"],
                profile=StatisticalProfile.from_dict(metric["profile"]),
            )
        )
    await _benchmark_repo.save_dataset(dataset)
    return {"dataset_id": payload.dataset_id, "ownership_mode": payload.ownership_mode}


register_health_endpoint(app, service_name=SERVICE_NAME, handler=health_check)
app.include_router(system.router)
app.include_router(benchmarks.router)

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8006"))
    uvicorn.run(app, host="0.0.0.0", port=port)  # nosec B104
