"""Pure financial math and ROI calculation kernel for Layer 3.

Provides deterministic calculation of ROI, NPV, IRR, payback period, and multi-scenario projections.
This kernel contains no external I/O or database dependencies and can be used standalone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic import BaseModel as TypedDictModel
else:
    from value_fabric.shared.models.typed_dict import TypedDictModel


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


class ScenarioComparisonResult(TypedDictModel):
    discount_rate: float
    scenarios: dict[str, Any]
    time_horizon_months: int


class FinancialMathKernel:
    """Pure mathematical and financial calculation engine for ROI modeling."""

    @staticmethod
    def calculate_npv(
        initial_investment: float,
        annual_cash_flows: list[float],
        discount_rate: float,
    ) -> float:
        """Calculate Net Present Value (NPV).

        Formula: -Initial_Investment + Sum(CF_t / (1 + r)^t)
        """
        npv = -initial_investment
        for year, cf in enumerate(annual_cash_flows, start=1):
            npv += cf / ((1 + discount_rate) ** year)
        return npv

    @staticmethod
    def calculate_irr(
        cash_flows: list[float],
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> float | None:
        """Calculate Internal Rate of Return (IRR) using Newton's method.

        Returns None if IRR cannot be determined within bounds [-0.99, 10.0].
        """
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

    @classmethod
    def calculate_payback_period(
        cls,
        initial_cost: float,
        annual_net_benefit: float,
    ) -> float:
        """Calculate payback period in months."""
        monthly_net = annual_net_benefit / 12.0
        if monthly_net <= 0:
            return float("inf")
        return round(min(initial_cost / monthly_net, 999.0), 1)

    @classmethod
    def calculate_roi(
        cls,
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
        hourly_rate = inputs.avg_salary / 2080.0  # Standard work hours per year

        productivity_benefit = (
            affected_employees * inputs.avg_salary * inputs.productivity_gain_pct
        )
        error_reduction_benefit = (
            inputs.current_cost_annual * inputs.error_reduction_pct
        )
        time_savings_benefit = (
            affected_employees * inputs.time_savings_hours_per_week * hourly_rate * 52.0
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
            inputs.implementation_cost
            + inputs.annual_license_cost
            + inputs.training_cost
        ) * sc.cost_multiplier
        annual_recurring_cost = inputs.annual_license_cost * sc.cost_multiplier

        # --- Multi-year projections ---
        total_benefit_year1 = annual_benefit
        total_cost_year1 = year1_cost

        total_benefit_3year = annual_benefit * years
        total_cost_3year = year1_cost + annual_recurring_cost * max(years - 1.0, 0.0)

        net_benefit_year1 = total_benefit_year1 - total_cost_year1
        net_benefit_3year = total_benefit_3year - total_cost_3year

        roi_pct_year1 = (
            (net_benefit_year1 / total_cost_year1 * 100.0)
            if total_cost_year1 > 0
            else 0.0
        )
        roi_pct_3year = (
            (net_benefit_3year / total_cost_3year * 100.0)
            if total_cost_3year > 0
            else 0.0
        )

        # Payback period (months)
        annual_net_for_payback = annual_benefit - annual_recurring_cost
        payback_months = cls.calculate_payback_period(
            year1_cost, annual_net_for_payback
        )

        # NPV calculation
        npv = cls.calculate_npv(
            initial_investment=year1_cost
            - inputs.annual_license_cost * sc.cost_multiplier,
            annual_cash_flows=[annual_benefit - annual_recurring_cost]
            * int(math.ceil(years)),
            discount_rate=discount_rate,
        )

        # IRR calculation
        cash_flows = [-year1_cost] + [annual_benefit - annual_recurring_cost] * int(
            math.ceil(years)
        )
        irr = cls.calculate_irr(cash_flows)

        return ROIOutputs(
            total_benefit_year1=round(total_benefit_year1, 2),
            total_benefit_3year=round(total_benefit_3year, 2),
            total_cost_year1=round(total_cost_year1, 2),
            total_cost_3year=round(total_cost_3year, 2),
            net_benefit_year1=round(net_benefit_year1, 2),
            net_benefit_3year=round(net_benefit_3year, 2),
            roi_pct_year1=round(roi_pct_year1, 2),
            roi_pct_3year=round(roi_pct_3year, 2),
            payback_months=payback_months,
            npv=round(npv, 2),
            irr=round(irr, 4) if irr is not None else None,
            benefit_breakdown={
                "productivity_gains": round(
                    productivity_benefit * sc.benefit_multiplier, 2
                ),
                "error_reduction": round(
                    error_reduction_benefit * sc.benefit_multiplier, 2
                ),
                "time_savings": round(time_savings_benefit * sc.benefit_multiplier, 2),
                "custom_benefits": round(custom_benefit, 2),
            },
            cost_breakdown={
                "implementation": round(
                    inputs.implementation_cost * sc.cost_multiplier, 2
                ),
                "annual_license": round(
                    inputs.annual_license_cost * sc.cost_multiplier, 2
                ),
                "training": round(inputs.training_cost * sc.cost_multiplier, 2),
            },
        )

    @classmethod
    def compare_scenarios(
        cls,
        inputs: ROIInputs,
        *,
        scenarios: list[str] | None = None,
        time_horizon_months: int = 36,
        discount_rate: float = 0.10,
    ) -> ScenarioComparisonResult:
        """Run the same inputs through multiple scenarios for comparison."""
        if scenarios is None:
            scenarios = ["conservative", "moderate", "aggressive"]

        results = {}
        for scenario_name in scenarios:
            result = cls.calculate_roi(
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

        return ScenarioComparisonResult.model_validate(
            {
                "scenarios": results,
                "time_horizon_months": time_horizon_months,
                "discount_rate": discount_rate,
            }
        )
