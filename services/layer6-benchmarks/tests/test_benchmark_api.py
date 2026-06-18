"""Tests for Layer 6 Benchmark Service API."""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import layer6_benchmarks.api.main as main_module
from httpx import ASGITransport, AsyncClient
from layer6_benchmarks.api.main import app
from layer6_benchmarks.api.deps import get_request_context
from value_fabric.shared.identity.context import RequestContext
from layer6_benchmarks.models.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)


@pytest.fixture(autouse=True)
def setup_mock_repo(monkeypatch):
    """Set up a deterministic benchmark repository for API tests."""
    mock_repo = AsyncMock()
    monkeypatch.setattr(main_module, "authorize_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module, "_neo4j_startup_error", None)

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
    dataset.add_metric(
        BenchmarkMetric(
            name="defect_rate_percent",
            unit="percent",
            description="defect",
            profile=StatisticalProfile(
                p10=Decimal("1"),
                p25=Decimal("2"),
                p50=Decimal("3"),
                p75=Decimal("4"),
                p90=Decimal("5"),
                mean=Decimal("3"),
                std_dev=Decimal("1"),
                sample_size=1000,
            ),
        )
    )

    mock_repo.list_datasets.return_value = [dataset]

    async def get_dataset(dataset_id, tenant_id="system"):
        if dataset_id == "manufacturing-efficiency-2024":
            return dataset
        return None

    mock_repo.get_dataset = AsyncMock(side_effect=get_dataset)
    monkeypatch.setattr(main_module, "_benchmark_repo", mock_repo)
    yield mock_repo


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "layer6-benchmarks"
    assert "checks" not in data


@pytest.mark.asyncio
async def test_ready_check(client: AsyncClient):
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "layer6-benchmarks"
    assert data["checks"]["config"]["status"] == "ok"
    assert data["checks"]["neo4j"]["status"] == "ok"
    assert data["checks"]["benchmark_store"]["status"] == "ok"
    assert data["checks"]["startup"]["status"] == "ok"


@pytest.mark.asyncio
async def test_list_datasets(client: AsyncClient):
    response = await client.get("/v1/benchmarks/datasets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["dataset_id"] == "manufacturing-efficiency-2024"
    assert data[0]["industry"] == "manufacturing"


@pytest.mark.asyncio
async def test_list_datasets_passes_tenant_id(client: AsyncClient, setup_mock_repo: AsyncMock):
    response = await client.get("/v1/benchmarks/datasets")
    assert response.status_code == 200
    _, kwargs = setup_mock_repo.list_datasets.call_args
    assert kwargs["tenant_id"] == "system"


@pytest.mark.asyncio
async def test_get_dataset(client: AsyncClient):
    response = await client.get("/v1/benchmarks/datasets/manufacturing-efficiency-2024")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "manufacturing-efficiency-2024"
    assert "metrics" in data
    assert "oee_overall_equipment_effectiveness" in data["metrics"]


@pytest.mark.asyncio
async def test_get_dataset_not_found(client: AsyncClient):
    response = await client.get("/v1/benchmarks/datasets/non-existent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_compare(client: AsyncClient):
    payload = {
        "dataset_id": "manufacturing-efficiency-2024",
        "metric": "oee_overall_equipment_effectiveness",
        "company_value": "72.5",
        "industry": "manufacturing",
    }
    response = await client.post("/v1/benchmarks/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "percentile" in data
    assert "peer_median" in data
    assert "confidence" in data
    assert "assessment" in data


@pytest.mark.asyncio
async def test_validate(client: AsyncClient):
    payload = {
        "dataset_id": "manufacturing-efficiency-2024",
        "metric": "defect_rate_percent",
        "value": "2.0",
        "tolerance_percent": 10,
    }
    response = await client.post("/v1/benchmarks/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_valid" in data
    assert "expected_range" in data
    assert "severity" in data


@pytest.mark.asyncio
async def test_list_industries(client: AsyncClient):
    response = await client.get("/v1/benchmarks/industries")
    assert response.status_code == 200
    data = response.json()
    assert "industries" in data
    assert "manufacturing" in data["industries"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("GET", "/v1/benchmarks/datasets", None),
        ("GET", "/v1/benchmarks/datasets/manufacturing-efficiency-2024", None),
        (
            "POST",
            "/v1/benchmarks/compare",
            {
                "dataset_id": "manufacturing-efficiency-2024",
                "metric": "oee_overall_equipment_effectiveness",
                "company_value": "72.5",
                "industry": "manufacturing",
            },
        ),
    ],
)
async def test_returns_503_when_repo_is_unavailable(
    client: AsyncClient, monkeypatch, method: str, path: str, payload: dict | None
):
    monkeypatch.setattr(main_module, "_benchmark_repo", None)
    response = await client.request(method, path, json=payload)
    assert response.status_code == 503
    assert "Benchmark store not initialized" in str(response.json())


@pytest.mark.asyncio
async def test_ready_returns_503_when_dependency_health_check_fails(client: AsyncClient, monkeypatch):
    async def failing_health(*args, **kwargs):
        return {"status": "unhealthy", "error": "neo4j down"}

    monkeypatch.setattr(main_module, "neo4j_health_check", failing_health)
    response = await client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "layer6-benchmarks",
        "liveness": "alive",
        "readiness": {"is_ready": False, "reason": "dependency_unhealthy"},
        "dependencies": [],
        "dependency_status": [],
        "timestamp": response.json()["timestamp"],
        "version": "1.0.0",
        "checks": {
            "config": {"status": "ok"},
            "neo4j": {"status": "failed", "detail": "neo4j down"},
            "benchmark_store": {"status": "ok", "detail": None, "datasets_loaded": 1},
            "startup": {"status": "ok", "detail": None},
        },
    }


@pytest.mark.asyncio
async def test_health_remains_liveness_only_when_dependency_degraded(client: AsyncClient, monkeypatch):
    async def failing_health(*args, **kwargs):
        return {"status": "unhealthy", "error": "neo4j down"}

    monkeypatch.setattr(main_module, "neo4j_health_check", failing_health)
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_tenant_user_cannot_create_global_benchmark(client: AsyncClient):
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        tenant_id="tenant-a",
        roles=["tenant_admin"],
        tenant_role="tenant_admin",
    )
    payload = {
        "dataset_id": "global-baseline-1",
        "name": "Global Baseline",
        "description": "global",
        "industry": "manufacturing",
        "metrics": {
            "m1": {
                "unit": "percent",
                "description": "desc",
                "profile": {"p10": "1", "p25": "2", "p50": "3", "p75": "4", "p90": "5", "mean": "3", "std_dev": "1", "sample_size": 10},
            }
        },
        "ownership_mode": "global_system",
    }
    response = await client.post("/v1/benchmarks/datasets", json=payload)
    assert response.status_code == 403
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_super_admin_can_create_global_benchmark(client: AsyncClient, setup_mock_repo: AsyncMock, monkeypatch):
    # Mock the global admin check to allow super_admin role
    monkeypatch.setattr(main_module, "_assert_global_benchmark_admin", lambda ctx: None)
    
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        tenant_id="tenant-a",
        roles=["super_admin"],
        tenant_role="super_admin",
    )
    payload = {
        "dataset_id": "global-baseline-1",
        "name": "Global Baseline",
        "description": "global",
        "industry": "manufacturing",
        "metrics": {
            "m1": {
                "unit": "percent",
                "description": "desc",
                "profile": {"p10": "1", "p25": "2", "p50": "3", "p75": "4", "p90": "5", "mean": "3", "std_dev": "1", "sample_size": 10},
            }
        },
        "ownership_mode": "global_system",
    }
    response = await client.post("/v1/benchmarks/datasets", json=payload)
    assert response.status_code == 200
    saved_dataset = setup_mock_repo.save_dataset.call_args.args[0]
    assert saved_dataset.tenant_id == "system"
    assert saved_dataset.ownership_mode == "global_system"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_tenant_user_cannot_update_existing_global_benchmark(client: AsyncClient, setup_mock_repo: AsyncMock):
    global_ds = BenchmarkDataset(
        dataset_id="global-baseline-1",
        tenant_id="system",
        ownership_mode="global_system",
        name="Global Baseline",
        description="global",
        industry="manufacturing",
        segment=None,
        geography="global",
    )
    setup_mock_repo.get_dataset.return_value = global_ds
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        tenant_id="tenant-b",
        roles=["tenant_admin"],
        tenant_role="tenant_admin",
    )
    payload = {
        "dataset_id": "global-baseline-1",
        "name": "Global Baseline",
        "description": "global update",
        "industry": "manufacturing",
        "metrics": {
            "m1": {
                "unit": "percent",
                "description": "desc",
                "profile": {"p10": "1", "p25": "2", "p50": "3", "p75": "4", "p90": "5", "mean": "3", "std_dev": "1", "sample_size": 10},
            }
        },
        "ownership_mode": "tenant",
    }
    response = await client.put("/v1/benchmarks/datasets/global-baseline-1", json=payload)
    # Returns 400 because ownership_mode mismatch: existing is global_system, payload is tenant
    assert response.status_code == 400
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ready_returns_503_with_startup_degraded_state(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(main_module, "_benchmark_repo", None)
    monkeypatch.setattr(main_module, "_neo4j_startup_error", "startup dependency failed")

    response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["neo4j"] == {
        "status": "failed",
        "detail": "Neo4j benchmark store unavailable",
    }
    assert data["checks"]["benchmark_store"] == {
        "status": "failed",
        "detail": "Benchmark store not initialized",
    }
    assert data["checks"]["startup"] == {
        "status": "failed",
        "detail": "Neo4j benchmark store unavailable",
    }


@pytest.mark.asyncio
async def test_ready_returns_503_when_config_validation_fails(client: AsyncClient, monkeypatch):
    def failing_settings_validation():
        raise RuntimeError("missing required setting")

    monkeypatch.setattr(main_module, "validate_layer6_startup_settings", failing_settings_validation)

    response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["config"] == {
        "status": "failed",
        "detail": "Configuration validation failed",
    }
