from __future__ import annotations

"""Comprehensive unit tests for ROICalculatorWorkflow.

Covers:
- State creation and validation
- Each pipeline step in isolation (with mocked tool registry)
- Error propagation and step-gate behaviour
- Division-by-zero defence
- Tenant context threading
- ToolResult unwrapping (production registry format) and raw-dict fallback
"""


from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from layer4_agents.models.agent_state import ROIAgentState, WorkflowStatus
from layer4_agents.tools.registry import ToolResult
from layer4_agents.workflows.roi_calculator import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_NONE,
    DEFAULT_ANNUAL_LICENSE_COST,
    DEFAULT_ANNUAL_REVENUE,
    DEFAULT_DISCOUNT_RATE,
    DEFAULT_EMPLOYEE_COUNT,
    DEFAULT_HOURLY_RATE,
    DEFAULT_HOURS_SAVED_WEEKLY,
    DEFAULT_IMPLEMENTATION_COST,
    NPV_YEARS,
    ROICalculatorWorkflow,
    _unwrap_tool_data,
    _unwrap_tool_error,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_tool_result(data: dict[str, Any] | None = None, *, error: dict[str, Any] | None = None) -> ToolResult:
    """Build a ToolResult as the real registry returns."""
    if error:
        return ToolResult(status="error", data=None, error=error, metadata={})
    return ToolResult(status="success", data=data or {}, error=None, metadata={})


def _make_state_with_output(**outputs: Any) -> ROIAgentState:
    """Build a minimal ROIAgentState with the given output_data pre-seeded."""
    return ROIAgentState(tenant_id="test-tenant", 
        workflow_type="roi_calculator",
        status=WorkflowStatus.RUNNING,
        input_data={},
        output_data=dict(outputs),
    )


@pytest.fixture
def workflow():
    """Fresh ROICalculatorWorkflow with a mocked tool registry."""
    registry = Mock()
    registry.execute = AsyncMock()
    return ROICalculatorWorkflow(tool_registry=registry), registry


# ---------------------------------------------------------------------------
# State creation
# ---------------------------------------------------------------------------
class TestCreateInitialState:
    def test_valid_input_produces_roi_state(self, workflow):
        wf, _ = workflow
        state = wf.create_initial_state(
            {
                "prospect_id": "p-001",
                "value_driver_ids": ["vd-1", "vd-2"],
                "industry_vertical": "manufacturing",
                "tenant_id": "t-42",
            },
            tenant_id="test-tenant",
        )
        assert state.workflow_type.value == "roi_calculator"
        assert state.status == WorkflowStatus.PENDING
        assert state.roi_input.prospect_id == "p-001"
        assert state.roi_input.value_driver_ids == ["vd-1", "vd-2"]
        assert state.tenant_id == "test-tenant"

    def test_empty_value_driver_ids_are_rejected(self, workflow):
        wf, _ = workflow

        with pytest.raises(ValidationError, match="At least one value_driver_id is required"):
            wf.create_initial_state(
                {"prospect_id": "p-001", "value_driver_ids": []},
                tenant_id="test-tenant",
            )


# ---------------------------------------------------------------------------
# ToolResult unwrapping helpers
# ---------------------------------------------------------------------------
class TestUnwrapHelpers:
    def test_unwrap_tool_data_from_tool_result(self):
        tr = _make_tool_result({"profile": {"name": "Acme"}})
        assert _unwrap_tool_data(tr) == {"profile": {"name": "Acme"}}

    def test_unwrap_tool_data_from_dict(self):
        assert _unwrap_tool_data({"foo": "bar"}) == {"foo": "bar"}

    def test_unwrap_tool_data_none_returns_empty(self):
        assert _unwrap_tool_data(None) == {}

    def test_unwrap_tool_error_when_failed(self):
        tr = _make_tool_result(error={"message": "boom", "code": "ERR"})
        assert _unwrap_tool_error(tr) == "boom"

    def test_unwrap_tool_error_when_success(self):
        tr = _make_tool_result({"ok": True})
        assert _unwrap_tool_error(tr) is None


