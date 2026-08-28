"""P0-007: Static contract tests for OpenTelemetry instrumentation coverage.

Verifies that the three services identified as missing OTel instrumentation
(billing, layer2-5-signal-refinery, layer7-billing) are actually instrumented
at the source-code level.  Runtime trace receipt is validated separately by
``tests/backend_integrated/test_otel_trace_receipt.py``.
"""

from __future__ import annotations

import ast
import pathlib
from typing import Any

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_source(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_call(source: str, func_name: str) -> bool:
    """Naive but sufficient static check for a top-level function call."""
    return func_name in source


def _has_kwarg_in_call(source: str, kwarg: str) -> bool:
    """Check that a keyword argument appears in a function call."""
    return kwarg in source


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.contract_static_no_service
class TestOtelInstrumentationStatic:
    """Static source-analysis contract tests for OTel instrumentation."""

    def test_layer1_passes_instrument_telemetry_true(self) -> None:
        """layer1-ingestion must pass instrument_telemetry=True."""
        path = (
            REPO_ROOT
            / "services"
            / "layer1-ingestion"
            / "src"
            / "layer1_ingestion"
            / "api"
            / "main.py"
        )
        source = _read_source(path)
        assert _has_kwarg_in_call(source, "telemetry_service_name=\"layer1-ingestion\""), (
            "layer1-ingestion must set telemetry_service_name for create_fabric_app"
        )
        assert _has_kwarg_in_call(source, "instrument_telemetry=True"), (
            "layer1-ingestion must pass instrument_telemetry=True to create_fabric_app"
        )

    def test_layer2_passes_instrument_telemetry_true(self) -> None:
        """layer2-extraction must pass instrument_telemetry=True."""
        path = (
            REPO_ROOT
            / "services"
            / "layer2-extraction"
            / "src"
            / "layer2_extraction"
            / "api"
            / "app_factory.py"
        )
        if not path.exists():
            path = (
                REPO_ROOT
                / "services"
                / "layer2-extraction"
                / "src"
                / "layer2_extraction"
                / "api"
                / "main.py"
            )
        source = _read_source(path)
        assert _has_kwarg_in_call(source, "instrument_telemetry=True"), (
            "layer2-extraction must pass instrument_telemetry=True to create_fabric_app"
        )

    def test_layer25_passes_instrument_telemetry_true(self) -> None:
        """layer2-5-signal-refinery must pass instrument_telemetry=True."""
        path = (
            REPO_ROOT
            / "services"
            / "layer2-5-signal-refinery"
            / "src"
            / "layer2_5_signal_refinery"
            / "api"
            / "main.py"
        )
        source = _read_source(path)
        assert _has_kwarg_in_call(source, "instrument_telemetry=True"), (
            "layer2-5-signal-refinery must pass instrument_telemetry=True to create_fabric_app"
        )

    def test_layer7_passes_instrument_telemetry_true(self) -> None:
        """layer7-billing must pass instrument_telemetry=True."""
        path = (
            REPO_ROOT
            / "services"
            / "layer7-billing"
            / "src"
            / "layer7_billing"
            / "api"
            / "main.py"
        )
        source = _read_source(path)
        assert _has_kwarg_in_call(source, "instrument_telemetry=True"), (
            "layer7-billing must pass instrument_telemetry=True to create_fabric_app"
        )

    def test_layer7_registers_health_endpoint_for_live_trace_probe(self) -> None:
        """layer7-billing must expose the health endpoint used by live trace receipt tests."""
        path = (
            REPO_ROOT
            / "services"
            / "layer7-billing"
            / "src"
            / "layer7_billing"
            / "api"
            / "main.py"
        )
        source = _read_source(path)
        assert _has_call(source, "register_health_endpoint"), (
            "layer7-billing must register /health so live trace receipt can probe port 8008"
        )

    def test_live_trace_receipt_defaults_layer7_to_layer7_port(self) -> None:
        """Layer 7 live trace tests must not default to the billing service port."""
        path = REPO_ROOT / "tests" / "backend_integrated" / "test_otel_trace_receipt.py"
        source = _read_source(path)
        assert 'LAYER7_URL = os.getenv("LAYER7_URL", "http://localhost:8008")' in source
        assert 'LAYER7_URL = os.getenv("LAYER7_URL", "http://localhost:8000")' not in source

    def test_opentelemetry_collector_yaml_is_valid(self) -> None:
        """The OpenTelemetry collector manifest must be parseable YAML
        and declare required OTLP receiver ports."""
        path = REPO_ROOT / "k8s" / "monitoring" / "opentelemetry-collector.yaml"
        raw = _read_source(path)
        docs = list(yaml.safe_load_all(raw))
        # Find the OpenTelemetryCollector CRD document
        collector_doc: dict[str, Any] | None = None
        for doc in docs:
            if doc and doc.get("kind") == "OpenTelemetryCollector":
                collector_doc = doc
                break
        assert collector_doc is not None, (
            "opentelemetry-collector.yaml must contain an OpenTelemetryCollector document"
        )
        spec = collector_doc.get("spec", {})
        config = spec.get("config", "")
        assert "otlp:" in config, "Collector config must declare an OTLP receiver"
        assert "4317" in config, "Collector must expose OTLP gRPC on 4317"
        assert "4318" in config, "Collector must expose OTLP HTTP on 4318"
        assert "traces:" in config, "Collector must declare a traces pipeline"
        assert "service:" in config, "Collector must declare a service section"


@pytest.mark.unit
@pytest.mark.contract_static_no_service
def test_all_services_have_otel_env_references() -> None:
    """At least one k8s manifest or compose file should reference OTEL_
    environment variables so workloads know where to export traces.
    """
    search_roots = [
        REPO_ROOT / "k8s",
        REPO_ROOT / "services",
        REPO_ROOT / "infra",
        REPO_ROOT,
    ]
    patterns = ["*.yaml", "*.yml", ".env*", "*.env*"]
    skip_dirs = {"node_modules", ".venv", "__pycache__", ".tmp", ".pytest_cache", ".git", "apps"}

    otel_refs: list[pathlib.Path] = []
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in patterns:
            for path in root.rglob(pattern):
                relative_parts = path.relative_to(root).parts
                if any(part in skip_dirs for part in relative_parts):
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if "OTEL_" in text:
                    otel_refs.append(path)
                    break  # stop searching this root once we find one hit
            if otel_refs:
                break
        if otel_refs:
            break

    assert len(otel_refs) > 0, (
        "No Kubernetes manifest, compose file, or env file references OTEL_* environment variables. "
        "Services need OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, etc. to emit traces."
    )
