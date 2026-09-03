from __future__ import annotations

"""Whitespace Analysis workflow implementation."""


import asyncio
import json
import logging
from typing import Any

from value_fabric.shared.identity.context import require_context
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..agents.base import AgentResult
from ..harness.prompt_registry import get_prompt_registry
from ..metrics import get_metrics
from ..models.agent_state import (
    GapAnalysis,
    WhitespaceAgentState,
    WhitespaceInputData,
    WorkflowStatus,
)
from ..models.workflow_config import WHITESPACE_WORKFLOW_CONFIG
from ..services.governed_llm_client import GovernedLLMClient
from ..services.llm_budget_guardrails import LLMBudgetExceededError, get_llm_budget_guardrails
from ..services.llm_output_parser import parse_llm_json
from ..services.llm_provider import get_llm_provider
from ..tools.registry import ToolRegistry, ToolResult
from .base import BaseWorkflow


def _unwrap_tool_data(result: Any) -> dict[str, Any]:
    """Extract data dict from ToolResult or return dict fallback."""
    if isinstance(result, ToolResult) and result.status == "success":
        return result.data or {}
    if isinstance(result, dict):
        return result
    return {}


class WhitespaceAnalysisWorkflow__execute_analyze_prospectResult(TypedDictModel):
    analysis_confidence: float | None = None
    company_size: Any | None = None
    error: str
    extracted_needs: Any | None = None
    industry_context: Any | None = None
    need_count: Any | None = None

class WhitespaceAnalysisWorkflow__execute_query_capabilitiesResult(TypedDictModel):
    capabilities: Any
    capability_count: Any
    categories: list[Any]

class WhitespaceAnalysisWorkflow__execute_identify_gapsResult(TypedDictModel):
    coverage_percentage: Any | None = None
    error: str
    gap_count: Any | None = None
    gaps: list[Any]

class WhitespaceAnalysisWorkflow__execute_score_opportunityResult(TypedDictModel):
    assessment: str
    factors: dict[str, Any] | None = None
    opportunity_score: Any | None = None
    recommendations: Any | None = None
    score: int


class ExtractedNeedsResponse(TypedDictModel):
    """Schema for LLM-extracted prospect needs."""

    needs: list[str]

logger = logging.getLogger(__name__)


