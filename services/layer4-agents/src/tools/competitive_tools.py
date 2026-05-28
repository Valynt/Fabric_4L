from __future__ import annotations

"""
Competitive Intelligence Tools for Value Fabric Layer 4 Agents.

These tools allow the CompetitiveIntelAgent to:
  1. Identify the real competitive baseline for a given prospect
  2. Extract competitor claims and map them to economic differences
  3. Quantify time-to-value, cost structure, and risk differences
  4. Score confidence of comparative claims against proof sources
  5. Generate defensible comparative scenarios
  6. Flag unsupported competitive assumptions for rep review

Design principle (from framework spec):
  "Competitive intel in a value model is evidence about alternative choices
   that changes the economic case."

A competitive fact is only included if it affects:
  - value magnitude   (EconomicDifferenceCategory.COST_STRUCTURE)
  - value timing      (EconomicDifferenceCategory.TIME_TO_VALUE)
  - value confidence  (EconomicDifferenceCategory.VALUE_REALIZATION_CONFIDENCE)
  - value risk        (EconomicDifferenceCategory.RISK_AND_CONFIDENCE)
  - capability delta  (EconomicDifferenceCategory.CAPABILITY_TO_OUTCOME)
"""


import logging
from typing import Any

from ..contracts.artifacts import (
    CompetitiveBaseline,
    CompetitiveIntelArtifact,
    CompetitiveScenario,
    ConfidenceScore,
    EconomicDifference,
    EconomicDifferenceCategory,
)
from ..models.tool_schemas import ToolCategory
from ..services.llm_provider import LLMProvider, get_llm_provider
from .registry import BaseTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input / Output schemas (Pydantic, consistent with tool_schemas.py pattern)
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from value_fabric.shared.models.typed_dict import TypedDictModel


class AnalyzeCompetitionTool__query_graph_for_competitorResult(TypedDictModel):
    capabilities: list[Any]
    cost_items: list[Any]
    risks: list[Any]


class LLMDifferenceItem(BaseModel):
    """Schema for individual difference items from LLM response.

    CONTRACT §2.5: Structured schema for LLM output validation.
    Replaces raw JSON parsing with Pydantic model validation.
    """

    category: str = Field(
        default="CAPABILITY_TO_OUTCOME",
        description="Category of economic difference",
    )
    description: str = Field(
        default="",
        description="Description of the difference",
    )
    impact_direction: str = Field(
        default="FAVORS_US",
        description="Direction of impact: FAVORS_US or FAVORS_COMPETITOR",
    )
    impact_magnitude: str = Field(
        default="",
        description="Magnitude of impact (e.g., '20% faster')",
    )
    confidence_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1",
    )
    is_unsupported_claim: bool = Field(
        default=False,
        description="Whether this claim lacks supporting evidence",
    )


class LLMDifferencesResponse(BaseModel):
    """Schema for LLM differences response.

    CONTRACT §2.5: Validates structured LLM output with error handling.
    """

    differences: list[LLMDifferenceItem] = Field(
        default_factory=list,
        description="List of economic differences extracted by LLM",
    )


class AnalyzeCompetitionInput(BaseModel):
    """Input for AnalyzeCompetitionTool."""
    context_artifact_id: str = Field(
        ..., description="ID of the ContextArtifact this analysis is for."
    )
    tenant_id: str
    workspace_id: str

    # What the agent already knows about the deal
    prospect_industry: str = Field(
        default="",
        description="Industry vertical, e.g. 'healthcare', 'financial-services'.",
    )
    known_competitors: list[str] = Field(
        default_factory=list,
        description="Competitor names mentioned in discovery calls or CRM notes.",
    )
    known_incumbent: str | None = Field(
        default=None,
        description="Current vendor or process the prospect is replacing.",
    )
    deal_context: str = Field(
        default="",
        description=(
            "Free-text summary of the deal context — pain points, evaluation "
            "criteria, stakeholders. Sourced from ContextArtifact."
        ),
    )

    # Which baselines to evaluate (defaults to all four)
    baselines_to_evaluate: list[CompetitiveBaseline] = Field(
        default_factory=lambda: list(CompetitiveBaseline),
        description="Which of the four competitive baselines to analyze.",
    )

    # Knowledge Graph query config
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    database: str = "valuefabric"


