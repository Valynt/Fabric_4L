from __future__ import annotations

"""Prometheus metrics collection for Layer 6 Benchmark Service."""


import hashlib
import logging
import time
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Info, generate_latest

from ..observability.metrics_contract import metric_spec_map

try:
    from value_fabric.shared.observability import PathNormalizer
except ImportError:  # pragma: no cover
    PathNormalizer = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

SERVICE_NAME = "layer6-benchmarks"
_L6_KNOWN_ROUTES: dict[str, str] = {
    "/": "/",
    "/health": "/health",
    "/ready": "/ready",
    "/metrics": "/metrics",
    "/docs": "/docs",
    "/redoc": "/redoc",
    "/openapi.json": "/openapi.json",
    "/v1/benchmarks/datasets": "/v1/benchmarks/datasets",
    "/v1/benchmarks/datasets/{dataset_id}": "/v1/benchmarks/datasets/{id}",
    "/v1/benchmarks/compare": "/v1/benchmarks/compare",
    "/v1/benchmarks/validate": "/v1/benchmarks/validate",
    "/v1/benchmarks/industries": "/v1/benchmarks/industries",
}


class MetricsConfig:
    """Configuration for metrics collection."""

    def __init__(
        self,
        enabled: bool = True,
        registry: CollectorRegistry | None = None,
        default_buckets: list[float] | None = None,
    ) -> None:
        self.enabled = enabled
        self.registry = registry or CollectorRegistry()
        self.default_buckets = default_buckets or [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]


class PrometheusMetrics:
    """Prometheus metrics collector for Layer 6 Benchmark Service."""

    def __init__(self, config: MetricsConfig | None = None) -> None:
        self.config = config or MetricsConfig()
        self._metrics: dict[str, Any] = {}
        self._setup_metrics()

    def _setup_metrics(self) -> None:
        specs = metric_spec_map()

        self._metrics["requests_total"] = Counter(
            specs["layer6_requests_total"].name,
            specs["layer6_requests_total"].description,
            list(specs["layer6_requests_total"].labels),
            registry=self.config.registry,
        )
        self._metrics["request_duration"] = Histogram(
            specs["layer6_request_duration_seconds"].name,
            specs["layer6_request_duration_seconds"].description,
            list(specs["layer6_request_duration_seconds"].labels),
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )
        self._metrics["dataset_comparisons_total"] = Counter(
            specs["layer6_dataset_comparisons_total"].name,
            specs["layer6_dataset_comparisons_total"].description,
            list(specs["layer6_dataset_comparisons_total"].labels),
            registry=self.config.registry,
        )
        self._metrics["errors_total"] = Counter(
            specs["layer6_errors_total"].name,
            specs["layer6_errors_total"].description,
            list(specs["layer6_errors_total"].labels),
            registry=self.config.registry,
        )
        self._metrics["auth_failures_total"] = Counter(
            specs["layer6_auth_failures_total"].name,
            specs["layer6_auth_failures_total"].description,
            list(specs["layer6_auth_failures_total"].labels),
            registry=self.config.registry,
        )
        self._metrics["health_status"] = Gauge(
            specs["layer6_health_status"].name,
            specs["layer6_health_status"].description,
            list(specs["layer6_health_status"].labels),
            registry=self.config.registry,
        )
        self._metrics["build_info"] = Info(
            "layer6_build_info",
            "Build information for the Layer 6 benchmark service",
            registry=self.config.registry,
        )
        self.set_health_status(True, service=SERVICE_NAME)

    @staticmethod
    def _status_class(status_code: int | str) -> str:
        code = int(status_code)
        return f"{code // 100}xx"

    @staticmethod
    def _tenant_bucket(tenant_id: str) -> str:
        if not tenant_id or tenant_id == "unknown":
            return "unknown"
        digest = hashlib.sha256(tenant_id.encode("utf-8")).digest()
        return f"bucket_{digest[0] % 64:02d}"

    def increment_requests_total(
        self,
        *,
        method: str,
        route: str,
        status_code: int | str,
        tenant_id: str = "unknown",
    ) -> None:
        if not self.config.enabled:
            return
        self._metrics["requests_total"].labels(
            route=route,
            method=method,
            status_class=self._status_class(status_code),
            tenant_bucket=self._tenant_bucket(tenant_id),
        ).inc()

    def observe_request_duration(
        self,
        *,
        duration: float,
        method: str,
        route: str,
        tenant_id: str = "unknown",
    ) -> None:
        if not self.config.enabled:
            return
        self._metrics["request_duration"].labels(
            route=route,
            method=method,
            tenant_bucket=self._tenant_bucket(tenant_id),
        ).observe(duration)

    def increment_dataset_comparisons(self, *, industry: str, outcome: str) -> None:
        if not self.config.enabled:
            return
        self._metrics["dataset_comparisons_total"].labels(industry=industry, outcome=outcome).inc()

    def set_health_status(self, healthy: bool, *, service: str = SERVICE_NAME) -> None:
        if not self.config.enabled:
            return
        self._metrics["health_status"].labels(service=service).set(1 if healthy else 0)

    def set_build_info(self, *, version: str, build_sha: str, service: str = SERVICE_NAME) -> None:
        if not self.config.enabled:
            return
        self._metrics["build_info"].info(
            {"service": service, "version": version, "build_sha": build_sha}
        )

    def increment_errors(self, *, error_type: str, component: str) -> None:
        """Record an error by type and component."""
        if not self.config.enabled:
            return
        self._metrics["errors_total"].labels(error_type=error_type, component=component).inc()

    def increment_auth_failure(self, *, reason: str, component: str = "http") -> None:
        """Record an authentication/authorization failure.

        `reason` should be a bounded token such as "missing_token",
        "invalid_token", "insufficient_role", "tenant_mismatch".
        """
        if not self.config.enabled:
            return
        self._metrics["auth_failures_total"].labels(reason=reason, component=component).inc()

    def get_metrics(self) -> str:
        if not self.config.enabled:
            return ""
        return generate_latest(self.config.registry).decode("utf-8")


