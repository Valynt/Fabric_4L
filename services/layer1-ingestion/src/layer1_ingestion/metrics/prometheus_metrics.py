"""Prometheus metrics collection for Layer 1 Ingestion Service."""

import logging
import time
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Info, generate_latest

logger = logging.getLogger(__name__)


class MetricsConfig:
    """Configuration for metrics collection."""

    def __init__(
        self,
        enabled: bool = True,
        registry: CollectorRegistry | None = None,
        prefix: str = "layer1_",
        label_namespace: str = "ingestion",
        default_buckets: list[float] | None = None,
    ):
        self.enabled = enabled
        self.registry = registry or CollectorRegistry()
        self.prefix = prefix
        self.label_namespace = label_namespace
        self.default_buckets = default_buckets or [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0]


class PrometheusMetrics:
    """Prometheus metrics collector for Layer 1."""

    def __init__(self, config: MetricsConfig | None = None):
        self.config = config or MetricsConfig()
        self._metrics: dict[str, Any] = {}
        self._setup_metrics()

    def _setup_metrics(self) -> None:
        """Setup all Prometheus metrics."""
        prefix = self.config.prefix

        # HTTP request metrics
        self._metrics["requests_total"] = Counter(
            f"{prefix}http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code"],
            registry=self.config.registry,
        )

        self._metrics["request_duration"] = Histogram(
            f"{prefix}http_request_duration_seconds",
            "HTTP request duration",
            ["method", "endpoint"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        # Ingestion-specific metrics
        self._metrics["ingestion_jobs_total"] = Counter(
            f"{prefix}ingestion_jobs_total",
            "Total ingestion jobs",
            ["status", "target_type"],
            registry=self.config.registry,
        )

        self._metrics["ingestion_duration"] = Histogram(
            f"{prefix}ingestion_duration_seconds",
            "Ingestion job duration",
            ["target_type"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        self._metrics["bytes_ingested_total"] = Counter(
            f"{prefix}bytes_ingested_total",
            "Total bytes ingested",
            ["source_type"],
            registry=self.config.registry,
        )

        self._metrics["pages_crawled_total"] = Counter(
            f"{prefix}pages_crawled_total",
            "Total pages crawled",
            ["status"],
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
        self._metrics["health_status"].labels(component="redis").set(1)

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

        # Security / operations metrics (P2)
        self._metrics["retry_events_total"] = Counter(
            f"{prefix}retry_events_total",
            "Total Celery retry events",
            ["stage", "reason", "domain_class"],
            registry=self.config.registry,
        )

        self._metrics["urls_blocked_total"] = Counter(
            f"{prefix}urls_blocked_total",
            "Total URLs blocked by compliance",
            ["reason", "domain_class"],
            registry=self.config.registry,
        )

        self._metrics["crawl_path_distribution"] = Counter(
            f"{prefix}crawl_path_distribution",
            "Distribution of crawl path choices",
            ["path", "domain_class"],
            registry=self.config.registry,
        )
        self._metrics["job_stage_duration_seconds"] = Histogram(
            f"{prefix}job_stage_duration_seconds",
            "Duration of ingestion job stages",
            ["stage", "status"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )
        self._metrics["stuck_job_age_seconds"] = Histogram(
            f"{prefix}stuck_job_age_seconds",
            "Age in seconds for jobs in non-terminal states (stuck-job candidates)",
            ["status"],
            buckets=self.config.default_buckets + [120.0, 300.0, 600.0, 1800.0, 3600.0],
            registry=self.config.registry,
        )
        self._metrics["queue_latency_seconds"] = Histogram(
            f"{prefix}queue_latency_seconds",
            "Queue latency in seconds before stage execution",
            ["stage", "status"],
            buckets=self.config.default_buckets + [120.0, 300.0, 600.0, 1800.0, 3600.0],
            registry=self.config.registry,
        )

        self._metrics["stuck_jobs"] = Gauge(
            f"{prefix}stuck_jobs",
            "Number of jobs stuck in non-terminal states",
            ["stage"],
            registry=self.config.registry,
        )

        self._metrics["outbox_dead_lettered_total"] = Counter(
            f"{prefix}outbox_dead_lettered_total",
            "Total outbox events dead-lettered",
            [],
            registry=self.config.registry,
        )

        # Maintenance operations metrics (P1 hardening)
        self._metrics["maintenance_tenant_enumerations_total"] = Counter(
            f"{prefix}maintenance_tenant_enumerations_total",
            "Total system maintenance tenant enumeration operations",
            [],
            registry=self.config.registry,
        )

        # Strict robots mode metrics (P2)
        self._metrics["strict_robots_blocks_total"] = Counter(
            f"{prefix}strict_robots_blocks_total",
            "Total strict robots mode blocks",
            ["domain", "reason"],
            registry=self.config.registry,
        )

        # API idempotency metrics (P3)
        self._metrics["idempotency_key_hits_total"] = Counter(
            f"{prefix}idempotency_key_hits_total",
            "Total idempotency key cache hits",
            [],
            registry=self.config.registry,
        )

        self._metrics["idempotency_key_misses_total"] = Counter(
            f"{prefix}idempotency_key_misses_total",
            "Total idempotency key cache misses",
            [],
            registry=self.config.registry,
        )

        # Circuit breaker metrics (P0)
        self._metrics["circuit_breaker_opens_total"] = Counter(
            f"{prefix}circuit_breaker_opens_total",
            "Total circuit breaker state transitions to OPEN",
            ["service"],
            registry=self.config.registry,
        )

        # Dead letter queue metrics (P0)
        self._metrics["dlq_tasks_total"] = Counter(
            f"{prefix}dlq_tasks_total",
            "Total tasks routed to dead letter queue",
            ["task_name"],
            registry=self.config.registry,
        )

        # Build info
        self._metrics["build_info"] = Info(
            f"{prefix}build_info", "Build information", registry=self.config.registry
        )
        self._metrics["build_info"].info({"version": "1.0.0", "service": "layer1-ingestion"})

    def increment_requests_total(self, method: str, endpoint: str, status_code: int) -> None:
        if self.config.enabled:
            self._metrics["requests_total"].labels(
                method=method, endpoint=endpoint, status_code=str(status_code)
            ).inc()

    def observe_request_duration(self, duration: float, method: str, endpoint: str) -> None:
        if self.config.enabled:
            self._metrics["request_duration"].labels(method=method, endpoint=endpoint).observe(
                duration
            )

    def increment_ingestion_jobs(self, status: str, target_type: str) -> None:
        if self.config.enabled:
            self._metrics["ingestion_jobs_total"].labels(
                status=status, target_type=target_type
            ).inc()

    def observe_ingestion_duration(self, duration: float, target_type: str) -> None:
        if self.config.enabled:
            self._metrics["ingestion_duration"].labels(target_type=target_type).observe(duration)

    def increment_bytes_ingested(self, bytes_count: int, source_type: str) -> None:
        if self.config.enabled:
            self._metrics["bytes_ingested_total"].labels(source_type=source_type).inc(bytes_count)

    def increment_pages_crawled(self, status: str) -> None:
        if self.config.enabled:
            self._metrics["pages_crawled_total"].labels(status=status).inc()

    def set_active_connections(self, count: int, connection_type: str = "total") -> None:
        if self.config.enabled:
            self._metrics["active_connections"].labels(connection_type=connection_type).set(count)

    def set_health_status(self, healthy: bool, component: str = "api") -> None:
        """Set health status gauge (1=healthy, 0=unhealthy)."""
        if self.config.enabled:
            status = 1 if healthy else 0
            self._metrics["health_status"].labels(component=component).set(status)

    def increment_errors(self, error_type: str, component: str) -> None:
        if self.config.enabled:
            self._metrics["errors_total"].labels(error_type=error_type, component=component).inc()

    def increment_privileged_db_session_activation(self, mode: str) -> None:
        if self.config.enabled:
            self._metrics["privileged_db_session_activations_total"].labels(mode=mode).inc()

    def increment_retry_event(self, stage: str, reason: str, domain_class: str = "unknown") -> None:
        if self.config.enabled:
            self._metrics["retry_events_total"].labels(
                stage=stage, reason=reason, domain_class=domain_class
            ).inc()

    def increment_url_blocked(self, reason: str, domain_class: str = "unknown") -> None:
        if self.config.enabled:
            self._metrics["urls_blocked_total"].labels(
                reason=reason, domain_class=domain_class
            ).inc()

    def increment_crawl_path(self, path: str, domain_class: str = "unknown") -> None:
        if self.config.enabled:
            self._metrics["crawl_path_distribution"].labels(path=path, domain_class=domain_class).inc()

    def observe_job_stage_duration(self, duration_seconds: float, stage: str, status: str) -> None:
        if self.config.enabled:
            self._metrics["job_stage_duration_seconds"].labels(stage=stage, status=status).observe(
                duration_seconds
            )

    def observe_stuck_job_age(self, age_seconds: float, status: str) -> None:
        if self.config.enabled:
            self._metrics["stuck_job_age_seconds"].labels(status=status).observe(age_seconds)

    def observe_queue_latency(self, latency_seconds: float, stage: str, status: str = "scheduled") -> None:
        if self.config.enabled:
            self._metrics["queue_latency_seconds"].labels(stage=stage, status=status).observe(
                latency_seconds
            )

    def set_stuck_jobs(self, count: int, stage: str) -> None:
        if self.config.enabled:
            self._metrics["stuck_jobs"].labels(stage=stage).set(count)

    def increment_outbox_dead_lettered(self) -> None:
        if self.config.enabled:
            self._metrics["outbox_dead_lettered_total"].inc()

    def increment_task_dead_lettered(self, original_task: str = "unknown") -> None:
        """Count a task dead-lettered after exhausting retries (P0-02 DLQ wiring).

        Uses the pre-declared ``dlq_tasks_total`` counter (label ``task_name``),
        which existed but was never incremented until V1-QUEUE-001 wired the
        task_failure -> layer1_dlq route.
        """
        if self.config.enabled:
            self._metrics["dlq_tasks_total"].labels(task_name=original_task).inc()

    def increment_maintenance_tenant_enumeration(self) -> None:
        if self.config.enabled:
            self._metrics["maintenance_tenant_enumerations_total"].inc()

    def increment_strict_robots_block(self, domain: str, reason: str) -> None:
        if self.config.enabled:
            self._metrics["strict_robots_blocks_total"].labels(domain=domain, reason=reason).inc()

    def increment_idempotency_key_hit(self) -> None:
        if self.config.enabled:
            self._metrics["idempotency_key_hits_total"].inc()

    def increment_idempotency_key_miss(self) -> None:
        if self.config.enabled:
            self._metrics["idempotency_key_misses_total"].inc()

    def refresh_stuck_jobs(self, counts_by_stage: dict[str, int]) -> None:
        """Update stuck jobs gauge from a dict of {stage: count}.

        Callers should compute counts via a system-authorized query
        and pass the result here.
        """
        if not self.config.enabled:
            return
        for stage, count in counts_by_stage.items():
            self._metrics["stuck_jobs"].labels(stage=stage).set(count)

    def get_metrics(self) -> str:
        """Get Prometheus metrics output."""
        if not self.config.enabled:
            return ""
        return generate_latest(self.config.registry).decode("utf-8")


class MetricsMiddleware:
    """Middleware to collect HTTP request metrics."""

    def __init__(self, metrics: PrometheusMetrics):
        self.metrics = metrics

    async def __call__(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        endpoint = request.url.path
        if endpoint.endswith("/"):
            endpoint = endpoint[:-1]
        if not endpoint:
            endpoint = "/"

        self.metrics.increment_requests_total(
            method=request.method, endpoint=endpoint, status_code=response.status_code
        )
        self.metrics.observe_request_duration(
            duration=duration, method=request.method, endpoint=endpoint
        )

        if response.status_code >= 400:
            error_type = "client_error" if response.status_code < 500 else "server_error"
            self.metrics.increment_errors(error_type=error_type, component="http")

        return response


_metrics: PrometheusMetrics | None = None


def get_metrics() -> PrometheusMetrics | None:
    return _metrics


def initialize_metrics(config: MetricsConfig | None = None) -> PrometheusMetrics | None:
    global _metrics
    _metrics = PrometheusMetrics(config)
    logger.info("Layer 1 Prometheus metrics initialized")
    return _metrics
