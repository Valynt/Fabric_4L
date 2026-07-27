"""Prometheus metrics collection for Layer 5 Ground Truth."""

import hashlib
import logging
import time
from typing import Any

try:
    from layer5_ground_truth import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.1.0"

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

try:
    from value_fabric.shared.observability import PathNormalizer
except ImportError:  # pragma: no cover - shared package not on path in some test envs
    PathNormalizer = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _tenant_bucket(tenant_id: str, count: int = 64) -> str:
    """Return a stable low-cardinality bucket label for a tenant_id.

    Raw tenant IDs are high-cardinality and sensitive; we hash them into a
    fixed set of buckets so Prometheus labels stay bounded.
    """
    if not tenant_id or tenant_id == "unknown":
        return "unknown"
    digest = hashlib.sha256(tenant_id.encode("utf-8")).digest()
    return f"bucket_{digest[0] % count:02d}"


class MetricsConfig:
    """Configuration for metrics collection."""

    def __init__(
        self,
        enabled: bool = True,
        registry: CollectorRegistry | None = None,
        prefix: str = "layer5_",
        label_namespace: str = "ground_truth",
        default_buckets: list[float] | None = None,
    ):
        self.enabled = enabled
        self.registry = registry or CollectorRegistry()
        self.prefix = prefix
        self.label_namespace = label_namespace
        self.default_buckets = default_buckets or [
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
            25.0,
            50.0,
        ]


