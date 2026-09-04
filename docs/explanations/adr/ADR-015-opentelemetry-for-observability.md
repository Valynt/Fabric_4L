<!-- Migrated from services/ADRs/ during legacy path cleanup. -->

# ADR-015: OpenTelemetry for Observability

**Status:** Accepted  
**Date:** April 2026  
**Authors:** Distinguished Engineering Team  
**Reviewers:** Platform Operations Committee

---

## Context

Value Fabric is a distributed system with:
- 6 independent service layers
- Multiple external dependencies (LLM providers, CRMs, databases)
- Complex multi-step workflows
- Real-time streaming requirements
- Multi-tenant isolation needs

We need comprehensive observability for:
- Debugging distributed transactions
- Performance optimization
- Root cause analysis
- Capacity planning
- SLA monitoring

We evaluated:
1. **OpenTelemetry** (CNCF standard, vendor-neutral)
2. **Datadog APM** (SaaS solution)
3. **New Relic** (SaaS solution)
4. **Jaeger + Prometheus + Grafana** (Self-hosted stack)

## Decision

We chose **OpenTelemetry** with the following architecture.

**Implementation (2026-09):** the stdlib client lives in
`packages/shared/src/value_fabric/shared/observability/platform.py`.
`create_fabric_app` is the reference installer. `configure_platform` installs
at most one SDK `TracerProvider` per process and fail-closes (returns
`provider=None`) on missing SDK/endpoint, invalid `OTEL_SAMPLE_RATIO`, or
exporter errors. Collector, Grafana, and SLO recording rules stay under
`monitoring/`; the six platform SLOs are contracted in
`monitoring/slo/slos.contract.json`. Audit events correlate via `request_id`
and `details.trace_id` without a schema migration.

```
┌─────────────────────────────────────────────────────────────────┐
│ Application Layer (Layer 1-6)                                   │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │
│ │ OpenTelemetry│ │ OpenTelemetry│ │ OpenTelemetry│              │
│ │ SDK (Python) │ │ SDK (Python) │ │ SDK (Python) │              │
│ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                 │
└────────┼───────────────┼───────────────┼────────────────────────┘
         │               │               │
         └───────────────┴───────────────┘
                         │
         ┌───────────────┴───────────────┐
         │ OpenTelemetry Collector       │
         │ - Batch processing            │
         │ - Sampling                    │
         │ - Routing                     │
         └───────────────┬───────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │ Jaeger  │    │Prometheus│    │  Loki   │
    │(Traces) │    │(Metrics) │    │ (Logs)   │
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │               │
    ┌────┴───────────────┴───────────────┴────┐
    │           Grafana (Dashboards)          │
    └─────────────────────────────────────────┘
```

## Rationale

### Why OpenTelemetry?

1. **Vendor Neutrality**: Avoid lock-in to specific vendor
   ```python
   # Same instrumentation works with any backend
   # - Jaeger (development)
   # - Datadog (if we switch)
   # - AWS X-Ray (if we migrate)
   # - Custom backend
   ```

2. **CNCF Standard**: Industry adoption and support
   - Wide language support
   - Active community
   - Long-term viability

3. **Unified Telemetry**: Single API for traces, metrics, logs
   ```python
   # Correlated telemetry
   with tracer.start_as_current_span("workflow"):
       logger.info("Starting workflow", extra={"trace_id": trace_id})
       counter.add(1, {"workflow_type": "whitespace"})
   ```

4. **Auto-Instrumentation**: Minimal code changes
   ```python
   from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
   from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
   
   # Automatic instrumentation
   FastAPIInstrumentor.instrument_app(app)
   SQLAlchemyInstrumentor().instrument()
   ```

### Why Not SaaS APM (Datadog/New Relic)?

- Vendor lock-in
- Cost at scale (per-host pricing)
- Limited customization
- Data residency concerns

### Why Not Self-Hosted Only?

- Jaeger doesn't handle metrics
- Prometheus doesn't handle traces
- Need correlation between signals
- OpenTelemetry provides unified solution

## Trade-offs

### Positive
- Vendor-neutral instrumentation
- Unified telemetry (traces, metrics, logs)
- Industry standard
- Cost-effective at scale
- Strong community support

### Negative
- Higher initial setup complexity
- Self-hosted infrastructure (Jaeger, Prometheus, Grafana)
- Learning curve for developers
- Collector configuration complexity

## Mitigations

| Risk | Mitigation |
|------|-----------|
| Setup complexity | Documented setup scripts, Terraform modules |
| Infrastructure | Kubernetes deployment with Helm charts |
| Learning curve | Developer documentation, code examples |
| Configuration | Default configurations, gradual customization |

## Implementation

### SDK Configuration

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

