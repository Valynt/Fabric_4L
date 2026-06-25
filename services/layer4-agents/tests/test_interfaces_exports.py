from __future__ import annotations

"""Tests for Layer 4 interfaces package exports and basic interface behavior.

Uses src.* imports with pytest pythonpath configuration.
"""


from decimal import Decimal

import pytest

from layer4_agents.adapters.benchmark_client import HTTPBenchmarkClient
from layer4_agents.interfaces import (
    ActivationRequest,
    BenchmarkDataset,
    BusinessCaseGroundTruthClientFactory,
    BusinessCaseGroundTruthPort,
    CompanyKnowledgePipelinePort,
    CompareDistributionRequest,
    ComparisonRequest,
    ContextFinancialExtractionPort,
    ContextIngestionPort,
    FormulaGovernance,
    FormulaStatus,
    GovernanceTransitionResult,
    GroundTruthProxyPort,
    IBenchmarkClient,
    IFormulaApprovalWorkflow,
    IFormulaGovernanceService,
    IGroundTruthVariableBridge,
    IValuePackService,
    IVariableRegistry,
    PackExecutionRequest,
    PackStatus,
    RecommendRangeRequest,
    ResolutionContext,
    SignalExtractionPort,
    SignalKnowledgePort,
    SignalReviewPort,
    ValidateValueRequest,
    ValuePack,
    Variable,
    VariableDataType,
    VariableSourceType,
)


@pytest.fixture
def sample_pack_id():
    """Sample pack ID for testing."""
    return "pack-1"


@pytest.fixture
def sample_workspace_id():
    """Sample workspace ID for testing."""
    return "ws-1"


@pytest.fixture
def sample_formula_id():
    """Sample formula ID for testing."""
    return "f-1"


def test_interfaces_module_exports_core_symbols():
    """Verify all core interface symbols are exported from the interfaces module."""
    assert IBenchmarkClient is not None
    assert BusinessCaseGroundTruthClientFactory is not None
    assert BusinessCaseGroundTruthPort is not None
    assert IValuePackService is not None
    assert IFormulaGovernanceService is not None
    assert IFormulaApprovalWorkflow is not None
    assert IVariableRegistry is not None
    assert IGroundTruthVariableBridge is not None
    assert CompanyKnowledgePipelinePort is not None
    assert ContextFinancialExtractionPort is not None
    assert ContextIngestionPort is not None
    assert GroundTruthProxyPort is not None
    assert SignalExtractionPort is not None
    assert SignalKnowledgePort is not None
    assert SignalReviewPort is not None


def test_http_benchmark_client_normalizes_base_url():
    """Verify HTTPBenchmarkClient removes trailing slash from base URL."""
    client = HTTPBenchmarkClient(base_url="http://localhost:8006/")
    assert client.base_url == "http://localhost:8006"


@pytest.mark.asyncio
async def test_http_benchmark_client_close_is_safe_without_open_client():
    """Verify closing an unopened HTTPBenchmarkClient is safe (no-op)."""
    client = HTTPBenchmarkClient(base_url="http://localhost:8006")
    # Should not raise even when client was never opened
    await client.close()  # No assertion needed - success means no exception raised


def test_value_pack_construction(sample_pack_id):
    """Verify ValuePack dataclass constructs with expected fields."""
    pack = ValuePack(
        pack_id=sample_pack_id,
        name="Manufacturing Pack",
        description="desc",
        industry="manufacturing",
        segment=None,
        status=PackStatus.DRAFT,
        version="1.0.0",
    )
    assert pack.pack_id == sample_pack_id
    assert pack.status == PackStatus.DRAFT


def test_pack_execution_request_construction(sample_pack_id, sample_workspace_id):
    """Verify PackExecutionRequest dataclass constructs with expected fields."""
    req = PackExecutionRequest(
        pack_id=sample_pack_id,
        workspace_id=sample_workspace_id,
        variables={"revenue": 1000},
    )
    assert req.pack_id == sample_pack_id
    assert req.workspace_id == sample_workspace_id


