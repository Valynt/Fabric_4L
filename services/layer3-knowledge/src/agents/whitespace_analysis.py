"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Whitespace Analysis Agent.

Implements gap identification, maturity assessment, and expansion pathway generation.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from neo4j import AsyncDriver
from value_fabric.shared.models.typed_dict import TypedDictModel

from .base import AgentResult, BaseAgent
from ..db.query_execution import run_validated_query


class WhitespaceAnalysisAgent__identify_gapsResult(TypedDictModel):
    error: str
    gap_summary: Any | None = None
    gaps: list[Any]
    gaps_identified: Any | None = None
    prospect_company: Any | None = None

class WhitespaceAnalysisAgent__assess_maturityResult(TypedDictModel):
    assessments: list[Any]
    average_maturity_score: Any | None = None
    error: str
    prospect_company: Any | None = None
    total_capabilities_assessed: Any | None = None

class WhitespaceAnalysisAgent__generate_expansion_pathwaysResult(TypedDictModel):
    error: str
    pathways: list[Any]
    prospect_company: Any | None = None
    starting_capability: Any | None = None
    total_pathways: Any | None = None

logger = logging.getLogger(__name__)


class GapType(Enum):
    """Types of gaps identified during analysis."""

    MISSING_CAPABILITY = "missing_capability"
    UNDERUTILIZED_CAPABILITY = "underutilized_capability"
    MATURITY_GAP = "maturity_gap"
    INTEGRATION_GAP = "integration_gap"


class MaturityLevel(Enum):
    """Capability maturity levels (1-5 scale)."""

    AD_HOC = 1
    DEVELOPING = 2
    DEFINED = 3
    MANAGED = 4
    OPTIMIZING = 5


@dataclass
class IdentifiedGap:
    """Gap identified during whitespace analysis."""

    gap_id: str
    gap_type: GapType
    prospect_company: str
    required_capability_id: str
    required_capability_name: str
    current_state: str | None
    target_state: str
    maturity_gap: int | None
    business_impact: str
    estimated_value: float | None
    confidence_score: float
    supporting_evidence: list[str]
    related_pain_points: list[str]
    expansion_pathways: list[dict[str, Any]]


@dataclass
class AccountPlan:
    """Generated account plan."""

    plan_id: str
    prospect_company: str
    prospect_ticker: str | None
    generated_at: str
    status: str
    executive_summary: str
    key_insights: list[str]
    strategic_alignment_score: float
    identified_gaps: list[dict[str, Any]]
    expansion_pathways: list[dict[str, Any]]
    total_estimated_value: float


