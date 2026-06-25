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
from ..models.valueos_contracts import validate_vmrt_trace
from ..models.vmrt_trace import VMRTTraceRecord
from ..repositories.benchmark_repository import BenchmarkRepository
from ..repositories.vmrt_trace_repository import VMRTTraceRepository
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
    BenchmarkProvenanceResponse,
    CompareDistributionRequestPayload,
    CompareDistributionResponse,
    ComparisonRequestPayload,
    ComparisonResponse,
    CoverageCell,
    CoverageStatusResponse,
    DatasetDetail,
    DatasetSummary,
    DatasetUpsertPayload,
    MetricCatalogItem,
    MetricCatalogResponse,
    MetricProvenanceRequestPayload,
    PercentileDistributionResponse,
    RecommendRangeRequestPayload,
    RecommendRangeResponse,
    ValidateValueRequestPayload,
    ValidateValueResponse,
    ValidationRequestPayload,
    ValidationResponse,
    VMRTTracePromotionRequestPayload,
    VMRTTraceRecordResponse,
    VMRTTraceUpsertRequestPayload,
    VMRTValidationRequestPayload,
    VMRTValidationResponse,
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
_vmrt_trace_repo: VMRTTraceRepository | None = None
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


def _confidence_for_sample_size(sample_size: int) -> str:
    if sample_size >= 1000:
        return "high"
    if sample_size >= 500:
        return "medium"
    return "low"


def _confidence_score_for_sample_size(sample_size: int) -> float:
    if sample_size >= 1000:
        return 0.9
    if sample_size >= 500:
        return 0.7
    return 0.45


def _profile_response(
    profile: StatisticalProfile, *, shape: str = "unknown"
) -> PercentileDistributionResponse:
    return PercentileDistributionResponse(
        p10=str(profile.p10),
        p25=str(profile.p25),
        p50=str(profile.p50),
        p75=str(profile.p75),
        p90=str(profile.p90),
        mean=str(profile.mean),
        std_dev=str(profile.std_dev),
        sample_size=profile.sample_size,
        shape=shape,
    )


def _provenance_response(
    *, dataset: BenchmarkDataset, metric: BenchmarkMetric
) -> BenchmarkProvenanceResponse:
    confidence_score = (
        metric.confidence_score
        if metric.confidence_score is not None
        else _confidence_score_for_sample_size(metric.profile.sample_size)
    )
    return BenchmarkProvenanceResponse(
        metric=metric.name,
        dataset_id=dataset.dataset_id,
        data_source=metric.source_name or dataset.data_source,
        source_count=metric.source_count or (1 if dataset.data_source else 0),
        confidence=_confidence_for_sample_size(metric.profile.sample_size),
        confidence_score=confidence_score,
        license_class=metric.license_class,
        caveats=metric.caveats,
    )


def _distribution_percentile(*, company_value: Decimal, metric: BenchmarkMetric) -> int:
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

    if metric.is_higher_better:
        return distribution_percentile
    return 100 - distribution_percentile


def _assessment_for_percentile(percentile: int) -> str:
    if percentile >= 80:
        return "top_performer"
    if percentile >= 60:
        return "above_average"
    if percentile >= 40:
        return "average"
    if percentile >= 20:
        return "below_average"
    return "needs_improvement"


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

    metrics = getattr(app.state, "metrics", None)
    if metrics is not None:
        logger.info("Prometheus metrics initialized")
        metrics.set_build_info(
            service=runtime_metadata["service"],
            version=runtime_metadata["version"],
            build_sha=runtime_metadata["build_sha"],
        )

    global _benchmark_repo, _vmrt_trace_repo, _neo4j_startup_error
    dataset_count = 0
    try:
        driver = await get_driver()
        _benchmark_repo = BenchmarkRepository(driver)
        _vmrt_trace_repo = VMRTTraceRepository(driver)
        await _init_seed_data()
        await load_default_benchmark_packs(_benchmark_repo)
        dataset_count = len(await _benchmark_repo.list_datasets(tenant_id="system"))
        _neo4j_startup_error = None
        logger.info("Layer 6 Benchmark Service started with %d datasets", dataset_count)
    except Exception as exc:  # pragma: no cover - exercised through readiness tests
        _benchmark_repo = None
        _vmrt_trace_repo = None
        _neo4j_startup_error = "Neo4j benchmark store unavailable"
        logger.warning(
            "Layer 6 Benchmark Service starting degraded; Neo4j benchmark store unavailable",
            exc_info=exc,
        )

    yield
    await close_driver()
    _benchmark_repo = None
    _vmrt_trace_repo = None


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
try:
    from value_fabric.shared.error_handling import register_exception_handlers

    register_exception_handlers(app)
