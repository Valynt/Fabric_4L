from __future__ import annotations

"""
Data Intelligence Layer — Phase 3 Tests.

Tests for:
  Task 3.1 — Narrative Builder Service
  Task 3.2 — Intelligence Orchestrator (Cross-Layer)

Uses mock Neo4j driver to avoid external dependencies.
"""


import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Now safe to import
# ---------------------------------------------------------------------------
from value_fabric.shared.identity.context import (
    RequestContext,
    clear_current_context,
    set_current_context,
)

from layer4_agents.services.intelligence_orchestrator import (
    READINESS_WEIGHTS,
    IntelligenceOrchestrator,
    _readiness_label,
)
from layer4_agents.services.narrative_builder_service import (
    SECTION_ORDER,
    TONE_TEMPLATES,
    NarrativeAudience,
    NarrativeBuilderService,
    NarrativeRequest,
    NarrativeStatus,
    NarrativeTone,
)

# ---------------------------------------------------------------------------
# Test Constants
# ---------------------------------------------------------------------------

TENANT_ID = "tenant-test-001"
ACCOUNT_ID = "acct-test-001"


@pytest.fixture(autouse=True)
def _set_tenant_context():
    """Provide a tenant context for intelligence orchestrator tests."""
    set_current_context(RequestContext(tenant_id=TENANT_ID, user_id="user-test"))
    yield
    clear_current_context()


# ---------------------------------------------------------------------------
# Mock Helpers
# ---------------------------------------------------------------------------


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


def make_mock_driver(results_sequence: list[list[dict[str, Any]]]):
    """Create a mock Neo4j driver that returns results in sequence."""
    call_idx = 0

    async def mock_run(query, params=None):
        nonlocal call_idx
        idx = min(call_idx, len(results_sequence) - 1)
        call_idx += 1
        return MockResult(results_sequence[idx])

    mock_session = AsyncMock()
    mock_session.run = AsyncMock(side_effect=mock_run)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    driver = MagicMock()
    driver.session = MagicMock(return_value=mock_session)
    return driver


# ===========================================================================
# Task 3.1 — Narrative Builder Service Tests
# ===========================================================================


class TestNarrativeEnums:
    """Test narrative enums and constants."""

    def test_tone_values(self):
        assert NarrativeTone.EXECUTIVE.value == "executive"
        assert NarrativeTone.TECHNICAL.value == "technical"
        assert NarrativeTone.FINANCIAL.value == "financial"
        assert NarrativeTone.CONSULTATIVE.value == "consultative"

    def test_audience_values(self):
        assert NarrativeAudience.C_SUITE.value == "c_suite"
        assert NarrativeAudience.VP_DIRECTOR.value == "vp_director"
        assert NarrativeAudience.TECHNICAL_BUYER.value == "technical_buyer"
        assert NarrativeAudience.CHAMPION.value == "champion"
        assert NarrativeAudience.EVALUATION_COMMITTEE.value == "evaluation_committee"

    def test_status_values(self):
        assert NarrativeStatus.DRAFT.value == "draft"
        assert NarrativeStatus.REVIEW.value == "review"
        assert NarrativeStatus.APPROVED.value == "approved"
        assert NarrativeStatus.DELIVERED.value == "delivered"

    def test_section_order(self):
        assert "executive_summary" in SECTION_ORDER
        assert "pain_points" in SECTION_ORDER
        assert "value_hypotheses" in SECTION_ORDER
        assert "competitive_positioning" in SECTION_ORDER
        assert "roi_projection" in SECTION_ORDER
        assert "evidence" in SECTION_ORDER
        assert "next_steps" in SECTION_ORDER
        assert len(SECTION_ORDER) == 7

    def test_tone_templates_exist_for_all_tones(self):
        for tone in NarrativeTone:
            assert tone.value in TONE_TEMPLATES
            for section in SECTION_ORDER:
                assert section in TONE_TEMPLATES[tone.value]


