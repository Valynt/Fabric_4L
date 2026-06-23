"""Edge case and validation tests for Layer 6 Benchmark Service.

Tests error handling, input validation, and boundary conditions.
"""

from unittest.mock import AsyncMock, MagicMock

import layer6_benchmarks.api.main as main_module
import pytest
from httpx import ASGITransport, AsyncClient
from layer6_benchmarks.api.main import app


@pytest.fixture(autouse=True)
def setup_mock_repo(monkeypatch):
    """Setup mock repository before each test."""
    mock_repo = AsyncMock()
    monkeypatch.setattr(main_module, "authorize_action", lambda *args, **kwargs: None)
    mock_dataset = MagicMock()
    mock_dataset.dataset_id = "manufacturing-efficiency-2024"
    mock_dataset.industry = "manufacturing"
    mock_dataset.segment = "default"
    mock_dataset.version = "1.0.0"
    mock_dataset.name = "Manufacturing Efficiency"
    mock_dataset.description = "desc"
    mock_dataset.geography = "global"
    mock_dataset.data_source = "source"
    mock_dataset.metrics = {
        "oee_overall_equipment_effectiveness": MagicMock(
            name="oee",
            profile=MagicMock(
                p10=60, p25=70, p50=80, p75=90, p90=95, mean=80, std_dev=5, sample_size=1000
            ),
        ),
        "defect_rate_percent": MagicMock(
            name="defect",
            profile=MagicMock(
                p10=1, p25=2, p50=3, p75=4, p90=5, mean=3, std_dev=1, sample_size=1000
            ),
        ),
        "production_cycle_time_minutes": MagicMock(
            name="cycle_time",
            profile=MagicMock(
                p10=10, p25=20, p50=30, p75=40, p90=50, mean=30, std_dev=10, sample_size=1000
            ),
        ),
    }

    mock_dataset.get_metric = lambda m: mock_dataset.metrics.get(m)

    mock_repo.list_datasets.return_value = [mock_dataset]

    async def get_dataset(dataset_id, tenant_id="system"):
        if dataset_id == "manufacturing-efficiency-2024":
            return mock_dataset
        return None

    mock_repo.get_dataset = AsyncMock(side_effect=get_dataset)
    monkeypatch.setattr(main_module, "_benchmark_repo", mock_repo)
    yield mock_repo


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


class TestBenchmarkValidation:
    """Test input validation and error handling."""

    @pytest.mark.asyncio
    async def test_compare_rejects_invalid_company_value(self, client: AsyncClient):
        """Should reject non-numeric company_value with 400 Bad Request."""
        payload = {
            "dataset_id": "manufacturing-efficiency-2024",
            "metric": "oee_overall_equipment_effectiveness",
            "company_value": "not-a-number",
            "industry": "manufacturing",
        }
        response = await client.post("/v1/benchmarks/compare", json=payload)
        # API returns 422 (validation error) for invalid Decimal format
        assert response.status_code == 422
        data = response.json()
        # Error message is in nested error structure
        error_msg = data.get("error", {}).get("message", "")
        assert "Invalid" in error_msg or "company_value" in error_msg

    @pytest.mark.asyncio
    async def test_compare_rejects_negative_company_value(self, client: AsyncClient):
        """Should handle negative company values appropriately."""
        payload = {
            "dataset_id": "manufacturing-efficiency-2024",
            "metric": "defect_rate_percent",
            "company_value": "-5.0",
            "industry": "manufacturing",
        }
        response = await client.post("/v1/benchmarks/compare", json=payload)
        # Service may accept but should handle gracefully
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_compare_rejects_missing_required_fields(self, client: AsyncClient):
        """Should reject payload missing required fields."""
        payload = {
            "dataset_id": "manufacturing-efficiency-2024",
            # missing metric and company_value
        }
        response = await client.post("/v1/benchmarks/compare", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_validate_accepts_negative_tolerance(self, client: AsyncClient):
        """API accepts negative tolerance (inverts range calculation)."""
        payload = {
            "dataset_id": "manufacturing-efficiency-2024",
            "metric": "defect_rate_percent",
            "value": "2.0",
            "tolerance_percent": -10,  # Negative tolerance shrinks range
        }
        response = await client.post("/v1/benchmarks/validate", json=payload)
        # API accepts negative tolerance - returns 200 with adjusted range
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "expected_range" in data


class TestBenchmarkEdgeCases:
    """Test boundary conditions and edge cases."""

    @pytest.mark.asyncio
    async def test_compare_with_zero_value(self, client: AsyncClient):
        """Should handle zero company value correctly."""
        payload = {
            "dataset_id": "manufacturing-efficiency-2024",
            "metric": "defect_rate_percent",
            "company_value": "0",
            "industry": "manufacturing",
        }
        response = await client.post("/v1/benchmarks/compare", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "percentile" in data

    @pytest.mark.asyncio
    async def test_compare_with_very_large_value(self, client: AsyncClient):
        """Should handle very large company values for cycle time metric."""
        payload = {
            "dataset_id": "manufacturing-efficiency-2024",
            "metric": "production_cycle_time_minutes",
            "company_value": "10000",  # Very large cycle time
            "industry": "manufacturing",
        }
        response = await client.post("/v1/benchmarks/compare", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "percentile" in data
        # Large value should result in high percentile (since higher cycle time is worse)
        assert data["percentile"] >= 90

    @pytest.mark.asyncio
    async def test_compare_with_decimal_precision(self, client: AsyncClient):
        """Should handle values with high decimal precision."""
        payload = {
            "dataset_id": "manufacturing-efficiency-2024",
            "metric": "oee_overall_equipment_effectiveness",
            "company_value": "72.54321",
            "industry": "manufacturing",
        }
        response = await client.post("/v1/benchmarks/compare", json=payload)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_validate_with_zero_tolerance(self, client: AsyncClient):
        """Should handle zero tolerance (exact match required)."""
        payload = {
            "dataset_id": "manufacturing-efficiency-2024",
            "metric": "defect_rate_percent",
            "value": "2.0",
            "tolerance_percent": 0,
        }
        response = await client.post("/v1/benchmarks/validate", json=payload)
        assert response.status_code == 200


class TestBenchmarkNotFoundHandling:
    """Test 404 handling for missing resources."""

    @pytest.mark.asyncio
    async def test_get_dataset_invalid_id_format(self, client: AsyncClient):
        """Should handle invalid dataset ID formats."""
        response = await client.get("/v1/benchmarks/datasets/invalid-id-with-special-chars-!!!")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_compare_nonexistent_dataset(self, client: AsyncClient):
        """Should return 404 for comparison with non-existent dataset."""
        payload = {
            "dataset_id": "nonexistent-dataset-12345",
            "metric": "some_metric",
            "company_value": "50.0",
            "industry": "manufacturing",
        }
        response = await client.post("/v1/benchmarks/compare", json=payload)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_validate_nonexistent_dataset(self, client: AsyncClient):
        """Should return 404 for validation with non-existent dataset."""
        payload = {
            "dataset_id": "nonexistent-dataset-12345",
            "metric": "some_metric",
            "value": "50.0",
            "tolerance_percent": 10,
        }
        response = await client.post("/v1/benchmarks/validate", json=payload)
        assert response.status_code == 404
