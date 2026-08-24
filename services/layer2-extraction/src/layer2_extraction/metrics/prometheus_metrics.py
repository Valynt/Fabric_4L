"""Prometheus metrics for Layer 2 extraction.

All tenant-scoped labels use a stable hash bucket (``tenant_bucket``) to bound
Prometheus label cardinality and avoid leaking raw tenant IDs into metric
labels. See ``_tenant_bucket`` for the derivation.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from pydantic import BaseModel, ConfigDict
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


def _tenant_bucket(tenant_id: str, count: int = 64) -> str:
    """Return a stable low-cardinality bucket label for a tenant_id.

    Raw tenant IDs are high-cardinality and sensitive; we hash them into a
    fixed set of buckets so Prometheus labels stay bounded.
    """
    if not tenant_id or tenant_id == "unknown":
        return "unknown"
    digest = hashlib.sha256(tenant_id.encode("utf-8")).digest()
    return f"bucket_{digest[0] % count:02d}"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class MetricsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    port: int = 9090
    endpoint: str = "/metrics"
    tenant_bucket_count: int = 64


class PrometheusMetrics:
    """Prometheus metrics collector for LLM cost tracking and extraction outcomes."""

    def __init__(self, config: MetricsConfig | None = None) -> None:
        self.config = config or MetricsConfig()
        self._accumulated_costs: dict[tuple[str, str, str], float] = {}
        self._token_counts: dict[tuple[str, str, str], int] = {}
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}
        self.set_health_status(True, component="api")

    def _normalized_labels(self, labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
        return tuple(sorted((k, str(v)) for k, v in labels.items()))

    def _record_counter(self, name: str, labels: dict[str, str], amount: float = 1.0) -> None:
        key = (name, self._normalized_labels(labels))
        self._counters[key] = self._counters.get(key, 0.0) + amount

    def _record_gauge(self, name: str, labels: dict[str, str], value: float) -> None:
        self._gauges[(name, self._normalized_labels(labels))] = value

    def _observe_histogram(self, name: str, labels: dict[str, str], value: float) -> None:
        key = (name, self._normalized_labels(labels))
        self._histograms.setdefault(key, []).append(value)

    def record_llm_cost(
        self,
        provider: str,
        model: str,
        tenant_id: str,
        cost_usd: float,
    ) -> None:
        """Record LLM cost for a provider/model/tenant combination."""
        key = (provider, model, tenant_id)
        self._accumulated_costs[key] = self._accumulated_costs.get(key, 0.0) + cost_usd

    def get_accumulated_cost(self, provider: str, model: str, tenant_id: str) -> float:
        """Get accumulated cost for a provider/model/tenant combination."""
        return self._accumulated_costs.get((provider, model, tenant_id), 0.0)

    def record_llm_tokens(
        self,
        provider: str,
        model: str,
        token_type: str,
        count: int,
    ) -> None:
        """Record LLM token count for a provider/model/token_type combination."""
        key = (provider, model, token_type)
        self._token_counts[key] = self._token_counts.get(key, 0) + count

    def record_extraction_outcome(
        self,
        *,
        status: str,
        tenant_id: str,
        ingestion_id: str,
        extraction_job_id: str,
        model_version: str,
        schema_version: str,
        value_pack_id: str,
    ) -> None:
        self._record_counter(
            "vf_extraction_outcomes_total",
            {
                "status": status,
                "tenant_bucket": _tenant_bucket(tenant_id, self.config.tenant_bucket_count),
                "model_version": model_version,
                "schema_version": schema_version,
            },
        )

    def record_schema_validation_failure(
        self,
        *,
        tenant_id: str,
        ingestion_id: str,
        extraction_job_id: str,
        model_version: str,
        schema_version: str,
        value_pack_id: str,
        endpoint: str,
    ) -> None:
        self._record_counter(
            "vf_schema_validation_failures_total",
            {
                "tenant_bucket": _tenant_bucket(tenant_id, self.config.tenant_bucket_count),
                "model_version": model_version,
                "schema_version": schema_version,
                "endpoint": endpoint,
            },
        )

    def record_retry(
        self,
        *,
        tenant_id: str,
        ingestion_id: str,
        extraction_job_id: str,
        model_version: str,
        schema_version: str,
        value_pack_id: str,
        endpoint: str,
    ) -> None:
        self._record_counter(
            "vf_extraction_retries_total",
            {
                "tenant_bucket": _tenant_bucket(tenant_id, self.config.tenant_bucket_count),
                "model_version": model_version,
                "schema_version": schema_version,
                "endpoint": endpoint,
            },
        )

    def record_model_latency(
        self,
        *,
        tenant_id: str,
        ingestion_id: str,
        extraction_job_id: str,
        model_version: str,
        schema_version: str,
        value_pack_id: str,
        endpoint: str,
        latency_seconds: float,
    ) -> None:
        self._observe_histogram(
            "vf_model_latency_seconds",
            {
                "tenant_bucket": _tenant_bucket(tenant_id, self.config.tenant_bucket_count),
                "model_version": model_version,
                "schema_version": schema_version,
                "endpoint": endpoint,
            },
            latency_seconds,
        )

    def record_confidence(
        self,
        *,
        tenant_id: str,
        ingestion_id: str,
        extraction_job_id: str,
        model_version: str,
        schema_version: str,
        value_pack_id: str,
        entity_type: str,
        confidence: float,
    ) -> None:
        labels = {
            "tenant_bucket": _tenant_bucket(tenant_id, self.config.tenant_bucket_count),
            "model_version": model_version,
            "schema_version": schema_version,
            "entity_type": entity_type,
        }
        self._observe_histogram("vf_extraction_confidence", labels, confidence)
        self._record_gauge("vf_extraction_confidence_avg", labels, confidence)

    def record_cache_failure(
        self,
        *,
        failure_type: str,
        tenant_id: str,
        ingestion_id: str,
        extraction_job_id: str,
        model_version: str,
        schema_version: str,
        value_pack_id: str,
        operation: str,
    ) -> None:
        self._record_counter(
            "vf_cache_failures_total",
            {
                "failure_type": failure_type,
                "tenant_bucket": _tenant_bucket(tenant_id, self.config.tenant_bucket_count),
                "operation": operation,
            },
        )

    def record_prompt_injection_attempt(
        self,
        *,
        tenant_id: str,
        risk_level: str,
        violation_count: int,
    ) -> None:
        """Record prompt-injection detection attempt with tenant context (no fallbacks)."""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id is required for prompt-injection telemetry")
        self._record_counter(
            "vf_prompt_injection_attempts_total",
            {
                "tenant_bucket": _tenant_bucket(tenant_id, self.config.tenant_bucket_count),
                "risk_level": risk_level,
            },
            amount=float(violation_count),
        )

    def record_auth_failure(
        self,
        *,
        reason: str,
        component: str = "http",
    ) -> None:
        """Record an authentication/authorization failure.

        `reason` should be a bounded token such as "missing_token",
        "invalid_token", "insufficient_role", "tenant_mismatch".
        """
        self._record_counter(
            "vf_auth_failures_total",
            {"reason": reason, "component": component},
        )

    def record_http_request(
        self,
        *,
        method: str,
        endpoint: str,
        status_code: int | str,
        tenant_id: str | None = None,
    ) -> None:
        """Record an HTTP request for SLI tracking across canonical metric names."""
        labels = {
            "method": method.upper(),
            "endpoint": endpoint,
            "status_code": str(status_code),
            "tenant_bucket": _tenant_bucket(
                tenant_id or "unknown", self.config.tenant_bucket_count
            ),
        }
        self._record_counter("layer2_http_requests_total", labels)
        self._record_counter("value_fabric_http_requests_total", labels)

    def record_http_duration(
        self,
        *,
        method: str,
        endpoint: str,
        duration_seconds: float,
        tenant_id: str | None = None,
    ) -> None:
        """Record HTTP duration for SLI tracking across canonical metric names."""
        labels = {
            "method": method.upper(),
            "endpoint": endpoint,
            "tenant_bucket": _tenant_bucket(
                tenant_id or "unknown", self.config.tenant_bucket_count
            ),
        }
        self._observe_histogram("layer2_http_request_duration_seconds", labels, duration_seconds)
        self._observe_histogram(
            "value_fabric_http_request_duration_seconds", labels, duration_seconds
        )

    def set_health_status(self, healthy: bool, component: str = "api") -> None:
        """Record health status for a component (1=healthy, 0=unhealthy)."""
        val = 1.0 if healthy else 0.0
        self._record_gauge("vf_health_status", {"component": component}, val)
        self._record_gauge("layer2_health_status", {"component": component}, val)
        self._record_gauge("value_fabric_health_status", {"component": component}, val)

    def get_metrics(self) -> str:
        """Generate Prometheus exposition format output."""
        lines: list[str] = []
        for (provider, model, tenant_id), cost in self._accumulated_costs.items():
            # Emit cost metrics with tenant_bucket, not raw tenant_id.
            lines.append(
                f'vf_llm_cost_usd_total{{provider="{provider}",model="{model}",tenant_bucket="{_tenant_bucket(tenant_id, self.config.tenant_bucket_count)}"}} {cost}'
            )
        for (provider, model, token_type), count in self._token_counts.items():
            lines.append(
                f'vf_llm_tokens_total{{provider="{provider}",model="{model}",token_type="{token_type}"}} {count}'
            )
        for (name, labels), value in self._counters.items():
            label_str = ",".join(f'{k}="{_escape_label(v)}"' for k, v in labels)
            lines.append(f"{name}{{{label_str}}} {value}")
        for (name, labels), values in self._histograms.items():
            if values:
                label_prefix = ",".join(f'{k}="{_escape_label(v)}"' for k, v in labels)
                buckets = [0.05, 0.1, 0.25, 0.5, 1.0, 1.5, 2.5, 5.0, 10.0]
                for b in buckets:
                    count_le = sum(1 for v in values if v <= b)
                    b_label = f'{label_prefix},le="{b}"' if label_prefix else f'le="{b}"'
                    lines.append(f"{name}_bucket{{{b_label}}} {count_le}")
                inf_label = f'{label_prefix},le="+Inf"' if label_prefix else 'le="+Inf"'
                lines.append(f"{name}_bucket{{{inf_label}}} {len(values)}")
                count_label = f"{{{label_prefix}}}" if label_prefix else ""
                lines.append(f"{name}_count{count_label} {len(values)}")
                lines.append(f"{name}_sum{count_label} {sum(values)}")
        for (name, labels), value in self._gauges.items():
            label_str = ",".join(f'{k}="{_escape_label(v)}"' for k, v in labels)
            lines.append(f"{name}{{{label_str}}} {value}")
        return "\n".join(lines)


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI / ASGI middleware for collecting Layer 2 HTTP metrics."""

    def __init__(self, app: Any = None, metrics: PrometheusMetrics | None = None) -> None:
        if isinstance(app, PrometheusMetrics) and metrics is None:
            super().__init__(None)  # type: ignore[arg-type]
            self.metrics = app
        else:
            super().__init__(app)
            self.metrics = metrics if metrics is not None else PrometheusMetrics()
        try:
            from value_fabric.shared.observability import PathNormalizer
            self._normalizer = PathNormalizer()
        except ImportError:
            self._normalizer = None

    def _normalize_path(self, path: str) -> str:
        if self._normalizer is None:
            return path.rstrip("/") or "/"
        return self._normalizer.normalize(path)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
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
            self.metrics.record_http_request(
                method=request.method,
                endpoint=route,
                status_code=status_code,
                tenant_id=tenant_id,
            )
            self.metrics.record_http_duration(
                method=request.method,
                endpoint=route,
                duration_seconds=duration,
                tenant_id=tenant_id,
            )
            if status_code == 401:
                self.metrics.record_auth_failure(reason="missing_token", component="http")
            elif status_code == 403:
                self.metrics.record_auth_failure(reason="insufficient_role", component="http")
        return response

    async def __call__(self, scope_or_request: Any, receive_or_call_next: Any = None, send: Any = None) -> Any:
        if receive_or_call_next is not None and send is None and callable(receive_or_call_next):
            return await self.dispatch(scope_or_request, receive_or_call_next)
        return await super().__call__(scope_or_request, receive_or_call_next, send)


_metrics_instance: PrometheusMetrics | None = None


def initialize_metrics(config: MetricsConfig | None = None) -> PrometheusMetrics:
    """Initialize and return the global PrometheusMetrics instance."""
    global _metrics_instance
    _metrics_instance = PrometheusMetrics(config=config)
    return _metrics_instance


def get_metrics() -> PrometheusMetrics | None:
    """Get the global PrometheusMetrics instance."""
    return _metrics_instance
