from __future__ import annotations

"""Tests for Layer 4 interfaces package exports and basic interface behavior.

Uses src.* imports with pytest pythonpath configuration.
"""


import pytest

from layer4_agents.adapters.benchmark_client import HTTPBenchmarkClient
from layer4_agents.interfaces import (
    ActivationRequest,
    BenchmarkDataset,
    ComparisonRequest,
    ContextFinancialExtractionPort,
    ContextIngestionPort,
    FormulaGovernance,
    FormulaStatus,
    GovernanceTransitionResult,
    IBenchmarkClient,
    IFormulaApprovalWorkflow,
    IFormulaGovernanceService,
    IGroundTruthVariableBridge,
    IValuePackService,
    IVariableRegistry,
    PackExecutionRequest,
    PackStatus,
    ResolutionContext,
    SignalExtractionPort,
    SignalKnowledgePort,
    SignalReviewPort,
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
    assert IValuePackService is not None
    assert IFormulaGovernanceService is not None
    assert IFormulaApprovalWorkflow is not None
    assert IVariableRegistry is not None
    assert IGroundTruthVariableBridge is not None
    assert ContextFinancialExtractionPort is not None
    assert ContextIngestionPort is not None
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


def test_variable_source_type_enum_values():
    """Verify VariableSourceType enum has expected string values."""
    assert VariableSourceType.BENCHMARK_LOOKUP.value == "benchmark_lookup"
