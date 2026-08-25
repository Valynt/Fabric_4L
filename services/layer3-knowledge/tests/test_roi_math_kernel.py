"""Unit tests for the Layer 3 ROI Financial Math Kernel."""

import pytest
from src.services.roi_math_kernel import (
    FinancialMathKernel,
    ROIInputs,
    ROIOutputs,
    STANDARD_SCENARIOS,
    ScenarioConfig,
)


@pytest.mark.unit
def test_financial_math_kernel_npv_calculation() -> None:
    """Verify NPV calculation against standard financial formula."""
    initial_inv = 100000.0
    cash_flows = [40000.0, 40000.0, 40000.0]
    discount_rate = 0.10

    npv = FinancialMathKernel.calculate_npv(initial_inv, cash_flows, discount_rate)
    # Year 1: 40000 / 1.1 = 36363.64
    # Year 2: 40000 / 1.21 = 33057.85
    # Year 3: 40000 / 1.331 = 30052.59
    # Sum: 99474.08 - 100000 = -525.92
    assert pytest.approx(npv, 0.1) == -525.92


@pytest.mark.unit
def test_financial_math_kernel_irr_calculation() -> None:
    """Verify IRR calculation with positive return."""
    cash_flows = [-100000.0, 50000.0, 50000.0, 50000.0]
    irr = FinancialMathKernel.calculate_irr(cash_flows)
    assert irr is not None
    assert 0.23 < irr < 0.24  # Approximately 23.38%


@pytest.mark.unit
def test_financial_math_kernel_irr_no_solution() -> None:
    """Verify IRR returns None when all cash flows are negative or positive."""
    assert FinancialMathKernel.calculate_irr([100.0, 200.0, 300.0]) is None
    assert FinancialMathKernel.calculate_irr([-100.0, -200.0]) is None
    assert FinancialMathKernel.calculate_irr([]) is None


@pytest.mark.unit
def test_financial_math_kernel_payback_period() -> None:
    """Verify payback period calculation in months."""
    initial_cost = 60000.0
    annual_benefit = 120000.0
    payback = FinancialMathKernel.calculate_payback_period(initial_cost, annual_benefit)
    assert payback == 6.0  # 6 months

    # Zero or negative benefit returns infinity
    assert FinancialMathKernel.calculate_payback_period(60000.0, 0.0) == float("inf")
    assert FinancialMathKernel.calculate_payback_period(60000.0, -10000.0) == float(
        "inf"
    )


@pytest.mark.unit
def test_financial_math_kernel_calculate_roi() -> None:
    """Verify full calculate_roi produces accurate outputs."""
    inputs = ROIInputs(
        annual_revenue=10000000.0,
        num_employees=100,
        avg_salary=100000.0,
        current_cost_annual=200000.0,
        implementation_cost=50000.0,
        annual_license_cost=30000.0,
        training_cost=10000.0,
        productivity_gain_pct=0.10,
        error_reduction_pct=0.20,
        time_savings_hours_per_week=5.0,
        affected_employees_pct=0.25,
    )

    outputs = FinancialMathKernel.calculate_roi(
        inputs, time_horizon_months=36, scenario="moderate"
    )
    assert outputs.total_benefit_year1 > 0
    assert outputs.total_cost_year1 == 90000.0  # 50k + 30k + 10k
    assert (
        outputs.net_benefit_year1
        == outputs.total_benefit_year1 - outputs.total_cost_year1
    )
    assert outputs.roi_pct_year1 > 0
    assert outputs.payback_months > 0


@pytest.mark.unit
def test_financial_math_kernel_compare_scenarios() -> None:
    """Verify compare_scenarios produces conservative, moderate, aggressive tiers."""
    inputs = ROIInputs(
        num_employees=50,
        avg_salary=80000.0,
        current_cost_annual=100000.0,
        implementation_cost=30000.0,
        annual_license_cost=20000.0,
    )

    result = FinancialMathKernel.compare_scenarios(inputs)
    scenarios = result["scenarios"]

    assert "conservative" in scenarios
    assert "moderate" in scenarios
    assert "aggressive" in scenarios
    assert (
        scenarios["aggressive"]["total_benefit_3year"]
        > scenarios["moderate"]["total_benefit_3year"]
    )
    assert (
        scenarios["moderate"]["total_benefit_3year"]
        > scenarios["conservative"]["total_benefit_3year"]
    )
