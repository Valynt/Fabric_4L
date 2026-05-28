from __future__ import annotations

"""Tests for LLM cost calculation and metric emission."""


import hashlib
import json
import os
import tempfile
from uuid import uuid4

import pytest
from prometheus_client import CollectorRegistry

from value_fabric.layer4.metrics.llm_cost_calculator import LLMCostCalculator
from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, PrometheusMetrics


def _expected_tenant_tier(tenant_id: str) -> str:
    """Reproduce the tier derivation logic used by PrometheusMetrics."""
    hash_bytes = hashlib.sha256(tenant_id.encode()).digest()
    return hash_bytes[:2].hex()


class TestLLMCostCalculator:
    def test_calculate_cost_known_model(self):
        calc = LLMCostCalculator()
        cost = calc.calculate_cost(
            provider="openai",
            model="gpt-4o",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        expected = (1000 / 1000) * 0.005 + (500 / 1000) * 0.015
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_mini_model(self):
        calc = LLMCostCalculator()
        cost = calc.calculate_cost(
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=2000,
            completion_tokens=1000,
        )
        expected = (2000 / 1000) * 0.00015 + (1000 / 1000) * 0.0006
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_unknown_model_returns_zero_and_logs_warning(self, caplog):
        calc = LLMCostCalculator()
        with caplog.at_level("WARNING"):
            cost = calc.calculate_cost(
                provider="openai",
                model="unknown-model",
                prompt_tokens=1000,
                completion_tokens=500,
            )
        assert cost == 0.0
        assert "Unknown model for cost calculation" in caplog.text

    def test_load_override_from_env(self):
        override = {
            "custom/provider": {"prompt": 0.01, "completion": 0.02},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(override, f)
            path = f.name

        old_env = os.environ.get("LLM_COST_TABLE_PATH")
        os.environ["LLM_COST_TABLE_PATH"] = path
        try:
            calc = LLMCostCalculator()
            cost = calc.calculate_cost(
                provider="custom",
                model="provider",
                prompt_tokens=1000,
                completion_tokens=1000,
            )
            expected = 0.01 + 0.02
            assert cost == pytest.approx(expected, rel=1e-6)
        finally:
            if old_env is None:
                os.environ.pop("LLM_COST_TABLE_PATH", None)
            else:
                os.environ["LLM_COST_TABLE_PATH"] = old_env
            os.unlink(path)


class TestLLMMetricEmission:
    @pytest.fixture
    def metrics(self):
        registry = CollectorRegistry()
        config = MetricsConfig(enabled=True, registry=registry, prefix="layer4_")
        return PrometheusMetrics(config)

    def test_record_llm_cost_increments_all_counters(self, metrics):
        tenant_id = str(uuid4())
        # Metrics use tenant_tier (a cardinality-limited hash bucket) not tenant_id
        expected_tier = _expected_tenant_tier(tenant_id)
        metrics.record_llm_cost(
            provider="openai",
            model="gpt-4o",
            tenant_id=tenant_id,
            cost=0.025,
            prompt_tokens=1000,
            completion_tokens=500,
            status="success",
        )

        cost_samples = list(
            metrics.config.registry.collect()
        )
        # Find vf_llm_cost_usd_total sample – labels use tenant_tier, not tenant_id
        cost_value = None
        prompt_value = None
        completion_value = None
        request_value = None

        for metric in cost_samples:
            for sample in metric.samples:
                if sample.name == "vf_llm_cost_usd_total":
                    if sample.labels.get("tenant_tier") == expected_tier:
                        cost_value = sample.value
                if sample.name == "vf_llm_tokens_total":
                    if sample.labels.get("tenant_tier") == expected_tier:
                        if sample.labels.get("token_type") == "prompt":
                            prompt_value = sample.value
                        elif sample.labels.get("token_type") == "completion":
                            completion_value = sample.value
                if sample.name == "vf_llm_requests_total":
                    if sample.labels.get("tenant_tier") == expected_tier:
                        request_value = sample.value

        assert cost_value == pytest.approx(0.025)
        assert prompt_value == 1000
        assert completion_value == 500
        assert request_value == 1

    def test_record_llm_cost_failure_status(self, metrics):
        tenant_id = str(uuid4())
        expected_tier = _expected_tenant_tier(tenant_id)
        metrics.record_llm_cost(
            provider="anthropic",
            model="claude-3-opus",
            tenant_id=tenant_id,
            cost=0.0,
            prompt_tokens=0,
            completion_tokens=0,
            status="failure",
        )

        request_value = None
        for metric in metrics.config.registry.collect():
            for sample in metric.samples:
                if sample.name == "vf_llm_requests_total":
                    if (
                        sample.labels.get("tenant_tier") == expected_tier
                        and sample.labels.get("status") == "failure"
                    ):
                        request_value = sample.value

        assert request_value == 1

    def test_disabled_metrics_noop(self):
        registry = CollectorRegistry()
        config = MetricsConfig(enabled=False, registry=registry, prefix="layer4_")
        metrics = PrometheusMetrics(config)

        # Should not raise
        metrics.record_llm_cost(
            provider="openai",
            model="gpt-4o",
            tenant_id=str(uuid4()),
            cost=0.1,
            prompt_tokens=100,
            completion_tokens=50,
            status="success",
        )

        # No samples should exist for vf_ metrics
        for metric in registry.collect():
            for sample in metric.samples:
                assert not sample.name.startswith("vf_llm_")
