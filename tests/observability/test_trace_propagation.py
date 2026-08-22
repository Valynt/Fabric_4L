from __future__ import annotations

from pathlib import Path

from value_fabric.shared.observability.trace_context import canonical_trace_headers
from value_fabric.shared.observability.w3c_trace_context import (
    TraceContext,
    extract_trace_context,
    inject_trace_context,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

MAINTAINED_APP_ENTRYPOINTS = {
    "api": REPO_ROOT / "services/api/app/main.py",
    "layer1": REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
    "layer2": REPO_ROOT
    / "services/layer2-extraction/src/layer2_extraction/api/app_factory.py",
    "layer3": REPO_ROOT / "services/layer3-knowledge/src/api/main.py",
    "layer4": REPO_ROOT / "services/layer4-agents/src/layer4_agents/api/app_factory.py",
    "layer5": REPO_ROOT
    / "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
    "layer6": REPO_ROOT
    / "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
}

BOUNDARY_SOURCES = {
    "api_boundary": REPO_ROOT
    / "packages/shared/src/value_fabric/shared/error_handling/middleware.py",
    "http_trace_boundary": REPO_ROOT
    / "packages/shared/src/value_fabric/shared/observability/w3c_trace_context.py",
    "db_boundary": REPO_ROOT
    / "packages/shared/src/value_fabric/shared/database/runtime_adapter.py",
    "queue_boundary": REPO_ROOT
    / "packages/shared/src/value_fabric/shared/audit/redis_queue.py",
    "worker_boundary": REPO_ROOT
    / "packages/shared/src/value_fabric/shared/audit/worker.py",
}


def test_canonical_trace_headers_mirror_request_and_alias_headers() -> None:
    headers = canonical_trace_headers("req-trace-contract")
    assert headers["X-Request-ID"] == "req-trace-contract"
    assert headers["X-Correlation-ID"] == "req-trace-contract"
    assert headers["X-Trace-ID"] == "req-trace-contract"


def test_w3c_trace_context_round_trip() -> None:
    context = TraceContext(
        trace_id="0" * 31 + "1",
        parent_id="0" * 15 + "2",
        flags="01",
    )
    headers: dict[str, str] = {}
    inject_trace_context(headers, context)

    extracted = extract_trace_context({"TraceParent": headers["traceparent"]})
    assert extracted == context


def test_maintained_entrypoints_enable_request_or_otel_instrumentation() -> None:
    for service, path in MAINTAINED_APP_ENTRYPOINTS.items():
        source = path.read_text(encoding="utf-8")
        assert (
            "instrument_telemetry=True" in source
            or "RequestIDMiddleware" in source
            or "add_request_id_middleware" in source
            or "TracingMiddleware" in source
            or "create_fabric_app" in source
        ), f"{service} entrypoint must install request/trace instrumentation"


def test_trace_context_has_boundary_coverage_hooks() -> None:
    boundary_tokens = {
        "api_boundary": ("resolve_trace_context", "canonical_trace_headers"),
        "http_trace_boundary": ("inject_trace_context", "extract_trace_context"),
        "db_boundary": ("tenant_context", "session.info"),
        "queue_boundary": ("model_dump", "retry"),
        "worker_boundary": ("request_id", "retry"),
    }
    for boundary, tokens in boundary_tokens.items():
        source = BOUNDARY_SOURCES[boundary].read_text(encoding="utf-8")
        for token in tokens:
            assert (
                token in source
            ), f"{boundary} must preserve trace/correlation context token {token}"