except ImportError:
    logger.warning("Shared error handling not available - exception handlers not registered")

try:
    from value_fabric.shared.identity.api_key_stub import reject_api_key_unsupported
    from value_fabric.shared.identity.middleware import GovernanceMiddleware

    app.add_middleware(GovernanceMiddleware, api_key_resolver=reject_api_key_unsupported)
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


async def _get_dataset_metric(
    *, dataset_id: str, metric_name: str, ctx: RequestContext
) -> tuple[BenchmarkDataset, BenchmarkMetric]:
    if _benchmark_repo is None:
        raise ServiceUnavailableError(message="Benchmark store not initialized")
    tenant_id = _require_tenant_id(ctx)
    dataset = await _benchmark_repo.get_dataset(dataset_id, tenant_id=tenant_id)
    if not dataset:
        raise NotFoundError(message="Dataset not found")

    metric = dataset.get_metric(metric_name)
    if not metric:
        raise NotFoundError(message=str(f"Metric '{metric_name}' not found"))
    return dataset, metric


async def recommend_range(
    payload: RecommendRangeRequestPayload, ctx: RequestContext = Depends(get_request_context)
):
    authorize_action("layer6.benchmarks.recommend_range", ctx)
    dataset, metric = await _get_dataset_metric(
        dataset_id=payload.dataset_id, metric_name=payload.metric, ctx=ctx
    )
    return RecommendRangeResponse(
        dataset_id=dataset.dataset_id,
        metric=metric.name,
        industry=dataset.industry,
        segment=dataset.segment,
        unit=metric.unit,
        distribution=_profile_response(metric.profile, shape=metric.distribution_shape),
        provenance=_provenance_response(dataset=dataset, metric=metric),
    )


async def compare_distribution(
    payload: CompareDistributionRequestPayload, ctx: RequestContext = Depends(get_request_context)
):
    authorize_action("layer6.benchmarks.compare_distribution", ctx)
    dataset, metric = await _get_dataset_metric(
        dataset_id=payload.dataset_id, metric_name=payload.metric, ctx=ctx
    )
    try:
        company_value = Decimal(payload.company_value)
    except (ValueError, decimal.InvalidOperation):
        raise ValidationError(message="Invalid company_value format")

    profile = metric.profile
    percentile = _distribution_percentile(company_value=company_value, metric=metric)
    median = profile.p50
    variance_from_median_percent = (
        0.0 if company_value == median else float((company_value - median) / median * 100)
    )

    _record_compare_metric(industry=dataset.industry, outcome="success")
    return CompareDistributionResponse(
        dataset_id=dataset.dataset_id,
        metric=metric.name,
        company_value=str(company_value),
        percentile=percentile,
        variance_from_median_percent=variance_from_median_percent,
        peer_median=str(profile.p50),
        peer_range=(str(profile.p10), str(profile.p90)),
        sample_size=profile.sample_size,
        confidence=_confidence_for_sample_size(profile.sample_size),
        assessment=_assessment_for_percentile(percentile),
        distribution=_profile_response(profile, shape=metric.distribution_shape),
        provenance=_provenance_response(dataset=dataset, metric=metric),
    )


async def validate_value(
    payload: ValidateValueRequestPayload, ctx: RequestContext = Depends(get_request_context)
):
    authorize_action("layer6.benchmarks.validate_value", ctx)
    dataset, metric = await _get_dataset_metric(
        dataset_id=payload.dataset_id, metric_name=payload.metric, ctx=ctx
    )
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
        message = f"Value {value} is within expected p10-p90 range ({range_min} - {range_max})"
    else:
        abs_deviation = abs(deviation_percent)
        if abs_deviation > 50:
            severity = "error"
        elif abs_deviation > 25:
            severity = "warning"
        else:
            severity = "info"
        message = f"Value {value} is outside expected p10-p90 range ({range_min} - {range_max})"

    return ValidateValueResponse(
        dataset_id=dataset.dataset_id,
        metric=metric.name,
        is_valid=is_valid,
        expected_range=(str(range_min), str(range_max)),
        actual_value=str(value),
        deviation_percent=deviation_percent,
        severity=severity,
        message=message,
        distribution=_profile_response(profile, shape=metric.distribution_shape),
        provenance=_provenance_response(dataset=dataset, metric=metric),
    )


