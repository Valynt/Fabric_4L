from __future__ import annotations

"""
Data Intelligence Layer Phase 2 — L4 Tests.

Tests for:
  - Task 2.1: Value Hypothesis Engine (value_hypothesis_engine.py)

These tests use mock Neo4j drivers to isolate service logic from the database.
Run with: pytest tests/test_value_hypothesis.py --noconftest -v
"""


import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from layer4_agents.services.value_hypothesis_engine import (
    RANKING_WEIGHTS,
    HypothesisStatus,
    RankingStrategy,
    ValueHypothesis,
    ValueHypothesisEngine,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_ID = "test-tenant-001"
ACCOUNT_ID = "acct-001"


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


def make_mock_driver(responses: list[list[dict[str, Any]]] | None = None):
    """Create a mock Neo4j driver that returns different data per call.

    Args:
        responses: List of response lists, one per session.run() call.
    """
    if responses is None:
        responses = [[]]

    call_index = 0

    async def mock_run(query, params=None):
        nonlocal call_index
        data = responses[min(call_index, len(responses) - 1)]
        call_index += 1
        return MockResult(data)

    mock_session = AsyncMock()
    mock_session.run = mock_run
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)

    return mock_driver


# ===========================================================================
# Enum Tests
# ===========================================================================


class TestHypothesisStatus:
    """Tests for HypothesisStatus enum."""

    def test_all_statuses(self):
        assert HypothesisStatus.DRAFT == "draft"
        assert HypothesisStatus.VALIDATED == "validated"
        assert HypothesisStatus.REJECTED == "rejected"
        assert HypothesisStatus.CONVERTED == "converted"

    def test_status_from_string(self):
        assert HypothesisStatus("draft") == HypothesisStatus.DRAFT


class TestRankingStrategy:
    """Tests for RankingStrategy enum."""

    def test_all_strategies(self):
        assert RankingStrategy.IMPACT == "impact"
        assert RankingStrategy.CONFIDENCE == "confidence"
        assert RankingStrategy.BALANCED == "balanced"
        assert RankingStrategy.EVIDENCE == "evidence"
        assert RankingStrategy.RECENCY == "recency"

    def test_weights_defined_for_all_strategies(self):
        for strategy in RankingStrategy:
            if strategy != RankingStrategy.RECENCY:
                assert strategy in RANKING_WEIGHTS


# ===========================================================================
# ValueHypothesis Data Model Tests
# ===========================================================================


class TestValueHypothesis:
    """Tests for ValueHypothesis data model."""

    def test_default_values(self):
        h = ValueHypothesis(
            tenant_id=TENANT_ID,
            account_id=ACCOUNT_ID,
            signal_id="sig-1",
            signal_name="Slow deployment",
            product_id="prod-1",
            product_name="Platform X",
            capability_id="cap-1",
            capability_name="CI/CD Automation",
            hypothesis_text="Deploy faster with Platform X",
        )
        assert h.confidence_score == 0.5
        assert h.status == HypothesisStatus.DRAFT
        assert h.evidence_ids == []
        assert h.estimated_impact_usd == 0.0
        assert h.impact_timeframe_days == 365

    def test_to_node_properties(self):
        h = ValueHypothesis(
            tenant_id=TENANT_ID,
            account_id=ACCOUNT_ID,
            signal_id="sig-1",
            signal_name="Test signal",
            product_id="prod-1",
            product_name="Test product",
            capability_id="cap-1",
            capability_name="Test cap",
            hypothesis_text="Test hypothesis",
            confidence_score=0.8,
            estimated_impact_usd=100000.0,
        )
        props = h.to_node_properties()

        assert props["tenant_id"] == TENANT_ID
        assert props["account_id"] == ACCOUNT_ID
        assert props["confidence_score"] == 0.8
        assert props["estimated_impact_usd"] == 100000.0
        assert props["entity_type"] == "ValueHypothesis"
        assert "id" in props
        assert "created_at" in props

    def test_id_is_uuid(self):
        h = ValueHypothesis(
            tenant_id=TENANT_ID,
            account_id=ACCOUNT_ID,
            signal_id="s",
            signal_name="s",
            product_id="p",
            product_name="p",
            capability_id="c",
            capability_name="c",
            hypothesis_text="t",
        )
        # Should be a valid UUID
        uuid.UUID(h.id)


# ===========================================================================
# Ranking Tests
# ===========================================================================


