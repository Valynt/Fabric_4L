from __future__ import annotations

"""
ROI Calculator Service — Data Intelligence Layer Phase 2, Task 2.3.

Calculates ROI projections using formulas from the knowledge graph,
account-specific inputs, and industry benchmarks. Provides:
  - Template-based ROI calculations with customizable inputs
  - Multi-scenario comparison (conservative / moderate / aggressive)
  - NPV, payback period, and IRR calculations
  - Industry benchmark integration for default assumptions
  - Calculation persistence and history tracking

Architecture:
  - ROI templates are stored as ROITemplate nodes in Neo4j
  - Completed calculations are stored as ROICalculation nodes
  - Templates link to Products and Industries via relationships
  - The service uses pure financial math (no external dependencies)
  - Calculations are tenant-scoped and optionally account-scoped

Neo4j Node Schema:
  ROITemplate:
    id, tenant_id, name, description, category,
    input_schema (JSON string of required inputs),
    default_assumptions (JSON string),
    applicable_industries (list), applicable_products (list),
    created_at, updated_at

  ROICalculation:
    id, tenant_id, account_id, template_id, template_name,
    inputs (JSON string), outputs (JSON string),
    assumptions (JSON string), scenario_name,
    time_horizon_months, discount_rate,
    created_at
"""


import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from neo4j import AsyncDriver
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..db.audited_mutation import AuditedGraphMutation
from ..db.query_execution import run_validated_query
from .cypher_scope_guard import validate_tenant_scoped_cypher


class ROICalculatorService_compare_scenariosResult(TypedDictModel):
    discount_rate: Any
    scenarios: Any
    time_horizon_months: Any

class ROICalculatorService_create_templateResult(TypedDictModel):
    id: Any

class ROICalculatorService_get_templatesResult(TypedDictModel):
    limit: Any
    skip: Any
    templates: Any
    total: Any

class ROICalculatorService_save_calculationResult(TypedDictModel):
    id: Any

class ROICalculatorService_list_calculationsResult(TypedDictModel):
    calculations: Any
    limit: Any
    skip: Any
    total: Any

class ROICalculatorService_get_industry_benchmarksResult(TypedDictModel):
    avg_deal_size: Any | None = None
    avg_time_to_value_days: Any | None = None
    case_count: Any | None = None
    company_sizes: Any | None = None
    defaults: dict[str, Any]
    has_benchmarks: bool
    industry: Any
    message: str

try:
    from value_fabric.shared.identity.context import require_context
except ImportError:
    require_context = None

logger = structlog.get_logger()


def _get_tenant_id() -> str:
    """Safely retrieve tenant ID from request context.

    Returns "default" if context is not available (e.g., in tests or background tasks).
    """
    if not require_context:
        return "default"
    try:
        return str(require_context().tenant_id)
    except RuntimeError:
        return "default"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class ROIInputs:
    """Standard ROI calculation inputs."""

    annual_revenue: float = 0.0
    num_employees: int = 0
    avg_salary: float = 75000.0
    current_cost_annual: float = 0.0
    implementation_cost: float = 0.0
    annual_license_cost: float = 0.0
    training_cost: float = 0.0
    productivity_gain_pct: float = 0.10
    error_reduction_pct: float = 0.20
    time_savings_hours_per_week: float = 5.0
    affected_employees_pct: float = 0.25
    custom_inputs: dict[str, float] = field(default_factory=dict)


@dataclass
class ROIOutputs:
    """Calculated ROI results."""

    total_benefit_year1: float = 0.0
    total_benefit_3year: float = 0.0
    total_cost_year1: float = 0.0
    total_cost_3year: float = 0.0
    net_benefit_year1: float = 0.0
    net_benefit_3year: float = 0.0
    roi_pct_year1: float = 0.0
    roi_pct_3year: float = 0.0
    payback_months: float = 0.0
    npv: float = 0.0
    irr: float | None = None
    benefit_breakdown: dict[str, float] = field(default_factory=dict)
    cost_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class ROITemplateCreate:
    """Input for creating an ROI template."""

    name: str
    description: str
    category: str = "general"
    input_schema: dict[str, Any] = field(default_factory=dict)
    default_assumptions: dict[str, float] = field(default_factory=dict)
    applicable_industries: list[str] = field(default_factory=list)
    applicable_products: list[str] = field(default_factory=list)


