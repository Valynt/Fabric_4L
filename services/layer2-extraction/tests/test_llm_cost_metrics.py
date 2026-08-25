"""Tests for LLM cost Prometheus metrics (Task 76/104)."""

from __future__ import annotations

import pytest
from layer2_extraction.metrics.prometheus_metrics import (
    MetricsConfig,
    PrometheusMetrics,
    initialize_metrics,
    get_metrics,
)


class TestLLMCostMetrics:
    """Verify LLM cost tracking metrics work correctly."""

    def test_metrics_initialization(self):
        """Prometheus metrics can be initialized."""
        metrics = initialize_metrics()
        assert metrics is not None
        assert metrics.config.enabled is True

    def test_record_llm_cost(self):
        """LLM cost can be recorded."""
        metrics = PrometheusMetrics()

        # Record a cost
        metrics.record_llm_cost(
            provider="openai", model="gpt-4o", tenant_id="test-tenant", cost_usd=0.025
        )

        # Verify the cost was accumulated
        key = ("openai", "gpt-4o", "test-tenant")
        assert metrics._accumulated_costs[key] == 0.025

    def test_accumulate_multiple_costs(self):
        """Multiple costs accumulate correctly."""
        metrics = PrometheusMetrics()

        # Record multiple costs for same provider/model/tenant
        metrics.record_llm_cost("openai", "gpt-4o", "tenant-1", 0.01)
        metrics.record_llm_cost("openai", "gpt-4o", "tenant-1", 0.02)
        metrics.record_llm_cost("openai", "gpt-4o", "tenant-1", 0.03)

        key = ("openai", "gpt-4o", "tenant-1")
        assert metrics._accumulated_costs[key] == 0.06

    def test_record_llm_tokens(self):
        """LLM token counts can be recorded."""
        metrics = PrometheusMetrics()

        # Record tokens
        metrics.record_llm_tokens(
            provider="openai", model="gpt-4o", token_type="prompt", count=1000
        )

        # Just verify no exception is raised
        assert True

    def test_get_metrics_output(self):
        """Metrics output can be generated."""
        metrics = PrometheusMetrics()

        # Record some data
        metrics.record_llm_cost("anthropic", "claude-3-5-sonnet", "tenant-2", 0.05)

        # Get metrics output
        output = metrics.get_metrics()
        assert isinstance(output, str)
        assert len(output) > 0
        # Should contain our metric
        assert "vf_llm_cost_usd_total" in output

    def test_tenant_isolation(self):
        """Costs are isolated by tenant."""
        metrics = PrometheusMetrics()

        # Record costs for different tenants
        metrics.record_llm_cost("openai", "gpt-4o", "tenant-a", 0.10)
        metrics.record_llm_cost("openai", "gpt-4o", "tenant-b", 0.20)

        # Verify separate accumulation
        assert metrics._accumulated_costs[("openai", "gpt-4o", "tenant-a")] == 0.10
        assert metrics._accumulated_costs[("openai", "gpt-4o", "tenant-b")] == 0.20

    def test_set_health_status(self):
        """Health status can be recorded and appears in metrics output."""
        metrics = PrometheusMetrics()
        metrics.set_health_status(True, component="api")
        metrics.set_health_status(False, component="layer3")
        output = metrics.get_metrics()
        assert "vf_health_status" in output
        assert "layer2_health_status" in output
        assert "value_fabric_health_status" in output
        assert 'component="api"' in output
        assert 'component="layer3"' in output

    def test_record_http_request_and_duration(self):
        """HTTP SLI request and latency metrics can be recorded."""
        metrics = PrometheusMetrics()
        metrics.record_http_request(
            method="POST",
            endpoint="/api/v1/extract",
            status_code=200,
            tenant_id="tenant-123",
        )
        metrics.record_http_duration(
            method="POST",
            endpoint="/api/v1/extract",
            duration_seconds=0.35,
            tenant_id="tenant-123",
        )
        output = metrics.get_metrics()
        assert "layer2_http_requests_total" in output
        assert "value_fabric_http_requests_total" in output
        assert 'method="POST"' in output
        assert 'endpoint="/api/v1/extract"' in output
        assert 'status_code="200"' in output
        assert "layer2_http_request_duration_seconds_bucket" in output
        assert 'le="0.5"' in output
        assert "layer2_http_request_duration_seconds_count" in output
        assert "layer2_http_request_duration_seconds_sum" in output

    def test_metrics_middleware_integration(self):
        """MetricsMiddleware records live HTTP requests through ASGI application."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from layer2_extraction.metrics import MetricsMiddleware, PrometheusMetrics
        from value_fabric.shared.fastapi_framework import install_metrics_middleware

        app = FastAPI()
        metrics = PrometheusMetrics()
        install_metrics_middleware(app, metrics=metrics, middleware_factory=MetricsMiddleware)

        @app.get("/test-route")
        def test_route():
            return {"status": "ok"}

        client = TestClient(app)
        res = client.get("/test-route")
        assert res.status_code == 200

        output = metrics.get_metrics()
        assert "layer2_http_requests_total" in output
        assert 'endpoint="/test-route"' in output
        assert 'status_code="200"' in output
        assert "layer2_http_request_duration_seconds_count" in output


class TestGlobalMetrics:
    """Verify global metrics singleton works."""

    def test_get_metrics_returns_initialized_metrics(self):
        """get_metrics() returns the initialized metrics instance."""
        # First initialize
        initialized = initialize_metrics()
        assert initialized is not None

        # Then get via global accessor
        retrieved = get_metrics()
        assert retrieved is initialized


def test_monitoring_contract_metric_names_and_labels() -> None:
    """Smoke assertion to prevent monitoring contract drift."""
    metrics = PrometheusMetrics()
    labels = dict(
        tenant_id="tenant-1",
        ingestion_id="ing-1",
        extraction_job_id="job-1",
        model_version="gpt-4o",
        schema_version="v1",
        value_pack_id="pack-1",
    )
    metrics.record_extraction_outcome(status="success", **labels)
    metrics.record_schema_validation_failure(endpoint="extract_capabilities", **labels)
    metrics.record_retry(endpoint="run_extraction", **labels)
    metrics.record_model_latency(endpoint="extract_capabilities", latency_seconds=0.42, **labels)
    metrics.record_confidence(entity_type="capability", confidence=0.91, **labels)
    metrics.record_cache_failure(failure_type="decode", operation="read", **labels)
    output = metrics.get_metrics()
    # Metrics use a stable low-cardinality tenant_bucket label (not raw tenant_id)
    # to bound Prometheus cardinality. extraction_job_id and value_pack_id are
    # stored internally but not emitted as Prometheus labels.
    for expected in (
        "vf_extraction_outcomes_total",
        "vf_schema_validation_failures_total",
        "vf_extraction_retries_total",
        "vf_model_latency_seconds_count",
        "vf_model_latency_seconds_sum",
        "vf_extraction_confidence_count",
        "vf_extraction_confidence_avg",
        "vf_cache_failures_total",
        "tenant_bucket",
        'schema_version="v1"',
    ):
        assert expected in output