class WhitespaceAnalysisAgent(BaseAgent):
    """Agent for whitespace analysis and account planning.

    Capabilities:
    - gap_identification: Find missing/underutilized capabilities
    - maturity_assessment: Evaluate capability maturity gaps
    - expansion_pathway_generation: Identify expansion opportunities
    - account_plan_synthesis: Generate comprehensive account plans
    """

    def __init__(self, driver: AsyncDriver | None = None):
        """Initialize whitespace analysis agent.

        Args:
            driver: Neo4j async driver for graph operations
        """
        super().__init__("WhitespaceAnalysisAgent")
        self._driver = driver

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Execute whitespace analysis.

        Args:
            context: Must contain:
                - operation: 'gap_analysis', 'maturity_assessment', 'expansion_pathways', 'account_plan'
                - prospect_company: Company name
                - Optional: pain_points (list of pain point IDs)
                - Optional: capabilities (list of existing capability IDs)

        Returns:
            AgentResult with analysis results
        """
        start_time = time.time()

        try:
            operation = context.get("operation", "gap_analysis")
            prospect_company = context.get("prospect_company")

            if not prospect_company:
                return self._create_result(
                    status="failed",
                    output={},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    errors=["prospect_company is required"],
                )

            if operation == "gap_analysis":
                result = await self._identify_gaps(
                    prospect_company,
                    context.get("pain_points", []),
                    context.get("capabilities", []),
                )
            elif operation == "maturity_assessment":
                result = await self._assess_maturity(
                    prospect_company,
                    context.get("capabilities", []),
                )
            elif operation == "expansion_pathways":
                result = await self._generate_expansion_pathways(
                    prospect_company,
                    context.get("target_capability_id"),
                )
            elif operation == "account_plan":
                result = await self._synthesize_account_plan(
                    prospect_company,
                    context.get("prospect_ticker"),
                    context.get("pain_points", []),
                )
            else:
                return self._create_result(
                    status="failed",
                    output={},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    errors=[f"Unknown operation: {operation}"],
                )

            return self._create_result(
                status="success",
                output=result,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.error(f"Whitespace analysis failed: {e}")
            return self._create_result(
                status="failed",
                output={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                errors=[str(e)],
            )

    async def _identify_gaps(
        self,
        prospect_company: str,
        pain_points: list[str],
        existing_capabilities: list[str],
        tenant_id: str = "system",
    ) -> dict[str, Any]:
        """Identify gaps between required and existing capabilities.

        Cypher pattern:
        MATCH (pain:PainPoint)-[:REQUIRES]->(c:Capability)
        WHERE pain.id IN $pain_points
        AND c.id NOT IN $existing_capabilities
        AND pain.tenant_id = $tenant_id

        Args:
            prospect_company: Company being analyzed
            pain_points: List of pain point IDs
            existing_capabilities: List of existing capability IDs
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with identified gaps
        """
        if not self._driver:
            return WhitespaceAnalysisAgent__identify_gapsResult.model_validate({"gaps": [], "error": "No database driver"})

        # Query for missing capabilities (with tenant isolation)
        missing_query = """
        MATCH (pain:ExtractedPainPoint {id: $pain_id, tenant_id: $tenant_id})-[:requires]->(c:Capability)
        WHERE c.tenant_id = $tenant_id AND NOT c.id IN $existing_capabilities
        RETURN c.id as capability_id, c.name as capability_name,
               pain.id as pain_id, pain.description as pain_description
        """

        gaps = []

        async with self._driver.session() as session:
            for pain_id in pain_points:
                result = await run_validated_query(session,
                    missing_query,
                    {
                        "pain_id": pain_id,
                        "existing_capabilities": existing_capabilities,
                        "tenant_id": tenant_id,
                    },
                )
                async for record in result:
                    gaps.append(
                        {
                            "gap_id": f"gap-{record['capability_id']}",
                            "gap_type": GapType.MISSING_CAPABILITY.value,
                            "prospect_company": prospect_company,
                            "required_capability_id": record["capability_id"],
                            "required_capability_name": record["capability_name"],
                            "current_state": "Not implemented",
                            "target_state": f"Implement {record['capability_name']}",
                            "business_impact": record["pain_description"],
                            "confidence_score": 0.8,
                            "supporting_evidence": [record["pain_description"]],
                            "related_pain_points": [pain_id],
                        }
                    )

        return WhitespaceAnalysisAgent__identify_gapsResult.model_validate({
            "prospect_company": prospect_company,
            "gaps_identified": len(gaps),
            "gaps": gaps,
            "gap_summary": self._summarize_gaps_by_category(gaps),
        })


    async def _assess_maturity(
        self,
        prospect_company: str,
        capabilities: list[str],
        tenant_id: str = "system",
    ) -> dict[str, Any]:
        """Assess maturity level of existing capabilities.

        Args:
            prospect_company: Company being analyzed
            capabilities: List of capability IDs to assess
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with maturity assessments
        """
        if not self._driver:
            return WhitespaceAnalysisAgent__assess_maturityResult.model_validate({"assessments": [], "error": "No database driver"})

        # Query capability maturity indicators (with tenant isolation)
        maturity_query = """
        MATCH (c:Capability {id: $cap_id})
        WHERE c.tenant_id = $tenant_id
        RETURN c.id as id, c.name as name, c.maturity_level as maturity_level,
               c.maturity_indicators as indicators
        """

        assessments = []

        async with self._driver.session() as session:
            for cap_id in capabilities:
                result = await run_validated_query(session, maturity_query, {"cap_id": cap_id, "tenant_id": tenant_id})
                record = await result.single()

                if record:
                    current_maturity = record.get("maturity_level", "DEVELOPING")
                    target_maturity = MaturityLevel.MANAGED.name

                    assessments.append(
                        {
                            "capability_id": cap_id,
                            "capability_name": record["name"],
                            "current_maturity": current_maturity,
                            "target_maturity": target_maturity,
                            "maturity_gap": self._calculate_maturity_gap(
                                current_maturity, target_maturity
                            ),
                            "indicators": record.get("indicators", []),
                        }
                    )

        return WhitespaceAnalysisAgent__assess_maturityResult.model_validate({
            "prospect_company": prospect_company,
            "total_capabilities_assessed": len(assessments),
            "assessments": assessments,
            "average_maturity_score": self._calculate_average_maturity(assessments),
        })


    async def _generate_expansion_pathways(
        self,
        prospect_company: str,
        target_capability_id: str | None,
        tenant_id: str = "system",
    ) -> dict[str, Any]:
        """Generate expansion pathways from a capability.

        Cypher pattern:
        MATCH (c:Capability)<-[:requires]-(uc:UseCase)
        OPTIONAL MATCH (uc)-[:delivers]->(vd:ValueDriver)

        Args:
            prospect_company: Company being analyzed
            target_capability_id: Starting capability ID
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with expansion pathways
        """
        if not self._driver:
            return WhitespaceAnalysisAgent__generate_expansion_pathwaysResult.model_validate({"pathways": [], "error": "No database driver"})

        if not target_capability_id:
            return WhitespaceAnalysisAgent__generate_expansion_pathwaysResult.model_validate({"pathways": [], "error": "target_capability_id required"})

        # Query for expansion pathways (with tenant isolation)
        expansion_query = """
        MATCH (c:Capability {id: $cap_id})<-[:enables|requires]-(uc:UseCase)
        WHERE c.tenant_id = $tenant_id AND uc.tenant_id = $tenant_id
        OPTIONAL MATCH (uc)-[:delivers|involves]->(vd:ValueDriver)
        WHERE vd.tenant_id = $tenant_id
        OPTIONAL MATCH (uc)-[:involves]->(p:Persona)
        WHERE p.tenant_id = $tenant_id
        RETURN uc.id as use_case_id, uc.name as use_case_name,
               uc.implementation_complexity as complexity,
               collect(DISTINCT vd.name) as value_drivers,
               collect(DISTINCT p.name) as target_personas
        ORDER BY uc.implementation_complexity
        """

        pathways = []

        async with self._driver.session() as session:
            result = await run_validated_query(session,
                expansion_query, {"cap_id": target_capability_id, "tenant_id": tenant_id}
            )
            async for record in result:
                pathways.append(
                    {
                        "use_case_id": record["use_case_id"],
                        "use_case_name": record["use_case_name"],
                        "implementation_complexity": record.get("complexity", "Medium"),
                        "value_drivers": record["value_drivers"],
                        "target_personas": record["target_personas"],
                        "estimated_value": self._estimate_value(
                            record["value_drivers"]
                        ),
                    }
                )

        return WhitespaceAnalysisAgent__generate_expansion_pathwaysResult.model_validate({
            "prospect_company": prospect_company,
            "starting_capability": target_capability_id,
            "pathways": pathways,
            "total_pathways": len(pathways),
        })


    async def _synthesize_account_plan(
        self,
        prospect_company: str,
        prospect_ticker: str | None,
        pain_points: list[str],
        tenant_id: str = "system",
    ) -> dict[str, Any]:
        """Synthesize comprehensive account plan.

        Args:
            prospect_company: Company name
            prospect_ticker: Optional stock ticker
            pain_points: List of pain point IDs
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with account plan
        """
        # Run gap analysis
        gap_analysis = await self._identify_gaps(
            prospect_company, pain_points, [], tenant_id
        )
        # Calculate total value
        total_value = sum(
            gap.get("estimated_value", 0) for gap in gap_analysis.get("gaps", [])
        )

        # Generate key insights
        insights = self._generate_insights(gap_analysis.get("gaps", []))

        account_plan = {
            "plan_id": f"plan-{prospect_company.lower().replace(' ', '-')}",
            "prospect_company": prospect_company,
            "prospect_ticker": prospect_ticker,
            "generated_at": datetime.utcnow().isoformat(),
            "status": "draft",
            "executive_summary": f"Analysis of {prospect_company} identified {gap_analysis['gaps_identified']} capability gaps",
            "key_insights": insights,
            "strategic_alignment_score": 0.75,
            "identified_gaps": gap_analysis.get("gaps", []),
            "gap_summary": gap_analysis.get("gap_summary", {}),
            "total_estimated_value": total_value,
        }

        return account_plan

    def _summarize_gaps_by_category(self, gaps: list[dict]) -> dict[str, int]:
        """Summarize gaps by category."""
        summary = {}
        for gap in gaps:
            gap_type = gap.get("gap_type", "unknown")
            summary[gap_type] = summary.get(gap_type, 0) + 1
        return summary

    def _calculate_maturity_gap(self, current: str, target: str) -> int | None:
        """Calculate numeric gap between maturity levels."""
        try:
            current_level = MaturityLevel[current].value
            target_level = MaturityLevel[target].value
            return max(0, target_level - current_level)
        except (KeyError, ValueError):
            return None

    def _calculate_average_maturity(self, assessments: list[dict]) -> float:
        """Calculate average maturity score."""
        if not assessments:
            return 0.0

        scores = []
        for assessment in assessments:
            maturity = assessment.get("current_maturity", "DEVELOPING")
            try:
                scores.append(MaturityLevel[maturity].value)
            except KeyError:
                scores.append(2)  # Default to DEVELOPING

        return sum(scores) / len(scores) if scores else 0.0

    def _estimate_value(self, value_drivers: list[str]) -> float:
        """Estimate monetary value from value drivers."""
        # Placeholder: In production, this would use actual value formulas
        base_value = 100000  # $100K base
        multiplier = len(value_drivers) if value_drivers else 1
        return base_value * multiplier

    def _generate_insights(self, gaps: list[dict]) -> list[str]:
        """Generate key insights from gap analysis."""
        insights = []

        if gaps:
            insights.append(
                f"Identified {len(gaps)} capability gaps requiring attention"
            )

            # Group by type
            by_type = {}
            for gap in gaps:
                gap_type = gap.get("gap_type", "unknown")
                by_type[gap_type] = by_type.get(gap_type, 0) + 1

            for gap_type, count in by_type.items():
                insights.append(f"{count} gaps classified as {gap_type}")

        return insights
