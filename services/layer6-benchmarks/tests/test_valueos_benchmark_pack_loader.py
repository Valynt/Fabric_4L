"""Tests for the governed ValueOS benchmark pack loader."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from layer6_benchmarks.seed.load_benchmark_packs import (
    BenchmarkPackValidationError,
    load_default_benchmark_packs,
    validate_valueos_pack,
    valueos_metrics_to_datasets,
)
from layer6_benchmarks.seed.valueos_default_pack import (
    VALUEOS_BASELINE_METRIC_TARGET,
    VALUEOS_REQUIRED_INDUSTRIES,
    build_valueos_default_metric_payloads,
    build_valueos_default_metrics,
)


def test_valueos_default_pack_contains_100_valid_distribution_first_metrics() -> None:
    metrics = build_valueos_default_metrics()

    assert len(metrics) == VALUEOS_BASELINE_METRIC_TARGET
    assert {metric.segmentation.industry for metric in metrics} == set(VALUEOS_REQUIRED_INDUSTRIES)
    assert all(metric.provenance for metric in metrics)
    assert all(
        metric.distribution.p10
        <= metric.distribution.p25
        <= metric.distribution.p50
        <= metric.distribution.p75
        <= metric.distribution.p90
        for metric in metrics
    )


def test_valueos_default_pack_rejects_missing_provenance() -> None:
    payloads = build_valueos_default_metric_payloads()
    payloads[0]["provenance"] = []

    with pytest.raises(ValidationError):
        [type(build_valueos_default_metrics()[0]).model_validate(payload) for payload in payloads]


def test_valueos_pack_validation_rejects_missing_required_industry() -> None:
    metrics = [
        metric
        for metric in build_valueos_default_metrics()
        if metric.segmentation.industry != "retail"
    ]

    with pytest.raises(BenchmarkPackValidationError, match="at least 100 metrics"):
        validate_valueos_pack(metrics)


def test_valueos_metrics_flatten_to_global_system_datasets() -> None:
    datasets = valueos_metrics_to_datasets(build_valueos_default_metrics())

    assert len(datasets) == len(VALUEOS_REQUIRED_INDUSTRIES)
    assert sum(len(dataset.metrics) for dataset in datasets) == VALUEOS_BASELINE_METRIC_TARGET
    assert {dataset.ownership_mode for dataset in datasets} == {"global_system"}
    assert {dataset.tenant_id for dataset in datasets} == {"system"}
    first_metric = next(iter(datasets[0].metrics.values()))
    assert first_metric.source_name
    assert first_metric.source_count == 1
    assert first_metric.confidence_score is not None
    assert first_metric.license_class == "internal"
    assert first_metric.vintage == "2026Q2"
    assert first_metric.distribution_shape in {"normal", "skewed_right"}


@pytest.mark.asyncio
async def test_load_default_benchmark_packs_persists_valueos_datasets() -> None:
    repo = AsyncMock()

    await load_default_benchmark_packs(repo)

    assert repo.save_dataset.await_count == len(VALUEOS_REQUIRED_INDUSTRIES)
    saved_datasets = [call.args[0] for call in repo.save_dataset.await_args_list]
    assert sum(len(dataset.metrics) for dataset in saved_datasets) == VALUEOS_BASELINE_METRIC_TARGET
    assert all(dataset.dataset_id.startswith("valueos-") for dataset in saved_datasets)