class TestNarrativeRequest:
    """Test NarrativeRequest dataclass."""

    def test_defaults(self):
        req = NarrativeRequest(account_id=ACCOUNT_ID)
        assert req.tone == "executive"
        assert req.audience == "c_suite"
        assert req.ranking_strategy == "balanced"
        assert req.roi_scenario == "moderate"
        assert req.roi_time_horizon_months == 36
        assert req.top_n_hypotheses == 5
        assert len(req.include_sections) == 7
        assert req.custom_next_steps == []

    def test_custom_values(self):
        req = NarrativeRequest(
            account_id=ACCOUNT_ID,
            title="Custom Narrative",
            tone="technical",
            audience="technical_buyer",
            include_sections=["executive_summary", "roi_projection"],
            custom_next_steps=["Step 1", "Step 2"],
        )
        assert req.title == "Custom Narrative"
        assert req.tone == "technical"
        assert len(req.include_sections) == 2
        assert len(req.custom_next_steps) == 2


class TestNarrativeBuilderSectionRendering:
    """Test the section rendering logic."""

    def test_build_context(self):
        driver = MagicMock()
        svc = NarrativeBuilderService(driver)

        request = NarrativeRequest(account_id=ACCOUNT_ID)
        context = svc._build_context(
            request=request,
            account_data={"name": "Acme Corp"},
            signals_data=[
                {"category": "cost", "confidence_score": 0.9, "impact_value": 50000},
                {"category": "efficiency", "confidence_score": 0.8, "impact_value": 30000},
            ],
            hypotheses_data=[
                {"hypothesis_text": "H1", "estimated_impact_usd": 100000, "confidence_score": 0.9},
                {"hypothesis_text": "H2", "estimated_impact_usd": 50000, "confidence_score": 0.7},
            ],
            competitive_data={"overall_win_rate": 0.65, "key_differentiators": ["speed", "accuracy"]},
            roi_data={"results": {"net_benefit_year1": 200000, "payback_months": 8, "roi_pct_year1": 150}},
            evidence_data=[
                {"industry": "technology", "title": "Case 1"},
                {"industry": "healthcare", "title": "Case 2"},
            ],
        )

        assert context["company_name"] == "Acme Corp"
        assert context["hypothesis_count"] == 2
        assert context["signal_count"] == 2
        assert context["evidence_count"] == 2
        assert context["total_impact"] == 150000
        assert context["win_rate"] == 0.65
        assert context["months"] == 36

    def test_render_section_executive_summary(self):
        driver = MagicMock()
        svc = NarrativeBuilderService(driver)

        context = {
            "company_name": "Acme Corp",
            "hypothesis_count": 3,
            "total_impact": 500000,
            "timeframe": "36 months",
            "signal_count": 5,
            "top_signal_areas": "cost, efficiency",
            "top_n": 3,
            "ranking_strategy": "balanced",
            "key_differentiators": "speed, accuracy",
            "win_rate": 0.7,
            "scenario": "moderate",
            "months": 36,
            "net_benefit": 400000,
            "payback": 8.5,
            "roi": 200,
            "npv": 350000,
            "hypotheses": [],
            "signals": [],
            "competitors": [],
            "evidence": [],
            "roi_scenarios": {},
            "custom_next_steps": [],
        }

        section = svc._render_section("executive_summary", "executive", context)
        assert "title" in section
        assert "summary" in section
        assert "Acme Corp" in section["summary"]
        assert "3 value opportunities" in section["summary"]

    def test_render_section_value_hypotheses_includes_items(self):
        driver = MagicMock()
        svc = NarrativeBuilderService(driver)

        context = {
            "company_name": "Test",
            "hypothesis_count": 2,
            "total_impact": 100000,
            "timeframe": "36 months",
            "signal_count": 1,
            "top_signal_areas": "cost",
            "top_n": 2,
            "ranking_strategy": "impact",
            "key_differentiators": "speed",
            "win_rate": 0.5,
            "scenario": "moderate",
            "months": 36,
            "net_benefit": 80000,
            "payback": 12,
            "roi": 100,
            "npv": 70000,
            "hypotheses": [
                {"hypothesis_text": "Reduce costs", "product_name": "Product A", "signal_name": "High costs", "confidence_score": 0.9, "estimated_impact_usd": 60000},
                {"hypothesis_text": "Improve speed", "product_name": "Product B", "signal_name": "Slow process", "confidence_score": 0.7, "estimated_impact_usd": 40000},
            ],
            "signals": [],
            "competitors": [],
            "evidence": [],
            "roi_scenarios": {},
            "custom_next_steps": [],
        }

        section = svc._render_section("value_hypotheses", "executive", context)
        assert "items" in section
        assert len(section["items"]) == 2
        assert section["items"][0]["hypothesis"] == "Reduce costs"

    def test_render_section_next_steps_custom(self):
        driver = MagicMock()
        svc = NarrativeBuilderService(driver)

        context = {
            "company_name": "Test",
            "hypothesis_count": 0,
            "total_impact": 0,
            "timeframe": "36 months",
            "signal_count": 0,
            "top_signal_areas": "",
            "top_n": 0,
            "ranking_strategy": "balanced",
            "key_differentiators": "",
            "win_rate": 0,
            "scenario": "moderate",
            "months": 36,
            "net_benefit": 0,
            "payback": 0,
            "roi": 0,
            "npv": 0,
            "hypotheses": [],
            "signals": [],
            "competitors": [],
            "evidence": [],
            "roi_scenarios": {},
            "custom_next_steps": ["Custom step 1", "Custom step 2"],
        }

        section = svc._render_section("next_steps", "executive", context)
        assert section["items"] == ["Custom step 1", "Custom step 2"]

    def test_render_section_next_steps_default(self):
        driver = MagicMock()
        svc = NarrativeBuilderService(driver)

        context = {
            "company_name": "Test",
            "hypothesis_count": 0,
            "total_impact": 0,
            "timeframe": "36 months",
            "signal_count": 0,
            "top_signal_areas": "",
            "top_n": 0,
            "ranking_strategy": "balanced",
            "key_differentiators": "",
            "win_rate": 0,
            "scenario": "moderate",
            "months": 36,
            "net_benefit": 0,
            "payback": 0,
            "roi": 0,
            "npv": 0,
            "hypotheses": [],
            "signals": [],
            "competitors": [],
            "evidence": [],
            "roi_scenarios": {},
            "custom_next_steps": [],
        }

        section = svc._render_section("next_steps", "executive", context)
        assert len(section["items"]) == 4
        assert "technical deep-dive" in section["items"][0]


