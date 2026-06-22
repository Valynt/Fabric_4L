"""Hostile tenant isolation and context propagation tests.

Validates that Layer 6 handlers correctly extract tenant_id from the RequestContext
and propagate it strictly down to the BenchmarkRepository.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from layer6_benchmarks.api.deps import get_request_context
from layer6_benchmarks.api.main import app
from layer6_benchmarks.models.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from value_fabric.shared.identity.context import RequestContext


def tenant_context(tenant_id: str) -> RequestContext:
    return RequestContext(
        tenant_id=tenant_id,
        user_id="00000000-0000-0000-0000-000000000000",
        org_id="00000000-0000-0000-0000-000000000000",
        roles=["admin"],
        permissions=[],
        auth_source="mock",
        tenant_role="admin",
        isolation_tier="shared",
        request_id="test",
    )


def benchmark_dataset(dataset_id: str, tenant_id: str) -> BenchmarkDataset:
    dataset = BenchmarkDataset(
        dataset_id=dataset_id,
        tenant_id=tenant_id,
        name="Tenant Dataset",
        industry="Tech",
        segment="Enterprise",
        description="Tenant-scoped benchmark data",
        geography="Global",
    )
    dataset.add_metric(
        BenchmarkMetric(
            name="revenue",
            unit="usd",
            description="Revenue",
            profile=StatisticalProfile(
                p10=Decimal("10"),
                p25=Decimal("25"),
                p50=Decimal("50"),
                p75=Decimal("75"),
                p90=Decimal("90"),
                mean=Decimal("52"),
                std_dev=Decimal("15"),
                sample_size=100,
            ),
        )
    )
    return dataset


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_repo_hostile(monkeypatch):
    """Create a pristine mock repo for asserting call arguments."""
    monkeypatch.setattr("layer6_benchmarks.api.main.authorize_action", lambda *args, **kwargs: None)
    with patch("layer6_benchmarks.api.main._benchmark_repo") as repo:
        repo.list_datasets = AsyncMock(return_value=[])
        repo.get_dataset = AsyncMock(return_value=None)
        yield repo


@pytest.fixture
async def isolated_client():
    """Client that allows injecting specific tenant contexts."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_list_datasets_propagates_tenant(
    isolated_client: AsyncClient, mock_repo_hostile: AsyncMock
):
    """Verify list_datasets enforces the context tenant_id down to the repository."""
    hostile_tenant = "hostile-tenant-xyz"

    # Override the context dependency for this specific test
    app.dependency_overrides[get_request_context] = lambda: tenant_context(hostile_tenant)

    response = await isolated_client.get("/v1/benchmarks/datasets")
    assert response.status_code == 200

    # Crucial assertion: Did the handler pass the EXACT tenant_id to the DB layer?
    mock_repo_hostile.list_datasets.assert_called_once()
    _, kwargs = mock_repo_hostile.list_datasets.call_args
    assert kwargs.get("tenant_id") == hostile_tenant


@pytest.mark.asyncio
async def test_get_dataset_propagates_tenant(
    isolated_client: AsyncClient, mock_repo_hostile: AsyncMock
):
    """Verify get_dataset enforces the context tenant_id down to the repository."""
    hostile_tenant = "hostile-tenant-abc"

    app.dependency_overrides[get_request_context] = lambda: tenant_context(hostile_tenant)

    response = await isolated_client.get("/v1/benchmarks/datasets/some-dataset-id")
    assert response.status_code == 404  # Since mock returns None, it raises 404

    mock_repo_hostile.get_dataset.assert_called_once()
    _, kwargs = mock_repo_hostile.get_dataset.call_args
    assert kwargs.get("tenant_id") == hostile_tenant


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_payload"),
    [
        ("GET", "/v1/benchmarks/datasets", None),
        ("GET", "/v1/benchmarks/datasets/some-dataset-id", None),
        (
            "POST",
            "/v1/benchmarks/compare",
            {
                "dataset_id": "some-dataset-id",
                "metric": "revenue",
                "company_value": "100",
                "industry": "Tech",
            },
        ),
        (
            "POST",
            "/v1/benchmarks/validate",
            {
                "dataset_id": "some-dataset-id",
                "metric": "revenue",
                "value": "100",
                "tolerance_percent": 10,
            },
        ),
        ("GET", "/v1/benchmarks/industries", None),
    ],
)
async def test_benchmark_endpoints_fail_closed_without_tenant_context(
    isolated_client: AsyncClient,
    mock_repo_hostile: AsyncMock,
    method: str,
    path: str,
    json_payload: dict | None,
):
    """Missing tenant context must fail before any repository fallback is used."""
    app.dependency_overrides[get_request_context] = lambda: None

    response = await isolated_client.request(method, path, json=json_payload)

    assert response.status_code == 401
    assert "Tenant context required" in response.text
    mock_repo_hostile.list_datasets.assert_not_called()
    mock_repo_hostile.get_dataset.assert_not_called()