async def list_metric_catalog(
    industry: str | None = None,
    segment: str | None = None,
    ctx: RequestContext = Depends(get_request_context),
):
    authorize_action("layer6.benchmarks.metric_catalog", ctx)
    if _benchmark_repo is None:
        raise ServiceUnavailableError(message="Benchmark store not initialized")
    tenant_id = _require_tenant_id(ctx)
    datasets = await _benchmark_repo.list_datasets(
        industry=industry,
        segment=segment,
        tenant_id=tenant_id,
    )
    items: list[MetricCatalogItem] = []
    for dataset in datasets:
        for metric in dataset.metrics.values():
            items.append(
                MetricCatalogItem(
                    dataset_id=dataset.dataset_id,
                    metric=metric.name,
                    display_name=metric.name.replace("_", " ").title(),
                    description=metric.description,
                    industry=dataset.industry,
                    segment=dataset.segment,
                    geography=dataset.geography,
                    unit=metric.unit,
                    sample_size=metric.profile.sample_size,
                    confidence=_confidence_for_sample_size(metric.profile.sample_size),
                )
            )
    return MetricCatalogResponse(metrics=items)


async def get_metric_provenance(
    payload: MetricProvenanceRequestPayload, ctx: RequestContext = Depends(get_request_context)
):
    authorize_action("layer6.benchmarks.metric_provenance", ctx)
    dataset, metric = await _get_dataset_metric(
        dataset_id=payload.dataset_id, metric_name=payload.metric, ctx=ctx
    )
    return _provenance_response(dataset=dataset, metric=metric)


async def get_coverage_status(ctx: RequestContext = Depends(get_request_context)):
    authorize_action("layer6.benchmarks.coverage", ctx)
    if _benchmark_repo is None:
        raise ServiceUnavailableError(message="Benchmark store not initialized")
    tenant_id = _require_tenant_id(ctx)
    datasets = await _benchmark_repo.list_datasets(tenant_id=tenant_id)
    required_industries = [
        "technology",
        "financial_services",
        "healthcare",
        "manufacturing",
        "retail",
    ]
    counts: dict[str, int] = {industry: 0 for industry in required_industries}
    for dataset in datasets:
        counts[dataset.industry] = counts.get(dataset.industry, 0) + len(dataset.metrics)

    cells = [
        CoverageCell(
            industry=industry,
            metric_count=metric_count,
            status=(
                "complete"
                if metric_count >= 20
                else "partial"
                if metric_count > 0
                else "empty"
            ),
        )
        for industry, metric_count in sorted(counts.items())
    ]
    missing_required_industries = [
        industry for industry in required_industries if counts.get(industry, 0) == 0
    ]
    return CoverageStatusResponse(
        total_metrics=sum(counts.values()),
        industries=cells,
        required_industries=required_industries,
        missing_required_industries=missing_required_industries,
    )


async def validate_vmrt(
    payload: VMRTValidationRequestPayload, ctx: RequestContext = Depends(get_request_context)
):
    authorize_action("layer6.benchmarks.vmrt.validate", ctx)
    _require_tenant_id(ctx)
    return _evaluate_vmrt_trace(
        trace_payload=payload.trace,
        min_quality_score=payload.min_quality_score,
    )


def _evaluate_vmrt_trace(
    *, trace_payload: dict[str, Any], min_quality_score: float
) -> VMRTValidationResponse:
    try:
        trace = validate_vmrt_trace(trace_payload)
    except Exception as exc:
        return VMRTValidationResponse(
            is_valid=False,
            trace_id=trace_payload.get("trace_id"),
            schema_version=trace_payload.get("schema_version"),
            production_ready=False,
            quality_score_overall=None,
            errors=[str(exc)],
        )

    score_values = [
        trace.quality_scores.logical_coherence,
        trace.quality_scores.benchmark_alignment,
        trace.quality_scores.financial_rigor,
        trace.quality_scores.story_clarity,
        trace.quality_scores.overall,
    ]
    production_ready = all(score >= Decimal(str(min_quality_score)) for score in score_values)
    return VMRTValidationResponse(
        is_valid=True,
        trace_id=trace.trace_id,
        schema_version=trace.schema_version,
        production_ready=production_ready,
        quality_score_overall=str(trace.quality_scores.overall),
        errors=[],
    )


