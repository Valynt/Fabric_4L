"""Tests for Layer 6 Benchmark Service API."""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from test_valueos_contracts import valid_vmrt_payload
from value_fabric.shared.identity.context import RequestContext

import layer6_benchmarks.api.main as main_module
from layer6_benchmarks.api.deps import get_request_context
from layer6_benchmarks.api.main import app
from layer6_benchmarks.models.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from layer6_benchmarks.models.vmrt_trace import VMRTTraceRecord


@pytest.fixture(autouse=True)
def setup_mock_repo(monkeypatch):
    """Set up a deterministic benchmark repository for API tests."""
    mock_repo = AsyncMock()
    vmrt_trace_repo = AsyncMock()
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
    vmrt_trace_repo.save_trace = AsyncMock(side_effect=lambda record: record)
    vmrt_trace_repo.get_trace = AsyncMock(return_value=None)
    vmrt_trace_repo.promote_trace = AsyncMock(return_value=None)
    monkeypatch.setattr(main_module, "_benchmark_repo", mock_repo)
    monkeypatch.setattr(main_module, "_vmrt_trace_repo", vmrt_trace_repo)
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
async def test_recommend_range_returns_distribution_and_provenance(client: AsyncClient):
    payload = {
        "dataset_id": "manufacturing-efficiency-2024",
        "metric": "oee_overall_equipment_effectiveness",
        "industry": "manufacturing",
    }
    response = await client.post("/v1/benchmarks/recommend-range", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "manufacturing-efficiency-2024"
    assert data["metric"] == "oee_overall_equipment_effectiveness"
    assert data["distribution"]["p10"] == "60"
    assert data["distribution"]["p90"] == "95"
    assert data["provenance"]["data_source"] == "source"
    assert data["provenance"]["confidence"] == "high"


@pytest.mark.asyncio
async def test_compare_distribution_positions_value_against_peer_distribution(
    client: AsyncClient,
):
    payload = {
        "dataset_id": "manufacturing-efficiency-2024",
        "metric": "oee_overall_equipment_effectiveness",
        "company_value": "92",
        "industry": "manufacturing",
    }
    response = await client.post("/v1/benchmarks/compare-distribution", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["percentile"] == 82
    assert data["assessment"] == "top_performer"
    assert data["variance_from_median_percent"] == 15.0
    assert data["distribution"]["sample_size"] == 1000


@pytest.mark.asyncio
async def test_validate_value_uses_p10_p90_as_default_expected_range(client: AsyncClient):
    payload = {
        "dataset_id": "manufacturing-efficiency-2024",
        "metric": "defect_rate_percent",
        "value": "6.0",
    }
    response = await client.post("/v1/benchmarks/validate-value", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert data["expected_range"] == ["1", "5"]
    assert data["severity"] == "error"
    assert data["provenance"]["source_count"] == 1


@pytest.mark.asyncio
async def test_metric_catalog_lists_metrics_without_raw_storage_access(client: AsyncClient):
    response = await client.get("/v1/benchmarks/metrics")

    assert response.status_code == 200
    data = response.json()
    assert [item["metric"] for item in data["metrics"]] == [
        "oee_overall_equipment_effectiveness",
        "defect_rate_percent",
    ]
    assert data["metrics"][0]["dataset_id"] == "manufacturing-efficiency-2024"


@pytest.mark.asyncio
async def test_metric_provenance_returns_safe_source_summary(client: AsyncClient):
    response = await client.post(
        "/v1/benchmarks/metric-provenance",
        json={
            "dataset_id": "manufacturing-efficiency-2024",
            "metric": "defect_rate_percent",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data_source"] == "source"
    assert data["confidence_score"] == 0.9
    assert data["license_class"] == "unspecified"


@pytest.mark.asyncio
async def test_coverage_status_reports_required_valueos_industries(client: AsyncClient):
    response = await client.get("/v1/benchmarks/coverage")

    assert response.status_code == 200
    data = response.json()
    assert data["total_metrics"] == 2
    assert "retail" in data["missing_required_industries"]
    manufacturing = next(
        cell for cell in data["industries"] if cell["industry"] == "manufacturing"
    )
    assert manufacturing == {
        "industry": "manufacturing",
        "metric_count": 2,
        "status": "partial",
    }


@pytest.mark.asyncio
async def test_validate_vmrt_accepts_production_ready_trace(client: AsyncClient):
    response = await client.post(
        "/v1/benchmarks/vmrt/validate",
        json={"trace": valid_vmrt_payload(), "min_quality_score": 3.5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "is_valid": True,
        "trace_id": "vos-pt1-trace-001",
        "schema_version": "1.0.0",
        "production_ready": True,
        "quality_score_overall": "4.25",
        "errors": [],
    }


@pytest.mark.asyncio
async def test_validate_vmrt_blocks_low_quality_trace_from_production(client: AsyncClient):
    trace = valid_vmrt_payload()
    trace["quality_scores"]["financial_rigor"] = 2.9

    response = await client.post(
        "/v1/benchmarks/vmrt/validate",
        json={"trace": trace, "min_quality_score": 3.5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["production_ready"] is False
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_validate_vmrt_fails_closed_on_broken_trace_linkage(client: AsyncClient):
    trace = valid_vmrt_payload()
    trace["financial_impacts"][0]["kpi_ids"] = ["missing-kpi"]

    response = await client.post(
        "/v1/benchmarks/vmrt/validate",
        json={"trace": trace, "min_quality_score": 3.5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert data["production_ready"] is False
    assert data["trace_id"] == "vos-pt1-trace-001"
    assert "VMRT_UNKNOWN_KPI_REF" in data["errors"][0]


@pytest.mark.asyncio
async def test_upsert_vmrt_trace_persists_tenant_scoped_record(client: AsyncClient):
    response = await client.post(
        "/v1/benchmarks/vmrt/traces",
        json={"trace": valid_vmrt_payload(), "min_quality_score": 3.5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "vos-pt1-trace-001"
    assert data["status"] == "production_ready"
    assert data["production_ready"] is True
    assert data["quality_score_overall"] == "4.25"
    assert data["trace"]["trace_id"] == "vos-pt1-trace-001"
    saved_record = main_module._vmrt_trace_repo.save_trace.call_args.args[0]
    assert saved_record.tenant_id == "system"


@pytest.mark.asyncio
async def test_upsert_vmrt_trace_rejects_broken_linkage(client: AsyncClient):
    trace = valid_vmrt_payload()
    trace["financial_impacts"][0]["kpi_ids"] = ["missing-kpi"]

    response = await client.post(
        "/v1/benchmarks/vmrt/traces",
        json={"trace": trace, "min_quality_score": 3.5},
    )

    assert response.status_code == 422
    assert main_module._vmrt_trace_repo.save_trace.await_count == 0


@pytest.mark.asyncio
async def test_get_vmrt_trace_returns_tenant_record(client: AsyncClient):
    record = VMRTTraceRecord(
        trace_id="vos-pt1-trace-001",
        tenant_id="test-tenant",
        schema_version="1.0.0",
        status="validated",
        trace=valid_vmrt_payload(),
        quality_score_overall="4.25",
        production_ready=False,
    )
    main_module._vmrt_trace_repo.get_trace.return_value = record

    response = await client.get("/v1/benchmarks/vmrt/traces/vos-pt1-trace-001")

    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "vos-pt1-trace-001"
    assert data["trace"]["schema_version"] == "1.0.0"
    main_module._vmrt_trace_repo.get_trace.assert_awaited_with(
        "vos-pt1-trace-001", tenant_id="system"
    )


@pytest.mark.asyncio
async def test_promote_vmrt_trace_rejects_low_quality_record(client: AsyncClient):
    trace = valid_vmrt_payload()
    trace["quality_scores"]["financial_rigor"] = 2.9
    record = VMRTTraceRecord(
        trace_id="vos-pt1-trace-001",
        tenant_id="test-tenant",
        schema_version="1.0.0",
        status="validated",
        trace=trace,
        quality_score_overall="4.25",
        production_ready=False,
    )
    main_module._vmrt_trace_repo.get_trace.return_value = record

    response = await client.post(
        "/v1/benchmarks/vmrt/traces/vos-pt1-trace-001/promote",
        json={"reviewer": "governance-owner", "min_quality_score": 3.5},
    )

    assert response.status_code == 422
    assert main_module._vmrt_trace_repo.promote_trace.await_count == 0


@pytest.mark.asyncio
async def test_promote_vmrt_trace_marks_ready_record(client: AsyncClient):
    existing = VMRTTraceRecord(
        trace_id="vos-pt1-trace-001",
        tenant_id="test-tenant",
        schema_version="1.0.0",
        status="production_ready",
        trace=valid_vmrt_payload(),
        quality_score_overall="4.25",
        production_ready=True,
    )
    promoted = VMRTTraceRecord(
        trace_id="vos-pt1-trace-001",
        tenant_id="test-tenant",
        schema_version="1.0.0",
        status="production_ready",
        trace=valid_vmrt_payload(),
        quality_score_overall="4.25",
        production_ready=True,
        reviewer="governance-owner",
    )
    main_module._vmrt_trace_repo.get_trace.return_value = existing
    main_module._vmrt_trace_repo.promote_trace.return_value = promoted

    response = await client.post(
        "/v1/benchmarks/vmrt/traces/vos-pt1-trace-001/promote",
        json={"reviewer": "governance-owner", "min_quality_score": 3.5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "production_ready"
    assert data["reviewer"] == "governance-owner"
    main_module._vmrt_trace_repo.promote_trace.assert_awaited_with(
        "vos-pt1-trace-001",
        tenant_id="system",
        reviewer="governance-owner",
    )


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
            "/v1/benchmarks/recommend-range",
            {
                "dataset_id": "manufacturing-efficiency-2024",
                "metric": "oee_overall_equipment_effectiveness",
            },
        ),
        ("GET", "/v1/benchmarks/metrics", None),
        ("GET", "/v1/benchmarks/coverage", None),
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
async def test_ready_returns_503_when_dependency_health_check_fails(
    client: AsyncClient, monkeypatch
):
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
async def test_health_remains_liveness_only_when_dependency_degraded(
    client: AsyncClient, monkeypatch
):
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
                "profile": {
                    "p10": "1",
                    "p25": "2",
                    "p50": "3",
                    "p75": "4",
                    "p90": "5",
                    "mean": "3",
                    "std_dev": "1",
                    "sample_size": 10,
                },
            }
        },
        "ownership_mode": "global_system",
    }
    response = await client.post("/v1/benchmarks/datasets", json=payload)
    assert response.status_code == 403
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_super_admin_can_create_global_benchmark(
    client: AsyncClient, setup_mock_repo: AsyncMock, monkeypatch
):
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
                "profile": {
                    "p10": "1",
                    "p25": "2",
                    "p50": "3",
                    "p75": "4",
                    "p90": "5",
                    "mean": "3",
                    "std_dev": "1",
                    "sample_size": 10,
                },
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
async def test_tenant_user_cannot_update_existing_global_benchmark(
    client: AsyncClient, setup_mock_repo: AsyncMock
):
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
    # Ensure the mocked repository returns the existing global dataset for any tenant,
    # matching the real repository behavior where global_system datasets are visible across tenants.
    setup_mock_repo.get_dataset.side_effect = None
    setup_mock_repo.get_dataset.return_value = global_ds
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        tenant_id="tenant-b",
        roles=["tenant_admin"],
        tenant_role="tenant_admin",
    )
    payload = {
        "dataset_id": "global-baseline-1",
        "name": "Global Baseline",
        "description": "revised global baseline",
        "industry": "manufacturing",
        "metrics": {
            "m1": {
                "unit": "percent",
                "description": "desc",
                "profile": {
                    "p10": "1",
                    "p25": "2",
                    "p50": "3",
                    "p75": "4",
                    "p90": "5",
                    "mean": "3",
                    "std_dev": "1",
                    "sample_size": 10,
                },
            }
        },
        "ownership_mode": "tenant",
    }
    response = await client.put("/v1/benchmarks/datasets/global-baseline-1", json=payload)
    # Only global admins may modify existing global_system datasets.
    assert response.status_code == 403
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

    monkeypatch.setattr(
        main_module, "validate_layer6_startup_settings", failing_settings_validation
    )

    response = await client.get("/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["config"] == {
        "status": "failed",
        "detail": "Configuration validation failed",
    }
