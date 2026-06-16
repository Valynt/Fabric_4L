"""Verify the compare endpoint returns snake_case percentile buckets."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.identity.context import RequestContext

import layer6_benchmarks.api.main as main_module
from layer6_benchmarks.api.deps import get_request_context
from layer6_benchmarks.api.main import app
from layer6_benchmarks.seed.load_benchmark_packs import (
    default_benchmark_packs_dir,
    load_benchmark_pack,
)


@pytest.fixture(autouse=True)
def setup_pack_repo(monkeypatch):
    """Seed the mock repository with the real SaaS SE Efficiency 2025 pack."""
    dataset = load_benchmark_pack(
        default_benchmark_packs_dir() / "saas-se-efficiency-2025.json"
    )

    mock_repo = AsyncMock()
    mock_repo.list_datasets.return_value = [dataset]

    async def get_dataset(dataset_id, tenant_id="system"):
        if dataset_id == dataset.dataset_id:
            return dataset
        return None

    mock_repo.get_dataset = AsyncMock(side_effect=get_dataset)
    monkeypatch.setattr(main_module, "authorize_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module, "_neo4j_startup_error", None)
    monkeypatch.setattr(main_module, "_benchmark_repo", mock_repo)
    yield mock_repo


@pytest.fixture
async def client():
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        tenant_id="tenant-a",
        roles=["tenant_admin"],
        tenant_role="tenant_admin",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("company_value", "expected_percentile", "expected_bucket"),
    [
        ("1.0", 5, "needs_improvement"),
        ("2.5", 37, "below_average"),
        ("4.5", 62, "above_average"),
        ("7.0", 82, "top_performer"),
    ],
)
async def test_compare_returns_snake_case_percentile_bucket(
    client: AsyncClient,
    company_value: str,
    expected_percentile: int,
    expected_bucket: str,
) -> None:
    response = await client.post(
        "/v1/benchmarks/compare",
        json={
            "dataset_id": "saas-se-efficiency-2025",
            "metric": "se_hours_per_opportunity",
            "company_value": company_value,
            "industry": "software",
            "segment": "mid-market",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["percentile"] == expected_percentile
    assert body["assessment"] == expected_bucket
    assert body["sample_size"] == 920
    assert body["confidence"] == "medium"


@pytest.mark.asyncio
async def test_compare_returns_above_average_for_nexus_scenario(client: AsyncClient) -> None:
    """The Nexus Analytics scenario uses 4.5 SE hours per opportunity."""
    response = await client.post(
        "/v1/benchmarks/compare",
        json={
            "dataset_id": "saas-se-efficiency-2025",
            "metric": "se_hours_per_opportunity",
            "company_value": "4.5",
            "industry": "software",
            "segment": "mid-market",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assessment"] == "above_average"
    assert body["percentile"] == 62