class TestRanking:
    """Tests for hypothesis ranking logic."""

    def _make_hypotheses(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "h1",
                "confidence_score": 0.9,
                "estimated_impact_usd": 50000,
                "evidence_ids": ["e1", "e2"],
                "created_at": "2026-01-01T00:00:00",
            },
            {
                "id": "h2",
                "confidence_score": 0.5,
                "estimated_impact_usd": 200000,
                "evidence_ids": ["e1"],
                "created_at": "2026-04-01T00:00:00",
            },
            {
                "id": "h3",
                "confidence_score": 0.7,
                "estimated_impact_usd": 100000,
                "evidence_ids": ["e1", "e2", "e3"],
                "created_at": "2026-02-15T00:00:00",
            },
        ]

    def test_impact_ranking(self):
        engine = ValueHypothesisEngine(MagicMock())
        hypotheses = self._make_hypotheses()

        ranked = engine.rank_hypotheses(hypotheses, RankingStrategy.IMPACT)

        # h2 has highest impact (200k), should be first
        assert ranked[0]["id"] == "h2"

    def test_confidence_ranking(self):
        engine = ValueHypothesisEngine(MagicMock())
        hypotheses = self._make_hypotheses()

        ranked = engine.rank_hypotheses(hypotheses, RankingStrategy.CONFIDENCE)

        # h1 has highest confidence (0.9), should be first
        assert ranked[0]["id"] == "h1"

    def test_evidence_ranking(self):
        engine = ValueHypothesisEngine(MagicMock())
        hypotheses = self._make_hypotheses()

        ranked = engine.rank_hypotheses(hypotheses, RankingStrategy.EVIDENCE)

        # h3 has most evidence (3), should be first
        assert ranked[0]["id"] == "h3"

    def test_recency_ranking(self):
        engine = ValueHypothesisEngine(MagicMock())
        hypotheses = self._make_hypotheses()

        ranked = engine.rank_hypotheses(hypotheses, RankingStrategy.RECENCY)

        # h2 has most recent date, should be first
        assert ranked[0]["id"] == "h2"

    def test_balanced_ranking_adds_composite_score(self):
        engine = ValueHypothesisEngine(MagicMock())
        hypotheses = self._make_hypotheses()

        ranked = engine.rank_hypotheses(hypotheses, RankingStrategy.BALANCED)

        for h in ranked:
            assert "composite_score" in h
            assert 0 <= h["composite_score"] <= 1.1  # Allow slight rounding

    def test_string_strategy(self):
        engine = ValueHypothesisEngine(MagicMock())
        hypotheses = self._make_hypotheses()

        # Should accept string strategy
        ranked = engine.rank_hypotheses(hypotheses, "balanced")
        assert len(ranked) == 3

    def test_empty_hypotheses(self):
        engine = ValueHypothesisEngine(MagicMock())
        ranked = engine.rank_hypotheses([], RankingStrategy.BALANCED)
        assert ranked == []


# ===========================================================================
# Engine Generation Tests
# ===========================================================================


class TestHypothesisGeneration:
    """Tests for hypothesis generation."""

    @pytest.mark.asyncio
    async def test_generate_hypotheses(self):
        """Test that generate_hypotheses produces hypotheses from graph paths."""
        # Response 1: signal→capability→product paths
        paths = [
            {
                "signal": {
                    "id": "sig-1",
                    "name": "Slow deployment",
                    "confidence_score": 0.8,
                    "industry": "technology",
                    "impact_value": 150000,
                },
                "capability": {"id": "cap-1", "name": "CI/CD Automation"},
                "product": {"id": "prod-1", "name": "Platform X", "category": "DevOps"},
                "match_score": 0.72,
            },
        ]
        # Response 2: evidence query
        evidence = [{"evidence_id": "ev-1"}, {"evidence_id": "ev-2"}]
        # Response 3: store hypothesis
        stored = [{
            "hypothesis": {
                "id": "h-new",
                "tenant_id": TENANT_ID,
                "account_id": ACCOUNT_ID,
                "signal_id": "sig-1",
                "signal_name": "Slow deployment",
                "product_id": "prod-1",
                "product_name": "Platform X",
                "capability_id": "cap-1",
                "capability_name": "CI/CD Automation",
                "hypothesis_text": "test",
                "confidence_score": 0.72,
                "estimated_impact_usd": 150000,
                "evidence_ids": ["ev-1", "ev-2"],
                "status": "draft",
                "created_at": "2026-04-01T00:00:00",
                "updated_at": "2026-04-01T00:00:00",
            }
        }]

        driver = make_mock_driver([paths, evidence, stored])
        engine = ValueHypothesisEngine(driver)

        result = await engine.generate_hypotheses(TENANT_ID, ACCOUNT_ID)

        assert len(result) == 1
        assert result[0]["signal_id"] == "sig-1"
        assert result[0]["product_id"] == "prod-1"

    @pytest.mark.asyncio
    async def test_generate_no_paths(self):
        """Test generation with no signal→product paths."""
        driver = make_mock_driver([[]])  # Empty paths
        engine = ValueHypothesisEngine(driver)

        result = await engine.generate_hypotheses(TENANT_ID, ACCOUNT_ID)
        assert result == []


# ===========================================================================
# Engine CRUD Tests
# ===========================================================================