@pytest.mark.asyncio
async def test_compare_and_validate_propagate_tenant(
    isolated_client: AsyncClient, mock_repo_hostile: AsyncMock
):
    """Verify write-like benchmark operations fetch datasets with the trusted tenant."""
    tenant_id = "tenant-for-analysis"
    mock_repo_hostile.get_dataset.return_value = benchmark_dataset("tenant-dataset", tenant_id)
    app.dependency_overrides[get_request_context] = lambda: tenant_context(tenant_id)

    compare_response = await isolated_client.post(
        "/v1/benchmarks/compare",
        json={
            "dataset_id": "tenant-dataset",
            "metric": "revenue",
            "company_value": "100",
            "industry": "Tech",
        },
    )
    validate_response = await isolated_client.post(
        "/v1/benchmarks/validate",
        json={
            "dataset_id": "tenant-dataset",
            "metric": "revenue",
            "value": "100",
            "tolerance_percent": 10,
        },
    )

    assert compare_response.status_code == 200
    assert validate_response.status_code == 200
    assert mock_repo_hostile.get_dataset.call_args_list[0].kwargs["tenant_id"] == tenant_id
    assert mock_repo_hostile.get_dataset.call_args_list[1].kwargs["tenant_id"] == tenant_id


@pytest.mark.asyncio
async def test_list_industries_propagates_tenant(
    isolated_client: AsyncClient, mock_repo_hostile: AsyncMock
):
    """Verify industries are derived only from tenant-scoped datasets."""
    tenant_id = "tenant-industries"
    mock_repo_hostile.list_datasets.return_value = [benchmark_dataset("tenant-dataset", tenant_id)]
    app.dependency_overrides[get_request_context] = lambda: tenant_context(tenant_id)

    response = await isolated_client.get("/v1/benchmarks/industries")

    assert response.status_code == 200
    mock_repo_hostile.list_datasets.assert_called_once()
    assert mock_repo_hostile.list_datasets.call_args.kwargs["tenant_id"] == tenant_id


@pytest.mark.asyncio
async def test_hostile_cross_tenant_access_blocked(isolated_client: AsyncClient, monkeypatch):
    """Verify a hostile tenant cannot access another tenant's benchmark data via the API."""
    import layer6_benchmarks.api.main as main_module

    monkeypatch.setattr(main_module, "authorize_action", lambda *args, **kwargs: None)

    # Create a mock repo that simulates returning data ONLY for a specific tenant
    mock_repo = AsyncMock()

    target_dataset = BenchmarkDataset(
        dataset_id="secret-dataset-1",
        tenant_id="victim-tenant",
        name="Victim Data",
        industry="Tech",
        segment="Enterprise",
        description="Confidential data",
        geography="Global",
    )

    async def simulated_get_dataset(dataset_id, tenant_id):
        if dataset_id == "secret-dataset-1" and tenant_id == "victim-tenant":
            return target_dataset
        return None

    mock_repo.get_dataset = AsyncMock(side_effect=simulated_get_dataset)
    monkeypatch.setattr(main_module, "_benchmark_repo", mock_repo)

    # Simulate a request from a hostile tenant
    app.dependency_overrides[get_request_context] = lambda: tenant_context(
        "hostile-attacker-tenant"
    )

    # The attacker tries to get the victim's dataset
    response = await isolated_client.get("/v1/benchmarks/datasets/secret-dataset-1")

    # Because the repo mock honors the tenant_id check (returning None if mismatch), the API should return 404
    assert response.status_code == 404

    # Try the compare endpoint
    compare_payload = {
        "dataset_id": "secret-dataset-1",
        "metric": "revenue",
        "company_value": "100",
        "industry": "Tech",
    }
    response_compare = await isolated_client.post("/v1/benchmarks/compare", json=compare_payload)
    assert response_compare.status_code == 404

    # Try the validate endpoint
    validate_payload = {
        "dataset_id": "secret-dataset-1",
        "metric": "revenue",
        "value": "100",
        "tolerance_percent": 10,
    }
    response_validate = await isolated_client.post("/v1/benchmarks/validate", json=validate_payload)
    assert response_validate.status_code == 404