_metrics: PrometheusMetrics | None = None


def get_metrics() -> PrometheusMetrics | None:
    return _metrics


def initialize_metrics(config: MetricsConfig | None = None) -> PrometheusMetrics:
    global _metrics
    _metrics = PrometheusMetrics(config)
    logger.info("Layer 6 Prometheus metrics initialized")
    return _metrics


class MetricsMiddleware:
    """FastAPI middleware for collecting bounded-cardinality HTTP metrics."""

    def __init__(self, metrics: PrometheusMetrics) -> None:
        self.metrics = metrics
        self._normalizer = (
            PathNormalizer(known_routes=_L6_KNOWN_ROUTES) if PathNormalizer is not None else None
        )

    def _normalize_path(self, path: str) -> str:
        if self._normalizer is None:
            path = path.rstrip("/") if path else ""
            return path or "/"
        return self._normalizer.normalize(path)

    async def __call__(self, request, call_next):
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            route = self._normalize_path(request.url.path)
            duration = time.perf_counter() - start_time
            context = getattr(request.state, "governance_context", None)
            tenant_id = str(getattr(context, "tenant_id", None) or "unknown")
            self.metrics.increment_requests_total(
                method=request.method,
                route=route,
                status_code=status_code,
                tenant_id=tenant_id,
            )
            self.metrics.observe_request_duration(
                duration=duration,
                method=request.method,
                route=route,
                tenant_id=tenant_id,
            )
            if status_code == 401:
                self.metrics.increment_auth_failure(reason="missing_token", component="http")
            elif status_code == 403:
                self.metrics.increment_auth_failure(reason="insufficient_role", component="http")
            elif status_code >= 400:
                error_type = "client_error" if status_code < 500 else "server_error"
                self.metrics.increment_errors(error_type=error_type, component="http")
        return response

    async def dispatch(self, request, call_next):
        return await self.__call__(request, call_next)
