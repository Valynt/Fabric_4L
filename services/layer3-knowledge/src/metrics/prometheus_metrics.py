"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Prometheus metrics collection for Value Fabric Layer 3 API.
"""

import asyncio
import re
import time
from datetime import UTC, datetime
from functools import wraps

try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Create dummy classes for type hints when prometheus_client is not available
    class CollectorRegistry:
        pass

    class Counter:
        pass

    class Histogram:
        pass

    class Gauge:
        pass

    class Info:
        pass


from src.logging_config import get_logger

logger = get_logger(__name__)


class MetricsConfig:
    """Configuration for metrics collection."""

    def __init__(
        self,
        enabled: bool = True,
        registry: CollectorRegistry | None = None,
        prefix: str = "value_fabric_",
        label_namespace: str = "layer3",
        default_buckets: list[float] = None,
    ):
        """Initialize metrics configuration.

        Args:
            enabled: Whether metrics collection is enabled
            registry: Prometheus registry instance
            prefix: Metric name prefix
            label_namespace: Default namespace for labels
            default_buckets: Default histogram buckets
        """
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
            100.0,
            250.0,
            500.0,
            1000.0,
        ]


class PrometheusMetrics:
    """Prometheus metrics collector for Value Fabric API."""

    def __init__(self, config: MetricsConfig | None = None):
        """Initialize Prometheus metrics.

        Args:
            config: Metrics configuration
        """
        if not PROMETHEUS_AVAILABLE:
            raise ImportError(
                "prometheus_client library is required for PrometheusMetrics"
            )

        self.config = config or MetricsConfig()
        self._metrics = {}
        self._setup_metrics()

    def _setup_metrics(self) -> None:
        """Setup all Prometheus metrics."""
        prefix = self.config.prefix

        # Request metrics
        self._metrics["requests_total"] = Counter(
            f"{prefix}http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code", "namespace"],
            registry=self.config.registry,
        )

        self._metrics["request_duration"] = Histogram(
            f"{prefix}http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint", "namespace"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        self._metrics["request_size"] = Histogram(
            f"{prefix}http_request_size_bytes",
            "HTTP request size in bytes",
            ["method", "endpoint", "namespace"],
            buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
            registry=self.config.registry,
        )

        self._metrics["response_size"] = Histogram(
            f"{prefix}http_response_size_bytes",
            "HTTP response size in bytes",
            ["method", "endpoint", "namespace"],
            buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
            registry=self.config.registry,
        )

        # Application metrics
        self._metrics["active_connections"] = Gauge(
            f"{prefix}active_connections",
            "Number of active connections",
            ["connection_type"],
            registry=self.config.registry,
        )

        self._metrics["database_operations_total"] = Counter(
            f"{prefix}database_operations_total",
            "Total database operations",
            ["operation", "database", "status"],
            registry=self.config.registry,
        )

        self._metrics["database_operation_duration"] = Histogram(
            f"{prefix}database_operation_duration_seconds",
            "Database operation duration in seconds",
            ["operation", "database"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        # Cache metrics
        self._metrics["cache_operations_total"] = Counter(
            f"{prefix}cache_operations_total",
            "Total cache operations",
            ["operation", "cache_type", "status"],
            registry=self.config.registry,
        )

        self._metrics["cache_hit_ratio"] = Gauge(
            f"{prefix}cache_hit_ratio",
            "Cache hit ratio",
            ["cache_type"],
            registry=self.config.registry,
        )

        # Business metrics
        self._metrics["search_queries_total"] = Counter(
            f"{prefix}search_queries_total",
            "Total search queries",
            ["search_type", "entity_type", "status"],
            registry=self.config.registry,
        )

        self._metrics["search_query_duration"] = Histogram(
            f"{prefix}search_query_duration_seconds",
            "Search query duration in seconds",
            ["search_type", "entity_type"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        self._metrics["ingestion_operations_total"] = Counter(
            f"{prefix}ingestion_operations_total",
            "Total ingestion operations",
            ["status", "source_type"],
            registry=self.config.registry,
        )

        # Phase 3 hardening: Dual-store mutation metrics (GOV-L3-METRICS-002)
        self._metrics["dual_store_mutation_total"] = Counter(
            f"{prefix}dual_store_mutation_total",
            "Total dual-store mutation operations",
            ["source", "status", "request_id"],
            registry=self.config.registry,
        )

        self._metrics["entities_processed_total"] = Counter(
            f"{prefix}entities_processed_total",
            "Total entities processed",
            ["entity_type", "operation"],
            registry=self.config.registry,
        )

        # System metrics
        self._metrics["memory_usage_bytes"] = Gauge(
            f"{prefix}memory_usage_bytes",
            "Memory usage in bytes",
            ["component"],
            registry=self.config.registry,
        )

        self._metrics["cpu_usage_percent"] = Gauge(
            f"{prefix}cpu_usage_percent",
            "CPU usage percentage",
            ["component"],
            registry=self.config.registry,
        )

        # Error metrics
        self._metrics["errors_total"] = Counter(
            f"{prefix}errors_total",
            "Total errors",
            ["error_type", "component", "namespace"],
            registry=self.config.registry,
        )

        # Health metrics
        self._metrics["health_status"] = Gauge(
            f"{prefix}health_status",
            "Health status (1=healthy, 0=unhealthy)",
            ["component"],
            registry=self.config.registry,
        )

        # Application info
        # Graph-specific SLO metrics (GOV-L3-METRICS-001)
        self._metrics["graph_traversal_depth"] = Histogram(
            f"{prefix}graph_traversal_depth",
            "Graph traversal depth distribution",
            ["endpoint", "operation"],
            buckets=[1, 2, 3, 5, 7, 10, 15, 20, 30, 50],
            registry=self.config.registry,
        )

        self._metrics["graph_result_size"] = Histogram(
            f"{prefix}graph_result_size",
            "Graph query result size",
            ["endpoint", "operation"],
            buckets=[0, 1, 5, 10, 25, 50, 100, 250, 500, 1000],
            registry=self.config.registry,
        )

        self._metrics["graph_slow_queries_total"] = Counter(
            f"{prefix}graph_slow_queries_total",
            "Slow graph query counter by threshold",
            ["operation", "threshold_bucket"],
            registry=self.config.registry,
        )

        # Phase 3 hardening: Graph mutation metrics
        self._metrics["graph_mutations_total"] = Counter(
            f"{prefix}graph_mutations_total",
            "Total graph mutations",
            ["operation", "route", "status", "entity_type"],
            registry=self.config.registry,
        )

        self._metrics["graph_mutation_rate"] = Gauge(
            f"{prefix}graph_mutation_rate",
            "Graph mutation rate per second",
            ["operation", "route"],
            registry=self.config.registry,
        )

        self._metrics["unauthorized_traversals_total"] = Counter(
            f"{prefix}unauthorized_traversals_total",
            "Total unauthorized graph traversals blocked",
            ["category", "route", "violation_type"],
            registry=self.config.registry,
        )

        self._metrics["graph_query_failures_total"] = Counter(
            f"{prefix}graph_query_failures_total",
            "Total failed graph queries by category",
            ["category", "operation", "route"],
            registry=self.config.registry,
        )

        self._metrics["graph_index_constraint_health_failures_total"] = Counter(
            f"{prefix}graph_index_constraint_health_failures_total",
            "Index/constraint health check failures",
            ["check_type", "component"],
            registry=self.config.registry,
        )

        # Phase 3 hardening: Entity resolution metrics
        self._metrics["entity_resolution_total"] = Counter(
            f"{prefix}entity_resolution_total",
            "Total entity resolution requests",
            ["strategy", "confidence", "entity_type"],
            registry=self.config.registry,
        )

        self._metrics["entity_resolution_duration"] = Histogram(
            f"{prefix}entity_resolution_duration_seconds",
            "Entity resolution duration in seconds",
            ["strategy", "entity_type"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        self._metrics["entity_resolution_confidence"] = Histogram(
            f"{prefix}entity_resolution_confidence",
            "Entity resolution confidence scores",
            ["strategy", "entity_type"],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.config.registry,
        )

        self._metrics["tenant_isolation_violations_total"] = Counter(
            f"{prefix}tenant_isolation_violations_total",
            "Tenant isolation violation attempts",
            ["component", "violation_type"],
            registry=self.config.registry,
        )

        self._metrics["build_info"] = Info(
            f"{prefix}build_info", "Build information", registry=self.config.registry
        )
        self._metrics["build_info"].info(
            {
                "version": "1.0.0",
                "build_date": datetime.now(UTC).isoformat(),
                "namespace": self.config.label_namespace,
            }
        )

    def increment_requests_total(
        self, method: str, endpoint: str, status_code: int, namespace: str | None = None
    ) -> None:
        """Increment total requests counter."""
        if not self.config.enabled:
            return

        namespace = namespace or self.config.label_namespace
        self._metrics["requests_total"].labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code),
            namespace=namespace,
        ).inc()

    def observe_request_duration(
        self, duration: float, method: str, endpoint: str, namespace: str | None = None
    ) -> None:
        """Observe request duration."""
        if not self.config.enabled:
            return

        namespace = namespace or self.config.label_namespace
        self._metrics["request_duration"].labels(
            method=method, endpoint=endpoint, namespace=namespace
        ).observe(duration)

    def observe_request_size(
        self, size: int, method: str, endpoint: str, namespace: str | None = None
    ) -> None:
        """Observe request size."""
        if not self.config.enabled:
            return

        namespace = namespace or self.config.label_namespace
        self._metrics["request_size"].labels(
            method=method, endpoint=endpoint, namespace=namespace
        ).observe(size)

    def observe_response_size(
        self, size: int, method: str, endpoint: str, namespace: str | None = None
    ) -> None:
        """Observe response size."""
        if not self.config.enabled:
            return

        namespace = namespace or self.config.label_namespace
        self._metrics["response_size"].labels(
            method=method, endpoint=endpoint, namespace=namespace
        ).observe(size)

    def set_active_connections(
        self, count: int, connection_type: str = "total"
    ) -> None:
        """Set active connections count."""
        if not self.config.enabled:
            return

        self._metrics["active_connections"].labels(connection_type=connection_type).set(
            count
        )

    def increment_database_operations(
        self, operation: str, database: str, status: str
    ) -> None:
        """Increment database operations counter."""
        if not self.config.enabled:
            return

        self._metrics["database_operations_total"].labels(
            operation=operation, database=database, status=status
        ).inc()

    def observe_database_operation_duration(
        self, duration: float, operation: str, database: str
    ) -> None:
        """Observe database operation duration."""
        if not self.config.enabled:
            return

        self._metrics["database_operation_duration"].labels(
            operation=operation, database=database
        ).observe(duration)

    def increment_cache_operations(
        self, operation: str, cache_type: str, status: str
    ) -> None:
        """Increment cache operations counter."""
        if not self.config.enabled:
            return

        self._metrics["cache_operations_total"].labels(
            operation=operation, cache_type=cache_type, status=status
        ).inc()

    def set_cache_hit_ratio(self, ratio: float, cache_type: str) -> None:
        """Set cache hit ratio."""
        if not self.config.enabled:
            return

        self._metrics["cache_hit_ratio"].labels(cache_type=cache_type).set(ratio)

    def increment_search_queries(
        self, search_type: str, entity_type: str | None, status: str
    ) -> None:
        """Increment search queries counter."""
        if not self.config.enabled:
            return

        entity_type = entity_type or "all"
        self._metrics["search_queries_total"].labels(
            search_type=search_type, entity_type=entity_type, status=status
        ).inc()

    def observe_search_query_duration(
        self, duration: float, search_type: str, entity_type: str | None
    ) -> None:
        """Observe search query duration."""
        if not self.config.enabled:
            return

        entity_type = entity_type or "all"
        self._metrics["search_query_duration"].labels(
            search_type=search_type, entity_type=entity_type
        ).observe(duration)

    def increment_ingestion_operations(
        self, status: str, source_type: str | None
    ) -> None:
        """Increment ingestion operations counter."""
        if not self.config.enabled:
            return

        source_type = source_type or "unknown"
        self._metrics["ingestion_operations_total"].labels(
            status=status, source_type=source_type
        ).inc()

    def increment_entities_processed(
        self, count: int, entity_type: str, operation: str
    ) -> None:
        """Increment entities processed counter."""
        if not self.config.enabled:
            return

        self._metrics["entities_processed_total"].labels(
            entity_type=entity_type, operation=operation
        ).inc(count)

    def set_memory_usage(self, bytes_used: int, component: str) -> None:
        """Set memory usage."""
        if not self.config.enabled:
            return

        self._metrics["memory_usage_bytes"].labels(component=component).set(bytes_used)

    def set_cpu_usage(self, percent: float, component: str) -> None:
        """Set CPU usage."""
        if not self.config.enabled:
            return

        self._metrics["cpu_usage_percent"].labels(component=component).set(percent)

    def increment_errors(
        self, error_type: str, component: str, namespace: str | None = None
    ) -> None:
        """Increment errors counter."""
        if not self.config.enabled:
            return

        namespace = namespace or self.config.label_namespace
        self._metrics["errors_total"].labels(
            error_type=error_type, component=component, namespace=namespace
        ).inc()

    def set_health_status(self, healthy: bool, component: str) -> None:
        """Set health status."""
        if not self.config.enabled:
            return

        status = 1 if healthy else 0
        self._metrics["health_status"].labels(component=component).set(status)

    def observe_graph_traversal_depth(
        self, depth: int, endpoint: str, operation: str
    ) -> None:
        """Observe graph traversal depth."""
        if not self.config.enabled:
            return
        self._metrics["graph_traversal_depth"].labels(
            endpoint=endpoint, operation=operation
        ).observe(depth)

    def observe_graph_result_size(
        self, size: int, endpoint: str, operation: str
    ) -> None:
        """Observe graph query result size."""
        if not self.config.enabled:
            return
        self._metrics["graph_result_size"].labels(
            endpoint=endpoint, operation=operation
        ).observe(size)

    def increment_graph_slow_queries(
        self, operation: str, threshold_bucket: str
    ) -> None:
        """Increment slow graph query counter."""
        if not self.config.enabled:
            return
        self._metrics["graph_slow_queries_total"].labels(
            operation=operation, threshold_bucket=threshold_bucket
        ).inc()

    def increment_tenant_isolation_violation(
        self, component: str, violation_type: str
    ) -> None:
        """Increment tenant isolation violation counter."""
        if not self.config.enabled:
            return
        self._metrics["tenant_isolation_violations_total"].labels(
            component=component, violation_type=violation_type
        ).inc()

    # Phase 3 hardening: Graph mutation metrics methods
    def increment_mutation_success(self, operation: str, route: str = "unknown", entity_type: str = "all") -> None:
        """Increment mutation success counter."""
        if not self.config.enabled:
            return
        self._metrics["graph_mutations_total"].labels(
            operation=operation, route=route, status="success", entity_type=entity_type
        ).inc()

    def increment_mutation_failure(self, operation: str = "unknown", route: str = "unknown", entity_type: str = "all") -> None:
        """Increment mutation failure counter."""
        if not self.config.enabled:
            return
        self._metrics["graph_mutations_total"].labels(
            operation=operation, route=route, status="failure", entity_type=entity_type
        ).inc()

    def increment_unauthorized_traversal(
        self, category: str, route: str, violation_type: str
    ) -> None:
        """Increment unauthorized traversal counter."""
        if not self.config.enabled:
            return
        self._metrics["unauthorized_traversals_total"].labels(
            category=category, route=route, violation_type=violation_type
        ).inc()

    # Phase 3 hardening: Entity resolution metrics methods
    def increment_entity_resolution(
        self, strategy: str, confidence: str, entity_type: str
    ) -> None:
        """Increment entity resolution counter."""
        if not self.config.enabled:
            return
        self._metrics["entity_resolution_total"].labels(
            strategy=strategy, confidence=confidence, entity_type=entity_type
        ).inc()

    def observe_entity_resolution_duration(
        self, duration: float, strategy: str, entity_type: str
    ) -> None:
        """Observe entity resolution duration."""
        if not self.config.enabled:
            return
        self._metrics["entity_resolution_duration"].labels(
            strategy=strategy, entity_type=entity_type
        ).observe(duration)

    def observe_entity_resolution_confidence(
        self, confidence: float, strategy: str, entity_type: str
    ) -> None:
        """Observe entity resolution confidence score."""
        if not self.config.enabled:
            return
        self._metrics["entity_resolution_confidence"].labels(
            strategy=strategy, entity_type=entity_type
        ).observe(confidence)


    def increment_graph_query_failure(
        self, category: str, operation: str, route: str
    ) -> None:
        """Increment failed graph query counter by category."""
        if not self.config.enabled:
            return
        self._metrics["graph_query_failures_total"].labels(
            category=category, operation=operation, route=route
        ).inc()

    def increment_index_constraint_health_failure(
        self, check_type: str, component: str
    ) -> None:
        """Increment index/constraint health failure counter."""
        if not self.config.enabled:
            return
        self._metrics["graph_index_constraint_health_failures_total"].labels(
            check_type=check_type, component=component
        ).inc()

    def increment_dual_store_mutation(
        self, source: str, status: str, request_id: str | None = None
    ) -> None:
        """Increment dual-store mutation counter.

        Args:
            source: Source module/component (e.g. "dual_store.coordinator")
            status: Mutation status ("success", "neo4j_failure", "postgres_failure_after_neo4j_success", etc.)
            request_id: Correlation request ID for labeling
        """
        if not self.config.enabled:
            return
        self._metrics["dual_store_mutation_total"].labels(
            source=source, status=status, request_id=request_id or "unknown"
        ).inc()

    def increment_graph_mutation_success(
        self, operation_type: str, route: str = "unknown", entity_type: str = "all"
    ) -> None:
        self.increment_mutation_success(operation=operation_type, route=route, entity_type=entity_type)

    def increment_graph_mutation_failure(
        self, error_type: str = "unknown", route: str = "unknown", entity_type: str = "all"
    ) -> None:
        self.increment_mutation_failure(operation=error_type, route=route, entity_type=entity_type)

    def get_metrics(self) -> str:
        """Get Prometheus metrics output.

        Returns:
            Prometheus metrics string
        """
        if not self.config.enabled:
            return ""

        return generate_latest(self.config.registry).decode("utf-8")


class MetricsMiddleware:
    """Middleware to collect HTTP request metrics."""

    # Patterns to replace with placeholders for cardinality control.
    _UUID_RE = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
    )
    _NUMERIC_SEGMENT_RE = re.compile(r"(?<=/)\d+(?=/|$)")

    @classmethod
    def _normalize_path(cls, path: str) -> str:
        """Strip UUIDs and numeric IDs from a URL path to control label cardinality.

        Examples:
            /entities/abc123def456-1234-5678-abcd-ef0123456789/details
              → /entities/{id}/details
            /accounts/42/signals → /accounts/{id}/signals
        """
        normalized = cls._UUID_RE.sub("{id}", path)
        normalized = cls._NUMERIC_SEGMENT_RE.sub("{id}", normalized)
        return normalized

    def __init__(self, metrics: PrometheusMetrics):
        """Initialize metrics middleware.

        Args:
            metrics: Prometheus metrics instance
        """
        self.metrics = metrics

    async def __call__(self, request, call_next):
        """Process request and collect metrics."""
        start_time = time.time()

        # Get request size
        request_size = 0
        if hasattr(request, "headers") and "content-length" in request.headers:
            try:
                request_size = int(request.headers["content-length"])
            except (ValueError, TypeError):
                request_size = 0

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Get response size
        response_size = 0
        if hasattr(response, "headers") and "content-length" in response.headers:
            try:
                response_size = int(response.headers["content-length"])
            except (ValueError, TypeError):
                response_size = 0

        # Extract endpoint path (remove query parameters) and normalize for cardinality control.
        endpoint = request.url.path
        if endpoint.endswith("/"):
            endpoint = endpoint[:-1]
        if not endpoint:
            endpoint = "/"
        endpoint = self._normalize_path(endpoint)

        # Record metrics
        self.metrics.increment_requests_total(
            method=request.method, endpoint=endpoint, status_code=response.status_code
        )

        self.metrics.observe_request_duration(
            duration=duration, method=request.method, endpoint=endpoint
        )

        self.metrics.observe_request_size(
            size=request_size, method=request.method, endpoint=endpoint
        )

        self.metrics.observe_response_size(
            size=response_size, method=request.method, endpoint=endpoint
        )

        # Record errors for 4xx and 5xx responses
        if response.status_code >= 400:
            error_type = (
                "client_error" if response.status_code < 500 else "server_error"
            )
            self.metrics.increment_errors(
                error_type=error_type, component="http", namespace="api"
            )

        return response


# Global metrics instance
_metrics: PrometheusMetrics | None = None


def get_metrics() -> PrometheusMetrics | None:
    """Get global metrics instance.

    Returns:
        Prometheus metrics instance or None if not initialized
    """
    return _metrics


def initialize_metrics(config: MetricsConfig | None = None) -> PrometheusMetrics:
    """Initialize global metrics instance.

    Args:
        config: Metrics configuration

    Returns:
        Prometheus metrics instance
    """
    global _metrics

    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus client not available, metrics disabled")
        _metrics = None
        return None

    _metrics = PrometheusMetrics(config)
    logger.info("Prometheus metrics initialized")
    return _metrics


def track_metrics(
    operation: str, component: str = "api", labels: dict[str, str] | None = None
):
    """Decorator to track function metrics.

    Args:
        operation: Operation name
        component: Component name
        labels: Additional labels

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics()
            if not metrics:
                # Fallback to direct execution
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            start_time = time.time()
            status = "success"

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                metrics.increment_errors(
                    error_type=type(e).__name__,
                    component=component,
                    namespace=labels.get("namespace") if labels else None,
                )
                raise
            finally:
                duration = time.time() - start_time

                # Record operation-specific metrics
                if operation == "database":
                    database = labels.get("database", "unknown")
                    db_operation = labels.get("db_operation", "query")
                    metrics.increment_database_operations(
                        db_operation, database, status
                    )
                    metrics.observe_database_operation_duration(
                        duration, db_operation, database
                    )
                elif operation == "cache":
                    cache_type = labels.get("cache_type", "redis")
                    cache_operation = labels.get("cache_operation", "get")
                    metrics.increment_cache_operations(
                        cache_operation, cache_type, status
                    )
                elif operation == "search":
                    search_type = labels.get("search_type", "hybrid")
                    entity_type = labels.get("entity_type")
                    metrics.increment_search_queries(search_type, entity_type, status)
                    metrics.observe_search_query_duration(
                        duration, search_type, entity_type
                    )

        return wrapper

    return decorator