class PrometheusMetrics:
    """Prometheus metrics collector for Layer 5 Ground Truth."""

    def __init__(self, config: MetricsConfig | None = None):
        self.config = config or MetricsConfig()
        self._metrics: dict[str, Any] = {}
        self._setup_metrics()

    def _setup_metrics(self) -> None:
        """Setup all Prometheus metrics."""
        prefix = self.config.prefix

        # HTTP request metrics — endpoint is normalized via PathNormalizer
        # in the middleware; tenant_id is hashed to a bucket to bound cardinality.
        self._metrics["requests_total"] = Counter(
            f"{prefix}http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_class", "tenant_bucket"],
            registry=self.config.registry,
        )

        self._metrics["request_duration"] = Histogram(
            f"{prefix}http_request_duration_seconds",
            "HTTP request duration",
            ["method", "endpoint", "tenant_bucket"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        # Truth object metrics
        self._metrics["truth_objects_total"] = Counter(
            f"{prefix}truth_objects_total",
            "Total truth objects created",
            ["claim_type", "status"],
            registry=self.config.registry,
        )

        self._metrics["validations_total"] = Counter(
            f"{prefix}validations_total",
            "Total validation state transitions",
            ["from_status", "to_status"],
            registry=self.config.registry,
        )
        self._metrics["validation_latency_seconds"] = Histogram(
            f"{prefix}validation_latency_seconds",
            "Validation transition latency in seconds",
            ["transition"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )
        self._metrics["validation_transition_failures_total"] = Counter(
            f"{prefix}validation_transition_failures_total",
            "Total failed validation transitions",
            ["transition", "reason"],
            registry=self.config.registry,
        )

        self._metrics["truth_objects_by_status"] = Gauge(
            f"{prefix}truth_objects_by_status",
            "Current truth objects by status",
            ["status", "claim_type"],
            registry=self.config.registry,
        )

        self._metrics["sources_added_total"] = Counter(
            f"{prefix}sources_added_total",
            "Total evidence sources added",
            registry=self.config.registry,
        )

        self._metrics["kg_sync_total"] = Counter(
            f"{prefix}kg_sync_total",
            "Total knowledge graph sync operations",
            ["status"],
            registry=self.config.registry,
        )
        self._metrics["kg_sync_outcomes_total"] = Counter(
            f"{prefix}kg_sync_outcomes_total",
            "Layer 3 KG sync outcomes by transition context",
            ["sync_status", "transition"],
            registry=self.config.registry,
        )

        self._metrics["freshness_checks_total"] = Counter(
            f"{prefix}freshness_checks_total",
            "Total freshness monitoring checks",
            registry=self.config.registry,
        )

        # Gauge (not Counter): reflects the *current* number of stale objects so
        # alert rules using `> threshold` correctly clear when staleness is
        # remediated. A Counter only increases and would keep alerts firing
        # forever once any staleness is observed.
        self._metrics["stale_objects_detected"] = Gauge(
            f"{prefix}stale_objects_detected",
            "Number of stale ground-truth objects currently detected",
            registry=self.config.registry,
        )

        # Active connections
        self._metrics["active_connections"] = Gauge(
            f"{prefix}active_connections",
            "Number of active connections",
            ["connection_type"],
            registry=self.config.registry,
        )

        # Health status gauge (for alerting)
        self._metrics["health_status"] = Gauge(
            f"{prefix}health_status",
            "Health status (1=healthy, 0=unhealthy)",
            ["component"],
            registry=self.config.registry,
        )
        # Initialize with healthy status
        self._metrics["health_status"].labels(component="api").set(1)
        self._metrics["health_status"].labels(component="database").set(1)

        # Error metrics
        self._metrics["errors_total"] = Counter(
            f"{prefix}errors_total",
            "Total errors",
            ["error_type", "component"],
            registry=self.config.registry,
        )

        self._metrics["privileged_db_session_activations_total"] = Counter(
            f"{prefix}privileged_db_session_activations_total",
            "Total privileged cross-tenant database session activations",
            ["mode"],
            registry=self.config.registry,
        )
        self._metrics["db_pool_size"] = Gauge(
            f"{prefix}db_pool_size",
            "Configured DB connection pool size",
            registry=self.config.registry,
        )
        self._metrics["db_pool_active_connections"] = Gauge(
            f"{prefix}db_pool_active_connections",
            "Active DB connections checked out from pool",
            registry=self.config.registry,
        )
        self._metrics["db_pool_idle_connections"] = Gauge(
            f"{prefix}db_pool_idle_connections",
            "Idle DB connections currently in pool",
            registry=self.config.registry,
        )
        self._metrics["db_pool_wait_seconds"] = Histogram(
            f"{prefix}db_pool_wait_seconds",
            "DB pool connection wait latency in seconds",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.config.registry,
        )
        self._metrics["db_pool_timeouts_total"] = Counter(
            f"{prefix}db_pool_timeouts_total",
            "Total DB pool checkout timeouts",
            registry=self.config.registry,
        )
        self._metrics["audit_write_failures_total"] = Counter(
            f"{prefix}audit_write_failures_total",
            "Total failed audit/event write attempts",
            registry=self.config.registry,
        )

        # ---------------------------------------------------------------------------
        # Phase N: security / auth-failure metrics (bounded labels)
        # ---------------------------------------------------------------------------
        self._metrics["auth_failures_total"] = Counter(
            f"{prefix}auth_failures_total",
            "Total authentication/authorization failures",
            ["reason", "component"],
            registry=self.config.registry,
        )

        # Build info
        self._metrics["build_info"] = Info(
            f"{prefix}build_info", "Build information", registry=self.config.registry
        )
        self._metrics["build_info"].info(
            {"version": __version__, "service": "layer5-ground-truth"}
        )

    @staticmethod
    def _status_class(status_code: int | str) -> str:
        code = int(status_code)
        return f"{code // 100}xx"

    def increment_requests_total(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        tenant_id: str = "unknown",
    ) -> None:
        if self.config.enabled:
            self._metrics["requests_total"].labels(
                method=method,
                endpoint=endpoint,
                status_class=self._status_class(status_code),
                tenant_bucket=_tenant_bucket(tenant_id),
            ).inc()

    def observe_request_duration(
        self,
        duration: float,
        method: str,
        endpoint: str,
        tenant_id: str = "unknown",
    ) -> None:
        if self.config.enabled:
            self._metrics["request_duration"].labels(
                method=method,
                endpoint=endpoint,
                tenant_bucket=_tenant_bucket(tenant_id),
            ).observe(duration)

    def increment_truth_objects(self, claim_type: str, status: str) -> None:
        if self.config.enabled:
            self._metrics["truth_objects_total"].labels(
                claim_type=claim_type, status=status
            ).inc()

    def increment_validations(self, from_status: str, to_status: str) -> None:
        if self.config.enabled:
            self._metrics["validations_total"].labels(
                from_status=from_status, to_status=to_status
            ).inc()

    def observe_validation_latency(self, transition: str, duration: float) -> None:
        if self.config.enabled:
            self._metrics["validation_latency_seconds"].labels(
                transition=transition
            ).observe(duration)

    def increment_validation_transition_failure(
        self, transition: str, reason: str
    ) -> None:
        if self.config.enabled:
            self._metrics["validation_transition_failures_total"].labels(
                transition=transition, reason=reason
            ).inc()

    def set_truth_objects_by_status(
        self, status: str, claim_type: str, count: int
    ) -> None:
        if self.config.enabled:
            self._metrics["truth_objects_by_status"].labels(
                status=status, claim_type=claim_type
            ).set(count)

    def increment_sources_added(self) -> None:
        if self.config.enabled:
            self._metrics["sources_added_total"].inc()

    def increment_kg_sync(self, status: str) -> None:
        if self.config.enabled:
            self._metrics["kg_sync_total"].labels(status=status).inc()

    def increment_kg_sync_outcome(self, sync_status: str, transition: str) -> None:
        if self.config.enabled:
            self._metrics["kg_sync_outcomes_total"].labels(
                sync_status=sync_status, transition=transition
            ).inc()

    def set_db_pool_state(self, *, pool_size: int, active: int, idle: int) -> None:
        if self.config.enabled:
            self._metrics["db_pool_size"].set(pool_size)
            self._metrics["db_pool_active_connections"].set(active)
            self._metrics["db_pool_idle_connections"].set(idle)

    def observe_db_pool_wait(self, duration: float) -> None:
        if self.config.enabled:
            self._metrics["db_pool_wait_seconds"].observe(duration)

    def increment_db_pool_timeout(self) -> None:
        if self.config.enabled:
            self._metrics["db_pool_timeouts_total"].inc()

    def increment_freshness_checks(self) -> None:
        if self.config.enabled:
            self._metrics["freshness_checks_total"].inc()

    def set_stale_objects_detected(self, count: int) -> None:
        """Set the current number of detected stale objects (Gauge)."""
        if self.config.enabled:
            self._metrics["stale_objects_detected"].set(count)

    def increment_stale_objects_detected(self) -> None:
        """Backward-compatible: bump the gauge by 1.

        Prefer :meth:`set_stale_objects_detected` for accurate alerting.
        """
        if self.config.enabled:
            self._metrics["stale_objects_detected"].inc()

    def set_health_status(self, healthy: bool, component: str = "api") -> None:
        if self.config.enabled:
            self._metrics["health_status"].labels(component=component).set(
                1 if healthy else 0
            )

    def increment_errors(self, error_type: str, component: str) -> None:
        if self.config.enabled:
            self._metrics["errors_total"].labels(
                error_type=error_type, component=component
            ).inc()

    def increment_privileged_db_session_activation(self, mode: str) -> None:
        if self.config.enabled:
            self._metrics["privileged_db_session_activations_total"].labels(
                mode=mode
            ).inc()

    def increment_audit_write_failures(self) -> None:
        if self.config.enabled:
            self._metrics["audit_write_failures_total"].inc()

    def increment_auth_failure(self, reason: str, component: str = "http") -> None:
        """Record an authentication/authorization failure.

        `reason` should be a bounded token such as "missing_token",
        "invalid_token", "insufficient_role", "tenant_mismatch".
        """
        if self.config.enabled:
            self._metrics["auth_failures_total"].labels(
                reason=reason, component=component
            ).inc()

    def get_metrics(self) -> str:
        """Get Prometheus metrics output."""
        if not self.config.enabled:
            return ""
        return generate_latest(self.config.registry).decode("utf-8")


# Known route templates for L5 Ground Truth API.
# Used to keep `endpoint` label cardinality bounded — anything outside this set
# is normalized via :class:`PathNormalizer` heuristics.
_L5_KNOWN_ROUTES: dict[str, str] = {
    "/api/v1/truths": "/api/v1/truths",
    "/api/v1/truths/{truth_id}": "/api/v1/truths/{id}",
    "/api/v1/truths/{truth_id}/validate": "/api/v1/truths/{id}/validate",
    "/api/v1/truths/{truth_id}/sources": "/api/v1/truths/{id}/sources",
    "/api/v1/truths/{truth_id}/audit": "/api/v1/truths/{id}/audit",
    "/api/v1/maturity-ladder": "/api/v1/maturity-ladder",
    "/health": "/health",
    "/api/v1/truths/sync-kg": "/api/v1/truths/sync-kg",
    "/api/v1/truths/check-stale": "/api/v1/truths/check-stale",
    "/api/v1/truths/stale": "/api/v1/truths/stale",
    "/api/v1/truths/freshness-summary": "/api/v1/truths/freshness-summary",
    "/metrics": "/metrics",
    "/docs": "/docs",
    "/redoc": "/redoc",
    "/openapi.json": "/openapi.json",
    "/": "/",
}


class MetricsMiddleware:
    """ASGI middleware to collect HTTP request metrics with path normalization."""

    def __init__(self, metrics: PrometheusMetrics):
        self.metrics = metrics
        if PathNormalizer is not None:
            self._normalizer = PathNormalizer(known_routes=_L5_KNOWN_ROUTES)
        else:
            self._normalizer = None

    def _normalize_path(self, path: str) -> str:
        if self._normalizer is None:
            return path or "/"
        return self._normalizer.normalize(path)

    async def __call__(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        # Normalize the endpoint path for metrics
        endpoint = self._normalize_path(request.url.path)
        context = getattr(request.state, "governance_context", None)
        tenant_id = str(getattr(context, "tenant_id", None) or "unknown")

        self.metrics.increment_requests_total(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
            tenant_id=tenant_id,
        )
        self.metrics.observe_request_duration(
            duration=duration,
            method=request.method,
            endpoint=endpoint,
            tenant_id=tenant_id,
        )

        if response.status_code == 401:
            self.metrics.increment_auth_failure(
                reason="missing_token", component="http"
            )
        elif response.status_code == 403:
            self.metrics.increment_auth_failure(
                reason="insufficient_role", component="http"
            )
        elif response.status_code >= 400:
            error_type = (
                "client_error" if response.status_code < 500 else "server_error"
            )
            self.metrics.increment_errors(error_type=error_type, component="http")

        return response


_metrics: PrometheusMetrics | None = None


def get_metrics() -> PrometheusMetrics | None:
    return _metrics


def initialize_metrics(config: MetricsConfig | None = None) -> PrometheusMetrics | None:
    global _metrics
    _metrics = PrometheusMetrics(config)
    logger.info("Layer 5 Prometheus metrics initialized")
    return _metrics