class TestNarrativeBuilderGeneration:
    """Test full narrative generation."""

    @pytest.mark.asyncio
    async def test_generate_narrative(self):
        driver = make_mock_driver([
            [{"narrative": {"id": "narr-001"}}],
        ])
        svc = NarrativeBuilderService(driver)

        request = NarrativeRequest(
            account_id=ACCOUNT_ID,
            title="Test Narrative",
        )

        result = await svc.generate_narrative(
            request,
            tenant_id=TENANT_ID,
            account_data={"name": "Acme Corp"},
            signals_data=[{"category": "cost", "confidence_score": 0.9}],
            hypotheses_data=[{"hypothesis_text": "H1", "estimated_impact_usd": 100000}],
            competitive_data={"overall_win_rate": 0.6, "key_differentiators": ["speed"]},
            roi_data={"results": {"net_benefit_year1": 200000, "payback_months": 8, "roi_pct_year1": 150}},
            evidence_data=[{"industry": "tech", "title": "Case 1"}],
        )

        assert result["tenant_id"] == TENANT_ID
        assert result["account_id"] == ACCOUNT_ID
        assert result["title"] == "Test Narrative"
        assert result["status"] == "draft"
        assert result["version"] == 1
        assert "sections" in result
        assert "executive_summary" in result["sections"]
        assert "metadata" in result
        assert result["metadata"]["hypothesis_count"] == 1

    @pytest.mark.asyncio
    async def test_generate_narrative_with_subset_sections(self):
        driver = make_mock_driver([
            [{"narrative": {"id": "narr-002"}}],
        ])
        svc = NarrativeBuilderService(driver)

        request = NarrativeRequest(
            account_id=ACCOUNT_ID,
            include_sections=["executive_summary", "roi_projection"],
        )

        result = await svc.generate_narrative(request, tenant_id=TENANT_ID)

        assert "executive_summary" in result["sections"]
        assert "roi_projection" in result["sections"]
        assert "pain_points" not in result["sections"]

    @pytest.mark.asyncio
    async def test_generate_narrative_empty_data(self):
        driver = make_mock_driver([
            [{"narrative": {"id": "narr-003"}}],
        ])
        svc = NarrativeBuilderService(driver)

        request = NarrativeRequest(account_id=ACCOUNT_ID)
        result = await svc.generate_narrative(request, tenant_id=TENANT_ID)

        assert result["metadata"]["hypothesis_count"] == 0
        assert result["metadata"]["signal_count"] == 0
        assert result["status"] == "draft"


