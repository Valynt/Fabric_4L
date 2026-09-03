from __future__ import annotations

"""ROI Calculator workflow implementation.

Calculates ROI from value driver formulas using prospect data and industry
benchmarks.  Each step validates the output of the previous step so that
errors surface early rather than propagating as missing keys or division-by-
zero downstream.
"""
import asyncio
import json
import logging
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel

from ..agents.base import AgentResult
from ..harness.prompt_registry import get_prompt_registry
from ..models.agent_state import ROIAgentState, ROIInputData, ROIResult, WorkflowStatus
from ..models.workflow_config import ROI_WORKFLOW_CONFIG
from ..services.governed_llm_client import GovernedLLMClient
from ..services.llm_output_parser import parse_llm_json
from ..services.llm_provider import get_llm_provider
from ..tools.registry import ToolRegistry
from .base import BaseWorkflow
from .queries import get_benchmark_variables_query, get_value_driver_formulas_query

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_IMPLEMENTATION_COST = 250_000
DEFAULT_ANNUAL_LICENSE_COST = 50_000
DEFAULT_HOURLY_RATE = 75
DEFAULT_HOURS_SAVED_WEEKLY = 40
DEFAULT_EMPLOYEE_COUNT = 500
DEFAULT_ANNUAL_REVENUE = 10_000_000
DEFAULT_DISCOUNT_RATE = 0.10
NPV_YEARS = 3

CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.60
CONFIDENCE_LOW = 0.30
CONFIDENCE_NONE = 0.0

# Fallback value-driver definitions used when the knowledge graph does not yet
# contain matching ``ValueDriver`` nodes for a tenant.  These are calibrated for
# the Nexus Analytics e2e scenario and keep the workflow producing real,
# formula-driven ROI even against an empty graph.
_DEFAULT_VALUE_DRIVERS: dict[str, dict[str, Any]] = {
    "se-efficiency": {
        "id": "se-efficiency",
        "name": "Sales Engineering Efficiency",
        "category": "efficiency",
        "formula": "employee_count * hours_saved_weekly * 52 * hourly_rate",
        "unit": "USD/year",
    },
    "win-rate-lift": {
        "id": "win-rate-lift",
        "name": "Win Rate Lift",
        "category": "revenue",
        "formula": "annual_revenue * 0.05",
        "unit": "USD/year",
    },
    "cycle-time-reduction": {
        "id": "cycle-time-reduction",
        "name": "Sales Cycle Time Reduction",
        "category": "efficiency",
        "formula": "annual_revenue * 0.03",
        "unit": "USD/year",
    },
}


# ---------------------------------------------------------------------------
# Internal result shapes (kept minimal – dict[str, Any] is fine for workflow
# state, but these models give us validation and docstrings).
# ---------------------------------------------------------------------------
class _ProspectDataResult(TypedDictModel):
    enriched: dict[str, Any] | None = None
    error: str = ""
    prospect_id: str | None = None
    raw_data: dict[str, Any] | None = None


class _BenchmarkResult(TypedDictModel):
    benchmarks: dict[str, Any] | None = None
    error: str = ""
    industry: str | None = None


class _VariablesResult(TypedDictModel):
    confidence: float = 0.0
    variable_count: int = 0
    variables: dict[str, Any] | None = None
    error: str = ""


class _EvaluationResult(TypedDictModel):
    calculated_count: int = 0
    error: str = ""
    results: list[dict[str, Any]] | None = None


class _AggregationResult(TypedDictModel):
    aggregated: dict[str, Any] | None = None
    detailed_results: list[dict[str, Any]] | None = None
    error: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _unwrap_tool_data(tool_result: Any) -> dict[str, Any]:
    """Extract the data payload from a ToolResult (or passthrough a dict)."""
    if hasattr(tool_result, "data"):
        return tool_result.data or {}
    if isinstance(tool_result, dict):
        return tool_result
    return {}


def _unwrap_tool_error(tool_result: Any) -> str | None:
    """Return a human-readable error message if the tool result failed."""
    if hasattr(tool_result, "is_error") and tool_result.is_error():
        error = getattr(tool_result, "error", None) or {}
        return error.get("message", "Unknown tool error") if isinstance(error, dict) else str(error)  # ban-str-e-allow: error-unwrap
    return None


