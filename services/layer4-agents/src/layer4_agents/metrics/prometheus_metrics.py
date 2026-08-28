from __future__ import annotations

"""Prometheus metrics collection for Layer 4 Agentic Workflow Engine.

SECURITY NOTE: Metrics use 'tenant_tier' instead of 'tenant_id' to prevent
high-cardinality label explosion which can cause Prometheus OOM.
Endpoint paths are normalized to strip IDs and prevent unbounded cardinality.
"""


import logging
import re
import time
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

logger = logging.getLogger(__name__)

# Regex to match UUIDs and numeric IDs for path normalization
_ID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32}|[0-9a-f]{24}|^\d+$", re.I)


def _normalize_path(path: str) -> str:
    """Normalize path to prevent high-cardinality metrics.

    SECURITY: Replaces UUIDs and numeric IDs with placeholders to prevent
    unbounded label cardinality from paths like /api/items/123, /api/items/456.
    """
    if not path:
        return "/"

    # Remove trailing slash
    if path.endswith("/"):
        path = path[:-1]

    # Replace UUIDs and numeric IDs with {id} placeholder
    parts = path.split("/")
    normalized_parts = []
    for part in parts:
        if _ID_PATTERN.match(part):
            normalized_parts.append("{id}")
        else:
            normalized_parts.append(part)

    return "/".join(normalized_parts) or "/"


def _derive_tenant_tier(tenant_id: str | None) -> str:
    """Derive a cardinality-limited tier from tenant_id.

    SECURITY: Maps tenant_id to a hash bucket (first 2 hex chars of hash)
    to limit cardinality to 256 buckets while preserving multi-tenant visibility.
    Returns 'unknown' if tenant_id is None or empty.
    """
    if not tenant_id:
        return "unknown"
    # Use first 2 chars of SHA256 hash to create 256 possible buckets
    import hashlib
    hash_bytes = hashlib.sha256(tenant_id.encode()).digest()
    return hash_bytes[:2].hex()


class MetricsConfig:
    """Configuration for metrics collection."""

    def __init__(
        self,
        enabled: bool = True,
        registry: CollectorRegistry | None = None,
        prefix: str = "layer4_",
        label_namespace: str = "agents",
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
            100.0,
        ]


