"""
Tests for the Scenario Engine what-if analysis functionality.
"""

from agents.scenario_engine import (
    VariableAdjustment,
    scenario_engine,
)


class TestScenarioEngine:
    """Test suite for scenario calculation engine."""

    def test_calculate_scenario_basic(self):
        """Test basic scenario calculation with single adjustment."""
        base_case = {
            "total_value": 500000,
            "implementation_cost": 200000,
            "roi_ratio": 1.5,
            "payback_months": 12.0,
        }

        adjustments = [
            VariableAdjustment(
                name="total_value",
                value=600000,
                original_value=500000,
            )
        ]

        result = scenario_engine.calculate_scenario(base_case, adjustments)

        assert result.original_value == 500000
        assert result.adjusted_value == 600000
        assert result.delta_percentage == 20.0
        assert result.new_roi == 2.0  # (600k - 200k) / 200k
        assert result.scenario_id is not None
        assert len(result.calculation_steps) > 0

    def test_calculate_scenario_implementation_cost(self):
        """Test scenario with implementation cost adjustment."""
        base_case = {
            "total_value": 500000,
            "implementation_cost": 200000,
            "roi_ratio": 1.5,
            "payback_months": 12.0,
        }

        adjustments = [
            VariableAdjustment(
                name="implementation_cost",
                value=250000,
                original_value=200000,
            )
        ]

        result = scenario_engine.calculate_scenario(base_case, adjustments)

        # Higher cost should reduce adjusted value
        assert result.adjusted_value == 450000  # 500k - 50k
        assert result.delta_percentage == -10.0

    def test_calculate_scenario_timeline_adjustment(self):
        """Test scenario with timeline adjustment using constant."""
        base_case = {
            "total_value": 500000,
            "implementation_cost": 200000,
            "roi_ratio": 1.5,
            "payback_months": 12.0,
        }

        # Reduce timeline by 3 months should save $30k (3 * $10k/month)
        adjustments = [
            VariableAdjustment(
                name="timeline_months",
                value=9,
                original_value=12,
            )
        ]

        result = scenario_engine.calculate_scenario(base_case, adjustments)

        # Should add savings from reduced timeline
        expected_value = 500000 + 30000  # +$30k from 3 months saved
        assert result.adjusted_value == expected_value

    def test_deterministic_scenario_id(self):
        """Test that same adjustments produce same scenario ID."""
        base_case = {
            "total_value": 500000,
            "implementation_cost": 200000,
        }

        adjustments = [
            VariableAdjustment(name="total_value", value=550000, original_value=500000),
        ]

        result1 = scenario_engine.calculate_scenario(base_case, adjustments)
        result2 = scenario_engine.calculate_scenario(base_case, adjustments)

        assert result1.scenario_id == result2.scenario_id

    def test_calculate_roi_zero_cost(self):
        """Test ROI calculation with zero implementation cost."""
        roi = scenario_engine._calculate_roi(500000, 0)
        assert roi == 0.0  # Should return 0, not infinity

    def test_calculate_payback_zero_value(self):
        """Test payback calculation with zero total value."""
        payback = scenario_engine._calculate_payback(0, 200000)
        assert payback == scenario_engine.MAX_PAYBACK_MONTHS

    def test_compare_scenarios(self):
        """Test comparing multiple scenarios."""
        base_case = {
            "total_value": 500000,
            "implementation_cost": 200000,
            "roi_ratio": 1.5,
            "payback_months": 12.0,
        }

        from agents.scenario_engine import SavedScenario

        scenarios = [
            SavedScenario(
                id="scenario_1",
                name="Conservative",
                base_case_id="bc_123",
                adjustments=[VariableAdjustment("total_value", 400000, 500000)],
                created_at="2024-01-01T00:00:00Z",
            ),
            SavedScenario(
                id="scenario_2",
                name="Optimistic",
                base_case_id="bc_123",
                adjustments=[VariableAdjustment("total_value", 700000, 500000)],
                created_at="2024-01-01T00:00:00Z",
            ),
        ]

        comparison = scenario_engine.compare_scenarios(base_case, scenarios)

        assert len(comparison["comparison"]) == 2
        assert comparison["best_scenario"]["name"] == "Optimistic"
        assert comparison["worst_scenario"]["name"] == "Conservative"

    def test_sensitivity_analysis(self):
        """Test sensitivity analysis across percentage range."""
        base_case = {
            "total_value": 500000,
            "implementation_cost": 200000,
        }

        results = scenario_engine.sensitivity_analysis(
            base_case,
            "total_value",
            [-20, -10, 0, 10, 20],
        )

        assert len(results) == 5
        # Results should be in order of percentage input
        assert results[0].adjusted_value == 400000  # -20%
        assert results[2].adjusted_value == 500000  # 0%
        assert results[4].adjusted_value == 600000  # +20%

    def test_negative_value_clamping(self):
        """Test that adjusted values cannot go negative."""
        base_case = {
            "total_value": 100000,
            "implementation_cost": 200000,
        }

        # Massive cost increase should not push value below 0
        adjustments = [
            VariableAdjustment(
                name="implementation_cost",
                value=500000,
                original_value=200000,
            )
        ]

        result = scenario_engine.calculate_scenario(base_case, adjustments)
        assert result.adjusted_value >= 0


class TestVariableAdjustment:
    """Test VariableAdjustment dataclass."""

    def test_create_adjustment(self):
        """Test creating a variable adjustment."""
        adj = VariableAdjustment(
            name="implementation_cost",
            value=250000,
            original_value=200000,
        )
        assert adj.name == "implementation_cost"
        assert adj.value == 250000
        assert adj.original_value == 200000