class TestHypothesisCRUD:
    """Tests for hypothesis CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_hypothesis(self):
        data = [{
            "hypothesis": {
                "id": "h1",
                "tenant_id": TENANT_ID,
                "signal_name": "Test signal",
                "product_name": "Test product",
                "confidence_score": 0.8,
            },
            "signal": {"id": "sig-1", "name": "Test signal"},
            "product": {"id": "prod-1", "name": "Test product"},
            "evidence": [{"id": "ev-1", "title": "Case Study 1", "industry": "tech"}],
        }]
        driver = make_mock_driver([data])
        engine = ValueHypothesisEngine(driver)

        result = await engine.get_hypothesis(TENANT_ID, "h1")

        assert result is not None
        assert result["signal_detail"]["name"] == "Test signal"
        assert result["product_detail"]["name"] == "Test product"
        assert len(result["evidence_detail"]) == 1

    @pytest.mark.asyncio
    async def test_get_nonexistent_hypothesis(self):
        driver = make_mock_driver([[{
            "hypothesis": None,
            "signal": None,
            "product": None,
            "evidence": [],
        }]])
        engine = ValueHypothesisEngine(driver)

        result = await engine.get_hypothesis(TENANT_ID, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_account_hypotheses(self):
        async def mock_run(query, params=None):
            if "AS total" in query:
                return MockResult([{"total": 2}])
            return MockResult([
                {"hypothesis": {"id": "h1", "confidence_score": 0.9}},
                {"hypothesis": {"id": "h2", "confidence_score": 0.7}},
            ])

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=mock_run)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        engine = ValueHypothesisEngine(driver)
        result = await engine.get_account_hypotheses(TENANT_ID, ACCOUNT_ID)

        assert result["total"] == 2
        assert len(result["hypotheses"]) == 2

    @pytest.mark.asyncio
    async def test_validate_hypothesis(self):
        driver = make_mock_driver([[{
            "hypothesis": {
                "id": "h1",
                "status": "validated",
                "confidence_score": 0.9,
                "last_feedback": "Looks good",
            }
        }]])
        engine = ValueHypothesisEngine(driver)

        result = await engine.validate_hypothesis(
            TENANT_ID,
            "h1",
            feedback="Looks good",
            new_status="validated",
            confidence_adjustment=0.1,
        )

        assert result is not None
        assert result["status"] == "validated"

    @pytest.mark.asyncio
    async def test_validate_nonexistent(self):
        driver = make_mock_driver([[]])  # No records
        # Need to handle single() returning None
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=MockResult([]))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        engine = ValueHypothesisEngine(driver)
        result = await engine.validate_hypothesis(
            TENANT_ID, "nonexistent", feedback="test"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_post_validation_orchestration_returns_driver_linkage(self):
        driver = make_mock_driver([[{
            "driver": {"id": "driver_h1", "name": "Ops Efficiency"},
            "lever": {"id": "lever_h1", "name": "Ops Efficiency"},
            "linkage_id": "vh:h1:driver:driver_h1",
        }]])
        engine = ValueHypothesisEngine(driver)
        result = await engine.orchestrate_post_validation(TENANT_ID, "h1", new_status="validated")
        assert result is not None
        assert result["created"] is True
        assert result["drivers"][0]["id"] == "driver_h1"
        assert result["linkages"][0]["hypothesis_id"] == "h1"

    @pytest.mark.asyncio
    async def test_delete_hypothesis(self):
        driver = make_mock_driver([[{"deleted": 1}]])
        engine = ValueHypothesisEngine(driver)

        result = await engine.delete_hypothesis(TENANT_ID, "h1")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        driver = make_mock_driver([[{"deleted": 0}]])
        engine = ValueHypothesisEngine(driver)

        result = await engine.delete_hypothesis(TENANT_ID, "nonexistent")
        assert result is False


# ===========================================================================
# Analytics Tests
# ===========================================================================


class TestHypothesisSummary:
    """Tests for hypothesis summary analytics."""

    @pytest.mark.asyncio
    async def test_summary_with_data(self):
        driver = make_mock_driver([[{
            "total": 20,
            "draft_count": 10,
            "validated_count": 5,
            "rejected_count": 3,
            "converted_count": 2,
            "avg_confidence": 0.72,
            "total_estimated_impact": 2500000.0,
            "avg_estimated_impact": 125000.0,
            "unique_products": 4,
            "unique_accounts": 8,
        }]])
        engine = ValueHypothesisEngine(driver)

        result = await engine.get_hypothesis_summary(TENANT_ID)

        assert result["total"] == 20
        assert result["by_status"]["draft"] == 10
        assert result["by_status"]["converted"] == 2
        assert result["avg_confidence"] == 0.72
        assert result["total_estimated_impact"] == 2500000.0

    @pytest.mark.asyncio
    async def test_summary_empty(self):
        driver = make_mock_driver([[]])
        # Need single() to return None
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=MockResult([]))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)

        engine = ValueHypothesisEngine(driver)
        result = await engine.get_hypothesis_summary(TENANT_ID)

        assert result["total"] == 0