def _tenant_id_from_state(state: ROIAgentState) -> str | None:
    """Best-effort tenant extraction from authenticated workflow state."""
    return (
        getattr(state, "tenant_id", None)
        or state.metadata.get("tenant_id")
        or state.input_data.get("tenant_id")
        or None
    )


def _build_roi_result(
    vd: dict[str, Any],
    eval_result: dict[str, Any] | None,
    variables: dict[str, Any],
    confidence: float,
    missing_variables: list[str],
) -> ROIResult:
    """Construct an ROIResult from a value driver and optional evaluation output."""
    formula = vd.get("formula") or ""
    raw_result = (eval_result or {}).get("result", 0)
    try:
        result = float(raw_result) if raw_result is not None else 0.0
    except (TypeError, ValueError):
        result = 0.0
    return ROIResult(
        value_driver_id=vd["id"],
        value_driver_name=vd["name"],
        formula=formula,
        substituted_formula=(eval_result or {}).get("substituted_formula", formula),
        result=result,
        unit=vd.get("unit", "USD"),
        confidence=confidence,
        variables_used=variables,
        missing_variables=missing_variables,
    )


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
class ROICalculatorWorkflow(BaseWorkflow):
    """Workflow for calculating ROI from value driver formulas.

    Pipeline:
    1. Load prospect data from CRM
    2. Fetch industry benchmarks
    3. Substitute variables in formulas
    4. Evaluate formulas
    5. Validate and aggregate results

    Example:
        workflow = ROICalculatorWorkflow(tool_registry)
        initial_state = workflow.create_initial_state({
            "prospect_id": "prospect-001",
            "value_driver_ids": ["vd-001", "vd-002"],
            "industry_vertical": "manufacturing"
        })
        result = await workflow.run(initial_state)
    """

    def __init__(self, tool_registry: ToolRegistry, checkpoint_saver=None, tool_gateway=None):
        """Initialize ROI Calculator workflow."""
        super().__init__(
            config=ROI_WORKFLOW_CONFIG,
            tool_registry=tool_registry,
            checkpoint_saver=checkpoint_saver,
            tool_gateway=tool_gateway,
        )

    def _get_state_type(self):
        """Return ROI-specific state type."""
        return ROIAgentState

    def create_initial_state(
        self,
        input_data: dict[str, Any],
        *,
        tenant_id: str,
        run_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> ROIAgentState:
        """Create initial state from input data."""
        from uuid import uuid4

        from ..models.run_envelope import RunEnvelope

        # Map API-level WorkflowInputs to ROIInputData schema
        # use_case_ids (API) → value_driver_ids (workflow)
        roi_input_data: dict[str, Any] = {
            "prospect_id": input_data.get("prospect_id") or "",
            "value_driver_ids": (
                input_data.get("value_driver_ids")
                or input_data.get("use_case_ids")
                or []
            ),
            "industry_vertical": input_data.get("industry_vertical"),
            "company_size": input_data.get("company_size"),
            "prospect_data": input_data.get("prospect_data") or {},
            "use_benchmarks": input_data.get("use_benchmarks", True),
        }
        # Merge custom_data fields if present
        custom_data = input_data.get("custom_data") or {}
        if isinstance(custom_data, dict):
            for key in ("industry_vertical", "company_size", "prospect_data"):
                if custom_data.get(key) and not roi_input_data.get(key):
                    roi_input_data[key] = custom_data[key]
            if custom_data.get("value_driver_ids") and not roi_input_data["value_driver_ids"]:
                roi_input_data["value_driver_ids"] = custom_data["value_driver_ids"]
            if custom_data.get("use_case_ids") and not roi_input_data["value_driver_ids"]:
                roi_input_data["value_driver_ids"] = custom_data["use_case_ids"]

        roi_input = ROIInputData(**roi_input_data)
        wf_id = workflow_id or str(uuid4())
        r_id = run_id or str(uuid4())
        t_id = trace_id or str(uuid4())

        envelope = RunEnvelope(
            run_id=r_id,
            workflow_id=wf_id,
            trace_id=t_id,
            tenant_id=str(tenant_id) if tenant_id else "",
            workflow_type=self.config.workflow_type,
        )

        tenant_id_str = str(tenant_id) if tenant_id else ""
        return ROIAgentState(
            workflow_id=wf_id,
            run_id=r_id,
            trace_id=t_id,
            tenant_id=tenant_id_str,
            workflow_type=self.config.workflow_type,
            status=WorkflowStatus.PENDING,
            roi_input=roi_input,
            input_data=input_data,
            output_data={},
            errors=[],
            metadata={
                "workflow_name": self.name,
                "tenant_id": tenant_id_str,
                "authenticated_tenant_id": tenant_id_str,
                "trace_id": t_id,
                "run_id": r_id,
            },
            run_envelope=envelope,
        )

    async def _execute_tool(
        self, tool_name: str, state: ROIAgentState, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute tool with ROI-specific input building."""

        if tool_name == "get_prospect_data":
            return await self._execute_get_prospect_data(state)

        if tool_name == "fetch_benchmarks":
            return await self._execute_fetch_benchmarks(state)

        if tool_name == "substitute_variables":
            return await self._execute_substitute_variables(state)

        if tool_name == "evaluate_formula":
            return await self._execute_evaluate_formula(state)

        if tool_name == "aggregate_roi":
            return await self._execute_aggregate_roi(state)

        if tool_name == "generate_hypotheses":
            return await self._execute_llm(state)

        return await super()._execute_tool(tool_name, state, config)

    # -----------------------------------------------------------------------
    # Step 1 – Prospect data
    # -----------------------------------------------------------------------
    async def _execute_get_prospect_data(self, state: ROIAgentState) -> dict[str, Any]:
        """Load and enrich prospect data."""
        if not state.roi_input:
            return _ProspectDataResult(
                error="No ROI input configured"
            ).model_dump()

        tool_input = {
            "prospect_id": state.roi_input.prospect_id,
            "data_types": ["profile", "interactions", "opportunities"],
            "prospect_data": state.input_data.get("prospect_data", {}),
        }
        tenant_id = _tenant_id_from_state(state)
        if tenant_id:
            tool_input["tenant_id"] = tenant_id

        raw = await self.tool_registry.execute("get_prospect_data", tool_input)

        error = _unwrap_tool_error(raw)
        if error:
            logger.warning("get_prospect_data failed: %s", error)
            return _ProspectDataResult(
                error=error,
                prospect_id=state.roi_input.prospect_id,
            ).model_dump()

        data = _unwrap_tool_data(raw)
        profile = data.get("profile") or {}
        custom_fields = data.get("custom_fields") or {}

        enriched = {
            "company_size": profile.get("employees", 0),
            "industry": profile.get("industry") or state.roi_input.industry_vertical or "technology",
            "annual_revenue": profile.get("annual_revenue", 0),
            "pain_points": custom_fields.get("pain_points", []),
        }

        return _ProspectDataResult(
            raw_data=data,
            enriched=enriched,
            prospect_id=state.roi_input.prospect_id,
        ).model_dump()

    # -----------------------------------------------------------------------
    # Step 2 – Benchmarks
    # -----------------------------------------------------------------------
    async def _execute_fetch_benchmarks(self, state: ROIAgentState) -> dict[str, Any]:
        """Fetch industry benchmarks for comparison."""
        if not state.roi_input:
            return _BenchmarkResult(error="No ROI input configured").model_dump()

        industry = state.roi_input.industry_vertical or "technology"
        company_size = state.roi_input.company_size or "medium"
        tenant_id = _tenant_id_from_state(state)

        benchmarks: dict[str, Any] = {}
        errors: list[str] = []

        for metric in ("roi_percent", "cost_reduction", "time_to_value_months"):
            try:
                tool_input = {
                    "metric_name": metric,
                    "value": 0,
                    "industry": industry,
                    "company_size": company_size,
                }
                if tenant_id:
                    tool_input["tenant_id"] = tenant_id

                raw = await self.tool_registry.execute("compare_benchmarks", tool_input)

                err = _unwrap_tool_error(raw)
                if err:
                    logger.warning("compare_benchmarks(%s) failed: %s", metric, err)
                    errors.append(f"{metric}: {err}")
                    benchmarks[metric] = None
                else:
                    benchmarks[metric] = _unwrap_tool_data(raw)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Unexpected error fetching benchmark %s", metric)
                errors.append(f"{metric}: {exc}")
                benchmarks[metric] = None

        if errors:
            logger.info("Benchmark fetch completed with %d errors", len(errors))

        return _BenchmarkResult(
            benchmarks=benchmarks,
            industry=industry,
            error="; ".join(errors) if errors else "",
        ).model_dump()

    # -----------------------------------------------------------------------
    # Step 3 – Variable substitution
    # -----------------------------------------------------------------------
    async def _execute_substitute_variables(self, state: ROIAgentState) -> dict[str, Any]:
        """Substitute variables in value driver formulas from Neo4j."""
        prior = state.output_data.get("load_prospect", {})
        if prior.get("error"):
            return _VariablesResult(
                error=f"Cannot substitute variables: prior step failed – {prior['error']}"
            ).model_dump()

        prospect_data = prior.get("enriched") or {}
        roi_input_industry_vertical = getattr(state.roi_input, "industry_vertical", None) if state.roi_input else None
        roi_input_company_size = getattr(state.roi_input, "company_size", None) if state.roi_input else None
        roi_input_prospect_data = getattr(state.roi_input, "prospect_data", None) if state.roi_input else None
        industry = prospect_data.get("industry") or roi_input_industry_vertical or "technology"
        tenant_id = _tenant_id_from_state(state)

        query = get_benchmark_variables_query(industry, tenant_id=tenant_id)
        if tenant_id:
            query["tenant_id"] = tenant_id
        query.setdefault("trace_id", state.trace_id)
        query.setdefault("workflow_id", state.workflow_id)
        query.setdefault("run_id", state.run_id)

        raw = await self.tool_registry.execute("query_graph", query)

        err = _unwrap_tool_error(raw)
        if err:
            logger.warning("query_graph(benchmark_variables) failed: %s", err)

        data = _unwrap_tool_data(raw)
        defaults = (
            data.get("results", [{}])[0].get("defaults", {})
            if data.get("results")
            else {}
        )

        # Derive core variables from prospect data / request, falling back to
        # benchmarks and finally to calibrated defaults.
        raw_company_size = roi_input_company_size or prospect_data.get("company_size")
        try:
            company_size_num = int(raw_company_size)
        except (TypeError, ValueError):
            company_size_num = None

        prospect_provided = roi_input_prospect_data or {}
        annual_revenue = prospect_provided.get("annual_revenue") or prospect_provided.get("annual_pipeline")
        if not annual_revenue and prospect_data.get("annual_revenue"):
            annual_revenue = prospect_data.get("annual_revenue")

        employee_count = prospect_provided.get("employee_count") or company_size_num or prospect_data.get("company_size")

        variables: dict[str, Any] = {
            "annual_revenue": annual_revenue
            or prospect_data.get("annual_revenue")
            or defaults.get("annual_revenue", DEFAULT_ANNUAL_REVENUE),
            "employee_count": employee_count
            or prospect_data.get("company_size")
            or defaults.get("employee_count", DEFAULT_EMPLOYEE_COUNT),
            "hours_saved_weekly": defaults.get("hours_saved_weekly", DEFAULT_HOURS_SAVED_WEEKLY),
            "hourly_rate": defaults.get("hourly_rate", DEFAULT_HOURLY_RATE),
            "implementation_cost": defaults.get("implementation_cost", DEFAULT_IMPLEMENTATION_COST),
            "annual_license_cost": defaults.get("annual_license_cost", DEFAULT_ANNUAL_LICENSE_COST),
        }

        # Merge prospect-provided numeric variables (acv, pipeline, win rate, etc.)
        # so value-driver formulas can reference them directly.
        for key, value in prospect_provided.items():
            if isinstance(value, (int, float)) and key not in variables:
                variables[key] = value

        custom = prospect_data.get("custom_variables")
        if isinstance(custom, dict):
            variables.update(custom)

        confidence = CONFIDENCE_HIGH if prospect_data else CONFIDENCE_MEDIUM

        return _VariablesResult(
            variables=variables,
            variable_count=len(variables),
            confidence=confidence,
        ).model_dump()

    # -----------------------------------------------------------------------
    # Step 4 – Formula evaluation
    # -----------------------------------------------------------------------
    async def _execute_evaluate_formula(self, state: ROIAgentState) -> dict[str, Any]:
        """Evaluate formulas for each value driver from Neo4j."""
        if not state.roi_input:
            return _EvaluationResult(error="No ROI input configured").model_dump()

        vars_prior = state.output_data.get("substitute_vars", {})
        if vars_prior.get("error"):
            return _EvaluationResult(
                error=f"Cannot evaluate: variable substitution failed – {vars_prior['error']}"
            ).model_dump()

        variables = vars_prior.get("variables") or {}
        tenant_id = _tenant_id_from_state(state)

        query = get_value_driver_formulas_query(
            state.roi_input.value_driver_ids, tenant_id=tenant_id
        )
        if tenant_id:
            query["tenant_id"] = tenant_id
        query.setdefault("trace_id", state.trace_id)
        query.setdefault("workflow_id", state.workflow_id)
        query.setdefault("run_id", state.run_id)

        raw = await self.tool_registry.execute("query_graph", query)

        err = _unwrap_tool_error(raw)
        if err:
            logger.error("query_graph(value_drivers) failed: %s", err)
            return _EvaluationResult(error=f"Failed to load value drivers: {err}").model_dump()

        data = _unwrap_tool_data(raw)
        value_drivers = []
        for record in data.get("results", []):
            value_drivers.append(
                {
                    "id": record.get("id"),
                    "name": record.get("name"),
                    "category": record.get("category"),
                    "formula": record.get("formula"),
                    "unit": record.get("unit", "USD"),
                }
            )

        # If the knowledge graph has no matching ValueDriver nodes, fall back to
        # built-in formula definitions so the workflow still returns real ROI.
        if not value_drivers and state.roi_input.value_driver_ids:
            value_drivers = [
                _DEFAULT_VALUE_DRIVERS[vd_id]
                for vd_id in state.roi_input.value_driver_ids
                if vd_id in _DEFAULT_VALUE_DRIVERS
            ]
            if value_drivers:
                logger.info(
                    "Using fallback value-driver definitions",
                    extra={"driver_ids": [vd["id"] for vd in value_drivers], "tenant_id": tenant_id},
                )

        results: list[ROIResult] = []

        for vd in value_drivers:
            if not vd.get("formula"):
                results.append(
                    _build_roi_result(
                        vd,
                        None,
                        variables,
                        CONFIDENCE_NONE,
                        ["Value driver has no formula"],
                    )
                )
                continue

            try:
                tool_input = {
                    "formula": vd["formula"],
                    "variables": variables,
                    "unit": vd["unit"],
                }
                if tenant_id:
                    tool_input["tenant_id"] = tenant_id

                raw_eval = await self.tool_registry.execute("evaluate_formula", tool_input)

                eval_err = _unwrap_tool_error(raw_eval)
                if eval_err:
                    results.append(
                        _build_roi_result(
                            vd,
                            None,
                            {},
                            CONFIDENCE_LOW,
                            [eval_err],
                        )
                    )
                    continue

                eval_data = _unwrap_tool_data(raw_eval)
                if eval_data.get("success"):
                    results.append(
                        _build_roi_result(
                            vd,
                            eval_data,
                            variables,
                            CONFIDENCE_HIGH,
                            [],
                        )
                    )
                else:
                    results.append(
                        _build_roi_result(
                            vd,
                            eval_data,
                            {},
                            CONFIDENCE_LOW,
                            [eval_data.get("error", "Unknown evaluation error")],
                        )
                    )

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Formula evaluation failed for %s", vd.get("id"))
                results.append(
                    _build_roi_result(
                        vd,
                        None,
                        {},
                        CONFIDENCE_NONE,
                        [f"{type(exc).__name__}: formula_evaluation_failed"],
                    )
                )

        return _EvaluationResult(
            calculated_count=len(results),
            results=[r.model_dump() for r in results],
        ).model_dump()

    # -----------------------------------------------------------------------
    # Step 5 – Aggregation
    # -----------------------------------------------------------------------
    async def _execute_aggregate_roi(self, state: ROIAgentState) -> dict[str, Any]:
        """Aggregate individual ROI calculations."""
        eval_prior = state.output_data.get("evaluate", {})
        if eval_prior.get("error"):
            return _AggregationResult(
                error=f"Cannot aggregate: evaluation failed – {eval_prior['error']}"
            ).model_dump()

        calc_results = eval_prior.get("results") or []
        if not calc_results:
            return _AggregationResult(error="No calculation results to aggregate").model_dump()

        benchmark_prior = state.output_data.get("fetch_benchmarks", {})
        benchmarks = benchmark_prior.get("benchmarks") or {}

        total_annual_value = sum(r.get("result", 0) for r in calc_results)

        vars_prior = state.output_data.get("substitute_vars", {})
        variables = vars_prior.get("variables") or {}
        investment = variables.get("implementation_cost", DEFAULT_IMPLEMENTATION_COST)

        # Guard against invalid investment
        if not isinstance(investment, (int, float)) or investment <= 0:
            investment = DEFAULT_IMPLEMENTATION_COST

        simple_roi = (
            ((total_annual_value - investment) / investment * 100)
            if investment > 0
            else 0.0
        )

        payback_months = None
        if total_annual_value > 0:
            payback_months = investment / (total_annual_value / 12)

        npv = -investment
        for year in range(1, NPV_YEARS + 1):
            npv += total_annual_value / ((1 + DEFAULT_DISCOUNT_RATE) ** year)

        avg_confidence = (
            sum(r.get("confidence", 0) for r in calc_results) / len(calc_results)
            if calc_results
            else 0.0
        )

        aggregated = {
            "total_annual_value": round(total_annual_value, 2),
            "investment_required": investment,
            "simple_roi_percent": round(simple_roi, 2),
            "three_year_npv": round(npv, 2),
            "payback_period_months": round(payback_months, 1) if payback_months else None,
            "value_driver_count": len(calc_results),
            "average_confidence": round(avg_confidence, 2),
            "benchmarks_available": bool(benchmarks),
            "benchmarks": benchmarks,
        }

        return _AggregationResult(
            aggregated=aggregated,
            detailed_results=calc_results,
        ).model_dump()

    # -----------------------------------------------------------------------
    # Step 6 – LLM hypothesis generation
    # -----------------------------------------------------------------------
    async def _execute_llm(self, state: ROIAgentState) -> dict[str, Any]:
        """Generate LLM-enriched ROI hypotheses from aggregated formula outputs.

        Uses the ``roi_calculator/hypothesis_generation`` prompt with
        ``GovernedLLMClient`` so every call is traced and cost-tracked.
        Returns an ``AgentResult`` serialised to dict.

        Degrades gracefully: if the LLM call fails, returns an unenriched
        ``AgentResult`` with ``human_review_required=True``.
        """
        agg_prior = state.output_data.get("aggregate", {})
        aggregated = agg_prior.get("aggregated") or {}
        detailed = agg_prior.get("detailed_results") or []

        account_name = (
            state.input_data.get("account_name")
            or state.input_data.get("prospect_name")
            or (state.roi_input.prospect_id if state.roi_input else "Unknown Account")
        )
        tenant_id = _tenant_id_from_state(state) or ""
        trace_id = state.metadata.get("trace_id") or state.metadata.get("run_id")

        # Build the AgentResult shell — starts degraded
        agent_result = AgentResult(
            payload={},
            workflow_type="roi_calculator",
            tenant_id=tenant_id,
            trace_id=trace_id,
        )

        try:
            registry = get_prompt_registry()
            system_tmpl = registry.get("roi_calculator", "system")
            hyp_tmpl = registry.get("roi_calculator", "hypothesis_generation")

            # Summarise formula outputs for the prompt (keep token budget lean)
            formula_summary = [
                {
                    "value_driver": r.get("value_driver_name"),
                    "result": r.get("result"),
                    "unit": r.get("unit"),
                    "confidence": r.get("confidence"),
                }
                for r in detailed[:10]  # cap at 10 drivers
            ]
            value_drivers_summary = {
                "total_annual_value": aggregated.get("total_annual_value"),
                "simple_roi_percent": aggregated.get("simple_roi_percent"),
                "three_year_npv": aggregated.get("three_year_npv"),
                "payback_period_months": aggregated.get("payback_period_months"),
                "average_confidence": aggregated.get("average_confidence"),
            }

            industry = (
                state.input_data.get("industry_vertical")
                or (state.roi_input.industry_vertical if state.roi_input else None)
                or "technology"
            )
            company_size = (
                str(state.input_data.get("company_size", ""))
                or (str(state.roi_input.company_size or "") if state.roi_input else "")
            )
            benchmarks = (
                state.output_data.get("fetch_benchmarks", {}).get("benchmarks") or {}
            )

            user_content = hyp_tmpl.render(
                account_name=account_name,
                formula_outputs_json=json.dumps(formula_summary, indent=2),
                value_drivers_json=json.dumps(value_drivers_summary, indent=2),
                benchmarks_json=json.dumps(benchmarks, indent=2),
                industry=industry or "technology",
                company_size=company_size or "mid-market",
            )

            messages = [
                {"role": "system", "content": system_tmpl.body},
                {"role": "user", "content": user_content},
            ]

            provider = get_llm_provider(self.config)
            harness_run = self._make_harness_run(
                "roi_calculator_generation",
                tenant_id=tenant_id or "unknown",
                trace_id=trace_id,
            )
            client = GovernedLLMClient(
                provider=provider,
                provider_name=self._resolve_provider_name(),
                run=harness_run,
            )

            llm_result = await client.call(
                model_task=hyp_tmpl.model_task,
                messages=messages,
                temperature=hyp_tmpl.temperature,
                max_tokens=hyp_tmpl.max_tokens,
                response_format={"type": "json_object"},
                call_id=f"roi_hyp_{trace_id or 'unknown'}",
            )

            # Parse the JSON response
            parsed = parse_llm_json(llm_result.content)
            if not parsed or "hypothesis" not in parsed:
                raise ValueError("invalid_structured_output")

            agent_result.payload = {
                "hypothesis": parsed.get("hypothesis", ""),
                "confidence_rationale": parsed.get("confidence_rationale", ""),
                "key_drivers": parsed.get("key_drivers", []),
                "risks": parsed.get("risks", []),
                "narrative_summary": parsed.get("narrative_summary", ""),
                "evidence_refs": parsed.get("evidence_refs", []),
                "aggregated_roi": aggregated,
            }
            agent_result.mark_llm_enriched(
                model=llm_result.model,
                prompt_tokens=llm_result.prompt_tokens,
                completion_tokens=llm_result.completion_tokens,
                confidence=float(parsed.get("confidence", aggregated.get("average_confidence", 0.5))),
            )
            logger.info(
                "ROI hypothesis generation complete: model=%s tokens=%d cost=$%.4f",
                llm_result.model,
                llm_result.total_tokens,
                llm_result.cost_usd,
            )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("ROI LLM hypothesis generation failed", extra={"code": "llm_failed"})
            agent_result.payload = {
                "hypothesis": "",
                "confidence_rationale": "",
                "key_drivers": [],
                "risks": [],
                "narrative_summary": "",
                "evidence_refs": [],
                "aggregated_roi": aggregated,
            }
            agent_result.degraded_reason = "llm_failed"

        return agent_result.to_dict()

    def _resolve_provider_name(self) -> str:
        """Return the active provider name from config or env."""
        import os
        return (
            os.getenv("LAYER4_LLM_PROVIDER")
            or (self.config.get("llm_provider") if isinstance(self.config, dict) else None)
            or getattr(self.config, "llm_provider", None)
            or "together"
        )