def test_formula_governance_construction(sample_formula_id):
    """Verify FormulaGovernance dataclass constructs with expected fields."""
    gov = FormulaGovernance(
        formula_id=sample_formula_id,
        current_version="1.0.0",
        status=FormulaStatus.DRAFT,
    )
    assert gov.formula_id == sample_formula_id
    assert gov.status == FormulaStatus.DRAFT


def test_activation_request_construction(sample_formula_id):
    """Verify ActivationRequest dataclass constructs with expected fields."""
    activation = ActivationRequest(
        formula_id=sample_formula_id,
        version="1.0.0",
        requested_by="user-1",
        justification="go live",
    )
    assert activation.formula_id == sample_formula_id
    assert activation.requested_by == "user-1"


def test_governance_transition_result_construction(sample_formula_id):
    """Verify GovernanceTransitionResult dataclass constructs with expected fields."""
    transition = GovernanceTransitionResult(
        success=True,
        formula_id=sample_formula_id,
        old_status=FormulaStatus.DRAFT,
        new_status=FormulaStatus.ACTIVE,
    )
    assert transition.formula_id == sample_formula_id
    assert transition.new_status == FormulaStatus.ACTIVE


def test_variable_construction():
    """Verify Variable dataclass constructs with expected fields."""
    variable = Variable(
        variable_id="v-1",
        name="Annual Revenue",
        description="Revenue in USD",
        data_type=VariableDataType.DECIMAL,
    )
    assert variable.variable_id == "v-1"
    assert variable.data_type == VariableDataType.DECIMAL


def test_resolution_context_construction(sample_workspace_id):
    """Verify ResolutionContext dataclass constructs with expected fields."""
    context = ResolutionContext(workspace_id=sample_workspace_id)
    assert context.workspace_id == sample_workspace_id


def test_benchmark_dataset_construction():
    """Verify BenchmarkDataset dataclass constructs with expected fields."""
    dataset = BenchmarkDataset(
        id="ds-1",
        name="Bench",
        industry="manufacturing",
        segment=None,
        metrics=["revenue"],
        statistical_profile={"p50": 123},
    )
    assert dataset.id == "ds-1"
    assert dataset.industry == "manufacturing"


def test_comparison_request_construction():
    """Verify ComparisonRequest dataclass constructs with expected fields."""
    dataset = BenchmarkDataset(
        id="ds-1",
        name="Bench",
        industry="manufacturing",
        segment=None,
        metrics=["revenue"],
        statistical_profile={"p50": 123},
    )
    comparison = ComparisonRequest(
        dataset_id=dataset.id,
        metric="revenue",
        company_value=100,
        industry="manufacturing",
    )
    assert comparison.dataset_id == dataset.id
    assert comparison.metric == "revenue"


def test_groundtruthapi_request_construction():
    """Verify ValueOS GroundTruthAPI request dataclasses construct cleanly."""
    range_request = RecommendRangeRequest(
        dataset_id="ds-1",
        metric="finance_ap_cost_per_invoice",
        industry="technology",
    )
    compare_request = CompareDistributionRequest(
        dataset_id="ds-1",
        metric="finance_ap_cost_per_invoice",
        company_value=100,
        industry="technology",
    )
    validate_request = ValidateValueRequest(
        dataset_id="ds-1",
        metric="finance_ap_cost_per_invoice",
        value=100,
    )

    assert range_request.metric == "finance_ap_cost_per_invoice"
    assert compare_request.company_value == 100
    assert validate_request.tolerance_percent == 0


class _FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError(f"unexpected status {self.status_code}")


class _FakeBenchmarkHttpClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, object | None]] = []

    async def get(self, url: str, params: dict | None = None) -> _FakeResponse:
        self.requests.append(("GET", url, params))
        return _FakeResponse(
            [
                {
                    "dataset_id": "ds-1",
                    "name": "Bench",
                    "industry": "technology",
                    "segment": "mid_market",
                    "metrics": ["finance_ap_cost_per_invoice"],
                }
            ]
        )

    async def post(self, url: str, json: dict | None = None) -> _FakeResponse:
        self.requests.append(("POST", url, json))
        if url.endswith("/recommend-range"):
            return _FakeResponse(_groundtruth_range_payload())
        if url.endswith("/compare-distribution"):
            payload = _groundtruth_range_payload()
            payload.update(
                {
                    "company_value": "12.4",
                    "percentile": 82,
                    "variance_from_median_percent": 47.6,
                    "peer_median": "8.4",
                    "peer_range": ["4.2", "14.9"],
                    "sample_size": 6744,
                    "confidence": "high",
                    "assessment": "top_performer",
                }
            )
            return _FakeResponse(payload)
        if url.endswith("/validate-value"):
            payload = _groundtruth_range_payload()
            payload.update(
                {
                    "is_valid": True,
                    "expected_range": ["4.2", "14.9"],
                    "actual_value": "12.4",
                    "deviation_percent": 47.6,
                    "severity": "info",
                    "message": "ok",
                }
            )
            return _FakeResponse(payload)
        raise AssertionError(f"unexpected url {url}")


def _groundtruth_range_payload() -> dict:
    return {
        "dataset_id": "ds-1",
        "metric": "finance_ap_cost_per_invoice",
        "industry": "technology",
        "segment": "mid_market",
        "unit": "USD",
        "distribution": {
            "p10": "4.2",
            "p25": "6.33",
            "p50": "8.4",
            "p75": "10.89",
            "p90": "14.9",
            "mean": "8.8",
            "std_dev": "2.1",
            "sample_size": 6744,
            "shape": "unknown",
        },
        "provenance": {
            "metric": "finance_ap_cost_per_invoice",
            "dataset_id": "ds-1",
            "data_source": "APQC",
            "source_count": 1,
            "confidence": "high",
            "confidence_score": 0.9,
            "license_class": "unspecified",
            "caveats": [],
        },
    }


@pytest.mark.asyncio
async def test_http_benchmark_client_uses_groundtruthapi_routes():
    """Verify the Layer 4 adapter reaches Layer 6 through governed endpoints."""
    client = HTTPBenchmarkClient(base_url="http://layer6:8006")
    fake_http = _FakeBenchmarkHttpClient()
    client._client = fake_http  # noqa: SLF001 - injected fake transport for port test.

    datasets = await client.list_datasets(industry="technology")
    recommended = await client.recommend_range(
        RecommendRangeRequest(dataset_id="ds-1", metric="finance_ap_cost_per_invoice")
    )
    compared = await client.compare_distribution(
        CompareDistributionRequest(
            dataset_id="ds-1",
            metric="finance_ap_cost_per_invoice",
            company_value=100,
        )
    )
    validated = await client.validate_value(
        ValidateValueRequest(
            dataset_id="ds-1",
            metric="finance_ap_cost_per_invoice",
            value=100,
        )
    )

    assert datasets[0].id == "ds-1"
    assert recommended.distribution.p90 == Decimal("14.9")
    assert compared.percentile == 82
    assert validated.is_valid is True
    assert [request[1] for request in fake_http.requests] == [
        "http://layer6:8006/v1/benchmarks/datasets",
        "http://layer6:8006/v1/benchmarks/recommend-range",
        "http://layer6:8006/v1/benchmarks/compare-distribution",
        "http://layer6:8006/v1/benchmarks/validate-value",
    ]


def test_variable_source_type_enum_values():
    """Verify VariableSourceType enum has expected string values."""
    assert VariableSourceType.BENCHMARK_LOOKUP.value == "benchmark_lookup"
