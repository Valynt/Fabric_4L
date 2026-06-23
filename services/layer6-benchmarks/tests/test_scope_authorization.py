from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import layer6_benchmarks.api.main as main_module
import pytest
from fastapi import HTTPException
from layer6_benchmarks.api.schemas import ComparisonRequestPayload
from layer6_benchmarks.models.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.permissions import Permission


@pytest.fixture
def benchmark_repo(monkeypatch):
    repo = AsyncMock()
    dataset = BenchmarkDataset(
        dataset_id="manufacturing-efficiency-2024",
        tenant_id="tenant-a",
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
    repo.get_dataset.return_value = dataset
    monkeypatch.setattr(main_module, "_benchmark_repo", repo)
    return repo


@pytest.mark.asyncio
async def test_compare_rejected_without_scope(benchmark_repo) -> None:
    payload = ComparisonRequestPayload(
        dataset_id="manufacturing-efficiency-2024",
        metric="oee_overall_equipment_effectiveness",
        company_value="72.5",
        industry="manufacturing",
    )
    context = RequestContext(
        tenant_id="tenant-a",
        user_id="viewer",
        roles=["read_only"],
        permissions=frozenset({Permission.READ_SEARCH}),
        auth_source="jwt_claim",
    )

    with pytest.raises(HTTPException) as exc_info:
        await main_module.compare(payload, ctx=context)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "INSUFFICIENT_SCOPE"


@pytest.mark.asyncio
async def test_compare_allowed_with_scope(benchmark_repo) -> None:
    payload = ComparisonRequestPayload(
        dataset_id="manufacturing-efficiency-2024",
        metric="oee_overall_equipment_effectiveness",
        company_value="72.5",
        industry="manufacturing",
    )
    context = RequestContext(
        tenant_id="tenant-a",
        user_id="analyst",
        roles=["analyst"],
        permissions=frozenset({Permission.READ_ANALYTICS}),
        auth_source="jwt_claim",
    )

    response = await main_module.compare(payload, ctx=context)

    assert response.percentile > 0