class PrometheusMetrics:
    """Prometheus metrics collector for Layer 4."""

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

        # Workflow metrics
        self._metrics["workflow_executions_total"] = Counter(
            f"{prefix}workflow_executions_total",
            "Total workflow executions",
            ["workflow_type", "status"],
            registry=self.config.registry,
        )

        self._metrics["workflow_duration"] = Histogram(
            f"{prefix}workflow_duration_seconds",
            "Workflow execution duration",
            ["workflow_type"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        # Agent/tool metrics
        self._metrics["agent_calls_total"] = Counter(
            f"{prefix}agent_calls_total",
            "Total agent/tool calls",
            ["agent_type", "status"],
            registry=self.config.registry,
        )

        self._metrics["agent_call_duration"] = Histogram(
            f"{prefix}agent_call_duration_seconds",
            "Agent call duration",
            ["agent_type"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        # Active connections gauge
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

        # Error metrics
        self._metrics["errors_total"] = Counter(
            f"{prefix}errors_total",
            "Total errors",
            ["error_type", "component"],
            registry=self.config.registry,
        )

        # Build info
        self._metrics["build_info"] = Info(
            f"{prefix}build_info", "Build information", registry=self.config.registry
        )
        self._metrics["build_info"].info({"version": "0.2.0", "service": "layer4-agents"})

        # Rate limiting metrics
        # SECURITY: Uses tenant_tier instead of tenant_id to prevent cardinality explosion
        self._metrics["rate_limit_hits_total"] = Counter(
            f"{prefix}rate_limit_hits_total",
            "Total rate limit hits",
            ["tenant_tier", "scope"],
            registry=self.config.registry,
        )

        self._metrics["privileged_db_session_activations_total"] = Counter(
            f"{prefix}privileged_db_session_activations_total",
            "Total privileged cross-tenant database session activations",
            ["tenant_tier", "mode"],
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

        # LLM cost metrics (cross-layer, vf_ prefix)
        # SECURITY: Uses tenant_tier instead of tenant_id to prevent cardinality explosion
        self._metrics["llm_cost_usd_total"] = Counter(
            "vf_llm_cost_usd_total",
            "Total LLM cost in USD",
            ["provider", "model", "tenant_tier"],
            registry=self.config.registry,
        )

        self._metrics["llm_tokens_total"] = Counter(
            "vf_llm_tokens_total",
            "Total LLM tokens consumed",
            ["provider", "model", "tenant_tier", "token_type"],
            registry=self.config.registry,
        )

        self._metrics["llm_requests_total"] = Counter(
            "vf_llm_requests_total",
            "Total LLM requests",
            ["provider", "model", "tenant_tier", "status"],
            registry=self.config.registry,
        )
        self._metrics["llm_budget_guardrail_events_total"] = Counter(
            "vf_llm_budget_guardrail_events_total",
            "Total budget guardrail events for LLM usage",
            ["tenant_tier", "action", "reason"],
            registry=self.config.registry,
        )

        # Formula approval pending gauge
        # SECURITY: Uses tenant_tier instead of tenant_id to prevent cardinality explosion
        self._metrics["formula_approval_pending"] = Gauge(
            f"{prefix}formula_approval_pending",
            "Number of formulas pending approval",
            ["tenant_tier"],
            registry=self.config.registry,
        )

        # CRM Salesforce metrics
        # SECURITY: Uses tenant_tier instead of tenant_id to prevent cardinality explosion
        self._metrics["crm_salesforce_connections_total"] = Gauge(
            f"{prefix}crm_salesforce_connections_total",
            "Total active Salesforce connections",
            ["tenant_tier"],
            registry=self.config.registry,
        )

        self._metrics["crm_salesforce_sync_started_total"] = Counter(
            f"{prefix}crm_salesforce_sync_started_total",
            "Total Salesforce sync jobs started",
            ["tenant_tier", "sync_type"],
            registry=self.config.registry,
        )

        self._metrics["crm_salesforce_sync_completed_total"] = Counter(
            f"{prefix}crm_salesforce_sync_completed_total",
            "Total Salesforce sync jobs completed",
            ["tenant_tier", "sync_type"],
            registry=self.config.registry,
        )

        self._metrics["crm_salesforce_sync_failed_total"] = Counter(
            f"{prefix}crm_salesforce_sync_failed_total",
            "Total Salesforce sync jobs failed",
            ["tenant_tier", "error_type"],
            registry=self.config.registry,
        )

        self._metrics["crm_salesforce_sync_duration_seconds"] = Histogram(
            f"{prefix}crm_salesforce_sync_duration_seconds",
            "Salesforce sync job duration",
            ["tenant_tier", "sync_type"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        self._metrics["crm_salesforce_records_synced_total"] = Counter(
            f"{prefix}crm_salesforce_records_synced_total",
            "Total Salesforce records synced",
            ["tenant_tier", "record_type"],
            registry=self.config.registry,
        )

        self._metrics["crm_salesforce_token_refresh_failed_total"] = Counter(
            f"{prefix}crm_salesforce_token_refresh_failed_total",
            "Total Salesforce token refresh failures",
            ["tenant_tier"],
            registry=self.config.registry,
        )

        self._metrics["crm_salesforce_rate_limit_total"] = Counter(
            f"{prefix}crm_salesforce_rate_limit_total",
            "Total Salesforce API rate limit hits",
            ["tenant_tier"],
            registry=self.config.registry,
        )

        # Security: cross-tenant WebSocket access denials (OBS-L4-009)
        # SECURITY: Uses tenant_tier (hash bucket) instead of raw tenant_id to
        # prevent high-cardinality label explosion while preserving alerting fidelity.
        self._metrics["ws_tenant_mismatch_total"] = Counter(
            "security_websocket_tenant_mismatch_total",
            "WebSocket connections denied due to cross-tenant workflow access (BOLA/IDOR probe signal)",
            ["actor_tenant_tier"],
            registry=self.config.registry,
        )

        # ------------------------------------------------------------------
        # Hardening observability metrics (approval latency + failure alerting)
        # ------------------------------------------------------------------
        self._metrics["approval_wait_seconds"] = Histogram(
            f"{prefix}approval_wait_seconds",
            "Time from gate creation to human decision",
            ["gate_type", "action_class", "tenant_tier"],
            buckets=self.config.default_buckets,
            registry=self.config.registry,
        )

        self._metrics["stuck_workflows_total"] = Gauge(
            f"{prefix}stuck_workflows_total",
            "Workflows stuck in RUNNING or WAITING_FOR_HUMAN longer than threshold",
            ["workflow_type", "tenant_tier"],
            registry=self.config.registry,
        )

        self._metrics["repeated_workflow_failures_total"] = Counter(
            f"{prefix}repeated_workflow_failures_total",
            "Workflows failing more than threshold times",
            ["workflow_type", "failure_class", "tenant_tier"],
            registry=self.config.registry,
        )

        self._metrics["tool_auth_failures_total"] = Counter(
            f"{prefix}tool_auth_failures_total",
            "Tool calls failing due to auth or authorization errors",
            ["tool_name", "tenant_tier"],
            registry=self.config.registry,
        )

        self._metrics["checkpoint_corruption_detected_total"] = Counter(
            f"{prefix}checkpoint_corruption_detected_total",
            "Checkpoint hash mismatches or unreadable checkpoints",
            ["workflow_type", "tenant_tier"],
            registry=self.config.registry,
        )
        self._metrics["checkpoint_collision_outcomes_total"] = Counter(
            f"{prefix}checkpoint_collision_outcomes_total",
            "Replay collision detection outcomes",
            ["workflow_type", "tenant_tier", "outcome"],
            registry=self.config.registry,
        )

        self._metrics["l5_degradation_events_total"] = Counter(
            f"{prefix}l5_degradation_events_total",
            "Layer 5 calls that swallowed an error and degraded instead of raising",
            ["operation", "tenant_tier", "error_class"],
            registry=self.config.registry,
        )

    def increment_l5_degradation(
        self, operation: str, tenant_id: str | None, error: BaseException
    ) -> None:
        """Record a Layer 5 degradation event (swallowed error).

        Uses cardinality-limited ``tenant_tier`` so an aggregate outage is
        visible without exploding label cardinality on raw tenant IDs.
        """
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(str(tenant_id) if tenant_id else "unknown")
            error_class = type(error).__name__
            self._metrics["l5_degradation_events_total"].labels(
                operation=operation,
                tenant_tier=tenant_tier,
                error_class=error_class,
            ).inc()

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

    def increment_workflow_executions(self, workflow_type: str, status: str) -> None:
        if self.config.enabled:
            self._metrics["workflow_executions_total"].labels(
                workflow_type=workflow_type, status=status
            ).inc()

    def observe_workflow_duration(self, duration: float, workflow_type: str) -> None:
        if self.config.enabled:
            self._metrics["workflow_duration"].labels(workflow_type=workflow_type).observe(duration)

    def increment_agent_calls(self, agent_type: str, status: str) -> None:
        if self.config.enabled:
            self._metrics["agent_calls_total"].labels(agent_type=agent_type, status=status).inc()

    def observe_agent_call_duration(self, duration: float, agent_type: str) -> None:
        if self.config.enabled:
            self._metrics["agent_call_duration"].labels(agent_type=agent_type).observe(duration)

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

    def increment_rate_limit_hit(self, tenant_id: str, scope: str) -> None:
        """Record rate limit hit with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["rate_limit_hits_total"].labels(tenant_tier=tenant_tier, scope=scope).inc()

    def increment_privileged_db_session_activation(self, tenant_id: str | None, mode: str) -> None:
        """Record privileged cross-tenant session activation."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["privileged_db_session_activations_total"].labels(
                tenant_tier=tenant_tier,
                mode=mode,
            ).inc()

    def observe_db_pool_wait(self, duration: float) -> None:
        if self.config.enabled:
            self._metrics["db_pool_wait_seconds"].observe(duration)

    def increment_db_pool_timeout(self) -> None:
        if self.config.enabled:
            self._metrics["db_pool_timeouts_total"].inc()

    def set_db_pool_state(self, *, pool_size: int, active: int, idle: int) -> None:
        if self.config.enabled:
            self._metrics["db_pool_size"].set(pool_size)
            self._metrics["db_pool_active_connections"].set(active)
            self._metrics["db_pool_idle_connections"].set(idle)

    def record_llm_cost(
        self,
        provider: str,
        model: str,
        tenant_id: str,
        cost: float,
        prompt_tokens: int,
        completion_tokens: int,
        status: str = "success",
    ) -> None:
        """Record LLM cost with cardinality-limited tenant_tier."""
        if not self.config.enabled:
            return
        tenant_tier = _derive_tenant_tier(tenant_id)
        self._metrics["llm_cost_usd_total"].labels(
            provider=provider, model=model, tenant_tier=tenant_tier
        ).inc(cost)
        self._metrics["llm_tokens_total"].labels(
            provider=provider, model=model, tenant_tier=tenant_tier, token_type="prompt"
        ).inc(prompt_tokens)
        self._metrics["llm_tokens_total"].labels(
            provider=provider, model=model, tenant_tier=tenant_tier, token_type="completion"
        ).inc(completion_tokens)
        self._metrics["llm_requests_total"].labels(
            provider=provider, model=model, tenant_tier=tenant_tier, status=status
        ).inc()

    def set_formula_approval_pending(self, tenant_id: str, value: int) -> None:
        """Set formula approval pending with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["formula_approval_pending"].labels(tenant_tier=tenant_tier).set(value)

    def increment_llm_budget_guardrail_event(
        self,
        tenant_id: str,
        action: str,
        reason: str,
    ) -> None:
        """Record LLM budget guardrail event with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["llm_budget_guardrail_events_total"].labels(
                tenant_tier=tenant_tier,
                action=action,
                reason=reason,
            ).inc()

    def inc_formula_approval_pending(self, tenant_id: str) -> None:
        """Increment formula approval pending with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["formula_approval_pending"].labels(tenant_tier=tenant_tier).inc()

    def dec_formula_approval_pending(self, tenant_id: str) -> None:
        """Decrement formula approval pending with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["formula_approval_pending"].labels(tenant_tier=tenant_tier).dec()

    # ------------------------------------------------------------------
    # CRM Salesforce metrics helpers
    # ------------------------------------------------------------------

    def set_crm_salesforce_connections(self, tenant_id: str, count: int) -> None:
        """Set active Salesforce connection count with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["crm_salesforce_connections_total"].labels(tenant_tier=tenant_tier).set(count)

    def increment_crm_salesforce_sync_started(self, tenant_id: str, sync_type: str = "incremental") -> None:
        """Record Salesforce sync start with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["crm_salesforce_sync_started_total"].labels(
                tenant_tier=tenant_tier, sync_type=sync_type
            ).inc()

    def increment_crm_salesforce_sync_completed(self, tenant_id: str, sync_type: str = "incremental") -> None:
        """Record Salesforce sync completion with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["crm_salesforce_sync_completed_total"].labels(
                tenant_tier=tenant_tier, sync_type=sync_type
            ).inc()

    def increment_crm_salesforce_sync_failed(self, tenant_id: str, error_type: str = "unknown") -> None:
        """Record Salesforce sync failure with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["crm_salesforce_sync_failed_total"].labels(
                tenant_tier=tenant_tier, error_type=error_type
            ).inc()

    def observe_approval_wait(
        self,
        duration: float,
        gate_type: str,
        action_class: str,
        tenant_id: str,
    ) -> None:
        """Record approval wait time with cardinality-limited labels."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["approval_wait_seconds"].labels(
                gate_type=gate_type,
                action_class=action_class,
                tenant_tier=tenant_tier,
            ).observe(duration)

    def set_stuck_workflows(
        self, count: int, workflow_type: str, tenant_id: str
    ) -> None:
        """Record stuck workflow gauge with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["stuck_workflows_total"].labels(
                workflow_type=workflow_type,
                tenant_tier=tenant_tier,
            ).set(count)

    def increment_repeated_failure(
        self, workflow_type: str, failure_class: str, tenant_id: str
    ) -> None:
        """Record repeated workflow failure with cardinality-limited labels."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["repeated_workflow_failures_total"].labels(
                workflow_type=workflow_type,
                failure_class=failure_class,
                tenant_tier=tenant_tier,
            ).inc()

    def increment_tool_auth_failure(
        self, tool_name: str, tenant_id: str
    ) -> None:
        """Record tool auth failure with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["tool_auth_failures_total"].labels(
                tool_name=tool_name,
                tenant_tier=tenant_tier,
            ).inc()

    def increment_checkpoint_corruption(
        self, workflow_type: str, tenant_id: str
    ) -> None:
        """Record checkpoint corruption detection with cardinality-limited labels."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["checkpoint_corruption_detected_total"].labels(
                workflow_type=workflow_type,
                tenant_tier=tenant_tier,
            ).inc()

    def increment_checkpoint_collision_outcome(
        self, workflow_type: str, tenant_id: str, outcome: str
    ) -> None:
        """Record checkpoint collision detector outcome."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["checkpoint_collision_outcomes_total"].labels(
                workflow_type=workflow_type,
                tenant_tier=tenant_tier,
                outcome=outcome,
            ).inc()

    def observe_crm_salesforce_sync_duration(self, tenant_id: str, duration: float, sync_type: str = "incremental") -> None:
        """Record Salesforce sync duration with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["crm_salesforce_sync_duration_seconds"].labels(
                tenant_tier=tenant_tier, sync_type=sync_type
            ).observe(duration)

    def increment_crm_salesforce_records_synced(self, tenant_id: str, record_type: str = "account", count: int = 1) -> None:
        """Record Salesforce records synced with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["crm_salesforce_records_synced_total"].labels(
                tenant_tier=tenant_tier, record_type=record_type
            ).inc(count)

    def increment_crm_salesforce_token_refresh_failed(self, tenant_id: str) -> None:
        """Record Salesforce token refresh failure with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["crm_salesforce_token_refresh_failed_total"].labels(
                tenant_tier=tenant_tier
            ).inc()

    def increment_crm_salesforce_rate_limit(self, tenant_id: str) -> None:
        """Record Salesforce API rate limit hit with cardinality-limited tenant_tier."""
        if self.config.enabled:
            tenant_tier = _derive_tenant_tier(tenant_id)
            self._metrics["crm_salesforce_rate_limit_total"].labels(
                tenant_tier=tenant_tier
            ).inc()

    def increment_ws_tenant_mismatch(self, actor_tenant_id: str | None) -> None:
        """Record a cross-tenant WebSocket access denial (OBS-L4-009).

        Emits ``security_websocket_tenant_mismatch_total`` with a
        cardinality-limited ``actor_tenant_tier`` label.  The raw tenant_id
        is intentionally excluded from the metric label to prevent label
        explosion; it is captured in the structured log at the call site.
        """
        if self.config.enabled:
            actor_tier = _derive_tenant_tier(actor_tenant_id)
            self._metrics["ws_tenant_mismatch_total"].labels(
                actor_tenant_tier=actor_tier
            ).inc()

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

        # Get request size
        if hasattr(request, "headers") and "content-length" in request.headers:
            try:
                int(request.headers["content-length"])
            except (ValueError, TypeError):
                pass

        response = await call_next(request)
        duration = time.time() - start_time

        # SECURITY: Normalize path to prevent high-cardinality from path parameters
        endpoint = _normalize_path(request.url.path)

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
    logger.info("Layer 4 Prometheus metrics initialized")
    return _metrics