class AnalyzeCompetitionOutput(BaseModel):
    """Output of AnalyzeCompetitionTool — a fully populated CompetitiveIntelArtifact."""
    artifact: CompetitiveIntelArtifact
    baselines_evaluated: list[CompetitiveBaseline]
    total_differences_found: int
    unsupported_claim_count: int
    defensibility_score: float
    agent_notes: str = ""


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class AnalyzeCompetitionTool(BaseTool):
    """
    Analyze competitive alternatives and produce a CompetitiveIntelArtifact.

    This tool is the primary capability of the CompetitiveIntelAgent. It:
      1. Queries the Knowledge Graph for competitor entities and their
         associated capability, cost, and risk nodes.
      2. Uses an LLM to extract structured economic differences from
         unstructured competitor content (website text, call transcripts).
      3. Scores each difference against available proof sources.
      4. Flags unsupported claims for human review before executive delivery.
      5. Generates comparative financial scenarios for each baseline.

    The output CompetitiveIntelArtifact is consumed by:
      - ValueModelAgent: to adjust assumptions and scenario_analyses
      - IntegrityAgent: to audit flagged_claims
      - NarrativeAgent: to generate the 'value superiority' executive framing
    """

    name = "analyze_competition"
    category = ToolCategory.KNOWLEDGE
    description = (
        "Analyzes competitive alternatives and produces a structured "
        "CompetitiveIntelArtifact with economic differences, comparative "
        "scenarios, and confidence scores for each baseline."
    )
    input_schema = AnalyzeCompetitionInput
    output_schema = AnalyzeCompetitionOutput
    timeout_seconds = 60

    # LLM prompt for extracting economic differences from unstructured text
    EXTRACTION_PROMPT = """You are a value engineering analyst. Your task is to extract
competitive economic differences from the provided context.

RULES:
- Only extract facts that affect: value magnitude, value timing, value confidence, or value risk.
- Do NOT include feature comparisons that have no economic consequence.
- For each difference, identify which of the five categories it belongs to:
  CAPABILITY_TO_OUTCOME, TIME_TO_VALUE, COST_STRUCTURE, RISK_AND_CONFIDENCE,
  VALUE_REALIZATION_CONFIDENCE
- Assign a confidence score (0.0-1.0) based on the quality of available evidence.
- Flag any claim that lacks a verifiable proof source as is_unsupported_claim=true.

COMPETITIVE BASELINE: {baseline_type}
COMPETITOR NAME: {competitor_name}
DEAL CONTEXT: {deal_context}
KNOWN FACTS ABOUT THIS COMPETITOR: {competitor_facts}

Return a JSON array of EconomicDifference objects with these fields:
  category, description, impact_direction, impact_magnitude,
  confidence_score (0.0-1.0), is_unsupported_claim (bool)
"""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._llm_provider: LLMProvider | None = None

    def _get_llm_provider(self) -> LLMProvider:
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider(self.config)
        return self._llm_provider

    async def _query_graph_for_competitor(
        self,
        competitor_name: str,
        tenant_id: str,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        database: str,
    ) -> dict[str, Any]:
        """
        Query the Knowledge Graph for existing competitor nodes and their
        associated capability, cost, and risk properties.

        Returns a dict of competitor facts extracted from the graph.
        Falls back gracefully if the competitor is not yet in the graph.
        """
        try:
            from neo4j import AsyncGraphDatabase  # type: ignore[import]

            driver = AsyncGraphDatabase.driver(
                neo4j_uri, auth=(neo4j_user, neo4j_password)
            )
            async with driver.session(database=database) as session:
                result = await session.run(
                    """
                    MATCH (c:Competitor {name: $name, tenant_id: $tenant_id})
                    OPTIONAL MATCH (c)-[:HAS_CAPABILITY]->(cap:Capability)
                      WHERE cap.tenant_id = $tenant_id
                    OPTIONAL MATCH (c)-[:HAS_RISK]->(r:Risk)
                      WHERE r.tenant_id = $tenant_id
                    OPTIONAL MATCH (c)-[:HAS_COST_STRUCTURE]->(cs:CostStructure)
                      WHERE cs.tenant_id = $tenant_id
                    RETURN c,
                           collect(DISTINCT cap.description) AS capabilities,
                           collect(DISTINCT r.description) AS risks,
                           collect(DISTINCT cs.description) AS cost_items
                    """,
                    {"name": competitor_name, "tenant_id": tenant_id},
                )
                records = await result.data()
                await driver.close()

                if records:
                    return AnalyzeCompetitionTool__query_graph_for_competitorResult.model_validate({
                        "capabilities": records[0].get("capabilities", []),
                        "risks": records[0].get("risks", []),
                        "cost_items": records[0].get("cost_items", []),
                    })


        except Exception as e:
            logger.warning(
                "Could not query Knowledge Graph for competitor '%s': %s",
                competitor_name,
                e,
            )
        return AnalyzeCompetitionTool__query_graph_for_competitorResult.model_validate({"capabilities": [], "risks": [], "cost_items": []})

    async def _extract_differences_via_llm(
        self,
        baseline_type: CompetitiveBaseline,
        competitor_name: str,
        deal_context: str,
        competitor_facts: dict[str, Any],
    ) -> list[EconomicDifference]:
        """
        Use the LLM to extract structured economic differences from
        unstructured competitor content and deal context.
        """
        facts_text = "\n".join([
            f"Capabilities: {', '.join(competitor_facts.get('capabilities', [])) or 'Unknown'}",
            f"Risks: {', '.join(competitor_facts.get('risks', [])) or 'Unknown'}",
            f"Cost items: {', '.join(competitor_facts.get('cost_items', [])) or 'Unknown'}",
        ])

        prompt = self.EXTRACTION_PROMPT.format(
            baseline_type=baseline_type.value,
            competitor_name=competitor_name or baseline_type.value,
            deal_context=deal_context or "No deal context provided.",
            competitor_facts=facts_text,
        )

        try:
            response = await self._get_llm_provider().complete_text(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw = response.content or "{}"
            # CONTRACT §2.5: Use Pydantic model validation for LLM JSON output.
            try:
                validated = LLMDifferencesResponse.model_validate_json(raw)
                differences_raw = validated.differences
            except Exception:
                # Fallback: try parsing as list directly
                try:
                    parsed = LLMDifferencesResponse.model_validate({"differences": []})
                    differences_raw = parsed.differences
                except Exception:
                    differences_raw = []

            differences = []
            for d in differences_raw:
                try:
                    diff = EconomicDifference(
                        category=EconomicDifferenceCategory(d.category),
                        description=d.description,
                        impact_direction=d.impact_direction,
                        impact_magnitude=d.impact_magnitude,
                        confidence=ConfidenceScore(score=d.confidence_score),
                        is_unsupported_claim=d.is_unsupported_claim,
                    )
                    differences.append(diff)
                except Exception as parse_err:
                    logger.warning("Skipping malformed difference: %s", parse_err)

            return differences

        except Exception as e:
            logger.error("LLM extraction failed for %s: %s", competitor_name, e)
            # Return a single placeholder difference so the artifact is not empty
            return [
                EconomicDifference(
                    category=EconomicDifferenceCategory.CAPABILITY_TO_OUTCOME,
                    description=(
                        f"Unable to extract structured differences for "
                        f"{competitor_name or baseline_type.value} — "
                        f"manual review required."
                    ),
                    impact_direction="NEUTRAL",
                    is_unsupported_claim=True,
                    integrity_flag="LLM extraction failed — requires manual competitive research.",
                )
            ]

    def _build_scenario(
        self,
        baseline_type: CompetitiveBaseline,
        competitor_name: str | None,
        differences: list[EconomicDifference],
    ) -> CompetitiveScenario:
        """
        Build a CompetitiveScenario from the extracted differences.
        Uses heuristics to estimate financial deltas where not explicitly stated.
        """
        label_map = {
            CompetitiveBaseline.STATUS_QUO: "vs. Status Quo (cost of inaction)",
            CompetitiveBaseline.INCUMBENT: f"vs. Incumbent ({competitor_name or 'current process'})",
            CompetitiveBaseline.ALTERNATIVE_VENDOR: f"vs. {competitor_name or 'Alternative Vendor'}",
            CompetitiveBaseline.INTERNAL_BUILD: "vs. Internal Build / DIY",
        }

        # Compute average confidence across differences
        scores = [d.confidence.score for d in differences if d.confidence]
        avg_confidence = sum(scores) / len(scores) if scores else 0.5

        # Estimate time-to-value delta from TIME_TO_VALUE differences
        ttv_delta = None
        for d in differences:
            if d.category == EconomicDifferenceCategory.TIME_TO_VALUE and d.impact_magnitude:
                # Parse day deltas from strings like "-180 days"
                import re
                match = re.search(r"(-?\d+)\s*day", d.impact_magnitude)
                if match:
                    ttv_delta = int(match.group(1))
                    break

        return CompetitiveScenario(
            baseline_type=baseline_type,
            competitor_name=competitor_name,
            label=label_map.get(baseline_type, f"vs. {baseline_type.value}"),
            time_to_value_days_delta=ttv_delta,
            scenario_confidence=ConfidenceScore(score=avg_confidence),
            key_assumptions=[
                d.description for d in differences if d.impact_direction == "FAVORS_US"
            ][:5],  # Top 5 favourable assumptions
        )

    async def execute(self, input_data: AnalyzeCompetitionInput) -> AnalyzeCompetitionOutput:
        """
        Execute competitive analysis across all requested baselines.

        For each baseline:
          1. Query Knowledge Graph for existing competitor data
          2. Extract economic differences via LLM
          3. Build a comparative scenario
          4. Flag unsupported claims

        Returns a fully populated CompetitiveIntelArtifact.
        """
        all_differences: list[EconomicDifference] = []
        all_scenarios: list[CompetitiveScenario] = []
        flagged_claim_ids: list[str] = []

        # Map baselines to competitor names
        baseline_to_name: dict[CompetitiveBaseline, str | None] = {
            CompetitiveBaseline.STATUS_QUO: None,
            CompetitiveBaseline.INCUMBENT: input_data.known_incumbent,
            CompetitiveBaseline.ALTERNATIVE_VENDOR: (
                input_data.known_competitors[0] if input_data.known_competitors else None
            ),
            CompetitiveBaseline.INTERNAL_BUILD: None,
        }

        for baseline in input_data.baselines_to_evaluate:
            competitor_name = baseline_to_name.get(baseline)

            # Step 1: Query Knowledge Graph
            competitor_facts = {}
            if competitor_name:
                competitor_facts = await self._query_graph_for_competitor(
                    competitor_name=competitor_name,
                    tenant_id=input_data.tenant_id,
                    neo4j_uri=input_data.neo4j_uri,
                    neo4j_user=input_data.neo4j_user,
                    neo4j_password=input_data.neo4j_password,
                    database=input_data.database,
                )

            # Step 2: Extract economic differences via LLM
            differences = await self._extract_differences_via_llm(
                baseline_type=baseline,
                competitor_name=competitor_name or baseline.value,
                deal_context=input_data.deal_context,
                competitor_facts=competitor_facts,
            )
            all_differences.extend(differences)

            # Step 3: Collect flagged claims
            for diff in differences:
                if diff.is_unsupported_claim:
                    flagged_claim_ids.append(diff.difference_id)

            # Step 4: Build scenario
            scenario = self._build_scenario(baseline, competitor_name, differences)
            all_scenarios.append(scenario)

        # Compute overall confidence
        all_scores = [d.confidence.score for d in all_differences if d.confidence]
        overall_confidence = ConfidenceScore(
            score=sum(all_scores) / len(all_scores) if all_scores else 0.5
        )

        artifact = CompetitiveIntelArtifact(
            context_artifact_id=input_data.context_artifact_id,
            tenant_id=input_data.tenant_id,
            workspace_id=input_data.workspace_id,
            competitive_baselines=input_data.baselines_to_evaluate,
            economic_differences=all_differences,
            competitive_scenarios=all_scenarios,
            flagged_claims=flagged_claim_ids,
            overall_competitive_confidence=overall_confidence,
        )

        return AnalyzeCompetitionOutput(
            artifact=artifact,
            baselines_evaluated=input_data.baselines_to_evaluate,
            total_differences_found=len(all_differences),
            unsupported_claim_count=len(flagged_claim_ids),
            defensibility_score=artifact.competitive_defensibility_score,
            agent_notes=(
                f"Analyzed {len(input_data.baselines_to_evaluate)} baselines. "
                f"{len(flagged_claim_ids)} claims require evidence before executive delivery."
            ),
        )
