"""Prometheus metrics for Layer 2 extraction."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class MetricsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    port: int = 9090
    endpoint: str = "/metrics"


class PrometheusMetrics:
    """Prometheus metrics collector for LLM cost tracking."""

    def __init__(self, config: MetricsConfig | None = None) -> None:
        self.config = config or MetricsConfig()
        self._accumulated_costs: dict[tuple[str, str, str], float] = {}
        self._token_counts: dict[tuple[str, str, str], int] = {}
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}

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

    def record_extraction_outcome(self, *, status: str, tenant_id: str, ingestion_id: str, extraction_job_id: str, model_version: str, schema_version: str, value_pack_id: str) -> None:
        self._record_counter('vf_extraction_outcomes_total', {
            'status': status,'tenant_id': tenant_id,'ingestion_id': ingestion_id,'extraction_job_id': extraction_job_id,'model_version': model_version,'schema_version': schema_version,'value_pack_id': value_pack_id,
        })

    def record_schema_validation_failure(self, *, tenant_id: str, ingestion_id: str, extraction_job_id: str, model_version: str, schema_version: str, value_pack_id: str, endpoint: str) -> None:
        self._record_counter('vf_schema_validation_failures_total', {
            'tenant_id': tenant_id,'ingestion_id': ingestion_id,'extraction_job_id': extraction_job_id,'model_version': model_version,'schema_version': schema_version,'value_pack_id': value_pack_id,'endpoint': endpoint,
        })

    def record_retry(self, *, tenant_id: str, ingestion_id: str, extraction_job_id: str, model_version: str, schema_version: str, value_pack_id: str, endpoint: str) -> None:
        self._record_counter('vf_extraction_retries_total', {
            'tenant_id': tenant_id,'ingestion_id': ingestion_id,'extraction_job_id': extraction_job_id,'model_version': model_version,'schema_version': schema_version,'value_pack_id': value_pack_id,'endpoint': endpoint,
        })

    def record_model_latency(self, *, tenant_id: str, ingestion_id: str, extraction_job_id: str, model_version: str, schema_version: str, value_pack_id: str, endpoint: str, latency_seconds: float) -> None:
        self._observe_histogram('vf_model_latency_seconds', {
            'tenant_id': tenant_id,'ingestion_id': ingestion_id,'extraction_job_id': extraction_job_id,'model_version': model_version,'schema_version': schema_version,'value_pack_id': value_pack_id,'endpoint': endpoint,
        }, latency_seconds)

    def record_confidence(self, *, tenant_id: str, ingestion_id: str, extraction_job_id: str, model_version: str, schema_version: str, value_pack_id: str, entity_type: str, confidence: float) -> None:
        labels={'tenant_id': tenant_id,'ingestion_id': ingestion_id,'extraction_job_id': extraction_job_id,'model_version': model_version,'schema_version': schema_version,'value_pack_id': value_pack_id,'entity_type': entity_type}
        self._observe_histogram('vf_extraction_confidence', labels, confidence)
        self._record_gauge('vf_extraction_confidence_avg', labels, confidence)

    def record_cache_failure(self, *, failure_type: str, tenant_id: str, ingestion_id: str, extraction_job_id: str, model_version: str, schema_version: str, value_pack_id: str, operation: str) -> None:
        self._record_counter('vf_cache_failures_total', {
            'failure_type': failure_type,'tenant_id': tenant_id,'ingestion_id': ingestion_id,'extraction_job_id': extraction_job_id,'model_version': model_version,'schema_version': schema_version,'value_pack_id': value_pack_id,'operation': operation,
        })

    def get_metrics(self) -> str:
        """Generate Prometheus exposition format output."""
        lines: list[str] = []
        for (provider, model, tenant_id), cost in self._accumulated_costs.items():
            lines.append(
                f'vf_llm_cost_usd_total{{provider="{provider}",model="{model}",tenant_id="{tenant_id}"}} {cost}'
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
                label_str = ",".join(f'{k}="{_escape_label(v)}"' for k, v in labels)
                lines.append(f"{name}_count{{{label_str}}} {len(values)}")
                lines.append(f"{name}_sum{{{label_str}}} {sum(values)}")
        for (name, labels), value in self._gauges.items():
            label_str = ",".join(f'{k}="{_escape_label(v)}"' for k, v in labels)
            lines.append(f"{name}{{{label_str}}} {value}")
        return "\n".join(lines)


_metrics_instance: PrometheusMetrics | None = None


def initialize_metrics(config: MetricsConfig | None = None) -> PrometheusMetrics:
    """Initialize and return the global PrometheusMetrics instance."""
    global _metrics_instance
    _metrics_instance = PrometheusMetrics(config=config)
    return _metrics_instance


def get_metrics() -> PrometheusMetrics | None:
    """Get the global PrometheusMetrics instance."""
    return _metrics_instance