# ---------------------------------------------------------------------------
# Step 1 – Prospect data
# ---------------------------------------------------------------------------
class TestExecuteGetProspectData:
    @pytest.mark.asyncio
    async def test_successful_enrichment(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output()
        state.roi_input = Mock()
        state.roi_input.prospect_id = "p-001"
        state.roi_input.industry_vertical = "healthcare"

        registry.execute.return_value = _make_tool_result(
            {
                "profile": {"employees": 500, "industry": "healthcare", "annual_revenue": 50_000_000},
                "custom_fields": {"pain_points": ["slow onboarding"]},
            }
        )

        result = await wf._execute_get_prospect_data(state)

        assert result["error"] == ""
        assert result["prospect_id"] == "p-001"
        assert result["enriched"]["company_size"] == 500
        assert result["enriched"]["industry"] == "healthcare"
        assert result["enriched"]["annual_revenue"] == 50_000_000
        assert result["enriched"]["pain_points"] == ["slow onboarding"]

    @pytest.mark.asyncio
    async def test_missing_roi_input_returns_error(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output()
        state.roi_input = None
        result = await wf._execute_get_prospect_data(state)
        assert result["error"] == "No ROI input configured"
        assert result["enriched"] is None

    @pytest.mark.asyncio
    async def test_tool_failure_returns_error(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output()
        state.roi_input = Mock()
        state.roi_input.prospect_id = "p-001"
        state.roi_input.industry_vertical = None

        registry.execute.return_value = _make_tool_result(error={"message": "CRM timeout"})

        result = await wf._execute_get_prospect_data(state)
        assert result["error"] == "CRM timeout"
        assert result["enriched"] is None

    @pytest.mark.asyncio
    async def test_tenant_id_passed_to_tool(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output()
        state.roi_input = Mock()
        state.roi_input.prospect_id = "p-001"
        state.roi_input.industry_vertical = None
        state.tenant_id = "tenant-99"

        registry.execute.return_value = _make_tool_result({"profile": {}})
        await wf._execute_get_prospect_data(state)

        call_args = registry.execute.call_args
        assert call_args[0][0] == "get_prospect_data"
        assert call_args[0][1]["tenant_id"] == "tenant-99"


# ---------------------------------------------------------------------------
# Step 2 – Benchmarks
# ---------------------------------------------------------------------------
class TestExecuteFetchBenchmarks:
    @pytest.mark.asyncio
    async def test_fetches_all_metrics(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output()
        state.roi_input = Mock()
        state.roi_input.industry_vertical = "saas"
        state.roi_input.company_size = "large"

        registry.execute.return_value = _make_tool_result({"percentile": 75})

        result = await wf._execute_fetch_benchmarks(state)

        assert result["industry"] == "saas"
        assert set(result["benchmarks"].keys()) == {"roi_percent", "cost_reduction", "time_to_value_months"}
        assert result["error"] == ""

    @pytest.mark.asyncio
    async def test_partial_failure_preserves_errors(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output()
        state.roi_input = Mock()
        state.roi_input.industry_vertical = "saas"
        state.roi_input.company_size = "large"

        async def side_effect(tool_name, params):
            if params["metric_name"] == "cost_reduction":
                return _make_tool_result(error={"message": "missing data"})
            return _make_tool_result({"score": 0.5})

        registry.execute.side_effect = side_effect

        result = await wf._execute_fetch_benchmarks(state)

        assert result["benchmarks"]["cost_reduction"] is None
        assert "cost_reduction: missing data" in result["error"]
        assert result["benchmarks"]["roi_percent"] == {"score": 0.5}

    @pytest.mark.asyncio
    async def test_no_roi_input_returns_error(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output()
        state.roi_input = None
        result = await wf._execute_fetch_benchmarks(state)
        assert result["error"] == "No ROI input configured"

    @pytest.mark.asyncio
    async def test_tenant_id_passed_to_tool(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output()
        state.roi_input = Mock()
        state.roi_input.industry_vertical = "saas"
        state.roi_input.company_size = "large"
        state.tenant_id = "tenant-77"

        registry.execute.return_value = _make_tool_result({})
        await wf._execute_fetch_benchmarks(state)

        # registry.execute is called with (tool_name, params_dict)
        call_args = registry.execute.call_args
        params = call_args[0][1]
        assert params.get("tenant_id") == "tenant-77"


# ---------------------------------------------------------------------------
# Step 3 – Variable substitution
# ---------------------------------------------------------------------------
class TestExecuteSubstituteVariables:
    @pytest.mark.asyncio
    async def test_successful_substitution(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output(
            load_prospect={
                "enriched": {
                    "annual_revenue": 20_000_000,
                    "company_size": 1000,
                    "custom_variables": {"extra": 42},
                }
            }
        )
        state.roi_input = None  # not used in this step

        registry.execute.return_value = _make_tool_result(
            {"results": [{"defaults": {"hourly_rate": 100}}]}
        )

        result = await wf._execute_substitute_variables(state)

        assert result.get("error") == ""
        assert result["variables"]["annual_revenue"] == 20_000_000
        assert result["variables"]["employee_count"] == 1000
        assert result["variables"]["hourly_rate"] == 100
        assert result["variables"]["extra"] == 42
        assert result["variable_count"] == 7  # 6 defaults + 1 custom
        assert result["confidence"] == CONFIDENCE_HIGH

    @pytest.mark.asyncio
    async def test_uses_defaults_when_no_prospect_data(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output(load_prospect={"enriched": {}})

        registry.execute.return_value = _make_tool_result({"results": []})

        result = await wf._execute_substitute_variables(state)

        assert result["variables"]["annual_revenue"] == DEFAULT_ANNUAL_REVENUE
        assert result["variables"]["employee_count"] == DEFAULT_EMPLOYEE_COUNT
        assert result["variables"]["hourly_rate"] == DEFAULT_HOURLY_RATE
        assert result["variables"]["hours_saved_weekly"] == DEFAULT_HOURS_SAVED_WEEKLY
        assert result["variables"]["implementation_cost"] == DEFAULT_IMPLEMENTATION_COST
        assert result["variables"]["annual_license_cost"] == DEFAULT_ANNUAL_LICENSE_COST
        assert result["confidence"] == CONFIDENCE_MEDIUM

    @pytest.mark.asyncio
    async def test_prior_step_error_blocked(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output(load_prospect={"error": "CRM down"})
        result = await wf._execute_substitute_variables(state)
        assert "prior step failed" in result["error"]


# ---------------------------------------------------------------------------
# Step 4 – Formula evaluation
# ---------------------------------------------------------------------------
class TestExecuteEvaluateFormula:
    @pytest.mark.asyncio
    async def test_successful_evaluation(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output(
            substitute_vars={"variables": {"revenue": 10_000_000}}
        )
        state.roi_input = Mock()
        state.roi_input.value_driver_ids = ["vd-1"]

        async def side_effect(tool_name, params):
            if tool_name == "query_graph":
                return _make_tool_result(
                    {
                        "results": [
                            {
                                "id": "vd-1",
                                "name": "Efficiency",
                                "category": "ops",
                                "formula": "revenue * 0.1",
                                "unit": "USD",
                            }
                        ]
                    }
                )
            if tool_name == "evaluate_formula":
                return _make_tool_result(
                    {"success": True, "result": 1_000_000, "substituted_formula": "10000000 * 0.1"}
                )
            return _make_tool_result({})

        registry.execute.side_effect = side_effect

        result = await wf._execute_evaluate_formula(state)

        assert result["error"] == ""
        assert result["calculated_count"] == 1
        res = result["results"][0]
        assert res["result"] == 1_000_000
        assert res["confidence"] == CONFIDENCE_HIGH
        assert res["missing_variables"] == []

    @pytest.mark.asyncio
    async def test_eval_formula_failure_path(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output(
            substitute_vars={"variables": {"revenue": 10_000_000}}
        )
        state.roi_input = Mock()
        state.roi_input.value_driver_ids = ["vd-1"]

        async def side_effect(tool_name, params):
            if tool_name == "query_graph":
                return _make_tool_result(
                    {
                        "results": [
                            {
                                "id": "vd-1",
                                "name": "Efficiency",
                                "category": "ops",
                                "formula": "revenue * 0.1",
                                "unit": "USD",
                            }
                        ]
                    }
                )
            if tool_name == "evaluate_formula":
                return _make_tool_result(
                    {"success": False, "error": "Division by zero"}
                )
            return _make_tool_result({})

        registry.execute.side_effect = side_effect

        result = await wf._execute_evaluate_formula(state)

        res = result["results"][0]
        assert res["confidence"] == CONFIDENCE_LOW
        assert "Division by zero" in res["missing_variables"]

    @pytest.mark.asyncio
    async def test_exception_during_eval(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output(
            substitute_vars={"variables": {"revenue": 10_000_000}}
        )
        state.roi_input = Mock()
        state.roi_input.value_driver_ids = ["vd-1"]

        async def side_effect(tool_name, params):
            if tool_name == "query_graph":
                return _make_tool_result(
                    {
                        "results": [
                            {
                                "id": "vd-1",
                                "name": "Efficiency",
                                "category": "ops",
                                "formula": "revenue * 0.1",
                                "unit": "USD",
                            }
                        ]
                    }
                )
            if tool_name == "evaluate_formula":
                raise RuntimeError(" evaluator crashed ")
            return _make_tool_result({})

        registry.execute.side_effect = side_effect

        result = await wf._execute_evaluate_formula(state)

        res = result["results"][0]
        assert res["confidence"] == CONFIDENCE_NONE
        assert res["missing_variables"][0] == "RuntimeError: formula_evaluation_failed"

    @pytest.mark.asyncio
    async def test_missing_value_driver_formula(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output(
            substitute_vars={"variables": {"revenue": 10_000_000}}
        )
        state.roi_input = Mock()
        state.roi_input.value_driver_ids = ["vd-empty"]

        registry.execute.return_value = _make_tool_result(
            {
                "results": [
                    {
                        "id": "vd-empty",
                        "name": "Empty",
                        "category": "ops",
                        "formula": None,
                        "unit": "USD",
                    }
                ]
            }
        )

        result = await wf._execute_evaluate_formula(state)

        res = result["results"][0]
        assert res["confidence"] == CONFIDENCE_NONE
        assert res["missing_variables"][0] == "Value driver has no formula"

    @pytest.mark.asyncio
    async def test_prior_step_error_blocked(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output(
            substitute_vars={"error": "vars failed"}
        )
        state.roi_input = Mock()
        state.roi_input.value_driver_ids = ["vd-1"]

        result = await wf._execute_evaluate_formula(state)
        assert "variable substitution failed" in result["error"]

    @pytest.mark.asyncio
    async def test_tenant_id_passed_to_tools(self, workflow):
        wf, registry = workflow
        state = _make_state_with_output(
            substitute_vars={"variables": {"revenue": 10_000_000}}
        )
        state.roi_input = Mock()
        state.roi_input.value_driver_ids = ["vd-1"]
        state.tenant_id = "tenant-abc"

        registry.execute.return_value = _make_tool_result(
            {
                "results": [
                    {
                        "id": "vd-1",
                        "name": "Efficiency",
                        "category": "ops",
                        "formula": "revenue * 0.1",
                        "unit": "USD",
                    }
                ]
            }
        )

        await wf._execute_evaluate_formula(state)

        calls = registry.execute.call_args_list
        # First call = query_graph, second = evaluate_formula
        # query_graph passes tenant_id inside parameters dict
        assert calls[0][0][1]["parameters"].get("tenant_id") == "tenant-abc"
        assert calls[1][0][1].get("tenant_id") == "tenant-abc"


# ---------------------------------------------------------------------------
# Step 5 – Aggregation
# ---------------------------------------------------------------------------
class TestExecuteAggregateRoi:
    @pytest.mark.asyncio
    async def test_happy_path(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output(
            evaluate={
                "results": [
                    {"result": 500_000, "confidence": CONFIDENCE_HIGH},
                    {"result": 300_000, "confidence": CONFIDENCE_MEDIUM},
                ]
            },
            substitute_vars={"variables": {"implementation_cost": 400_000}},
        )

        result = await wf._execute_aggregate_roi(state)

        agg = result["aggregated"]
        assert agg["total_annual_value"] == 800_000
        assert agg["investment_required"] == 400_000
        assert agg["simple_roi_percent"] == 100.0
        assert agg["value_driver_count"] == 2
        assert agg["payback_period_months"] == 6.0
        assert agg["average_confidence"] == round((CONFIDENCE_HIGH + CONFIDENCE_MEDIUM) / 2, 2)

        # NPV sanity check: -400k + 800k/1.1 + 800k/1.1^2 + 800k/1.1^3
        expected_npv = -400_000
        for y in range(1, NPV_YEARS + 1):
            expected_npv += 800_000 / ((1 + DEFAULT_DISCOUNT_RATE) ** y)
        assert agg["three_year_npv"] == round(expected_npv, 2)

    @pytest.mark.asyncio
    async def test_no_results_returns_error(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output(evaluate={"results": []})
        result = await wf._execute_aggregate_roi(state)
        assert result["error"] == "No calculation results to aggregate"

    @pytest.mark.asyncio
    async def test_prior_step_error_blocked(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output(evaluate={"error": "eval failed"})
        result = await wf._execute_aggregate_roi(state)
        assert "evaluation failed" in result["error"]

    @pytest.mark.asyncio
    async def test_zero_investment_falls_back_to_default(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output(
            evaluate={"results": [{"result": 100_000, "confidence": 1.0}]},
            substitute_vars={"variables": {"implementation_cost": 0}},
        )
        result = await wf._execute_aggregate_roi(state)
        assert result["aggregated"]["investment_required"] == DEFAULT_IMPLEMENTATION_COST

    @pytest.mark.asyncio
    async def test_negative_investment_falls_back_to_default(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output(
            evaluate={"results": [{"result": 100_000, "confidence": 1.0}]},
            substitute_vars={"variables": {"implementation_cost": -100}},
        )
        result = await wf._execute_aggregate_roi(state)
        assert result["aggregated"]["investment_required"] == DEFAULT_IMPLEMENTATION_COST

    @pytest.mark.asyncio
    async def test_zero_annual_value_no_payback(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output(
            evaluate={"results": [{"result": 0, "confidence": 1.0}]},
            substitute_vars={"variables": {"implementation_cost": 100_000}},
        )
        result = await wf._execute_aggregate_roi(state)
        assert result["aggregated"]["payback_period_months"] is None

    @pytest.mark.asyncio
    async def test_uses_default_when_no_variables(self, workflow):
        wf, _ = workflow
        state = _make_state_with_output(
            evaluate={"results": [{"result": 500_000, "confidence": 1.0}]},
        )
        result = await wf._execute_aggregate_roi(state)
        assert result["aggregated"]["investment_required"] == DEFAULT_IMPLEMENTATION_COST


# ---------------------------------------------------------------------------
# Integration-style end-to-end
# ---------------------------------------------------------------------------
class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocked_tools(self, workflow):
        wf, registry = workflow
        state = wf.create_initial_state(
            {
                "prospect_id": "p-001",
                "value_driver_ids": ["vd-1"],
                "industry_vertical": "saas",
                "tenant_id": "t-1",
            },
            tenant_id="test-tenant",
        )

        async def side_effect(tool_name, params):
            if tool_name == "get_prospect_data":
                return _make_tool_result(
                    {
                        "profile": {"employees": 100, "industry": "saas", "annual_revenue": 1_000_000},
                        "custom_fields": {},
                    }
                )
            if tool_name == "compare_benchmarks":
                return _make_tool_result({"percentile": 50})
            if tool_name == "query_graph":
                if "benchmark" in params.get("cypher_query", "").lower():
                    return _make_tool_result({"results": [{"defaults": {}}]})
                return _make_tool_result(
                    {
                        "results": [
                            {
                                "id": "vd-1",
                                "name": "Test",
                                "category": "ops",
                                "formula": "annual_revenue * 0.05",
                                "unit": "USD",
                            }
                        ]
                    }
                )
            if tool_name == "evaluate_formula":
                return _make_tool_result(
                    {"success": True, "result": 50_000, "substituted_formula": "1000000 * 0.05"}
                )
            return _make_tool_result({})

        registry.execute.side_effect = side_effect

        # Run through each step manually to verify integration
        r1 = await wf._execute_get_prospect_data(state)
        state.output_data["load_prospect"] = r1

        r2 = await wf._execute_fetch_benchmarks(state)
        state.output_data["fetch_benchmarks"] = r2

        r3 = await wf._execute_substitute_variables(state)
        state.output_data["substitute_vars"] = r3

        r4 = await wf._execute_evaluate_formula(state)
        state.output_data["evaluate"] = r4

        r5 = await wf._execute_aggregate_roi(state)

        assert r5["error"] == ""
        assert r5["aggregated"]["total_annual_value"] == 50_000
        assert r5["aggregated"]["value_driver_count"] == 1