class WhitespaceAnalysisWorkflow(BaseWorkflow):
    """Workflow for identifying gaps between prospect needs and solution capabilities.

    Pipeline:
    1. Analyze prospect needs from description and CRM data
    2. Query solution capabilities from knowledge graph
    3. Identify gaps through semantic matching
    4. Score opportunity potential
    5. Generate recommendations

    Example:
        workflow = WhitespaceAnalysisWorkflow(tool_registry)
        initial_state = workflow.create_initial_state({
            "prospect_id": "prospect-001",
            "prospect_needs": "We need to automate our invoice processing..."
        })
        result = await workflow.run(initial_state)
    """

    def __init__(self, tool_registry: ToolRegistry, checkpoint_saver=None):
        """Initialize Whitespace Analysis workflow."""
        super().__init__(
            config=WHITESPACE_WORKFLOW_CONFIG,
            tool_registry=tool_registry,
            checkpoint_saver=checkpoint_saver,
        )

    def _get_state_type(self):
        """Return Whitespace-specific state type."""
        return WhitespaceAgentState

    def create_initial_state(
        self,
        input_data: dict[str, Any],
        *,
        tenant_id: str,
        run_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> WhitespaceAgentState:
        """Create initial state from input data."""
        from uuid import uuid4

        from ..models.run_envelope import RunEnvelope

        whitespace_input = WhitespaceInputData(**input_data)
        wf_id = workflow_id or str(uuid4())
        r_id = run_id or str(uuid4())
        t_id = trace_id or str(uuid4())

        envelope = RunEnvelope(
            run_id=r_id,
            workflow_id=wf_id,
            trace_id=t_id,
            tenant_id=str(tenant_id) if tenant_id else "",
            workflow_type=self.config.workflow_type,
        )

        return WhitespaceAgentState(  # type: ignore[call-arg]
            workflow_id=wf_id,
            run_id=r_id,
            trace_id=t_id,
            tenant_id=str(tenant_id) if tenant_id else "",
            workflow_type=self.config.workflow_type,  # type: ignore[arg-type]
            status=WorkflowStatus.PENDING,
            whitespace_input=whitespace_input,
            input_data=input_data,
            output_data={},
            errors=[],
            metadata={"workflow_name": self.name},
            run_envelope=envelope,
        )

    async def _execute_tool(
        self, tool_name: str, state: WhitespaceAgentState, config: dict[str, Any]  # type: ignore[override]
    ) -> dict[str, Any]:
        """Execute tool with Whitespace-specific input building."""

        if tool_name == "analyze_prospect_needs":
            return await self._execute_analyze_prospect(state)

        elif tool_name == "query_graph":
            return await self._execute_query_capabilities(state)

        elif tool_name == "identify_gaps":
            return await self._execute_identify_gaps(state)

        elif tool_name == "score_opportunity":
            return await self._execute_score_opportunity(state)

        elif tool_name == "generate_hypotheses":
            return await self._execute_llm_hypotheses(state)

        return await super()._execute_tool(tool_name, state, config)

    async def _execute_analyze_prospect(self, state: WhitespaceAgentState) -> dict[str, Any]:
        """Analyze prospect needs using LLM extraction."""
        if not state.whitespace_input:
            return WhitespaceAnalysisWorkflow__execute_analyze_prospectResult.model_validate({"error": "No whitespace input configured"})  # type: ignore[no-any-return]

        needs_text = state.whitespace_input.prospect_needs

        # Get prospect data for context
        prospect_data = await self.tool_registry.execute(
            "get_prospect_data",
            {"prospect_id": state.whitespace_input.prospect_id, "data_types": ["profile"]},
        )

        profile = prospect_data.get("profile", {})

        # Budget guardrail pre-check (throttle / escalation) before dispatching.
        initial_model = "gpt-4o-mini"
        decision = await get_llm_budget_guardrails().precheck_or_raise(initial_model)
        if decision.throttle_seconds > 0:
            await asyncio.sleep(decision.throttle_seconds)

        ctx = require_context()
        tenant_id = str(ctx.tenant_id) if ctx.tenant_id else "unknown"

        try:
            # Load prompt from registry — no inline prompt literals.
            prompt_registry = get_prompt_registry()
            needs_tmpl = prompt_registry.get("whitespace_analysis", "needs_extraction")
            user_content = needs_tmpl.render(
                prospect_name=profile.get("name", "Unknown"),
                industry=profile.get("industry", "Unknown"),
                needs_text=needs_text or "",
            )
            provider = get_llm_provider(self.config)  # type: ignore[arg-type]
            harness_run = self._make_harness_run(
                "value_model_generation",
                tenant_id=tenant_id,
            )
            llm_client = GovernedLLMClient(
                provider=provider,
                provider_name=self._resolve_provider_name(),
                run=harness_run,
            )
            llm_result = await llm_client.call(
                model_task=needs_tmpl.model_task,
                messages=[{"role": "user", "content": user_content}],
                temperature=needs_tmpl.temperature,
                max_tokens=needs_tmpl.max_tokens,
                response_format={"type": "json_object"},
                call_id=f"ws_needs_{tenant_id}",
            )
            content = llm_result.content
            # Strip markdown fences if present.
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            extracted_needs = ExtractedNeedsResponse.model_validate_json(content).needs
            await get_llm_budget_guardrails().record_usage(cost_usd=llm_result.cost_usd)
            metrics = get_metrics()
            if metrics:
                metrics.record_llm_cost(
                    provider=llm_result.provider,
                    model=llm_result.model,
                    tenant_id=tenant_id,
                    cost=llm_result.cost_usd,
                    prompt_tokens=llm_result.prompt_tokens,
                    completion_tokens=llm_result.completion_tokens,
                    status="throttled" if decision.escalation_required else "success",
                )
        except LLMBudgetExceededError as e:
            logger.error("LLM need extraction blocked by budget guardrail: %s", e)
            extracted_needs = self._extract_needs_basic(needs_text)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("LLM need extraction failed: %s", e)
            # Fallback to basic extraction
            extracted_needs = self._extract_needs_basic(needs_text)

        return WhitespaceAnalysisWorkflow__execute_analyze_prospectResult.model_validate({  # type: ignore[no-any-return]
            "extracted_needs": extracted_needs
            if isinstance(extracted_needs, list)
            else [extracted_needs],
            "need_count": len(extracted_needs) if isinstance(extracted_needs, list) else 1,
            "industry_context": profile.get("industry", "Unknown"),
            "company_size": profile.get("employees", 0),
            "analysis_confidence": 0.85,
            "error": "",
        })


    def _extract_needs_basic(self, text: str) -> list[str]:
        """Basic keyword-based extraction as fallback."""
        sentences = text.replace(".", "|").replace("!", "|").replace("?", "|").split("|")

        need_keywords = ["need", "want", "require", "looking for", "challenge", "problem", "pain"]

        needs = []
        for sentence in sentences:
            sentence = sentence.strip()
            if any(kw in sentence.lower() for kw in need_keywords) and len(sentence) > 10:
                needs.append(sentence)

        if not needs and text.strip():
            needs = [text.strip()]

        return needs[:5]

    async def _execute_query_capabilities(self, state: WhitespaceAgentState) -> dict[str, Any]:
        """Query solution capabilities from knowledge graph."""
        # Query for capabilities
        query_result = await self.tool_registry.execute(
            "query_graph",
            {
                "cypher_query": """
                    MATCH (c:Capability)
                    WHERE c.status = 'VALIDATED'
                    RETURN c.id as id, c.name as name, 
                           c.description as description, c.category as category
                    LIMIT 100
                """,
                "parameters": {},
            },
        )

        capabilities = _unwrap_tool_data(query_result).get("results", [])

        # Transform to simplified format
        simplified = [
            {
                "id": c.get("c.id", f"cap-{i}"),
                "name": c.get("c.name", "Unknown"),
                "description": c.get("c.description", ""),
                "category": c.get("c.category", "General"),
            }
            for i, c in enumerate(capabilities)
        ]

        return WhitespaceAnalysisWorkflow__execute_query_capabilitiesResult.model_validate({  # type: ignore[no-any-return]
            "capabilities": simplified,
            "capability_count": len(simplified),
            "categories": list(set(c.get("category", "General") for c in simplified)),
        })


    async def _execute_identify_gaps(self, state: WhitespaceAgentState) -> dict[str, Any]:
        """Identify gaps between needs and capabilities using embeddings."""
        needs = state.output_data.get("analyze_prospect", {}).get("extracted_needs", [])  # type: ignore[union-attr]
        capabilities = state.output_data.get("query_capabilities", {}).get("capabilities", [])  # type: ignore[union-attr]

        if not needs:
            return WhitespaceAnalysisWorkflow__execute_identify_gapsResult.model_validate({"error": "No needs extracted", "gaps": []})  # type: ignore[no-any-return]

        if not capabilities:
            return WhitespaceAnalysisWorkflow__execute_identify_gapsResult.model_validate({"error": "No capabilities available", "gaps": []})  # type: ignore[no-any-return]

        gaps: list[GapAnalysis] = []

        # Use semantic search to find best matches
        for need in needs:
            best_match = None
            best_score = 0.0

            # Search for similar capabilities using semantic search
            try:
                search_result = await self.tool_registry.execute(
                    "semantic_search", {"query": need, "top_k": 3, "similarity_threshold": 0.5}
                )

                matches = _unwrap_tool_data(search_result).get("results", [])
                if matches:
                    best_match = matches[0]
                    best_score = best_match.get("similarity_score", 0)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Semantic search failed: {e}")
                # Fallback to simple text matching
                for cap in capabilities:
                    score = self._calculate_similarity(need, cap.get("description", ""))
                    if score > best_score:
                        best_score = score
                        best_match = cap

            # Determine gap type based on match score
            _match_name = best_match.get("name", "N/A") if isinstance(best_match, dict) else "N/A"
            if best_score >= 0.7:
                gap_type = "none"
                impact = "low"
                recommendation = f"Strong match with capability: {_match_name}"
            elif best_score >= 0.4:
                gap_type = "coverage"
                impact = "medium"
                recommendation = (
                    f"Partial match - explore {_match_name} with customizations"
                )
            else:
                gap_type = "capability"
                impact = "high"
                recommendation = "New capability opportunity - engage solution engineering"

            gap = GapAnalysis(
                need_statement=need,
                matched_capability=best_match.get("name") if best_match else None,
                match_score=round(best_score, 2),
                gap_type=gap_type,
                impact=impact,
                recommendation=recommendation,
            )
            gaps.append(gap)

        return WhitespaceAnalysisWorkflow__execute_identify_gapsResult.model_validate({  # type: ignore[no-any-return]
            "gaps": [g.model_dump() for g in gaps],
            "gap_count": len(gaps),
            "coverage_percentage": sum(1 for g in gaps if g.gap_type == "none") / len(gaps) * 100
            if gaps
            else 0,
            "error": "",
        })


    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity as fallback."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        overlap = len(words1 & words2)
        return overlap / max(len(words1), len(words2))

    async def _execute_score_opportunity(self, state: WhitespaceAgentState) -> dict[str, Any]:
        """Score overall opportunity potential."""
        gaps_data = state.output_data.get("identify_gaps", {})  # type: ignore[union-attr]
        gaps = gaps_data.get("gaps", [])

        if not gaps:
            return WhitespaceAnalysisWorkflow__execute_score_opportunityResult.model_validate({"score": 0, "assessment": "No gaps analyzed"})  # type: ignore[no-any-return]

        # Calculate opportunity score based on gap analysis
        high_impact_gaps = sum(1 for g in gaps if g.get("impact") == "high")
        medium_impact_gaps = sum(1 for g in gaps if g.get("impact") == "medium")

        # Score factors
        gap_factor = min(30, (high_impact_gaps * 10) + (medium_impact_gaps * 5))

        # Coverage factor (inverse - lower coverage means more whitespace)
        coverage = gaps_data.get("coverage_percentage", 0)
        whitespace_factor = max(0, (100 - coverage) / 2)

        # Need count factor (more needs = more opportunity)
        need_count = len(gaps)
        needs_factor = min(20, need_count * 4)

        total_score = gap_factor + whitespace_factor + needs_factor

        # Ensure score is 0-100
        total_score = min(100, max(0, total_score))

        # Generate assessment
        if total_score >= 70:
            assessment = "High opportunity - significant whitespace with clear needs"
        elif total_score >= 40:
            assessment = "Medium opportunity - some gaps to address"
        else:
            assessment = "Lower opportunity - good solution fit or unclear needs"

        # Generate recommendations
        recommendations = []

        if high_impact_gaps > 0:
            recommendations.append(f"Prioritize {high_impact_gaps} high-impact capability gaps")

        if coverage < 50:
            recommendations.append(
                "Significant whitespace exists - consider custom solution approach"
            )
        elif coverage > 80:
            recommendations.append("Strong fit - emphasize standard solution capabilities")

        if need_count >= 3:
            recommendations.append("Multiple needs identified - propose phased implementation")

        recommendations.append("Schedule technical deep-dive to validate assumptions")

        return WhitespaceAnalysisWorkflow__execute_score_opportunityResult.model_validate({  # type: ignore[no-any-return]
            "opportunity_score": round(total_score, 1),
            "assessment": assessment,
            "score": int(total_score),
            "factors": {
                "gap_contribution": round(gap_factor, 1),
                "whitespace_contribution": round(whitespace_factor, 1),
                "needs_contribution": round(needs_factor, 1),
            },
            "recommendations": recommendations,
        })

    # -----------------------------------------------------------------------
    # LLM hypothesis generation
    # -----------------------------------------------------------------------
    async def _execute_llm_hypotheses(self, state: WhitespaceAgentState) -> dict[str, Any]:
        """Generate LLM-enriched whitespace hypotheses from gap analysis + opportunity score.

        Runs three sequential prompts:
        1. ``extraction`` — re-summarise entities and signals from prospect needs
        2. ``gap_analysis`` — structured gap analysis against capabilities
        3. ``hypothesis_generation`` — value hypotheses from gaps + opportunity score

        Degrades gracefully on any LLM failure.
        """
        tenant_id = (
            state.metadata.get("tenant_id")
            or state.input_data.get("tenant_id")
            or ""
        )
        trace_id = state.metadata.get("trace_id") or state.metadata.get("run_id")
        account_name = (
            state.input_data.get("account_name")
            or state.input_data.get("prospect_name")
            or (state.whitespace_input.prospect_id if state.whitespace_input else "Unknown")
        )

        agent_result = AgentResult(
            payload={},
            workflow_type="whitespace_analysis",
            tenant_id=tenant_id,
            trace_id=trace_id,
        )

        try:
            registry = get_prompt_registry()
            system_tmpl = registry.get("whitespace_analysis", "system")
            extraction_tmpl = registry.get("whitespace_analysis", "extraction")
            gap_tmpl = registry.get("whitespace_analysis", "gap_analysis")
            hyp_tmpl = registry.get("whitespace_analysis", "hypothesis_generation")

            provider = get_llm_provider(self.config)  # type: ignore[arg-type]
            harness_run = self._make_harness_run(
                "value_model_generation",
                tenant_id=tenant_id or "unknown",
                trace_id=trace_id,
            )
            client = GovernedLLMClient(
                provider=provider,
                provider_name=self._resolve_provider_name(),
                run=harness_run,
            )
            system_msg = {"role": "system", "content": system_tmpl.body}

            # ── Step 1: extraction ──────────────────────────────────────
            needs_text = (
                state.whitespace_input.prospect_needs
                if state.whitespace_input
                else state.input_data.get("prospect_needs", "")
            )
            extraction_content = extraction_tmpl.render(
                account_name=account_name,
                source_material=needs_text or "",
            )
            extraction_result = await client.call(
                model_task=extraction_tmpl.model_task,
                messages=[system_msg, {"role": "user", "content": extraction_content}],
                temperature=extraction_tmpl.temperature,
                max_tokens=extraction_tmpl.max_tokens,
                call_id=f"ws_extract_{trace_id or 'unknown'}",
            )
            extracted = parse_llm_json(extraction_result.content)

            # ── Step 2: gap analysis ────────────────────────────────────
            gaps_prior = state.output_data.get("identify_gaps", {})  # type: ignore[union-attr]
            search_results = {
                "gaps": gaps_prior.get("gaps", [])[:8],
                "coverage_percentage": gaps_prior.get("coverage_percentage", 0),
                "capabilities_matched": gaps_prior.get("capabilities_matched", []),
            }
            gap_content = gap_tmpl.render(
                account_name=account_name,
                needs_json=json.dumps(extracted, indent=2),
                search_results_json=json.dumps(search_results, indent=2),
                existing_coverage_json=json.dumps(
                    {"coverage_percentage": gaps_prior.get("coverage_percentage", 0)},
                    indent=2,
                ),
            )
            gap_result = await client.call(
                model_task=gap_tmpl.model_task,
                messages=[system_msg, {"role": "user", "content": gap_content}],
                temperature=gap_tmpl.temperature,
                max_tokens=gap_tmpl.max_tokens,
                call_id=f"ws_gap_{trace_id or 'unknown'}",
            )
            gap_analysis = parse_llm_json(gap_result.content)

            # ── Step 3: hypothesis generation ──────────────────────────
            score_prior = state.output_data.get("score_opportunity", {})  # type: ignore[union-attr]
            opportunity_score = score_prior.get("opportunity_score", score_prior.get("score", 0))
            hyp_content = hyp_tmpl.render(
                account_name=account_name,
                gap_analysis_json=json.dumps(gap_analysis, indent=2),
                opportunity_score=str(opportunity_score),
            )
            hyp_result = await client.call(
                model_task=hyp_tmpl.model_task,
                messages=[system_msg, {"role": "user", "content": hyp_content}],
                temperature=hyp_tmpl.temperature,
                max_tokens=hyp_tmpl.max_tokens,
                response_format={"type": "json_object"},
                call_id=f"ws_hyp_{trace_id or 'unknown'}",
            )
            hypotheses = parse_llm_json(hyp_result.content)
            if not hypotheses or "hypotheses" not in hypotheses:
                raise ValueError("invalid_structured_output")

            # Aggregate token usage across all three calls
            total_prompt = (
                extraction_result.prompt_tokens
                + gap_result.prompt_tokens
                + hyp_result.prompt_tokens
            )
            total_completion = (
                extraction_result.completion_tokens
                + gap_result.completion_tokens
                + hyp_result.completion_tokens
            )
            confidence = float(
                hypotheses.get("confidence", gap_analysis.get("confidence", 0.6))
            )

            agent_result.payload = {
                "extracted_entities": extracted,
                "gap_analysis": gap_analysis,
                "hypotheses": hypotheses.get("hypotheses", []),
                "opportunity_score": opportunity_score,
            }
            agent_result.mark_llm_enriched(
                model=hyp_result.model,
                prompt_tokens=total_prompt,
                completion_tokens=total_completion,
                confidence=confidence,
            )
            logger.info(
                "Whitespace hypothesis generation complete: model=%s tokens=%d",
                hyp_result.model,
                total_prompt + total_completion,
            )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Whitespace LLM hypothesis generation failed", extra={"code": "llm_failed"})
            agent_result.payload = {
                "extracted_entities": {},
                "gap_analysis": {},
                "hypotheses": [],
                "opportunity_score": 0,
            }
            agent_result.degraded_reason = "llm_failed"

        return agent_result.to_dict()

    def _resolve_provider_name(self) -> str:
        import os
        return (
            os.getenv("LAYER4_LLM_PROVIDER")
            or (self.config.get("llm_provider") if isinstance(self.config, dict) else None)
            or getattr(self.config, "llm_provider", None)
            or "together"
        )

