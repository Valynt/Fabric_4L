from __future__ import annotations

"""
Data Intelligence Layer Phase 2 — L3 Tests.

Tests for:
  - Task 2.2: Competitive Intelligence Service (competitive_intel_service.py)
  - Task 2.3: ROI Calculator Service (roi_calculator_service.py)

These tests use mock Neo4j drivers to isolate service logic from the database.
Run with: pytest tests/test_dil_phase2.py --noconftest -v
"""


import json
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import services directly (no conftest dependency)
# ---------------------------------------------------------------------------

from src.services.competitive_intel_service import (
    BattlecardCreate,
    CompetitorCreate,
    CompetitiveIntelService,
    WinLossRecord,
)
from src.services.roi_calculator_service import (
    ROICalculatorService,
    ROIInputs,
    ROIOutputs,
    ROITemplateCreate,
)
from src.services.roi_math_kernel import STANDARD_SCENARIOS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_ID = "test-tenant-001"


class MockRecord:
    """Simulates a Neo4j record."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def __getitem__(self, key: str):
        return self._data[key]

    def get(self, key: str, default=None):
        return self._data.get(key, default)


class MockResult:
    """Simulates a Neo4j result set."""

    def __init__(self, records: list[dict[str, Any]]):
        self._records = [MockRecord(r) for r in records]
        self._index = 0

    async def single(self):
        return self._records[0] if self._records else None

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._records):
            raise StopAsyncIteration
        record = self._records[self._index]
        self._index += 1
        return record


def make_mock_driver(return_data: list[dict[str, Any]] | None = None):
    """Create a mock Neo4j driver that returns specified data."""
    if return_data is None:
        return_data = []

    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=MockResult(return_data))
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)

    return mock_driver


# ===========================================================================
# Task 2.2: Competitive Intelligence Service Tests
# ===========================================================================


class TestCompetitorCreate:
    """Tests for CompetitorCreate data model."""

    def test_default_values(self):
        c = CompetitorCreate(name="Acme", description="A competitor")
        assert c.name == "Acme"
        assert c.market_position == "challenger"
        assert c.pricing_tier == "mid"
        assert c.strengths == []
        assert c.weaknesses == []
        assert c.target_segments == []

    def test_full_values(self):
        c = CompetitorCreate(
            name="BigCorp",
            description="Enterprise competitor",
            domain="bigcorp.com",
            founded_year=2010,
            strengths=["Brand recognition", "Large sales team"],
            weaknesses=["Slow innovation", "High cost"],
            market_position="leader",
            pricing_tier="premium",
            target_segments=["enterprise", "mid-market"],
        )
        assert c.founded_year == 2010
        assert len(c.strengths) == 2
        assert c.market_position == "leader"


class TestBattlecardCreate:
    """Tests for BattlecardCreate data model."""

    def test_default_values(self):
        bc = BattlecardCreate(product_id="p1", positioning="We are faster")
        assert bc.product_id == "p1"
        assert bc.differentiators == []
        assert bc.objection_handlers == []
        assert bc.talk_tracks == []

    def test_with_objection_handlers(self):
        bc = BattlecardCreate(
            product_id="p1",
            positioning="We are faster",
            objection_handlers=[
                {"objection": "Too expensive", "response": "Consider TCO"},
            ],
        )
        assert len(bc.objection_handlers) == 1
        assert bc.objection_handlers[0]["objection"] == "Too expensive"


class TestWinLossRecord:
    """Tests for WinLossRecord data model."""

    def test_default_values(self):
        wl = WinLossRecord(
            competitor_id="c1",
            product_id="p1",
            outcome="won",
        )
        assert wl.outcome == "won"
        assert wl.deal_size_usd == 0.0
        assert wl.reason == ""

    def test_full_values(self):
        wl = WinLossRecord(
            competitor_id="c1",
            product_id="p1",
            outcome="lost",
            deal_size_usd=50000.0,
            reason="Price too high",
            industry="manufacturing",
        )
        assert wl.deal_size_usd == 50000.0
        assert wl.reason == "Price too high"


class TestCompetitiveIntelServiceAddCompetitor:
    """Tests for CompetitiveIntelService.add_competitor."""

    @pytest.mark.asyncio
    async def test_add_competitor_returns_id(self):
        comp_data = {
            "competitor": {
                "id": "test-id",
                "name": "Acme",
                "tenant_id": TENANT_ID,
            }
        }
        driver = make_mock_driver([comp_data])
        svc = CompetitiveIntelService(driver)

        result = await svc.add_competitor(
            TENANT_ID,
            CompetitorCreate(name="Acme", description="A competitor"),
        )

        assert "id" in result
        assert result["name"] == "Acme"

    @pytest.mark.asyncio
    async def test_add_competitor_calls_neo4j(self):
        driver = make_mock_driver([{"competitor": {"id": "x", "name": "Y"}}])
        svc = CompetitiveIntelService(driver)

        await svc.add_competitor(
            TENANT_ID,
            CompetitorCreate(name="Y", description="Desc"),
        )

        session = driver.session().__aenter__.return_value
        # The run method should have been called (CREATE query)
        assert driver.session.called


class TestCompetitiveIntelServiceGetCompetitor:
    """Tests for CompetitiveIntelService.get_competitor."""

    @pytest.mark.asyncio
    async def test_get_existing_competitor(self):
        comp_data = {
            "competitor": {
                "id": "c1",
                "name": "Acme",
                "market_position": "leader",
            },
            "competing_products": [{"id": "p1", "name": "Widget", "overlap_score": 0.8}],
            "battlecards": [{"id": "bc1", "product_id": "p1", "positioning": "We're better"}],
        }
        driver = make_mock_driver([comp_data])
        svc = CompetitiveIntelService(driver)

        result = await svc.get_competitor(TENANT_ID, "c1")

        assert result is not None
        assert result["name"] == "Acme"
        assert len(result["competing_products"]) == 1
        assert len(result["battlecards"]) == 1

    @pytest.mark.asyncio
    async def test_get_nonexistent_competitor(self):
        driver = make_mock_driver([{"competitor": None, "competing_products": [], "battlecards": []}])
        svc = CompetitiveIntelService(driver)

        result = await svc.get_competitor(TENANT_ID, "nonexistent")
        assert result is None


class TestCompetitiveIntelServiceListCompetitors:
    """Tests for CompetitiveIntelService.list_competitors."""

    @pytest.mark.asyncio
    async def test_list_competitors(self):
        # The service opens a new session for each query, so we need the
        # mock driver to return different sessions (or the same session
        # that returns different results per call).
        call_count = 0

        async def mock_run(query, params=None):
            nonlocal call_count
            call_count += 1
            if "AS total" in query:
                return MockResult([{"total": 2}])
            return MockResult([
                {"competitor": {"id": "c1", "name": "A"}, "product_overlap_count": 1},
                {"competitor": {"id": "c2", "name": "B"}, "product_overlap_count": 0},
            ])

        # list_competitors uses a single `async with self._driver.session() as session:`
        # block, so both run calls go to the same session.
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=mock_run)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        svc = CompetitiveIntelService(driver)
        result = await svc.list_competitors(TENANT_ID)

        assert result["total"] == 2
        assert len(result["competitors"]) == 2


class TestCompetitiveIntelServiceDeleteCompetitor:
    """Tests for CompetitiveIntelService.delete_competitor."""

    @pytest.mark.asyncio
    async def test_delete_existing(self):
        driver = make_mock_driver([{"deleted": 1}])
        svc = CompetitiveIntelService(driver)

        result = await svc.delete_competitor(TENANT_ID, "c1")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        driver = make_mock_driver([{"deleted": 0}])
        svc = CompetitiveIntelService(driver)

        result = await svc.delete_competitor(TENANT_ID, "nonexistent")
        assert result is False


class TestCompetitiveIntelServiceAnalysis:
    """Tests for competitive landscape analysis."""

    @pytest.mark.asyncio
    async def test_analyze_landscape(self):
        driver = make_mock_driver([
            {
                "competitor": {"id": "c1", "name": "A", "market_position": "leader", "pricing_tier": "high"},
                "product_overlaps": 2,
                "wins": 5,
                "losses": 3,
                "overlap_score": 0.8,
            },
            {
                "competitor": {"id": "c2", "name": "B", "market_position": "niche", "pricing_tier": "low"},
                "product_overlaps": 1,
                "wins": 1,
                "losses": 4,
                "overlap_score": 0.3,
            },
        ])
        svc = CompetitiveIntelService(driver)

        result = await svc.analyze_competitive_landscape(TENANT_ID)

        assert result["total_competitors"] == 2
        assert result["total_wins"] == 6
        assert result["total_losses"] == 7
        assert result["overall_win_rate"] == round(6 / 13, 3)
        assert result["landscape"][0]["win_rate"] == round(5 / 8, 3)

    @pytest.mark.asyncio
    async def test_win_loss_summary(self):
        driver = make_mock_driver([
            {
                "competitor": {"id": "c1", "name": "A", "market_position": "leader"},
                "wins": 10,
                "losses": 5,
                "won_revenue": 500000.0,
                "lost_revenue": 200000.0,
            },
        ])
        svc = CompetitiveIntelService(driver)

        result = await svc.get_win_loss_summary(TENANT_ID)

        assert result["total_competitors"] == 1
        assert result["competitors"][0]["win_rate"] == round(10 / 15, 3)
        assert result["competitors"][0]["won_revenue"] == 500000.0


# ===========================================================================
# Task 2.3: ROI Calculator Service Tests
# ===========================================================================


class TestROIInputsDefaults:
    """Tests for ROIInputs data model defaults."""

    def test_default_values(self):
        inputs = ROIInputs()
        assert inputs.annual_revenue == 0.0
        assert inputs.num_employees == 0
        assert inputs.avg_salary == 75000.0
        assert inputs.productivity_gain_pct == 0.10
        assert inputs.affected_employees_pct == 0.25

    def test_custom_values(self):
        inputs = ROIInputs(
            annual_revenue=10_000_000,
            num_employees=500,
            implementation_cost=100_000,
            annual_license_cost=50_000,
        )
        assert inputs.annual_revenue == 10_000_000
        assert inputs.num_employees == 500


class TestStandardScenarios:
    """Tests for standard scenario configurations."""

    def test_conservative_scenario(self):
        sc = STANDARD_SCENARIOS["conservative"]
        assert sc.benefit_multiplier < 1.0
        assert sc.cost_multiplier > 1.0

    def test_moderate_scenario(self):
        sc = STANDARD_SCENARIOS["moderate"]
        assert sc.benefit_multiplier == 1.0
        assert sc.cost_multiplier == 1.0

    def test_aggressive_scenario(self):
        sc = STANDARD_SCENARIOS["aggressive"]
        assert sc.benefit_multiplier > 1.0
        assert sc.cost_multiplier < 1.0


class TestROICalculation:
    """Tests for the core ROI calculation engine."""

    def _make_service(self):
        return ROICalculatorService(make_mock_driver())

    def test_basic_calculation(self):
        svc = self._make_service()
        inputs = ROIInputs(
            num_employees=100,
            avg_salary=80000,
            current_cost_annual=500000,
            implementation_cost=200000,
            annual_license_cost=100000,
            training_cost=50000,
            productivity_gain_pct=0.15,
            error_reduction_pct=0.20,
            time_savings_hours_per_week=5.0,
            affected_employees_pct=0.30,
        )

        result = svc.calculate_roi(inputs, scenario="moderate")

        assert isinstance(result, ROIOutputs)
        assert result.total_benefit_year1 > 0
        assert result.total_cost_year1 > 0
        assert result.payback_months > 0
        assert result.benefit_breakdown["productivity_gains"] > 0
        assert result.benefit_breakdown["error_reduction"] > 0
        assert result.benefit_breakdown["time_savings"] > 0

    def test_zero_inputs_no_crash(self):
        svc = self._make_service()
        inputs = ROIInputs()

        result = svc.calculate_roi(inputs)

        assert result.total_benefit_year1 == 0.0
        assert result.total_cost_year1 == 0.0
        assert result.roi_pct_year1 == 0.0

    def test_conservative_lower_than_aggressive(self):
        svc = self._make_service()
        inputs = ROIInputs(
            num_employees=200,
            avg_salary=90000,
            implementation_cost=300000,
            annual_license_cost=120000,
        )

        conservative = svc.calculate_roi(inputs, scenario="conservative")
        aggressive = svc.calculate_roi(inputs, scenario="aggressive")

        assert conservative.total_benefit_year1 < aggressive.total_benefit_year1
        assert conservative.total_cost_year1 > aggressive.total_cost_year1

    def test_payback_period_reasonable(self):
        svc = self._make_service()
        inputs = ROIInputs(
            num_employees=50,
            avg_salary=70000,
            implementation_cost=50000,
            annual_license_cost=30000,
            training_cost=10000,
            productivity_gain_pct=0.20,
            affected_employees_pct=0.50,
        )

        result = svc.calculate_roi(inputs)

        # With these inputs, payback should be reasonable (< 36 months)
        assert result.payback_months < 36
        assert result.payback_months > 0

    def test_3year_benefit_greater_than_1year(self):
        svc = self._make_service()
        inputs = ROIInputs(
            num_employees=100,
            avg_salary=80000,
            implementation_cost=100000,
            annual_license_cost=50000,
        )

        result = svc.calculate_roi(inputs, time_horizon_months=36)

        assert result.total_benefit_3year > result.total_benefit_year1

    def test_custom_inputs_included(self):
        svc = self._make_service()
        inputs = ROIInputs(
            num_employees=10,
            custom_inputs={"compliance_savings": 50000, "risk_reduction": 30000},
        )

        result = svc.calculate_roi(inputs)

        assert result.benefit_breakdown["custom_benefits"] == 80000.0


class TestNPVCalculation:
    """Tests for NPV financial math."""

    def test_positive_npv(self):
        npv = ROICalculatorService._calculate_npv(
            initial_investment=100000,
            annual_cash_flows=[50000, 50000, 50000],
            discount_rate=0.10,
        )
        assert npv > 0  # 3 years of 50k at 10% discount > 100k investment

    def test_negative_npv(self):
        npv = ROICalculatorService._calculate_npv(
            initial_investment=100000,
            annual_cash_flows=[10000, 10000, 10000],
            discount_rate=0.10,
        )
        assert npv < 0  # 3 years of 10k at 10% discount < 100k investment

    def test_zero_discount_rate(self):
        npv = ROICalculatorService._calculate_npv(
            initial_investment=100000,
            annual_cash_flows=[50000, 50000],
            discount_rate=0.0,
        )
        assert npv == 0.0  # 100k investment, 100k return at 0% discount


class TestIRRCalculation:
    """Tests for IRR financial math."""

    def test_basic_irr(self):
        # -100k investment, then 50k per year for 3 years
        irr = ROICalculatorService._calculate_irr([-100000, 50000, 50000, 50000])
        assert irr is not None
        assert 0.2 < irr < 0.3  # IRR should be around 23.4%

    def test_no_cash_flows(self):
        irr = ROICalculatorService._calculate_irr([])
        assert irr is None

    def test_single_cash_flow(self):
        irr = ROICalculatorService._calculate_irr([-100000])
        assert irr is None


class TestScenarioComparison:
    """Tests for scenario comparison."""

    def test_compare_all_scenarios(self):
        svc = ROICalculatorService(make_mock_driver())
        inputs = ROIInputs(
            num_employees=100,
            avg_salary=80000,
            implementation_cost=200000,
            annual_license_cost=100000,
        )

        result = svc.compare_scenarios(inputs)

        assert "scenarios" in result
        assert "conservative" in result["scenarios"]
        assert "moderate" in result["scenarios"]
        assert "aggressive" in result["scenarios"]

        # Conservative should have lowest ROI
        assert (
            result["scenarios"]["conservative"]["roi_pct_3year"]
            < result["scenarios"]["aggressive"]["roi_pct_3year"]
        )

    def test_compare_custom_scenarios(self):
        svc = ROICalculatorService(make_mock_driver())
        inputs = ROIInputs(num_employees=50)

        result = svc.compare_scenarios(
            inputs, scenarios=["conservative", "moderate"]
        )

        assert len(result["scenarios"]) == 2
        assert "aggressive" not in result["scenarios"]


class TestROITemplateCreate:
    """Tests for ROITemplateCreate data model."""

    def test_default_values(self):
        t = ROITemplateCreate(name="Test", description="A template")
        assert t.category == "general"
        assert t.input_schema == {}
        assert t.applicable_industries == []

    def test_full_values(self):
        t = ROITemplateCreate(
            name="SaaS ROI",
            description="Standard SaaS ROI template",
            category="saas",
            input_schema={"annual_revenue": {"type": "number", "required": True}},
            default_assumptions={"productivity_gain_pct": 0.12},
            applicable_industries=["technology", "finance"],
            applicable_products=["Platform X"],
        )
        assert t.category == "saas"
        assert len(t.applicable_industries) == 2


class TestROITemplateManagement:
    """Tests for ROI template CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_template(self):
        driver = make_mock_driver([{
            "template": {
                "id": "t1",
                "name": "Test Template",
                "category": "general",
            }
        }])
        svc = ROICalculatorService(driver)

        result = await svc.create_template_for_tenant(
            TENANT_ID,
            ROITemplateCreate(name="Test Template", description="Desc"),
        )

        assert "id" in result
        assert result["name"] == "Test Template"

    @pytest.mark.asyncio
    async def test_get_templates(self):
        mock_session = AsyncMock()
        call_count = 0

        async def mock_run(query, params=None):
            nonlocal call_count
            call_count += 1
            if "AS total" in query:
                return MockResult([{"total": 1}])
            return MockResult([{
                "template": {"id": "t1", "name": "Template A", "category": "saas"}
            }])

        mock_session.run = mock_run
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        svc = ROICalculatorService(driver)
        result = await svc.get_templates(TENANT_ID)

        assert result["total"] == 1
        assert len(result["templates"]) == 1


