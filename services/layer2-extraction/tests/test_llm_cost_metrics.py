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
            provider="openai",
            model="gpt-4o",
            tenant_id="test-tenant",
            cost_usd=0.025
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
            provider="openai",
            model="gpt-4o",
            token_type="prompt",
            count=1000
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
