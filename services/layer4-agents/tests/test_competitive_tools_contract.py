from __future__ import annotations

import asyncio
import json
import sys
from types import SimpleNamespace

import pytest

import layer4_agents.tools.competitive_tools as module
from layer4_agents.contracts.artifacts import (
    CompetitiveBaseline,
    ConfidenceScore,
    EconomicDifference,
    EconomicDifferenceCategory,
)
from layer4_agents.tools.competitive_tools import (
    AnalyzeCompetitionInput,
    AnalyzeCompetitionTool,
    ConfigurationError,
)


class Result:
    def __init__(self, records):
        self.records = records

    async def data(self):
        return self.records


class Session:
    def __init__(self, records):
        self.records = records
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def run(self, query, params):
        self.calls.append((query, params))
        if isinstance(self.records, BaseException):
            raise self.records
        return Result(self.records)


class Driver:
    def __init__(self, records):
        self.session_value = Session(records)
        self.closed = 0

    def session(self, **_kwargs):
        return self.session_value

    async def close(self):
        self.closed += 1


@pytest.mark.asyncio
async def test_graph_query_requires_password_and_returns_tenant_scoped_facts(monkeypatch) -> None:
    monkeypatch.setattr(module, "get_settings", lambda: SimpleNamespace(neo4j_password=None))
    with pytest.raises(ConfigurationError, match="password is required"):
        await AnalyzeCompetitionTool()._query_graph_for_competitor(
            "Rival", "tenant", "bolt://graph", "neo4j", None, "database"
        )

    driver = Driver(
        [{"capabilities": ["Automation"], "risks": ["Delay"], "cost_items": ["License"]}]
    )
    graph = SimpleNamespace(driver=lambda uri, auth: driver)
    monkeypatch.setitem(sys.modules, "neo4j", SimpleNamespace(AsyncGraphDatabase=graph))
    result = await AnalyzeCompetitionTool()._query_graph_for_competitor(
        "Rival", "tenant", "bolt://graph", "neo4j", "password", "database"
    )
    assert result.capabilities == ["Automation"]
    query, params = driver.session_value.calls[0]
    assert "tenant_id" in query and params == {"name": "Rival", "tenant_id": "tenant"}
    assert driver.closed == 1


@pytest.mark.asyncio
async def test_graph_query_empty_error_and_cancellation(monkeypatch) -> None:
    for records in ([], RuntimeError("offline")):
        driver = Driver(records)
        graph = SimpleNamespace(driver=lambda *_args, _driver=driver, **_kwargs: _driver)
        monkeypatch.setitem(sys.modules, "neo4j", SimpleNamespace(AsyncGraphDatabase=graph))
        result = await AnalyzeCompetitionTool()._query_graph_for_competitor(
            "Rival", "tenant", "bolt://graph", "neo4j", "password", "database"
        )
        assert result.capabilities == [] and result.risks == [] and result.cost_items == []

    driver = Driver(asyncio.CancelledError())
    graph = SimpleNamespace(driver=lambda *_args, **_kwargs: driver)
    monkeypatch.setitem(sys.modules, "neo4j", SimpleNamespace(AsyncGraphDatabase=graph))
    with pytest.raises(asyncio.CancelledError):
        await AnalyzeCompetitionTool()._query_graph_for_competitor(
            "Rival", "tenant", "bolt://graph", "neo4j", "password", "database"
        )


def test_llm_provider_is_lazy_and_cached(monkeypatch) -> None:
    provider = object()
    calls = []
    monkeypatch.setattr(module, "get_llm_provider", lambda config: calls.append(config) or provider)
    tool = AnalyzeCompetitionTool({"llm_provider": "test"})
    assert tool._get_llm_provider() is provider and tool._get_llm_provider() is provider
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_llm_extraction_validates_structured_differences_and_skips_invalid() -> None:
    payload = {
        "differences": [
            {
                "category": "TIME_TO_VALUE",
                "description": "Faster deployment",
                "impact_direction": "FAVORS_US",
                "impact_magnitude": "-180 days",
                "confidence_score": 0.9,
                "is_unsupported_claim": False,
            },
            {
                "category": "NOT_A_CATEGORY",
                "description": "Invalid",
                "confidence_score": 0.5,
            },
        ]
    }

    class Provider:
        async def complete_text(self, **kwargs):
            assert kwargs["response_format"] == {"type": "json_object"}
            assert "Capabilities: Automation" in kwargs["messages"][0]["content"]
            return SimpleNamespace(content=json.dumps(payload))

    tool = AnalyzeCompetitionTool()
    tool._llm_provider = Provider()
    differences = await tool._extract_differences_via_llm(
        CompetitiveBaseline.ALTERNATIVE_VENDOR,
        "Rival",
        "Deal context",
        {"capabilities": ["Automation"], "risks": [], "cost_items": []},
    )
    assert len(differences) == 1
    assert differences[0].category == EconomicDifferenceCategory.TIME_TO_VALUE
    assert differences[0].confidence.score == 0.9