class TestROICalculationPersistence:
    """Tests for saving and retrieving calculations."""

    @pytest.mark.asyncio
    async def test_save_calculation(self):
        driver = make_mock_driver([{
            "calculation": {
                "id": "calc-1",
                "scenario_name": "moderate",
                "inputs": "{}",
                "outputs": "{}",
            }
        }])
        svc = ROICalculatorService(driver)

        result = await svc.save_calculation(
            TENANT_ID,
            account_id="acct-1",
            inputs={"num_employees": 100},
            outputs={"roi_pct_year1": 150.0},
            scenario_name="moderate",
        )

        assert "id" in result

    @pytest.mark.asyncio
    async def test_get_calculation(self):
        driver = make_mock_driver([{
            "calculation": {
                "id": "calc-1",
                "inputs": json.dumps({"num_employees": 100}),
                "outputs": json.dumps({"roi_pct_year1": 150.0}),
                "assumptions": json.dumps({}),
            }
        }])
        svc = ROICalculatorService(driver)

        result = await svc.get_calculation(TENANT_ID, "calc-1")

        assert result is not None
        assert result["inputs"]["num_employees"] == 100
        assert result["outputs"]["roi_pct_year1"] == 150.0

    @pytest.mark.asyncio
    async def test_get_nonexistent_calculation(self):
        driver = make_mock_driver([{"calculation": None}])
        svc = ROICalculatorService(driver)

        result = await svc.get_calculation(TENANT_ID, "nonexistent")
        assert result is None


class TestROIBenchmarks:
    """Tests for industry benchmarks."""

    @pytest.mark.asyncio
    async def test_benchmarks_with_data(self):
        driver = make_mock_driver([{
            "case_count": 15,
            "avg_time_to_value_days": 120.0,
            "avg_deal_size": 250000.0,
            "company_sizes": ["medium", "large", "enterprise"],
        }])
        svc = ROICalculatorService(driver)

        result = await svc.get_industry_benchmarks(TENANT_ID, "technology")

        assert result["has_benchmarks"] is True
        assert result["case_count"] == 15
        assert result["avg_time_to_value_days"] == 120.0
        assert "defaults" in result

    @pytest.mark.asyncio
    async def test_benchmarks_no_data(self):
        driver = make_mock_driver([{
            "case_count": 0,
            "avg_time_to_value_days": None,
            "avg_deal_size": None,
            "company_sizes": [],
        }])
        svc = ROICalculatorService(driver)

        result = await svc.get_industry_benchmarks(TENANT_ID, "unknown_industry")

        assert result["has_benchmarks"] is False
        assert "defaults" in result
        assert result["defaults"]["productivity_gain_pct"] == 0.10