# Resource identifies the service
resource = Resource.create({
    SERVICE_NAME: "layer4-agents",
    "service.version": "2.0.0",
    "deployment.environment": "production",
})

# Trace provider
tracer_provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
    endpoint="http://otel-collector:4318/v1/traces"
)
span_processor = BatchSpanProcessor(
    otlp_exporter,
    max_queue_size=2048,
    max_export_batch_size=512,
    schedule_delay_millis=5000,
)
tracer_provider.add_span_processor(span_processor)
trace.set_tracer_provider(tracer_provider)

# Metric provider
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics"),
    export_interval_millis=60000,
)
meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[metric_reader],
)
metrics.set_meter_provider(meter_provider)
```

### Manual Instrumentation

```python
# Get tracer and meter
tracer = trace.get_tracer("layer4-agents")
meter = metrics.get_meter("layer4-agents")

# Create metrics
workflow_starts = meter.create_counter(
    "workflow.starts",
    description="Total workflow starts",
    unit="1",
)

workflow_duration = meter.create_histogram(
    "workflow.duration",
    description="Workflow execution time",
    unit="s",
)

active_workflows = meter.create_up_down_counter(
    "workflows.active",
    description="Number of active workflows",
    unit="1",
)

class WorkflowService:
    """Service with full observability."""
    
    async def execute_workflow(
        self,
        workflow_id: str,
        tenant_id: UUID,
        inputs: dict,
    ) -> WorkflowResult:
        """Execute workflow with full telemetry."""
        
        # Start trace
        with tracer.start_as_current_span(
            "workflow.execute",
            attributes={
                "workflow.id": workflow_id,
                "tenant.id": str(tenant_id),
                "workflow.type": inputs.get("type"),
            },
        ) as span:
            start_time = time.time()
            
            # Record metrics
            workflow_starts.add(1, {"type": inputs.get("type")})
            active_workflows.add(1)
            
            try:
                # Child span for extraction
                with tracer.start_as_current_span("workflow.extract") as extract_span:
                    entities = await self._extract_entities(inputs)
                    extract_span.set_attribute("entities.count", len(entities))
                
                # Child span for analysis
                with tracer.start_as_current_span("workflow.analyze"):
                    analysis = await self._analyze(entities)
                
                result = WorkflowResult(
                    workflow_id=workflow_id,
                    analysis=analysis,
                )
                
                span.set_attribute("result.status", "success")
                return result
                
            except Exception as e:
                span.record_exception(e)
                span.set_attribute("result.status", "error")
                span.set_attribute("error.message", str(e))
                raise
            
            finally:
                duration = time.time() - start_time
                workflow_duration.record(duration)
                active_workflows.add(-1)
```

### Collector Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  
  resource:
    attributes:
      - key: environment
        value: production
        action: upsert
  
  tail_sampling:
    decision_wait: 10s
    num_traces: 100
    expected_new_traces_per_sec: 10
    policies:
      - name: errors
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: slow_requests
        type: latency
        latency: {threshold_ms: 1000}

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  
  prometheusremotewrite:
    endpoint: http://prometheus:9090/api/v1/write
  
  loki:
    endpoint: http://loki:3100/loki/api/v1/push

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, tail_sampling]
      exporters: [jaeger]
    
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheusremotewrite]
    
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [loki]
```

### Correlation with Logs

```python
import structlog
from opentelemetry import trace

# Configure structlog with trace correlation
def add_trace_info(logger, method_name, event_dict):
    """Add trace context to log entries."""
    span = trace.get_current_span()
    if span:
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        add_trace_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

# Usage - logs automatically include trace info
logger = structlog.get_logger()

with tracer.start_as_current_span("operation"):
    logger.info("Starting operation")  # Includes trace_id, span_id
```

## Consequences

### Accepted
- Self-hosted infrastructure maintenance
- Initial setup complexity
- Learning curve for developers

### Mitigated
- Infrastructure via Kubernetes/Helm
- Setup via documented automation
- Learning via documentation and examples

## SLOs with OpenTelemetry

| SLO | Metric | Target | Alert |
|-----|--------|--------|-------|
| Availability | `up{job="layer4-agents"}` | 99.9% | < 99.9% for 5m |
| Latency p99 | `histogram_quantile(0.99, workflow_duration)` | < 5s | > 5s for 10m |
| Error Rate | `rate(workflow_starts{status="error"}[5m])` | < 0.1% | > 0.1% for 5m |
| Saturation | `process_resident_memory_bytes / container_spec_memory_limit_bytes` | < 80% | > 80% |

## Related Decisions

- ADR-001: Multi-layer architecture (distributed tracing critical)
- ADR-005: Circuit breaker pattern (correlate with traces)

---

**Last Updated:** April 21, 2026
