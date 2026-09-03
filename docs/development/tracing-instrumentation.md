# Distributed Tracing Instrumentation Guide — Fabric_4L v1.2.0

**Author:** SRE Team (Staff+)  
**Status:** Production-Ready  
**Scope:** All 6 backend layers + React frontend  
**OTel Version:** `opentelemetry-api==1.25.0`, `opentelemetry-sdk==1.25.0`

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Python Instrumentation (L1-L6)](#python-instrumentation-l1-l6)
   - [Shared OTel Bootstrap](#shared-otel-bootstrap)
   - [L1: Ingestion Service](#l1-ingestion-service)
   - [L2: Extraction Service](#l2-extraction-service)
   - [L3: Knowledge Service](#l3-knowledge-service)
   - [L4: Agents Service](#l4-agents-service)
   - [L5: Ground Truth Service](#l5-ground-truth-service)
   - [L6: Benchmarks Service](#l6-benchmarks-service)
3. [Frontend Instrumentation](#frontend-instrumentation)
4. [Cross-Service Trace Propagation](#cross-service-trace-propagation)
5. [Validation & Testing](#validation--testing)
6. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Trace Flow (W3C Trace Context)               │
│                                                                      │
│   React Frontend                                                      │
│        │                                                              │
│        │  traceparent: 00-<trace_id>-<span_id>-01                     │
│        ▼                                                              │
│   L1 Ingestion ──► L2 Extraction ──► L3 Knowledge                    │
│        │                    ▲               │                         │
│        │                    │               │                         │
│        ▼                    │               ▼                         │
│   L5 Ground Truth ◄────────┘         L4 Agents                       │
│                                             │                         │
│                                             ▼                         │
│                                        L6 Benchmarks                  │
│                                                                      │
│   Collector: otel-collector:4317 (gRPC) / :4318 (HTTP)              │
│   Storage:   Jaeger (traces) / Prometheus (metrics)                  │
└──────────────────────────────────────────────────────────────────────┘
```

**Propagation format:** W3C Trace Context (`traceparent` header)  
**Batching:** 1s timeout, 1024 batch size  
**Sampling:** Tail-based (errors: 100%, latency >500ms: 100%, else: 10%)

---

## Python Instrumentation (L1-L6)

### Required Dependencies

```txt
# requirements-otel.txt
opentelemetry-api==1.25.0
opentelemetry-sdk==1.25.0
opentelemetry-exporter-otlp==1.25.0
opentelemetry-instrumentation==0.46b0
opentelemetry-instrumentation-fastapi==0.46b0
opentelemetry-instrumentation-sqlalchemy==0.46b0
opentelemetry-instrumentation-redis==0.46b0
opentelemetry-instrumentation-httpx==0.46b0
opentelemetry-instrumentation-logging==0.46b0
```

### Shared OTel Bootstrap

Canonical client: `value_fabric.shared.observability.platform`.

Do not initialize a `TracerProvider` in a service. `create_fabric_app(..., telemetry_service_name=..., instrument_telemetry=True)` is the reference path. Per-layer `prometheus_metrics.py` modules remain adapters. SLOs are encoded in `monitoring/slo/slos.contract.json`.

`configure_platform` is fail-closed and once-per-process: missing SDK/endpoint, invalid `OTEL_SAMPLE_RATIO`, exporter errors, and FastAPI instrumentor failures no-op instead of crashing startup. A second call reuses the installed SDK `TracerProvider` rather than creating an orphan provider (OpenTelemetry forbids override).

```python
from value_fabric.shared.observability import (
    bind_context,
    configure_platform,
    correlation_fields,
)
from value_fabric.shared.fastapi_framework import create_fabric_app

app = create_fabric_app(
    service_name="layer4-agents",
    title="Layer 4 Agents",
    version="1.2.0",
    description="Agentic workflow engine",
    telemetry_service_name="layer4-agents",
    instrument_telemetry=True,
)

# Optional: bind identifiers for logs + audit correlation (no DB column).
bind_context(request_id="req-1", tenant_id="tenant-a")
fields = correlation_fields()  # request_id, trace_id, span_id, tenant_id
```

Missing `OTEL_EXPORTER_OTLP_ENDPOINT` or OpenTelemetry SDK → no-op provider; the process still starts.

### L1: Ingestion Service

```python
"""
L1 Ingestion Service — FastAPI + OpenTelemetry instrumentation.
Port: 8001
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.propagate import inject, extract
import structlog

from fabric4l.observability.bootstrap import bootstrap_telemetry

# ---------------------------------------------------------------------------
# Bootstrap OTel
# ---------------------------------------------------------------------------
tracer = bootstrap_telemetry(
    service_name="fabric4l.layer1.ingestion",
    service_version="1.2.0",
)

# ---------------------------------------------------------------------------
# Instrument libraries (BEFORE creating app / engine / redis client)
# ---------------------------------------------------------------------------
RedisInstrumentor().instrument()

logger = structlog.get_logger()

app = FastAPI(title="Fabric_4L L1 Ingestion", version="1.2.0")
FastAPIInstrumentor.instrument_app(
    app,
    excluded_urls="/health,/metrics",
    server_request_hook=lambda span, request: span.set_attribute(
        "tenant.id", _get_tenant_id(request)
    ),
)

# Instrument SQLAlchemy AFTER engine creation
from sqlalchemy import create_engine
engine = create_engine(os.getenv("DATABASE_URL"))
SQLAlchemyInstrumentor().instrument(
    engine=engine,
    enable_commenter=True,
    commenter_options={"db_framework": True, "otel_lib": True},
)


# ---------------------------------------------------------------------------
# Dependency: tenant extraction with trace enrichment
# ---------------------------------------------------------------------------
def _get_tenant_id(request: Request) -> str:
    tenant_id = request.headers.get("x-tenant-id", "unknown")
    # Hash tenant ID for privacy in observability
    import hashlib
    return hashlib.sha256(tenant_id.encode()).hexdigest()[:16]


async def get_current_tenant(request: Request) -> str:
    tenant_id = _get_tenant_id(request)
    current_span = trace.get_current_span()
    current_span.set_attribute("tenant.id", tenant_id)
    current_span.set_attribute("tenant.source", request.headers.get("x-tenant-id", "unknown"))
    return tenant_id


# ---------------------------------------------------------------------------
# Trace-context propagation helper
# ---------------------------------------------------------------------------
def propagate_trace_context(headers: dict) -> dict:
    """
    Inject current trace context into outgoing request headers.
    Use this when calling downstream services (L2, L3, etc.).
    """
    inject(headers)
    return headers


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/v1/documents/ingest")
async def ingest_document(
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
):
    """
    Ingest a single document. Trace context propagates to L2.
    """
    with tracer.start_as_current_span("ingest_document") as span:
        span.set_attribute("document.source", request.headers.get("x-doc-source", "unknown"))
        span.set_attribute("document.content_type", request.headers.get("content-type", "unknown"))

        # Forward to L2 with trace propagation
        import httpx
        headers = propagate_trace_context({"x-tenant-id": request.headers.get("x-tenant-id", "")})

        with tracer.start_as_current_span("l2.extract_request") as child_span:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://l2-extraction:8002/api/v1/extract",
                    headers=headers,
                    json=await request.json(),
                )
                child_span.set_attribute("http.status_code", response.status_code)
                child_span.set_attribute("http.response.size", len(response.content))

        span.set_attribute("document.status", "ingested")
        return JSONResponse({"status": "ingested", "document_id": "doc-123"})


@app.get("/health")
async def health():
    return {"status": "healthy", "layer": "L1"}
```

### L2: Extraction Service

```python
"""
L2 Extraction Service — FastAPI + OpenTelemetry instrumentation.
Port: 8002
"""

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from fabric4l.observability.bootstrap import bootstrap_telemetry

# ---------------------------------------------------------------------------
# Bootstrap OTel
# ---------------------------------------------------------------------------
tracer = bootstrap_telemetry(
    service_name="fabric4l.layer2.extraction",
    service_version="1.2.0",
)

# ... SQLAlchemy engine setup, Redis client setup ...
app = FastAPI(title="Fabric_4L L2 Extraction", version="1.2.0")
FastAPIInstrumentor.instrument_app(app, excluded_urls="/health,/metrics")
SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True)


@app.post("/api/v1/extract")
async def extract_entities(request: Request):
    """
    Extract entities and relationships from a document.
    Trace context received from L1 via traceparent header.
    """
    with tracer.start_as_current_span("extract_entities") as span:
        body = await request.json()
        span.set_attribute("extraction.model", "spacy-en-core-web-lg")
        span.set_attribute("document.text_length", len(body.get("text", "")))

        # Entity extraction sub-span
        with tracer.start_as_current_span("ner_pipeline") as ner_span:
            entities = run_ner(body["text"])
            ner_span.set_attribute("entities.count", len(entities))

        # Relationship extraction sub-span
        with tracer.start_as_current_span("relation_extraction") as rel_span:
            relationships = extract_relationships(entities)
            rel_span.set_attribute("relationships.count", len(relationships))

        span.set_attribute("extraction.total_entities", len(entities))
        span.set_attribute("extraction.total_relationships", len(relationships))

        return {"entities": entities, "relationships": relationships}
```

### L3: Knowledge Service

```python
"""
L3 Knowledge Service — Neo4j + pgvector + OpenTelemetry.
Port: 8003
"""

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.neo4j import Neo4jInstrumentor  # via contrib
from fabric4l.observability.bootstrap import bootstrap_telemetry

tracer = bootstrap_telemetry(
    service_name="fabric4l.layer3.knowledge",
    service_version="1.2.0",
)

app = FastAPI(title="Fabric_4L L3 Knowledge", version="1.2.0")
FastAPIInstrumentor.instrument_app(app, excluded_urls="/health,/metrics")
SQLAlchemyInstrumentor().instrument(engine=pg_engine, enable_commenter=True)
Neo4jInstrumentor().instrument()


@app.post("/api/v1/knowledge/graph/ingest")
async def ingest_to_graph(request: Request):
    """Ingest entities into Neo4j knowledge graph."""
    with tracer.start_as_current_span("knowledge_graph_ingest") as span:
        body = await request.json()
        span.set_attribute("graph.operation", "MERGE")
        span.set_attribute("graph.batch_size", len(body.get("entities", [])))

        with tracer.start_as_current_span("neo4j_merge") as neo_span:
            result = neo4j_session.run(
                """
                UNWIND $entities AS entity
                MERGE (n:Entity {id: entity.id})
                ON CREATE SET n += entity.properties
                RETURN count(n) AS created
                """,
                entities=body["entities"],
            )
            record = result.single()
            neo_span.set_attribute("neo4j.nodes_merged", record["created"] if record else 0)

        return {"status": "ingested", "nodes_merged": record["created"] if record else 0}


@app.post("/api/v1/knowledge/vector/search")
async def vector_search(request: Request):
    """Semantic search via pgvector with traced query."""
    with tracer.start_as_current_span("vector_search") as span:
        body = await request.json()
        span.set_attribute("vector.query", body.get("query", "")[:100])
        span.set_attribute("vector.top_k", body.get("top_k", 10))

        with tracer.start_as_current_span("pgvector_query") as pg_span:
            embedding = get_embedding(body["query"])
            results = pg_session.execute(
                """
                SELECT id, content, embedding <=> :embedding AS distance
                FROM document_embeddings
                ORDER BY embedding <=> :embedding
                LIMIT :top_k
                """,
                {"embedding": str(embedding), "top_k": body.get("top_k", 10)},
            )
            pg_span.set_attribute("db.rows_returned", results.rowcount)

        return {"results": [dict(r) for r in results.mappings()]}
```

### L4: Agents Service

```python
"""
L4 Agents Service — LangGraph + OpenTelemetry custom instrumentation.
Port: 8004
"""

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fabric4l.observability.bootstrap import bootstrap_telemetry
from opentelemetry.trace import Status, StatusCode

tracer = bootstrap_telemetry(
    service_name="fabric4l.layer4.agents",
    service_version="1.2.0",
)

app = FastAPI(title="Fabric_4L L4 Agents", version="1.2.0")
FastAPIInstrumentor.instrument_app(app, excluded_urls="/health,/metrics")


# ---------------------------------------------------------------------------
# LangGraph workflow instrumentation
# ---------------------------------------------------------------------------
def instrument_langgraph_workflow(workflow_name: str, func):
    """Decorator to instrument a LangGraph workflow execution."""
    async def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(f"agent.workflow.{workflow_name}") as span:
            span.set_attribute("agent.workflow.name", workflow_name)
            span.set_attribute("agent.framework", "langgraph")

            start_time = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                span.set_attribute("agent.workflow.status", "completed")
                span.set_attribute("agent.workflow.steps", result.get("step_count", 0))
                return result
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.set_attribute("agent.workflow.status", "failed")
                span.record_exception(exc)
                raise
            finally:
                duration_ms = (time.monotonic() - start_time) * 1000
                span.set_attribute("duration_ms", duration_ms)

    return wrapper


@app.post("/api/v1/agents/workflow/{workflow_name}")
@instrument_langgraph_workflow("default")
async def execute_workflow(workflow_name: str, request: Request):
    """Execute a LangGraph agent workflow with full tracing."""
    body = await request.json()

    with tracer.start_as_current_span("llm.invoke") as llm_span:
        llm_span.set_attribute("llm.provider", body.get("provider", "openai"))
        llm_span.set_attribute("llm.model", body.get("model", "gpt-4"))
        llm_span.set_attribute("llm.temperature", body.get("temperature", 0.0))

        # Track token usage
        response = await call_llm(body["messages"], model=body.get("model", "gpt-4"))
        llm_span.set_attribute("llm.tokens.prompt", response["usage"]["prompt_tokens"])
        llm_span.set_attribute("llm.tokens.completion", response["usage"]["completion_tokens"])
        llm_span.set_attribute("llm.tokens.total", response["usage"]["total_tokens"])

    return {"workflow": workflow_name, "result": response}
```

### L5: Ground Truth Service

```python
"""
L5 Ground Truth Service — Human validation workflow tracing.
Port: 8005
"""

from fabric4l.observability.bootstrap import bootstrap_telemetry
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

tracer = bootstrap_telemetry(
    service_name="fabric4l.layer5.groundtruth",
    service_version="1.2.0",
)

app = FastAPI(title="Fabric_4L L5 Ground Truth", version="1.2.0")
FastAPIInstrumentor.instrument_app(app, excluded_urls="/health,/metrics")
SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True)


@app.post("/api/v1/validation/submit")
async def submit_validation(request: Request):
    """Submit a human validation decision with full audit trace."""
    with tracer.start_as_current_span("validation.submit") as span:
        body = await request.json()
        span.set_attribute("validation.item_id", body.get("item_id", ""))
        span.set_attribute("validation.decision", body.get("decision", ""))
        span.set_attribute("validation.reviewer_id", body.get("reviewer_id", "anonymous"))

        with tracer.start_as_current_span("db.insert_validation") as db_span:
            # Insert into PostgreSQL with RLS
            result = db_session.execute(
                "INSERT INTO validations (item_id, decision, reviewer_id) VALUES (:i, :d, :r) RETURNING id",
                {"i": body["item_id"], "d": body["decision"], "r": body["reviewer_id"]},
            )
            validation_id = result.scalar_one()
            db_span.set_attribute("db.inserted_id", validation_id)

        return {"validation_id": validation_id, "status": "recorded"}
```

### L6: Benchmarks Service

```python
"""
L6 Benchmarks Service — Performance evaluation tracing.
Port: 8006
"""

from fabric4l.observability.bootstrap import bootstrap_telemetry
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

tracer = bootstrap_telemetry(
    service_name="fabric4l.layer6.benchmarks",
    service_version="1.2.0",
)

app = FastAPI(title="Fabric_4L L6 Benchmarks", version="1.2.0")
FastAPIInstrumentor.instrument_app(app, excluded_urls="/health,/metrics")
SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True)


@app.post("/api/v1/benchmarks/run")
async def run_benchmark(request: Request):
    """Run a benchmark suite with detailed performance traces."""
    with tracer.start_as_current_span("benchmark.run") as span:
        body = await request.json()
        benchmark_name = body.get("name", "default")
        span.set_attribute("benchmark.name", benchmark_name)
        span.set_attribute("benchmark.dataset_size", body.get("dataset_size", 0))

        # Each benchmark iteration gets its own span
        results = []
        for i in range(body.get("iterations", 1)):
            with tracer.start_as_current_span(f"benchmark.iteration.{i}") as iter_span:
                start = time.monotonic()
                score = await run_single_benchmark(body["dataset"])
                duration_ms = (time.monotonic() - start) * 1000
                iter_span.set_attribute("benchmark.score", score)
                iter_span.set_attribute("duration_ms", duration_ms)
                results.append({"iteration": i, "score": score, "duration_ms": duration_ms})

        avg_score = sum(r["score"] for r in results) / len(results)
        span.set_attribute("benchmark.avg_score", avg_score)
        return {"benchmark": benchmark_name, "results": results, "avg_score": avg_score}
```

---

## Frontend Instrumentation

```typescript
// src/observability.ts
// React + OpenTelemetry Web instrumentation

import { WebTracerProvider, BatchSpanProcessor } from '@opentelemetry/sdk-trace-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';
import { W3CTraceContextPropagator } from '@opentelemetry/core';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

const resource = new Resource({
  [SemanticResourceAttributes.SERVICE_NAME]: 'fabric4l.frontend',
  [SemanticResourceAttributes.SERVICE_NAMESPACE]: 'fabric4l',
  [SemanticResourceAttributes.SERVICE_VERSION]: '1.2.0',
});

const traceExporter = new OTLPTraceExporter({
  url: 'http://otel-collector:4318/v1/traces', // OTLP HTTP endpoint
});

const provider = new WebTracerProvider({
  resource,
  spanProcessors: [new BatchSpanProcessor(traceExporter)],
});

provider.register({
  propagator: new W3CTraceContextPropagator(),
});

registerInstrumentations({
  instrumentations: [
    getWebAutoInstrumentations({
      '@opentelemetry/instrumentation-xml-http-request': {
        propagateTraceHeaderCorsUrls: [
          /http:\/\/l[1-6]-[^:]+/,
          /http:\/\/localhost:800[1-6]/,
        ],
        clearTimingResources: true,
      },
      '@opentelemetry/instrumentation-fetch': {
        propagateTraceHeaderCorsUrls: [
          /http:\/\/l[1-6]-[^:]+/,
          /http:\/\/localhost:800[1-6]/,
        ],
        clearTimingResources: true,
      },
      '@opentelemetry/instrumentation-document-load': {},
    }),
  ],
});

// ---------------------------------------------------------------------------
// Custom trace context helper for API calls
// ---------------------------------------------------------------------------
export function getTraceHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  new W3CTraceContextPropagator().inject(
    {},
    headers,
    { set: (h, key, value) => { h[key] = value; } },
  );
  return headers;
}

// Usage in API client:
// fetch('/api/ingest', { headers: { ...getTraceHeaders(), 'x-tenant-id': tenantId } })
```

---

## Cross-Service Trace Propagation

### Python: Propagate via `traceparent` header

```python
import httpx
from opentelemetry.propagate import inject, extract

async def call_downstream_service(
    downstream_url: str,
    payload: dict,
    tenant_id: str,
) -> dict:
    """
    Make an HTTP call to a downstream service with trace context propagation.

    The current span context is injected into the outgoing request headers
    via the W3C Trace Context (traceparent) header. The downstream service
    automatically extracts this and continues the trace.
    """
    headers: dict[str, str] = {
        "x-tenant-id": tenant_id,
        "content-type": "application/json",
    }

    # Inject current trace context into headers (adds traceparent, tracestate)
    inject(headers)

    current_span = trace.get_current_span()
    current_span.set_attribute("downstream.url", downstream_url)
    current_span.set_attribute("downstream.method", "POST")

    with tracer.start_as_current_span("http.downstream_request") as span:
        span.set_attribute("http.url", downstream_url)
        span.set_attribute("http.method", "POST")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(downstream_url, json=payload, headers=headers)

            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response.size", len(response.content))

            if response.status_code >= 400:
                span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                span.record_exception(Exception(response.text[:500]))

        return response.json()
```

### Extracting trace context at the receiving service

When using `FastAPIInstrumentor`, trace context is **automatically extracted**
from incoming `traceparent` headers. No manual extraction is needed.

If you need manual extraction (e.g., in a background task):

```python
from opentelemetry.propagate import extract
from opentelemetry import trace

async def background_task(headers: dict):
    """Extract trace context from headers and continue the trace."""
    context = extract(headers)  # extracts traceparent/tracestate
    with trace.get_tracer(__name__).start_as_current_span(
        "background_task",
        context=context,
    ) as span:
        # This span will be a child of the incoming request span
        span.set_attribute("task.type", "async_cleanup")
        await do_work()
```

---

## Validation & Testing

### 1. Check OTel Collector is receiving data

```bash
# Check collector health
curl http://localhost:13133

# Check zpages for active spans
curl http://localhost:55679/debug/tracez

# View a specific trace in Jaeger
curl "http://localhost:16686/api/traces?service=fabric4l.layer1.ingestion&limit=10"
```

### 2. Verify trace propagation end-to-end

```bash
# Send a request to L1 with a custom traceparent
TRACEPARENT="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
curl -X POST http://localhost:8001/api/v1/documents/ingest \
  -H "traceparent: $TRACEPARENT" \
  -H "x-tenant-id: tenant-acme" \
  -H "content-type: application/json" \
  -d '{"text": "Hello world", "source": "test"}'

# Verify in Jaeger that all 6 layers appear in a single trace
open http://localhost:16686/search?service=fabric4l.layer1.ingestion
```

### 3. Unit test for trace context propagation

```python
# tests/test_trace_propagation.py
import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


@pytest.fixture
tracer_and_exporter():
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    yield trace.get_tracer("test"), exporter
    exporter.clear()


def test_trace_propagation_to_downstream(tracer_and_exporter):
    tracer, exporter = tracer_and_exporter

    with tracer.start_as_current_span("parent_span"):
        headers = {}
        inject(headers)

        assert "traceparent" in headers
        trace_id = format(trace.get_current_span().get_span_context().trace_id, "032x")
        assert trace_id in headers["traceparent"]

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "parent_span"
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No traces in Jaeger | OTel Collector not reachable | Check `OTEL_EXPORTER_OTLP_ENDPOINT` env var; verify collector health at `:13133` |
| Traces not linking across services | Missing `traceparent` header | Ensure `inject(headers)` is called before every outbound HTTP request |
| Spans missing SQL queries | SQLAlchemy not instrumented | Call `SQLAlchemyInstrumentor().instrument(engine=...)` **after** engine creation |
| High memory usage in Collector | Batch size too large | Reduce `send_batch_size` to 512; add `memory_limiter` processor |
| Frontend traces not appearing | CORS blocking headers | Add `traceparent` to `allowed_headers` in OTel Collector CORS config |

---

## Appendix: Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4317` | OTLP gRPC endpoint for traces + metrics |
| `OTEL_SERVICE_NAME` | — | Override service name |
| `OTEL_RESOURCE_ATTRIBUTES` | — | Comma-separated `key=value` resource attributes |
| `OTEL_TRACES_SAMPLER` | `parentbased_traceidratio` | Sampling strategy |
| `OTEL_TRACES_SAMPLER_ARG` | `0.1` | Sampling ratio (0.0–1.0) |
| `DEPLOYMENT_ENVIRONMENT` | `development` | Environment label (dev/staging/prod) |