class TestNarrativeBuilderCRUD:
    """Test narrative CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_narrative(self):
        driver = make_mock_driver([
            [{"narrative": {
                "id": "narr-001",
                "title": "Test",
                "sections": json.dumps({"executive_summary": {"title": "Summary"}}),
                "metadata": json.dumps({"hypothesis_count": 3}),
            }}],
        ])
        svc = NarrativeBuilderService(driver)

        result = await svc.get_narrative(TENANT_ID, "narr-001")
        assert result is not None
        assert result["id"] == "narr-001"
        assert isinstance(result["sections"], dict)
        assert isinstance(result["metadata"], dict)

    @pytest.mark.asyncio
    async def test_get_nonexistent_narrative(self):
        driver = make_mock_driver([[]])
        svc = NarrativeBuilderService(driver)

        result = await svc.get_narrative(TENANT_ID, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_narratives(self):
        async def mock_run(query, params=None):
            if "AS total" in query:
                return MockResult([{"total": 2}])
            return MockResult([
                {"narrative": {"id": "n1", "title": "Narrative 1"}},
                {"narrative": {"id": "n2", "title": "Narrative 2"}},
            ])

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=mock_run)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        svc = NarrativeBuilderService(driver)
        result = await svc.list_narratives(TENANT_ID)

        assert result["total"] == 2
        assert len(result["narratives"]) == 2

    @pytest.mark.asyncio
    async def test_update_status(self):
        driver = make_mock_driver([
            [{"narrative": {
                "id": "narr-001",
                "status": "approved",
                "sections": "{}",
                "metadata": "{}",
            }}],
        ])
        svc = NarrativeBuilderService(driver)

        result = await svc.update_status(TENANT_ID, "narr-001", "approved")
        assert result is not None
        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_update_status_nonexistent(self):
        driver = make_mock_driver([[]])
        svc = NarrativeBuilderService(driver)

        result = await svc.update_status(TENANT_ID, "nonexistent", "approved")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_narrative(self):
        driver = make_mock_driver([[{"deleted": 1}]])
        svc = NarrativeBuilderService(driver)

        result = await svc.delete_narrative(TENANT_ID, "narr-001")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        driver = make_mock_driver([[{"deleted": 0}]])
        svc = NarrativeBuilderService(driver)

        result = await svc.delete_narrative(TENANT_ID, "nonexistent")
        assert result is False


# ===========================================================================
# Task 3.2 — Intelligence Orchestrator Tests
# ===========================================================================


class TestReadinessScoring:
    """Test deal readiness scoring logic."""

    def test_readiness_label_not_ready(self):
        assert _readiness_label(0.0) == "not_ready"
        assert _readiness_label(0.15) == "not_ready"

    def test_readiness_label_early_stage(self):
        assert _readiness_label(0.20) == "early_stage"
        assert _readiness_label(0.35) == "early_stage"

    def test_readiness_label_developing(self):
        assert _readiness_label(0.40) == "developing"
        assert _readiness_label(0.55) == "developing"

    def test_readiness_label_prepared(self):
        assert _readiness_label(0.60) == "prepared"
        assert _readiness_label(0.75) == "prepared"

    def test_readiness_label_deal_ready(self):
        assert _readiness_label(0.80) == "deal_ready"
        assert _readiness_label(1.0) == "deal_ready"

    def test_readiness_weights_sum_to_one(self):
        total = sum(READINESS_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_compute_deal_readiness_empty(self):
        orchestrator = IntelligenceOrchestrator(MagicMock())
        result = orchestrator._compute_deal_readiness(
            signals=[],
            hypotheses=[],
            competitive={},
            roi={},
            evidence=[],
            narrative=None,
        )
        assert result["score"] == 0.0
        assert result["label"] == "not_ready"
        assert len(result["recommendations"]) > 0

    def test_compute_deal_readiness_full(self):
        orchestrator = IntelligenceOrchestrator(MagicMock())
        result = orchestrator._compute_deal_readiness(
            signals=[{"id": f"s{i}"} for i in range(5)],
            hypotheses=[
                {"id": f"h{i}", "status": "validated"} for i in range(5)
            ],
            competitive={"total_competitors": 3},
            roi={"results": {"roi_pct_year1": 200}},
            evidence=[{"id": f"e{i}"} for i in range(3)],
            narrative={"id": "n1"},
        )
        assert result["score"] >= 0.8
        assert result["label"] == "deal_ready"
        assert len(result["recommendations"]) == 0

    def test_compute_deal_readiness_partial(self):
        orchestrator = IntelligenceOrchestrator(MagicMock())
        result = orchestrator._compute_deal_readiness(
            signals=[{"id": "s1"}, {"id": "s2"}],
            hypotheses=[{"id": "h1", "status": "draft"}],
            competitive={"total_competitors": 1},
            roi={},
            evidence=[],
            narrative=None,
        )
        assert 0.0 < result["score"] < 0.8
        assert result["label"] in ("early_stage", "developing", "prepared")
        assert len(result["recommendations"]) > 0

    def test_generate_recommendations(self):
        orchestrator = IntelligenceOrchestrator(MagicMock())
        recs = orchestrator._generate_recommendations({
            "signals_identified": 0.2,
            "hypotheses_generated": 0.0,
            "hypotheses_validated": 0.0,
            "competitive_intel": 0.0,
            "roi_calculated": 0.0,
            "evidence_matched": 0.0,
            "narrative_generated": 0.0,
        })
        assert len(recs) >= 5
        assert any("signal" in r.lower() for r in recs)
        assert any("roi" in r.lower() for r in recs)


class TestIntelligenceOrchestratorBriefing:
    """Test account briefing assembly."""

    @pytest.mark.asyncio
    async def test_get_account_briefing(self):
        """Test full briefing assembly with mocked Neo4j queries."""
        call_idx = 0

        async def mock_run(query, params=None):
            nonlocal call_idx
            call_idx += 1

            # Signal query
            if "Signal" in query and "account_id" in str(params):
                return MockResult([
                    {"signal": {"id": "s1", "category": "cost", "confidence_score": 0.9}},
                ])
            # Hypothesis query
            if "ValueHypothesis" in query and "account_id" in str(params) and "LIMIT" in query:
                return MockResult([
                    {"hypothesis": {"id": "h1", "status": "validated", "confidence_score": 0.9, "estimated_impact_usd": 100000}},
                ])
            # Competitive query
            if "Competitor" in query:
                return MockResult([
                    {"total_competitors": 2, "total_wins": 5, "total_losses": 3},
                ])
            # ROI query
            if "ROICalculation" in query:
                return MockResult([])
            # Evidence query
            if "Evidence" in query:
                return MockResult([
                    {"evidence": {"id": "e1", "industry": "tech", "title": "Case 1"}},
                ])
            return MockResult([])

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=mock_run)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        orchestrator = IntelligenceOrchestrator(driver)
        result = await orchestrator.get_account_briefing(ACCOUNT_ID)

        assert result["account_id"] == ACCOUNT_ID
        assert "deal_readiness" in result
        assert "sections" in result
        assert "signals" in result["sections"]
        assert "value_hypotheses" in result["sections"]
        assert "competitive_landscape" in result["sections"]
        assert "evidence" in result["sections"]

    @pytest.mark.asyncio
    async def test_get_account_briefing_empty(self):
        """Test briefing with no data."""
        async def mock_run(query, params=None):
            return MockResult([])

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=mock_run)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        orchestrator = IntelligenceOrchestrator(driver)
        result = await orchestrator.get_account_briefing(ACCOUNT_ID)

        assert result["deal_readiness"]["score"] == 0.0
        assert result["deal_readiness"]["label"] == "not_ready"


class TestIntelligenceOrchestratorDealReadiness:
    """Test deal readiness endpoint."""

    @pytest.mark.asyncio
    async def test_get_deal_readiness(self):
        async def mock_run(query, params=None):
            if "Signal" in query:
                return MockResult([
                    {"signal": {"id": "s1"}},
                    {"signal": {"id": "s2"}},
                    {"signal": {"id": "s3"}},
                ])
            if "ValueHypothesis" in query and "LIMIT" in query:
                return MockResult([
                    {"hypothesis": {"id": "h1", "status": "validated"}},
                    {"hypothesis": {"id": "h2", "status": "draft"}},
                ])
            if "Competitor" in query:
                return MockResult([{"total_competitors": 2, "total_wins": 4, "total_losses": 2}])
            if "ROICalculation" in query:
                return MockResult([{"calculation": {"roi_pct_year1": 150}}])
            if "Evidence" in query:
                return MockResult([{"evidence": {"id": "e1"}}])
            if "Narrative" in query:
                return MockResult([{"narrative": {"id": "n1"}}])
            return MockResult([])

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=mock_run)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        orchestrator = IntelligenceOrchestrator(driver)
        result = await orchestrator.get_deal_readiness(ACCOUNT_ID)

        assert "score" in result
        assert "label" in result
        assert "components" in result
        assert "recommendations" in result
        assert result["account_id"] == ACCOUNT_ID


class TestIntelligenceOrchestratorPipeline:
    """Test pipeline intelligence."""

    @pytest.mark.asyncio
    async def test_get_pipeline_summary(self):
        driver = make_mock_driver([
            [
                {
                    "account_id": "acct-001",
                    "hypothesis_count": 5,
                    "avg_confidence": 0.85,
                    "total_impact": 500000,
                    "statuses": ["validated", "draft"],
                },
                {
                    "account_id": "acct-002",
                    "hypothesis_count": 3,
                    "avg_confidence": 0.72,
                    "total_impact": 200000,
                    "statuses": ["draft"],
                },
            ],
        ])

        orchestrator = IntelligenceOrchestrator(driver)
        result = await orchestrator.get_pipeline_summary()

        assert result["tenant_id"] in [TENANT_ID, "default"]  # Tenant from context or default
        assert result["summary"]["total_accounts"] == 2
        assert result["summary"]["total_hypotheses"] == 8
        assert result["summary"]["total_pipeline_value"] == 700000
        assert len(result["accounts"]) == 2
        assert result["accounts"][0]["has_validated"] is True
        assert result["accounts"][1]["has_validated"] is False

    @pytest.mark.asyncio
    async def test_get_pipeline_summary_empty(self):
        driver = make_mock_driver([[]])

        orchestrator = IntelligenceOrchestrator(driver)
        result = await orchestrator.get_pipeline_summary()

        assert result["summary"]["total_accounts"] == 0
        assert result["summary"]["total_pipeline_value"] == 0
        assert result["summary"]["avg_hypotheses_per_account"] == 0


# ===========================================================================
# Cross-Service Integration Tests (Mock-Based)
# ===========================================================================


class TestCrossServiceIntegration:
    """Integration tests verifying data flows between DIL services."""

    @pytest.mark.asyncio
    async def test_narrative_uses_hypothesis_data(self):
        """Verify narrative builder correctly processes hypothesis data."""
        driver = make_mock_driver([[{"narrative": {"id": "n1"}}]])
        svc = NarrativeBuilderService(driver)

        hypotheses = [
            {
                "hypothesis_text": "Reduce operational costs by 30%",
                "product_name": "AutoPlatform",
                "signal_name": "High manual processing costs",
                "confidence_score": 0.92,
                "estimated_impact_usd": 250000,
            },
            {
                "hypothesis_text": "Improve compliance rate to 99%",
                "product_name": "ComplianceGuard",
                "signal_name": "Regulatory audit failures",
                "confidence_score": 0.85,
                "estimated_impact_usd": 150000,
            },
        ]

        request = NarrativeRequest(account_id=ACCOUNT_ID)
        result = await svc.generate_narrative(
            request,
            tenant_id=TENANT_ID, hypotheses_data=hypotheses
        )

        assert result["metadata"]["hypothesis_count"] == 2
        assert result["metadata"]["total_impact"] == 400000
        vh_section = result["sections"]["value_hypotheses"]
        assert len(vh_section["items"]) == 2
        assert vh_section["items"][0]["hypothesis"] == "Reduce operational costs by 30%"

    @pytest.mark.asyncio
    async def test_narrative_uses_competitive_data(self):
        """Verify narrative builder correctly processes competitive data."""
        driver = make_mock_driver([[{"narrative": {"id": "n2"}}]])
        svc = NarrativeBuilderService(driver)

        competitive = {
            "overall_win_rate": 0.72,
            "key_differentiators": ["AI-powered analytics", "Real-time processing"],
            "landscape": [
                {"name": "CompetitorA", "market_position": "leader", "win_rate": 0.65, "threat_level": "high"},
            ],
        }

        request = NarrativeRequest(account_id=ACCOUNT_ID)
        result = await svc.generate_narrative(
            request,
            tenant_id=TENANT_ID, competitive_data=competitive
        )

        cp_section = result["sections"]["competitive_positioning"]
        assert "72%" in cp_section["summary"] or "0.72" in cp_section["summary"]
        assert len(cp_section["competitors"]) == 1

    @pytest.mark.asyncio
    async def test_narrative_uses_evidence_data(self):
        """Verify narrative builder correctly processes evidence data."""
        driver = make_mock_driver([[{"narrative": {"id": "n3"}}]])
        svc = NarrativeBuilderService(driver)

        evidence = [
            {"title": "Enterprise Success", "industry": "finance", "company_size": "large", "outcome_summary": "50% cost reduction"},
            {"title": "Mid-Market Win", "industry": "healthcare", "company_size": "mid-market", "outcome_summary": "99% compliance"},
        ]

        request = NarrativeRequest(account_id=ACCOUNT_ID)
        result = await svc.generate_narrative(
            request,
            tenant_id=TENANT_ID, evidence_data=evidence
        )

        ev_section = result["sections"]["evidence"]
        assert len(ev_section["case_studies"]) == 2
        assert ev_section["case_studies"][0]["title"] == "Enterprise Success"

    @pytest.mark.asyncio
    async def test_briefing_includes_readiness_recommendations(self):
        """Verify briefing includes actionable recommendations for gaps."""
        async def mock_run(query, params=None):
            return MockResult([])

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=mock_run)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        orchestrator = IntelligenceOrchestrator(driver)
        result = await orchestrator.get_account_briefing(ACCOUNT_ID)

        recs = result["deal_readiness"]["recommendations"]
        assert len(recs) >= 5
        assert any("signal" in r.lower() for r in recs)
        assert any("hypothesis" in r.lower() or "hypotheses" in r.lower() for r in recs)

    @pytest.mark.asyncio
    async def test_all_tones_produce_valid_narratives(self):
        """Verify all tone presets produce valid narrative output."""
        for tone in NarrativeTone:
            driver = make_mock_driver([[{"narrative": {"id": f"n-{tone.value}"}}]])
            svc = NarrativeBuilderService(driver)

            request = NarrativeRequest(
                account_id=ACCOUNT_ID,
                tone=tone.value,
            )
            result = await svc.generate_narrative(
                request,
                tenant_id=TENANT_ID,
                account_data={"name": "TestCo"},
                hypotheses_data=[{"estimated_impact_usd": 50000}],
            )

            assert result["tone"] == tone.value
            assert len(result["sections"]) == 7
            for section_key in SECTION_ORDER:
                assert section_key in result["sections"]
                assert "summary" in result["sections"][section_key]
