from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import layer6_benchmarks.api.main as main_module
from httpx import ASGITransport, AsyncClient
from layer6_benchmarks.api.main import app
from layer6_benchmarks.models.benchmark_dataset import BenchmarkDataset, BenchmarkMetric, StatisticalProfile
from value_fabric.shared.identity.context import RequestContext, get_request_context


@pytest.fixture(autouse=True)
def setup_repo_and_auth(monkeypatch):
    mock_repo = AsyncMock()

    def allow_auth(*args, **kwargs):
        return None

    monkeypatch.setattr(main_module, "authorize_action", allow_auth)
    monkeypatch.setattr(main_module, "_neo4j_startup_error", None)

    def make_dataset(dataset_id: str, tenant_id: str, sample_size: int = 20) -> BenchmarkDataset:
        ds = BenchmarkDataset(
            dataset_id=dataset_id,
            tenant_id=tenant_id,
            name="Ops Benchmark",
            description="benchmark with lineage",
            industry="manufacturing",
            segment="smb",
            geography="global",
            version="2026.04",
            data_source="industry-council-v7",
        )
        ds.add_metric(
            BenchmarkMetric(
                name="throughput",
                unit="units/hour",
                description="line speed",
                profile=StatisticalProfile(
                    p10=Decimal("10"),
                    p25=Decimal("15"),
                    p50=Decimal("20"),
                    p75=Decimal("25"),
                    p90=Decimal("30"),
                    mean=Decimal("20"),
                    std_dev=Decimal("2"),
                    sample_size=sample_size,
                ),
            )
        )
        return ds

    system_ds = make_dataset("global-throughput", "system", sample_size=8)
    tenant_ds = make_dataset("tenant-a-throughput", "tenant-a", sample_size=4)

    async def list_datasets(*, industry=None, segment=None, tenant_id="system"):
        datasets = [system_ds] if tenant_id == "system" else [tenant_ds]
        if industry:
            datasets = [d for d in datasets if d.industry == industry]
        if segment:
            datasets = [d for d in datasets if d.segment == segment]
        return datasets

    async def get_dataset(dataset_id: str, tenant_id="system"):
        if tenant_id == "tenant-a" and dataset_id == tenant_ds.dataset_id:
            return tenant_ds
        if tenant_id == "system" and dataset_id == system_ds.dataset_id:
            return system_ds
        return None

    mock_repo.list_datasets = AsyncMock(side_effect=list_datasets)
    mock_repo.get_dataset = AsyncMock(side_effect=get_dataset)
    mock_repo.save_dataset = AsyncMock()

    monkeypatch.setattr(main_module, "_benchmark_repo", mock_repo)
    yield mock_repo


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_route_matrix_happy_and_hostile_paths(client: AsyncClient):
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        tenant_id="tenant-a",
        roles=["tenant_admin"],
        tenant_role="tenant_admin",
    )

    happy_cases = [
        ("GET", "/v1/benchmarks/datasets", None, 200),
        ("GET", "/v1/benchmarks/datasets/tenant-a-throughput", None, 200),
        (
            "POST",
            "/v1/benchmarks/compare",
            {"dataset_id": "tenant-a-throughput", "metric": "throughput", "company_value": "22", "industry": "manufacturing"},
            200,
        ),
        (
            "POST",
            "/v1/benchmarks/validate",
            {"dataset_id": "tenant-a-throughput", "metric": "throughput", "value": "22", "tolerance_percent": 10},
            200,
        ),
        ("GET", "/v1/benchmarks/industries", None, 200),
        (
            "POST",
            "/v1/benchmarks/datasets",
            {
                "dataset_id": "tenant-a-new",
                "name": "Tenant A Dataset",
                "description": "desc",
                "industry": "manufacturing",
                "metrics": {"throughput": {"unit": "units/hour", "description": "line speed", "profile": {"p10": "10", "p25": "15", "p50": "20", "p75": "25", "p90": "30", "mean": "20", "std_dev": "2", "sample_size": 40}}},
                "ownership_mode": "tenant",
            },
            200,
        ),
        (
            "PUT",
            "/v1/benchmarks/datasets/tenant-a-throughput",
            {
                "dataset_id": "ignored-by-route",
                "name": "Tenant A Dataset Updated",
                "description": "desc",
                "industry": "manufacturing",
                "metrics": {"throughput": {"unit": "units/hour", "description": "line speed", "profile": {"p10": "10", "p25": "15", "p50": "20", "p75": "25", "p90": "30", "mean": "20", "std_dev": "2", "sample_size": 40}}},
                "ownership_mode": "tenant",
            },
            200,
        ),
    ]

    for method, path, payload, expected_status in happy_cases:
        response = await client.request(method, path, json=payload)
        assert response.status_code == expected_status

    hostile_cases = [
        ("GET", "/v1/benchmarks/datasets/global-throughput", None, 404),
        (
            "POST",
            "/v1/benchmarks/compare",
            {"dataset_id": "global-throughput", "metric": "throughput", "company_value": "22", "industry": "manufacturing"},
            404,
        ),
        ("POST", "/v1/benchmarks/compare", {"dataset_id": "tenant-a-throughput", "metric": "throughput", "industry": "manufacturing"}, 422),
        (
            "POST",
            "/v1/benchmarks/validate",
            {"dataset_id": "tenant-a-throughput", "metric": "throughput", "value": "bad", "tolerance_percent": 10},
            400,
        ),
    ]
    for method, path, payload, expected_status in hostile_cases:
        response = await client.request(method, path, json=payload)
        assert response.status_code == expected_status

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dataset_lineage_preserved_through_list_get_compare_validate(client: AsyncClient):
    app.dependency_overrides[get_request_context] = lambda: RequestContext(tenant_id="tenant-a", roles=["tenant_admin"], tenant_role="tenant_admin")

    list_resp = await client.get("/v1/benchmarks/datasets")
    item = list_resp.json()[0]
    assert item["version"] == "2026.04"
    assert item["data_source"] == "industry-council-v7"

    detail_resp = await client.get("/v1/benchmarks/datasets/tenant-a-throughput")
    detail = detail_resp.json()
    assert detail["version"] == "2026.04"
    assert detail["data_source"] == "industry-council-v7"

    compare_resp = await client.post(
        "/v1/benchmarks/compare",
        json={"dataset_id": "tenant-a-throughput", "metric": "throughput", "company_value": "28", "industry": "manufacturing"},
    )
    assert compare_resp.status_code == 200
    assert compare_resp.json()["sample_size"] == 4

    validate_resp = await client.post(
        "/v1/benchmarks/validate",
        json={"dataset_id": "tenant-a-throughput", "metric": "throughput", "value": "28", "tolerance_percent": 10},
    )
    assert validate_resp.status_code == 200
    assert validate_resp.json()["actual_value"] == "28"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_statistical_edge_cases_small_sample_and_percentile_boundaries(client: AsyncClient):
    app.dependency_overrides[get_request_context] = lambda: RequestContext(tenant_id="tenant-a", roles=["tenant_admin"], tenant_role="tenant_admin")

    # Boundary at p10 should remain in first band and low confidence for small sample.
    resp = await client.post(
        "/v1/benchmarks/compare",
        json={"dataset_id": "tenant-a-throughput", "metric": "throughput", "company_value": "10", "industry": "manufacturing"},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["percentile"] == 5
    assert body["confidence"] == "low"

    # Outlier and malformed/null handling.
    outlier = await client.post(
        "/v1/benchmarks/validate",
        json={"dataset_id": "tenant-a-throughput", "metric": "throughput", "value": "1000", "tolerance_percent": 10},
    )
    assert outlier.status_code == 200
    assert outlier.json()["severity"] == "error"

    null_value = await client.post(
        "/v1/benchmarks/validate",
        json={"dataset_id": "tenant-a-throughput", "metric": "throughput", "value": None, "tolerance_percent": 10},
    )
    assert null_value.status_code == 422

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_authorization_negative_path_returns_403(client: AsyncClient, monkeypatch):
    def deny(*args, **kwargs):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="forbidden")

    monkeypatch.setattr(main_module, "authorize_action", deny)
    app.dependency_overrides[get_request_context] = lambda: RequestContext(tenant_id="tenant-a", roles=["viewer"], tenant_role="viewer")
    response = await client.get("/v1/benchmarks/datasets")
    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_openapi_contract_shape_regression_for_benchmark_responses():
    contract_path = Path(__file__).parent.parent.parent.parent / "contracts" / "openapi" / "layer6-benchmarks.json"
    contract = json.loads(contract_path.read_text())

    compare_schema = contract["components"]["schemas"]["ComparisonResponse"]
    validate_schema = contract["components"]["schemas"]["ValidationResponse"]
    dataset_summary_schema = contract["components"]["schemas"]["DatasetSummary"]

    assert set(compare_schema["required"]) >= {"percentile", "peer_median", "peer_range", "sample_size", "confidence", "assessment"}
    assert set(validate_schema["required"]) >= {"is_valid", "expected_range", "actual_value", "deviation_percent", "severity", "message"}
    assert set(dataset_summary_schema["required"]) >= {"dataset_id", "version", "data_source", "metrics", "metric_count"}