@pytest.mark.asyncio
async def test_llm_extraction_malformed_empty_failure_and_cancellation() -> None:
    class Provider:
        def __init__(self, value):
            self.value = value

        async def complete_text(self, **_kwargs):
            if isinstance(self.value, BaseException):
                raise self.value
            return SimpleNamespace(content=self.value)

    tool = AnalyzeCompetitionTool()
    tool._llm_provider = Provider("not-json")
    assert await tool._extract_differences_via_llm(CompetitiveBaseline.STATUS_QUO, "", "", {}) == []
    tool._llm_provider = Provider(None)
    assert await tool._extract_differences_via_llm(CompetitiveBaseline.STATUS_QUO, "", "", {}) == []
    tool._llm_provider = Provider(RuntimeError("offline"))
    result = await tool._extract_differences_via_llm(CompetitiveBaseline.INCUMBENT, "Rival", "", {})
    assert len(result) == 1 and result[0].is_unsupported_claim
    assert "manual review" in result[0].description
    tool._llm_provider = Provider(asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await tool._extract_differences_via_llm(CompetitiveBaseline.INCUMBENT, "Rival", "", {})


def difference(
    category=EconomicDifferenceCategory.CAPABILITY_TO_OUTCOME,
    description="Better outcome",
    direction="FAVORS_US",
    magnitude="",
    confidence=0.8,
    unsupported=False,
):
    return EconomicDifference(
        category=category,
        description=description,
        impact_direction=direction,
        impact_magnitude=magnitude,
        confidence=ConfidenceScore(score=confidence),
        is_unsupported_claim=unsupported,
    )


@pytest.mark.parametrize(
    ("baseline", "competitor", "label_part"),
    [
        (CompetitiveBaseline.STATUS_QUO, None, "Status Quo"),
        (CompetitiveBaseline.INCUMBENT, None, "current process"),
        (CompetitiveBaseline.ALTERNATIVE_VENDOR, "Rival", "Rival"),
        (CompetitiveBaseline.INTERNAL_BUILD, None, "Internal Build"),
    ],
)
def test_build_scenario_labels_confidence_ttv_and_assumptions(
    baseline, competitor, label_part
) -> None:
    differences = [
        difference(
            EconomicDifferenceCategory.TIME_TO_VALUE,
            "Faster",
            magnitude="-180 days",
            confidence=0.9,
        ),
        difference(description="Risk", direction="FAVORS_COMPETITOR", confidence=0.5),
    ]
    scenario = AnalyzeCompetitionTool()._build_scenario(baseline, competitor, differences)
    assert label_part in scenario.label
    assert scenario.time_to_value_days_delta == -180
    assert scenario.scenario_confidence.score == pytest.approx(0.7)
    assert scenario.key_assumptions == ["Faster"]
    empty = AnalyzeCompetitionTool()._build_scenario(baseline, competitor, [])
    assert empty.scenario_confidence.score == 0.5 and empty.time_to_value_days_delta is None


@pytest.mark.asyncio
async def test_execute_builds_artifact_for_all_requested_baselines() -> None:
    tool = AnalyzeCompetitionTool()
    graph_calls = []

    async def graph(**kwargs):
        graph_calls.append(kwargs)
        return {"capabilities": ["Automation"]}

    async def extract(baseline_type, competitor_name, **_kwargs):
        return [
            difference(
                description=f"Difference for {competitor_name}",
                confidence=0.75,
                unsupported=baseline_type == CompetitiveBaseline.INCUMBENT,
            )
        ]

    tool._query_graph_for_competitor = graph
    tool._extract_differences_via_llm = extract
    baselines = [
        CompetitiveBaseline.STATUS_QUO,
        CompetitiveBaseline.INCUMBENT,
        CompetitiveBaseline.ALTERNATIVE_VENDOR,
        CompetitiveBaseline.INTERNAL_BUILD,
    ]
    result = await tool.execute(
        AnalyzeCompetitionInput(
            context_artifact_id="context",
            tenant_id="tenant",
            workspace_id="workspace",
            known_incumbent="Incumbent",
            known_competitors=["Rival"],
            deal_context="Context",
            baselines_to_evaluate=baselines,
            neo4j_password="password",
        )
    )
    assert result.baselines_evaluated == baselines
    assert result.total_differences_found == 4
    assert result.unsupported_claim_count == 1
    assert len(result.artifact.competitive_scenarios) == 4
    assert result.artifact.overall_competitive_confidence.score == 0.75
    assert {call["competitor_name"] for call in graph_calls} == {"Incumbent", "Rival"}
    assert "1 claims require evidence" in result.agent_notes


@pytest.mark.asyncio
async def test_execute_empty_baselines_uses_neutral_confidence() -> None:
    result = await AnalyzeCompetitionTool().execute(
        AnalyzeCompetitionInput(
            context_artifact_id="context",
            tenant_id="tenant",
            workspace_id="workspace",
            baselines_to_evaluate=[],
        )
    )
    assert result.total_differences_found == 0
    assert result.artifact.overall_competitive_confidence.score == 0.5
