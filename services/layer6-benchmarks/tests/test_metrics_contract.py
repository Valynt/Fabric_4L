import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import layer6_benchmarks.api.main as main_module
from httpx import ASGITransport, AsyncClient
from prometheus_client import CollectorRegistry
from layer6_benchmarks.api.main import app
from layer6_benchmarks.metrics.prometheus_metrics import (
    MetricsConfig,
    MetricsMiddleware,
    PrometheusMetrics,
)
from layer6_benchmarks.models.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from layer6_benchmarks.observability.metrics_contract import metric_names

CONTRACT = Path(__file__).resolve().parents[3] / "contracts" / "observability" / "layer6-metrics.json"


def _contract_metrics() -> dict[str, dict]:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    return {metric["name"]: metric for metric in payload["metrics"]}


def _sample_dataset() -> BenchmarkDataset:
    dataset = BenchmarkDataset(
        dataset_id="manufacturing-efficiency-2024",
        tenant_id="system",
        name="Manufacturing Efficiency",
        description="desc",
        industry="manufacturing",
        segment="default",
        geography="global",
        version="1.0.0",
        data_source="source",
    )
    dataset.add_metric(
        BenchmarkMetric(
            name="oee_overall_equipment_effectiveness",
            unit="percent",
            description="oee",
            profile=StatisticalProfile(
                p10=Decimal("60"),
                p25=Decimal("70"),
                p50=Decimal("80"),
                p75=Decimal("90"),
                p90=Decimal("95"),
                mean=Decimal("80"),
                std_dev=Decimal("5"),
                sample_size=1000,
            ),
        )
    )
    return dataset


@pytest.fixture
def isolated_metrics(monkeypatch) -> PrometheusMetrics:
    metrics = PrometheusMetrics(MetricsConfig(registry=CollectorRegistry()))
    monkeypatch.setattr(main_module, "authorize_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module.app.state, "metrics", metrics, raising=False)
    metrics_module = __import__("layer6_benchmarks.metrics.prometheus_metrics", fromlist=["_metrics"])
    monkeypatch.setattr(metrics_module, "_metrics", metrics)
    return metrics


@pytest.fixture
def benchmark_repo(monkeypatch):
    repo = AsyncMock()
    dataset = _sample_dataset()
    repo.list_datasets.return_value = [dataset]
    repo.get_dataset = AsyncMock(return_value=dataset)
    monkeypatch.setattr(main_module, "_benchmark_repo", repo)
    return repo


@pytest.mark.asyncio
async def test_required_metrics_are_emitted_with_expected_labels(
    isolated_metrics: PrometheusMetrics,
    benchmark_repo,
):
    isolated_metrics.increment_requests_total(
        method="POST",
        route="/v1/benchmarks/compare",
        status_code=200,
    )
    isolated_metrics.observe_request_duration(
        duration=0.25,
        method="POST",
        route="/v1/benchmarks/compare",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/benchmarks/compare",
            json={
                "dataset_id": "manufacturing-efficiency-2024",
                "metric": "oee_overall_equipment_effectiveness",
                "company_value": "72.5",
                "industry": "manufacturing",
            },
        )

    assert response.status_code == 200
    exposition = isolated_metrics.get_metrics()
    assert 'layer6_requests_total{' in exposition
    assert 'route="/v1/benchmarks/compare"' in exposition
    assert 'method="POST"' in exposition
    assert 'status_class="2xx"' in exposition
    assert 'layer6_dataset_comparisons_total{industry="manufacturing",outcome="success"} 1.0' in exposition
    assert 'layer6_health_status{service="layer6-benchmarks"} 1.0' in exposition
    assert "layer6_request_duration_seconds_bucket" in exposition


def test_metric_label_cardinality_constraints_are_bounded() -> None:
    for metric in _contract_metrics().values():
        for label in metric["labels"]:
            assert label in metric["max_cardinality"]
            assert 0 < metric["max_cardinality"][label] <= 100


def test_metric_contract_names_match_runtime_metric_families() -> None:
    assert metric_names() == set(_contract_metrics())


def test_metrics_middleware_normalizes_high_entropy_paths() -> None:
    metrics = PrometheusMetrics(MetricsConfig(registry=CollectorRegistry()))
    middleware = MetricsMiddleware(metrics)
    normalized = middleware._normalize_path(
        "/v1/benchmarks/datasets/550e8400-e29b-41d4-a716-446655440000"
    )
    assert normalized == "/v1/benchmarks/datasets/{id}"


def test_compare_outcomes_fit_contract_cardinality() -> None:
    outcomes = {"success", "dataset_not_found", "metric_not_found", "invalid_input"}
    contract = _contract_metrics()["layer6_dataset_comparisons_total"]
    assert len(outcomes) <= contract["max_cardinality"]["outcome"]
