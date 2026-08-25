from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.tracing.middleware import TracingMiddleware


def test_trace_context_propagates_between_upstream_and_layer3(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(
        "src.tracing.middleware._otel_tracer",
        provider.get_tracer("layer3-trace-context-test"),
    )

    upstream = FastAPI()
    layer3 = FastAPI()

    @layer3.get("/layer3")
    async def layer3_endpoint():
        return {"ok": True}

    layer3.add_middleware(TracingMiddleware)

    @upstream.get("/proxy")
    async def proxy_endpoint(request: Request):
        with TestClient(layer3) as downstream_client:
            downstream = downstream_client.get(
                "/layer3",
                headers={"traceparent": request.headers["traceparent"]},
            )
            return {
                "trace_id": downstream.headers.get("X-Trace-ID"),
                "span_id": downstream.headers.get("X-Span-Id"),
            }

    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    with TestClient(upstream) as client:
        response = client.get("/proxy", headers={"traceparent": traceparent})

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert body["span_id"]

    spans = exporter.get_finished_spans()
    layer3_server_spans = [s for s in spans if s.name == "GET /layer3"]
    assert layer3_server_spans
    assert layer3_server_spans[-1].parent
    assert (
        format(layer3_server_spans[-1].context.trace_id, "032x")
        == "4bf92f3577b34da6a3ce929d0e0e4736"
    )


def test_trace_headers_and_request_ids_are_preserved_and_logged(caplog) -> None:
    caplog.set_level("INFO")

    layer3 = FastAPI()

    @layer3.get("/layer3")
    async def layer3_endpoint():
        return {"ok": True}

    layer3.add_middleware(TracingMiddleware)

    with TestClient(layer3) as client:
        response = client.get(
            "/layer3",
            headers={
                "X-Request-ID": "req-otel-1",
                "X-Correlation-ID": "corr-otel-1",
            },
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == response.headers["X-Trace-ID"]
    assert response.headers["X-Correlation-ID"] == response.headers["X-Trace-ID"]
    assert response.headers.get("X-Span-Id")

    records = [
        rec
        for rec in caplog.records
        if rec.message in {"request_tracing_started", "request_tracing_finished"}
    ]
    assert records
    assert any(getattr(rec, "request_id", None) == "req-otel-1" for rec in records)
    assert any(getattr(rec, "correlation_id", None) == "corr-otel-1" for rec in records)