def _vmrt_trace_response(
    record: VMRTTraceRecord, *, include_trace: bool = False
) -> VMRTTraceRecordResponse:
    return VMRTTraceRecordResponse(
        trace_id=record.trace_id,
        schema_version=record.schema_version,
        status=record.status,
        production_ready=record.production_ready,
        quality_score_overall=record.quality_score_overall,
        errors=record.errors,
        reviewer=record.reviewer,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
        promoted_at=record.promoted_at.isoformat() if record.promoted_at else None,
        trace=record.trace if include_trace else None,
    )


async def upsert_vmrt_trace(
    payload: VMRTTraceUpsertRequestPayload, ctx: RequestContext = Depends(get_request_context)
):
    authorize_action("layer6.benchmarks.vmrt.write", ctx)
    if _vmrt_trace_repo is None:
        raise ServiceUnavailableError(message="VMRT trace store not initialized")
    tenant_id = _require_tenant_id(ctx)
    evaluation = _evaluate_vmrt_trace(
        trace_payload=payload.trace,
        min_quality_score=payload.min_quality_score,
    )
    if not evaluation.is_valid:
        raise ValidationError(
            message="VMRT trace failed schema or linkage validation",
            details={"errors": evaluation.errors},
        )

    trace = validate_vmrt_trace(payload.trace)
    status = "production_ready" if evaluation.production_ready else payload.status
    trace_payload = trace.model_dump(mode="json")
    record = VMRTTraceRecord(
        trace_id=trace.trace_id,
        tenant_id=tenant_id,
        schema_version=trace.schema_version,
        status=status,
        trace=trace_payload,
        quality_score_overall=evaluation.quality_score_overall,
        production_ready=evaluation.production_ready,
        errors=evaluation.errors,
    )
    saved = await _vmrt_trace_repo.save_trace(record)
    return _vmrt_trace_response(saved, include_trace=True)


async def get_vmrt_trace(
    trace_id: str, ctx: RequestContext = Depends(get_request_context)
) -> VMRTTraceRecordResponse:
    authorize_action("layer6.benchmarks.vmrt.read", ctx)
    if _vmrt_trace_repo is None:
        raise ServiceUnavailableError(message="VMRT trace store not initialized")
    tenant_id = _require_tenant_id(ctx)
    record = await _vmrt_trace_repo.get_trace(trace_id, tenant_id=tenant_id)
    if record is None:
        raise NotFoundError(message="VMRT trace not found")
    return _vmrt_trace_response(record, include_trace=True)


async def promote_vmrt_trace(
    trace_id: str,
    payload: VMRTTracePromotionRequestPayload,
    ctx: RequestContext = Depends(get_request_context),
) -> VMRTTraceRecordResponse:
    authorize_action("layer6.benchmarks.vmrt.promote", ctx)
    if _vmrt_trace_repo is None:
        raise ServiceUnavailableError(message="VMRT trace store not initialized")
    tenant_id = _require_tenant_id(ctx)
    existing = await _vmrt_trace_repo.get_trace(trace_id, tenant_id=tenant_id)
    if existing is None:
        raise NotFoundError(message="VMRT trace not found")

    evaluation = _evaluate_vmrt_trace(
        trace_payload=existing.trace,
        min_quality_score=payload.min_quality_score,
    )
    if not evaluation.is_valid:
        raise ValidationError(
            message="VMRT trace failed schema or linkage validation",
            details={"errors": evaluation.errors},
        )
    if not evaluation.production_ready:
        raise ValidationError(
            message="VMRT trace quality scores are below production readiness threshold",
            details={
                "trace_id": trace_id,
                "quality_score_overall": evaluation.quality_score_overall,
            },
        )

    promoted = await _vmrt_trace_repo.promote_trace(
        trace_id,
        tenant_id=tenant_id,
        reviewer=payload.reviewer,
    )
    if promoted is None:
        raise ValidationError(message="VMRT trace is not production ready")
    return _vmrt_trace_response(promoted, include_trace=True)


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