@dataclass
class ScenarioConfig:
    """Configuration for a scenario multiplier."""

    name: str
    benefit_multiplier: float = 1.0
    cost_multiplier: float = 1.0
    description: str = ""


# Standard scenario configurations
STANDARD_SCENARIOS: dict[str, ScenarioConfig] = {
    "conservative": ScenarioConfig(
        name="Conservative",
        benefit_multiplier=0.7,
        cost_multiplier=1.15,
        description="Lower benefits, higher costs — risk-adjusted baseline",
    ),
    "moderate": ScenarioConfig(
        name="Moderate",
        benefit_multiplier=1.0,
        cost_multiplier=1.0,
        description="Expected case based on typical customer outcomes",
    ),
    "aggressive": ScenarioConfig(
        name="Aggressive",
        benefit_multiplier=1.3,
        cost_multiplier=0.9,
        description="Best-case scenario with optimistic assumptions",
    ),
}


# ---------------------------------------------------------------------------
# ROI Calculator Service
# ---------------------------------------------------------------------------


class ROICalculatorService:
    """Service for calculating and managing ROI projections."""

    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    # ------------------------------------------------------------------
    # Core Calculation Engine
    # ------------------------------------------------------------------

    def calculate_roi(
        self,
        inputs: ROIInputs,
        *,
        time_horizon_months: int = 36,
        discount_rate: float = 0.10,
        scenario: str = "moderate",
    ) -> ROIOutputs:
        """Calculate ROI from inputs using standard financial formulas.

        Benefits are computed from:
          1. Productivity gains: affected_employees * salary * productivity_gain_pct
          2. Error reduction savings: current_cost * error_reduction_pct
          3. Time savings: affected_employees * time_savings * hourly_rate * 52
          4. Custom benefit inputs

        Costs include:
          1. Implementation (one-time, year 1)
          2. Annual license
          3. Training (one-time, year 1)
        """
        sc = STANDARD_SCENARIOS.get(scenario, STANDARD_SCENARIOS["moderate"])
        years = time_horizon_months / 12.0

        # --- Benefits ---
        affected_employees = inputs.num_employees * inputs.affected_employees_pct
        hourly_rate = inputs.avg_salary / 2080  # Standard work hours per year

        productivity_benefit = (
            affected_employees * inputs.avg_salary * inputs.productivity_gain_pct
        )
        error_reduction_benefit = (
            inputs.current_cost_annual * inputs.error_reduction_pct
        )
        time_savings_benefit = (
            affected_employees * inputs.time_savings_hours_per_week * hourly_rate * 52
        )

        # Apply scenario multiplier
        annual_benefit = (
            productivity_benefit + error_reduction_benefit + time_savings_benefit
        ) * sc.benefit_multiplier

        # Add custom benefits
        custom_benefit = sum(inputs.custom_inputs.values()) * sc.benefit_multiplier
        annual_benefit += custom_benefit

        # --- Costs ---
        year1_cost = (
            inputs.implementation_cost + inputs.annual_license_cost + inputs.training_cost
        ) * sc.cost_multiplier
        annual_recurring_cost = inputs.annual_license_cost * sc.cost_multiplier

        # --- Multi-year projections ---
        total_benefit_year1 = annual_benefit
        total_cost_year1 = year1_cost

        total_benefit_3year = annual_benefit * years
        total_cost_3year = year1_cost + annual_recurring_cost * max(years - 1, 0)

        net_benefit_year1 = total_benefit_year1 - total_cost_year1
        net_benefit_3year = total_benefit_3year - total_cost_3year

        roi_pct_year1 = (
            (net_benefit_year1 / total_cost_year1 * 100)
            if total_cost_year1 > 0
            else 0.0
        )
        roi_pct_3year = (
            (net_benefit_3year / total_cost_3year * 100)
            if total_cost_3year > 0
            else 0.0
        )

        # Payback period (months)
        monthly_net = (annual_benefit - annual_recurring_cost) / 12
        payback_months = (
            year1_cost / monthly_net if monthly_net > 0 else float("inf")
        )

        # NPV calculation
        npv = self._calculate_npv(
            initial_investment=year1_cost - inputs.annual_license_cost * sc.cost_multiplier,
            annual_cash_flows=[annual_benefit - annual_recurring_cost] * int(math.ceil(years)),
            discount_rate=discount_rate,
        )

        # IRR calculation
        cash_flows = [-year1_cost] + [
            annual_benefit - annual_recurring_cost
        ] * int(math.ceil(years))
        irr = self._calculate_irr(cash_flows)

        return ROIOutputs(
            total_benefit_year1=round(total_benefit_year1, 2),
            total_benefit_3year=round(total_benefit_3year, 2),
            total_cost_year1=round(total_cost_year1, 2),
            total_cost_3year=round(total_cost_3year, 2),
            net_benefit_year1=round(net_benefit_year1, 2),
            net_benefit_3year=round(net_benefit_3year, 2),
            roi_pct_year1=round(roi_pct_year1, 2),
            roi_pct_3year=round(roi_pct_3year, 2),
            payback_months=round(min(payback_months, 999), 1),
            npv=round(npv, 2),
            irr=round(irr, 4) if irr is not None else None,
            benefit_breakdown={
                "productivity_gains": round(productivity_benefit * sc.benefit_multiplier, 2),
                "error_reduction": round(error_reduction_benefit * sc.benefit_multiplier, 2),
                "time_savings": round(time_savings_benefit * sc.benefit_multiplier, 2),
                "custom_benefits": round(custom_benefit, 2),
            },
            cost_breakdown={
                "implementation": round(inputs.implementation_cost * sc.cost_multiplier, 2),
                "annual_license": round(inputs.annual_license_cost * sc.cost_multiplier, 2),
                "training": round(inputs.training_cost * sc.cost_multiplier, 2),
            },
        )

    def compare_scenarios(
        self,
        inputs: ROIInputs,
        *,
        scenarios: list[str] | None = None,
        time_horizon_months: int = 36,
        discount_rate: float = 0.10,
    ) -> dict[str, Any]:
        """Run the same inputs through multiple scenarios for comparison."""
        if scenarios is None:
            scenarios = ["conservative", "moderate", "aggressive"]

        results = {}
        for scenario_name in scenarios:
            result = self.calculate_roi(
                inputs,
                time_horizon_months=time_horizon_months,
                discount_rate=discount_rate,
                scenario=scenario_name,
            )
            sc = STANDARD_SCENARIOS.get(scenario_name, STANDARD_SCENARIOS["moderate"])
            results[scenario_name] = {
                "scenario_name": sc.name,
                "description": sc.description,
                "roi_pct_3year": result.roi_pct_3year,
                "net_benefit_3year": result.net_benefit_3year,
                "payback_months": result.payback_months,
                "npv": result.npv,
                "total_benefit_3year": result.total_benefit_3year,
                "total_cost_3year": result.total_cost_3year,
            }

        return ROICalculatorService_compare_scenariosResult.model_validate({
            "scenarios": results,
            "time_horizon_months": time_horizon_months,
            "discount_rate": discount_rate,
        })


    # ------------------------------------------------------------------
    # Financial Math Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_npv(
        initial_investment: float,
        annual_cash_flows: list[float],
        discount_rate: float,
    ) -> float:
        """Calculate Net Present Value."""
        npv = -initial_investment
        for year, cf in enumerate(annual_cash_flows, start=1):
            npv += cf / ((1 + discount_rate) ** year)
        return npv

    @staticmethod
    def _calculate_irr(
        cash_flows: list[float],
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> float | None:
        """Calculate Internal Rate of Return using Newton's method."""
        if not cash_flows or len(cash_flows) < 2:
            return None

        # Initial guess
        rate = 0.10

        for _ in range(max_iterations):
            npv = sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cash_flows))
            # Derivative of NPV with respect to rate
            dnpv = sum(
                -t * cf / ((1 + rate) ** (t + 1))
                for t, cf in enumerate(cash_flows)
                if t > 0
            )

            if abs(dnpv) < 1e-12:
                return None

            new_rate = rate - npv / dnpv

            if abs(new_rate - rate) < tolerance:
                return new_rate

            rate = new_rate

            # Guard against divergence
            if rate < -0.99 or rate > 10.0:
                return None

        return None

    # ------------------------------------------------------------------
    # Template Management (Neo4j)
    # ------------------------------------------------------------------

    async def create_template(
        self, template: ROITemplateCreate
    ) -> dict[str, Any]:
        """Create an ROI calculation template using current tenant context."""
        tenant_id = _get_tenant_id()
        template_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        template_props = {
            "id": template_id,
            "tenant_id": tenant_id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "input_schema": json.dumps(template.input_schema),
            "default_assumptions": json.dumps(template.default_assumptions),
            "applicable_industries": template.applicable_industries,
            "applicable_products": template.applicable_products,
            "entity_type": "ROITemplate",
            "created_at": now,
            "updated_at": now,
        }
        async with self._driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="roi_calculator_service.create_template",
            )
            await mutation.write_node("ROITemplate", template_id, template_props)

        logger.info("roi_template_created", template_id=template_id, name=template.name)
        return ROICalculatorService_create_templateResult.model_validate(template_props)

    async def create_template_for_tenant(
        self, tenant_id: str, template: ROITemplateCreate
    ) -> dict[str, Any]:
        """Create an ROI calculation template for an explicit tenant."""
        template_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        template_props = {
            "id": template_id,
            "tenant_id": str(tenant_id),
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "input_schema": json.dumps(template.input_schema),
            "default_assumptions": json.dumps(template.default_assumptions),
            "applicable_industries": template.applicable_industries,
            "applicable_products": template.applicable_products,
            "entity_type": "ROITemplate",
            "created_at": now,
            "updated_at": now,
        }
        async with self._driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=str(tenant_id),
                session=session,
                operation_source="roi_calculator_service.create_template_for_tenant",
            )
            await mutation.write_node("ROITemplate", template_id, template_props)

        logger.info("roi_template_created", template_id=template_id, name=template.name, tenant_id=tenant_id)
        return ROICalculatorService_create_templateResult.model_validate(template_props)

    async def get_templates(
        self,
        tenant_id: str | None = None,
        *,
        category: str | None = None,
        industry: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List ROI templates with optional filtering."""
        tenant_id = tenant_id or _get_tenant_id()
        where_clauses = ["t.tenant_id = $tenant_id"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "skip": skip,
            "limit": limit,
        }

        if category:
            where_clauses.append("t.category = $category")
            params["category"] = category

        if industry:
            where_clauses.append("$industry IN t.applicable_industries")
            params["industry"] = industry

        where = " AND ".join(where_clauses)

        query = f"""
        MATCH (t:ROITemplate) WHERE {where}
        RETURN t {{.*}} AS template
        ORDER BY t.name
        SKIP $skip LIMIT $limit
        """
        count_query = f"MATCH (t:ROITemplate) WHERE {where} RETURN count(t) AS total"

        validate_tenant_scoped_cypher(query)
        validate_tenant_scoped_cypher(count_query)

        async with self._driver.session() as session:
            # strict-scoped-query-execution: dynamic query parameters include tenant_id
            count_result = await run_validated_query(
                session,
                count_query,
                params,
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="roi_calculator_service.get_templates.count",
            )
            count_record = await count_result.single()
            total = count_record["total"] if count_record else 0

            # strict-scoped-query-execution: dynamic query parameters include tenant_id
            list_result = await run_validated_query(
                session,
                query,
                params,
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="roi_calculator_service.get_templates",
            )
            records = [record async for record in list_result]

        return ROICalculatorService_get_templatesResult.model_validate({
            "templates": [r["template"] for r in records],
            "total": total,
            "skip": skip,
            "limit": limit,
        })


    # ------------------------------------------------------------------
    # Calculation Persistence
    # ------------------------------------------------------------------

    async def save_calculation(
        self,
        tenant_id: str | None = None,
        *,
        account_id: str | None = None,
        template_id: str | None = None,
        template_name: str = "Custom",
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        assumptions: dict[str, Any] | None = None,
        scenario_name: str = "moderate",
        time_horizon_months: int = 36,
        discount_rate: float = 0.10,
    ) -> dict[str, Any]:
        """Persist an ROI calculation to Neo4j."""
        tenant_id = tenant_id or _get_tenant_id()
        calc_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        calculation_props = {
            "id": calc_id,
            "tenant_id": tenant_id,
            "account_id": account_id or "",
            "template_id": template_id or "",
            "template_name": template_name,
            "inputs": json.dumps(inputs),
            "outputs": json.dumps(outputs),
            "assumptions": json.dumps(assumptions or {}),
            "scenario_name": scenario_name,
            "time_horizon_months": time_horizon_months,
            "discount_rate": discount_rate,
            "entity_type": "ROICalculation",
            "created_at": now,
        }
        async with self._driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="roi_calculator_service.save_calculation",
            )
            await mutation.write_node("ROICalculation", calc_id, calculation_props)

        logger.info("roi_calculation_saved", calc_id=calc_id, scenario=scenario_name)
        return ROICalculatorService_save_calculationResult.model_validate(calculation_props)

    async def get_calculation(
        self, tenant_or_calc_id: str, calc_id: str | None = None
    ) -> dict[str, Any] | None:
        """Retrieve a saved ROI calculation."""
        if calc_id is None:
            calc_id = tenant_or_calc_id
            tenant_id = _get_tenant_id()
        else:
            tenant_id = str(tenant_or_calc_id)
        query = """
        MATCH (rc:ROICalculation {id: $calc_id, tenant_id: $tenant_id})
        RETURN rc {.*} AS calculation
        """
        async with self._driver.session() as session:
            result = await run_validated_query(
                session,
                query,
                {
                    "calc_id": calc_id,
                    "tenant_id": tenant_id,
                },
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="roi_calculator_service.get_calculation",
            )
            record = await result.single()

        if not record or not record["calculation"]:
            return None

        calc = record["calculation"]
        # Deserialize JSON strings
        for json_field in ("inputs", "outputs", "assumptions"):
            if isinstance(calc.get(json_field), str):
                try:
                    calc[json_field] = json.loads(calc[json_field])
                except (json.JSONDecodeError, TypeError):
                    pass

        return calc

    async def list_calculations(
        self,
        *,
        account_id: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List saved ROI calculations."""
        tenant_id = _get_tenant_id()
        where_clauses = ["rc.tenant_id = $tenant_id"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "skip": skip,
            "limit": limit,
        }

        if account_id:
            where_clauses.append("rc.account_id = $account_id")
            params["account_id"] = account_id

        where = " AND ".join(where_clauses)

        query = f"""
        MATCH (rc:ROICalculation) WHERE {where}
        RETURN rc {{.*}} AS calculation
        ORDER BY rc.created_at DESC
        SKIP $skip LIMIT $limit
        """
        count_query = f"MATCH (rc:ROICalculation) WHERE {where} RETURN count(rc) AS total"

        validate_tenant_scoped_cypher(query)
        validate_tenant_scoped_cypher(count_query)

        async with self._driver.session() as session:
            # strict-scoped-query-execution: dynamic query parameters include tenant_id
            count_result = await run_validated_query(
                session,
                count_query,
                params,
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="roi_calculator_service.list_calculations.count",
            )
            count_record = await count_result.single()
            total = count_record["total"] if count_record else 0

            # strict-scoped-query-execution: dynamic query parameters include tenant_id
            list_result = await run_validated_query(
                session,
                query,
                params,
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="roi_calculator_service.list_calculations",
            )
            records = [record async for record in list_result]

        calculations = []
        for r in records:
            calc = r["calculation"]
            for json_field in ("inputs", "outputs", "assumptions"):
                if isinstance(calc.get(json_field), str):
                    try:
                        calc[json_field] = json.loads(calc[json_field])
                    except (json.JSONDecodeError, TypeError):
                        pass
            calculations.append(calc)

        return ROICalculatorService_list_calculationsResult.model_validate({
            "calculations": calculations,
            "total": total,
            "skip": skip,
            "limit": limit,
        })


    # ------------------------------------------------------------------
    # Industry Benchmarks
    # ------------------------------------------------------------------

    async def get_industry_benchmarks(
        self, tenant_or_industry: str, industry: str | None = None
    ) -> dict[str, Any]:
        """Get industry-specific benchmarks for ROI assumptions.

        Retrieves industry benchmarks from case study evidence in the
        knowledge graph for the specified industry.
        """
        if industry is None:
            industry = tenant_or_industry
            tenant_id = _get_tenant_id()
        else:
            tenant_id = str(tenant_or_industry)
        query = """
        MATCH (e:Evidence {tenant_id: $tenant_id, evidence_type: 'case_study'})
        WHERE e.industry = $industry
        WITH e,
             CASE WHEN e.time_to_value_days IS NOT NULL
                  THEN e.time_to_value_days ELSE 180 END AS ttv
        RETURN count(e) AS case_count,
               avg(ttv) AS avg_time_to_value_days,
               avg(COALESCE(e.deal_size_usd, 0)) AS avg_deal_size,
               collect(DISTINCT e.company_size) AS company_sizes
        """
        async with self._driver.session() as session:
            result = await run_validated_query(
                session,
                query,
                {
                    "tenant_id": tenant_id,
                    "industry": industry,
                },
                tenant_id=tenant_id,
                require_explicit_tenant_id=True,
                query_name="roi_calculator_service.get_industry_benchmarks",
            )
            record = await result.single()

        if not record or record["case_count"] == 0:
            return ROICalculatorService_get_industry_benchmarksResult.model_validate({
                "industry": industry,
                "has_benchmarks": False,
                "message": "No case studies found for this industry",
                "defaults": {
                    "productivity_gain_pct": 0.10,
                    "error_reduction_pct": 0.15,
                    "time_savings_hours_per_week": 4.0,
                    "avg_time_to_value_days": 180,
                },
            })


        return ROICalculatorService_get_industry_benchmarksResult.model_validate({
            "industry": industry,
            "has_benchmarks": True,
            "message": "Benchmarks found for this industry",
            "case_count": record["case_count"],
            "avg_time_to_value_days": round(record["avg_time_to_value_days"] or 180, 0),
            "avg_deal_size": round(record["avg_deal_size"] or 0, 2),
            "company_sizes": record["company_sizes"],
            "defaults": {
                "productivity_gain_pct": 0.12,
                "error_reduction_pct": 0.20,
                "time_savings_hours_per_week": 5.0,
                "avg_time_to_value_days": round(record["avg_time_to_value_days"] or 180, 0),
            },
        })
