from __future__ import annotations

import json
from pathlib import Path

from value_fabric.shared.observability.logging import (
    enrich_event_with_logging_context,
    enrich_event_with_request_context,
)
from value_fabric.shared.observability.request_context import (
    LoggingContext,
    clear_logging_context,
    set_logging_context,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

STRUCTURED_LOGGING_FILES = {
    "api": REPO_ROOT / "services/api/app/logging_config.py",
    "layer2": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/logging_config.py",
    "layer3": REPO_ROOT / "services/layer3-knowledge/src/logging_config.py",
    "layer5": REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/observability/structured_logging.py",
    "layer6": REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/logging_config.py",
    "shared": REPO_ROOT / "packages/shared/src/value_fabric/shared/observability/logging.py",
}

REQUIRED_LOG_FIELDS = {"event", "level", "timestamp", "tenant_id", "request_id", "correlation_id"}


def test_structured_logging_reference_defines_required_fields() -> None:
    reference = (REPO_ROOT / "docs/reference/structured-logging-fields.md").read_text(encoding="utf-8")
    for field in REQUIRED_LOG_FIELDS:
        assert f"`{field}`" in reference, f"structured logging reference must define {field}"


def test_production_logging_paths_use_json_renderer() -> None:
    for service, path in STRUCTURED_LOGGING_FILES.items():
        source = path.read_text(encoding="utf-8")
        assert (
            "JSONRenderer" in source
            or "JSONFormatter" in source
            or "json.dumps" in source
        ), f"{service} logging must emit JSON in production"
        assert "TimeStamper" in source or "timestamp" in source, f"{service} logs must include timestamps"


def test_shared_log_enrichment_adds_correlation_fields() -> None:
    event = enrich_event_with_request_context(None, None, {"event": "contract_check"})
    assert "trace_id" in event
    assert event["correlation_id"] == event["trace_id"]


def test_logging_context_enrichment_uses_request_context() -> None:
    set_logging_context(
        LoggingContext(
            request_id="req-contract",
            correlation_id="req-contract",
            tenant_id="tenant-alpha",
            route="/v1/contracts",
            method="GET",
            status=200,
            latency_ms=12.5,
        )
    )
    try:
        event = enrich_event_with_logging_context(None, None, {"event": "request"})
    finally:
        clear_logging_context()

    assert event["request_id"] == "req-contract"
    assert event["correlation_id"] == "req-contract"
    assert event["tenant_id"] == "tenant-alpha"
    json.dumps(event)
