from __future__ import annotations

"""Canonical agent taxonomy — 9 GATE-governed agent types.

Implements the validated agent roster for the Value Fabric Layer 4 system.

Value Spine Agents (artifact producers):
1. ContextExtractionAgent — customer context, stakeholders, pain points, financials
2. ValueModelAgent — value trees, gap analysis, ROI calculations, sensitivity
3. IntegrityAgent — claim validation, formula verification, evidence auditing
4. NarrativeAgent — executive summaries, proposals, slide decks
5. CompetitiveIntelAgent — competitive landscape, win/loss analysis

Operational Agents:
6. SignalDetectionAgent — (see signal_detection.py)
7. CRMSyncAgent — (see crm_sync_agent.py, future)

Orchestration Agents:
8. ConversationAgent — user-facing ValuePilot copilot
9. OrchestrationController — workflow scheduling, task distribution

Backward Compatibility:
Old class names (DocumentIngestionAgent, FinancialExtractionAgent, etc.)
are preserved as aliases at module bottom for import compatibility.
See DEPRECATION_MAP.md for migration timeline.
"""


import logging
from collections.abc import Callable, Mapping
from enum import Enum
from typing import Any

from value_fabric.shared.identity.context import get_request_context

from ..interfaces.context_clients import (
    ContextFinancialExtractionPort,
    ContextIngestionPort,
)
from .base import AgentCapability, AgentResult, BaseAgent

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Enumeration of all canonical agent types."""

    # Value Spine
    CONTEXT_EXTRACTION = "ContextExtractionAgent"
    VALUE_MODEL = "ValueModelAgent"
    INTEGRITY = "IntegrityAgent"
    NARRATIVE = "NarrativeAgent"
    COMPETITIVE_INTEL = "CompetitiveIntelAgent"

    # Operational
    SIGNAL_DETECTION = "SignalDetectionAgent"
    CRM_SYNC = "CRMSyncAgent"

    # Orchestration
    CONVERSATION = "ConversationAgent"
    ORCHESTRATION = "OrchestrationController"

    # ── Deprecated aliases (kept for backward compatibility) ──
    DOCUMENT_INGESTION = "DocumentIngestionAgent"
    FINANCIAL_EXTRACTION = "FinancialExtractionAgent"
    VALUE_TREE_PROJECTION = "ValueTreeProjectionAgent"
    WHITESPACE_ANALYSIS = "WhitespaceAnalysisAgent"
    ROI_CALCULATION = "ROICalculationAgent"
    NARRATIVE_SYNTHESIS = "NarrativeSynthesisAgent"
    PROVENANCE_TRACKING = "ProvenanceTrackingAgent"


# ---------------------------------------------------------------------------
# Helper: GATE-aware tool execution
# ---------------------------------------------------------------------------


async def _gate_execute(
    ctx: dict[str, Any],
    tool_name: str,
    input_data: dict[str, Any],
    estimated_cost_usd: float = 0.0,
) -> dict[str, Any]:
    """Execute a tool through ToolGateway if available, else fall back to registry.

    All agent ``execute()`` methods MUST call this helper instead of
    reaching into ``ToolRegistry`` directly.  This ensures GATE policy
    enforcement, invariant checks, and audit emission are always applied.
    """
    effective_input = dict(input_data)
    if "tenant_id" not in effective_input:
        tenant_id = ctx.get("tenant_id")
        if tenant_id is None:
            request_context = get_request_context()
            tenant_id = (
                str(request_context.tenant_id)
                if request_context and request_context.tenant_id
                else None
            )
        if tenant_id is not None:
            effective_input["tenant_id"] = str(tenant_id)

    gateway = ctx.get("tool_gateway")
    if gateway is not None:
        return await gateway.execute(tool_name, effective_input, estimated_cost_usd)

    # Graceful degradation: direct registry call when GATE is not injected
    registry = ctx.get("tool_registry")
    if registry is not None:
        logger.warning(
            "GATE ToolGateway not available — falling back to direct registry "
            "call for tool '%s'. This bypasses policy enforcement.",
            tool_name,
        )
        return await registry.execute(tool_name, effective_input)

    raise RuntimeError(
        f"Cannot execute tool '{tool_name}': neither tool_gateway nor "
        "tool_registry found in execution context."
    )


# ---------------------------------------------------------------------------
# Governance helpers
# ---------------------------------------------------------------------------


def _governed_result(
    payload: dict[str, Any],
    workflow_type: str,
    context: dict[str, Any],
    *,
    confidence: float = 0.8,
    hypothesis: str | None = None,
) -> dict[str, Any]:
    """Wrap a tool-layer payload in an AgentResult governance envelope.

    All taxonomy agents return tool-delegated payloads.  This helper
    ensures every response carries the standard governance flags
    (customer_facing_allowed, human_review_required, degraded_reason)
    so downstream consumers can make safe surfacing decisions.

    **Governance invariant — llm_enrichment=False:**
    Taxonomy agents delegate to ABOM tools rather than calling an LLM
    directly, so ``llm_enrichment`` is always ``False`` here.
    ``AgentResult.__post_init__`` therefore forces
    ``customer_facing_allowed=False`` and ``human_review_required=True``
    for *every* result, regardless of confidence.  Downstream consumers
    that gate on ``customer_facing_allowed`` will never see ``True`` from
    any taxonomy agent.

    If a future taxonomy capability produces LLM-backed output that should
    be promotable to customer-facing, introduce a ``tool_enriched=True``
    flag on ``AgentResult`` (or call ``result.mark_llm_enriched(...)``
    after construction) rather than changing this helper.

    Args:
        payload: The raw tool output dict.
        workflow_type: Canonical workflow identifier string.
        context: Agent execution context (used to extract tenant_id/trace_id).
        confidence: Aggregate confidence score [0.0, 1.0].
        hypothesis: Optional one-line hypothesis about the extracted content.
    """
    tenant_id = str(context.get("tenant_id") or "")
    trace_id = str(context.get("trace_id") or "")
    result = AgentResult(
        payload=(
            payload if hypothesis is None else {**payload, "hypothesis": hypothesis}
        ),
        workflow_type=workflow_type,
        tenant_id=tenant_id,
        trace_id=trace_id,
        llm_enrichment=False,  # taxonomy agents delegate to tools, not LLM directly
        confidence=confidence,
    )
    return result.to_dict()


def _degraded_result(
    workflow_type: str,
    context: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    """Return a degraded AgentResult for unknown capability or tool failure."""
    tenant_id = str(context.get("tenant_id") or "")
    trace_id = str(context.get("trace_id") or "")
    result = AgentResult(
        payload={},
        workflow_type=workflow_type,
        tenant_id=tenant_id,
        trace_id=trace_id,
        llm_enrichment=False,
        confidence=0.0,
        degraded_reason=reason,
    )
    return result.to_dict()


# ============================================================================
# 1. CONTEXT EXTRACTION AGENT
# ============================================================================


class ContextExtractionAgent(BaseAgent):
    """Extracts customer context from ingested sources.

    Consolidates the former DocumentIngestionAgent and
    FinancialExtractionAgent into a single context-gathering stage.

    Produces: ContextArtifact (profile, stakeholders, pain points,
    financial metrics, risk factors).

    ABOM tools: query_graph, semantic_search, get_entity,
    get_relationships, traverse_tree, find_paths, validate_input
    """

    agent_type = AgentType.CONTEXT_EXTRACTION

    def __init__(
        self,
        *,
        layer1_client: ContextIngestionPort | None = None,
        layer2_client: ContextFinancialExtractionPort | None = None,
        layer1_client_factory: (
            Callable[[Mapping[str, Any]], ContextIngestionPort] | None
        ) = None,
        layer2_client_factory: (
            Callable[[Mapping[str, Any]], ContextFinancialExtractionPort] | None
        ) = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.layer1_client = layer1_client
        self.layer2_client = layer2_client
        self._layer1_client_factory = layer1_client_factory
        self._layer2_client_factory = layer2_client_factory

    async def _initialize_resources(self) -> None:
        """Initialize Layer 1 ingestion and Layer 2 extraction clients."""
        if self.layer1_client is None and self._layer1_client_factory is not None:
            try:
                self.layer1_client = self._layer1_client_factory(self.config)
            except ImportError:
                logger.info(
                    "Layer1IngestionClient not available — document parsing disabled"
                )
        if self.layer2_client is None and self._layer2_client_factory is not None:
            try:
                self.layer2_client = self._layer2_client_factory(self.config)
            except ImportError:
                logger.info(
                    "Layer2ExtractionClient not available — financial extraction disabled"
                )

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="extract_profile",
                description="Extract customer profile from ingested documents",
                input_schema={"account_id": "string", "source_urls": "array"},
                output_schema={"profile": "object", "confidence": "number"},
                timeout_seconds=300,
            ),
            AgentCapability(
                name="extract_stakeholders",
                description="Identify key stakeholders and their roles",
                input_schema={"account_id": "string"},
                output_schema={"stakeholders": "array"},
                timeout_seconds=180,
            ),
            AgentCapability(
                name="extract_pain_points",
                description="Extract and categorize customer pain points",
                input_schema={"account_id": "string", "context_text": "string"},
                output_schema={"pain_points": "array", "categories": "array"},
                timeout_seconds=240,
            ),
            AgentCapability(
                name="extract_financials",
                description="Extract financial metrics from SEC filings and reports",
                input_schema={
                    "filing_url": "string",
                    "filing_type": "string",
                    "ticker": "string",
                },
                output_schema={"financial_data": "object", "period": "string"},
                timeout_seconds=600,
            ),
            AgentCapability(
                name="extract_risk_factors",
                description="Identify and categorize risk factors from filings",
                input_schema={"filing_text": "string"},
                output_schema={"risks": "array", "categories": "array"},
                timeout_seconds=300,
            ),
        ]

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute context extraction through GATE-governed tools."""
        capability = task.get("capability")
        params = task.get("parameters", {})

        if capability == "extract_profile":
            account_data = await _gate_execute(
                context,
                "get_entity",
                {"entity_type": "Account", "entity_id": params["account_id"]},
            )
            enrichment = await _gate_execute(
                context,
                "semantic_search",
                {"query": f"company profile {params['account_id']}", "top_k": 10},
            )
            payload = {
                "profile": {
                    **account_data,
                    "enrichment_sources": enrichment.get("results", []),
                },
                "confidence": enrichment.get("avg_score", 0.0),
            }
            return _governed_result(
                payload,
                "account_intelligence",
                context,
                confidence=float(enrichment.get("avg_score", 0.8)),
            )

        elif capability == "extract_stakeholders":
            results = await _gate_execute(
                context,
                "get_relationships",
                {
                    "entity_id": params["account_id"],
                    "relationship_type": "HAS_STAKEHOLDER",
                },
            )
            payload = {"stakeholders": results.get("relationships", [])}
            return _governed_result(payload, "account_intelligence", context)

        elif capability == "extract_pain_points":
            search_results = await _gate_execute(
                context,
                "semantic_search",
                {
                    "query": f"pain points challenges {params.get('context_text', '')}",
                    "top_k": 20,
                },
            )
            validated = await _gate_execute(
                context,
                "validate_input",
                {"data": search_results.get("results", []), "schema": "pain_point"},
            )
            pain_points = validated.get("valid_items", [])
            categories = validated.get("categories", [])
            # Hypothesis: summarise the dominant pain category for downstream agents.
            hypothesis = (
                f"Primary pain category: {categories[0]}" if categories else None
            )
            payload = {"pain_points": pain_points, "categories": categories}
            return _governed_result(
                payload, "account_intelligence", context, hypothesis=hypothesis
            )

        elif capability == "extract_financials":
            if self.layer2_client:
                extraction = await self.layer2_client.extract_filing(
                    url=params["filing_url"],
                    filing_type=params["filing_type"],
                    ticker=params.get("ticker"),
                )
            else:
                extraction = {"financial_data": {}, "period": "unknown"}
            await _gate_execute(
                context,
                "query_graph",
                {
                    "operation": "merge_financial_data",
                    "ticker": params.get("ticker"),
                    "data": extraction,
                },
            )
            return _governed_result(extraction, "account_intelligence", context)

        elif capability == "extract_risk_factors":
            search_results = await _gate_execute(
                context,
                "semantic_search",
                {"query": "risk factors regulatory compliance", "top_k": 15},
            )
            payload = {
                "risks": search_results.get("results", []),
                "categories": ["regulatory", "market", "operational", "financial"],
            }
            return _governed_result(payload, "account_intelligence", context)

        return _degraded_result(
            "account_intelligence", context, reason=f"unknown_capability:{capability}"
        )


# ============================================================================
# 2. VALUE MODEL AGENT
# ============================================================================


class ValueModelAgent(BaseAgent):
    """Builds value models from extracted context.

    Consolidates the former ValueTreeProjectionAgent,
    WhitespaceAnalysisAgent, and ROICalculationAgent.

    Produces: ValueModelArtifact (value trees, gap analysis,
    ROI projections, sensitivity analysis).

    ABOM tools: query_graph, semantic_search, get_entity,
    get_relationships, traverse_tree, find_paths, evaluate_formula,
    calculate_roi, compare_benchmarks, sensitivity_analysis,
    validate_input, format_currency
    """

    agent_type = AgentType.VALUE_MODEL

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="project_value_tree",
                description="Project value trees for an account based on pain points and capabilities",
                input_schema={"account_id": "string", "pain_points": "array"},
                output_schema={"value_tree": "object", "nodes_created": "number"},
                timeout_seconds=300,
            ),
            AgentCapability(
                name="identify_gaps",
                description="Identify gaps between prospect needs and solution capabilities",
                input_schema={
                    "prospect_id": "string",
                    "needs": "array",
                    "capabilities": "array",
                },
                output_schema={"gaps": "array", "coverage_percentage": "number"},
                timeout_seconds=400,
            ),
            AgentCapability(
                name="calculate_roi",
                description="Execute ROI calculations with formula validation",
                input_schema={
                    "formula": "string",
                    "variables": "object",
                    "unit": "string",
                },
                output_schema={"result": "number", "substituted_formula": "string"},
                timeout_seconds=120,
            ),
            AgentCapability(
                name="sensitivity_analysis",
                description="Perform sensitivity analysis on ROI calculations",
                input_schema={"base_formula": "string", "variable_ranges": "object"},
                output_schema={"scenarios": "array", "tornado_data": "array"},
                timeout_seconds=300,
            ),
            AgentCapability(
                name="compare_benchmarks",
                description="Compare metrics against industry benchmarks",
                input_schema={"metrics": "object", "industry": "string"},
                output_schema={"comparisons": "array", "percentile_rank": "number"},
                timeout_seconds=180,
            ),
        ]

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute value modeling through GATE-governed tools."""
        capability = task.get("capability")
        params = task.get("parameters", {})

        if capability == "project_value_tree":
            capabilities = await _gate_execute(
                context,
                "traverse_tree",
                {"root_id": "capability_root", "max_depth": 4},
            )
            matches = await _gate_execute(
                context,
                "semantic_search",
                {"query": " ".join(params.get("pain_points", [])), "top_k": 20},
            )
            tree = await _gate_execute(
                context,
                "query_graph",
                {
                    "operation": "project_value_tree",
                    "account_id": params["account_id"],
                    "matches": matches.get("results", []),
                    "capabilities": capabilities.get("nodes", []),
                },
            )
            payload = {
                "value_tree": tree,
                "nodes_created": tree.get("nodes_created", 0),
            }
            return _governed_result(payload, "value_model_generation", context)

        elif capability == "identify_gaps":
            gap_analysis = await _gate_execute(
                context,
                "find_paths",
                {
                    "source_type": "Need",
                    "target_type": "Capability",
                    "prospect_id": params["prospect_id"],
                },
            )
            gaps = gap_analysis.get("unmatched", [])
            coverage = float(gap_analysis.get("coverage_pct", 0.0))
            # Hypothesis: characterise the gap severity for downstream narrative agents.
            if coverage >= 0.8:
                hypothesis = (
                    f"High capability coverage ({coverage:.0%}); minor gaps only."
                )
            elif coverage >= 0.5:
                hypothesis = f"Moderate coverage ({coverage:.0%}); targeted gap-fill recommended."
            else:
                hypothesis = f"Low coverage ({coverage:.0%}); significant whitespace opportunity."
            payload = {"gaps": gaps, "coverage_percentage": coverage}
            return _governed_result(
                payload,
                "value_model_generation",
                context,
                confidence=coverage,
                hypothesis=hypothesis,
            )

        elif capability == "calculate_roi":
            result = await _gate_execute(
                context,
                "calculate_roi",
                {
                    "formula": params["formula"],
                    "variables": params["variables"],
                    "unit": params.get("unit", "USD"),
                },
            )
            return _governed_result(result, "value_model_generation", context)

        elif capability == "sensitivity_analysis":
            result = await _gate_execute(
                context,
                "sensitivity_analysis",
                {
                    "base_formula": params["base_formula"],
                    "variable_ranges": params["variable_ranges"],
                },
            )
            return _governed_result(result, "value_model_generation", context)

        elif capability == "compare_benchmarks":
            result = await _gate_execute(
                context,
                "compare_benchmarks",
                {
                    "metrics": params["metrics"],
                    "industry": params["industry"],
                },
            )
            return _governed_result(result, "value_model_generation", context)

        return _degraded_result(
            "value_model_generation", context, reason=f"unknown_capability:{capability}"
        )


# ============================================================================
# 3. INTEGRITY AGENT
# ============================================================================


class IntegrityAgent(BaseAgent):
    """Validates claims, formulas, and evidence before narrative generation.

    New agent — no legacy predecessor.  Sits between ValueModelAgent
    and NarrativeAgent in the value spine to ensure all quantitative
    claims are traceable and correct.

    Produces: IntegrityReport (validation results, violation list,
    confidence scores).

    ABOM tools: query_graph, semantic_search, get_entity,
    get_relationships, evaluate_formula, compare_benchmarks,
    validate_input
    """

    agent_type = AgentType.INTEGRITY

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="validate_claims",
                description="Validate narrative claims against evidence pointers",
                input_schema={"claims": "array", "evidence_graph_id": "string"},
                output_schema={"validated": "array", "violations": "array"},
                timeout_seconds=300,
            ),
            AgentCapability(
                name="verify_formulas",
                description="Re-execute ROI formulas and verify results match",
                input_schema={"formulas": "array"},
                output_schema={"verified": "array", "discrepancies": "array"},
                timeout_seconds=240,
            ),
            AgentCapability(
                name="audit_evidence",
                description="Audit evidence chain completeness and freshness",
                input_schema={"evidence_ids": "array", "max_age_days": "number"},
                output_schema={"audit_result": "object", "stale_evidence": "array"},
                timeout_seconds=180,
            ),
        ]

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute integrity validation through GATE-governed tools."""
        capability = task.get("capability")
        params = task.get("parameters", {})

        if capability == "validate_claims":
            violations = []
            validated = []
            for claim in params.get("claims", []):
                claim_id = claim.get("claim_id", "unknown")
                evidence_refs = claim.get("evidence_pointers", [])
                if not evidence_refs:
                    violations.append(
                        {
                            "claim_id": claim_id,
                            "type": "missing_evidence",
                            "message": "Claim has no evidence pointers",
                        }
                    )
                    continue
                for ref in evidence_refs:
                    entity = await _gate_execute(
                        context,
                        "get_entity",
                        {"entity_type": "Evidence", "entity_id": ref},
                    )
                    if entity.get("found"):
                        validated.append(
                            {
                                "claim_id": claim_id,
                                "evidence_id": ref,
                                "status": "valid",
                            }
                        )
                    else:
                        violations.append(
                            {
                                "claim_id": claim_id,
                                "evidence_id": ref,
                                "type": "evidence_not_found",
                                "message": f"Evidence {ref} not found in graph",
                            }
                        )
            total = len(validated) + len(violations)
            confidence = len(validated) / total if total > 0 else 0.0
            payload = {"validated": validated, "violations": violations}
            return _governed_result(
                payload, "evidence_matching", context, confidence=confidence
            )

        elif capability == "verify_formulas":
            verified = []
            discrepancies = []
            for formula_spec in params.get("formulas", []):
                result = await _gate_execute(
                    context,
                    "evaluate_formula",
                    {
                        "formula": formula_spec["formula"],
                        "variables": formula_spec["variables"],
                    },
                )
                expected = formula_spec.get("expected_result")
                actual = result.get("result")
                entry = {
                    "formula_id": formula_spec.get("formula_id", "unknown"),
                    "expected": expected,
                    "actual": actual,
                }
                if (
                    expected is not None
                    and abs(float(actual or 0) - float(expected)) > 0.01
                ):
                    entry["status"] = "discrepancy"
                    discrepancies.append(entry)
                else:
                    entry["status"] = "verified"
                    verified.append(entry)
            payload = {"verified": verified, "discrepancies": discrepancies}
            return _governed_result(payload, "evidence_matching", context)

        elif capability == "audit_evidence":
            audit_results = []
            stale = []
            for eid in params.get("evidence_ids", []):
                entity = await _gate_execute(
                    context,
                    "get_entity",
                    {"entity_type": "Evidence", "entity_id": eid},
                )
                audit_results.append(entity)
                age_days = entity.get("age_days", 999)
                max_age = params.get("max_age_days", 90)
                if age_days > max_age:
                    stale.append({"evidence_id": eid, "age_days": age_days})
            payload = {
                "audit_result": {
                    "total": len(audit_results),
                    "stale_count": len(stale),
                },
                "stale_evidence": stale,
            }
            return _governed_result(payload, "evidence_matching", context)

        return _degraded_result(
            "evidence_matching", context, reason=f"unknown_capability:{capability}"
        )


# ============================================================================
# 4. NARRATIVE AGENT
# ============================================================================


class NarrativeAgent(BaseAgent):
    """Generates executive narratives and deliverable documents.

    Replaces the former NarrativeSynthesisAgent with GATE-governed
    tool access and human-approval gating on export_document.

    Produces: NarrativeArtifact (executive summaries, proposals,
    slide decks, stakeholder alignment documents).

    ABOM tools: query_graph, semantic_search, get_entity,
    get_relationships, traverse_tree, generate_section, create_chart,
    format_table, assemble_document, export_document, validate_input,
    format_currency
    """

    agent_type = AgentType.NARRATIVE

    TEMPLATES = {
        "c_suite_executive_summary": "C-Suite Executive Summary",
        "board_presentation": "Board Presentation",
        "procurement_proposal": "Procurement Proposal",
        "technical_architecture_review": "Technical Architecture Review",
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.llm_config = {
            "model": self.config.get("model", "gpt-4-turbo"),
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 4000),
        }

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="generate_executive_summary",
                description="Generate C-suite executive summaries",
                input_schema={
                    "roi_data": "object",
                    "gap_analysis": "object",
                    "template": "string",
                },
                output_schema={
                    "summary": "string",
                    "key_points": "array",
                    "word_count": "number",
                },
                timeout_seconds=300,
            ),
            AgentCapability(
                name="create_slide_deck",
                description="Create presentation slide decks",
                input_schema={
                    "content": "object",
                    "template": "string",
                    "slide_count": "number",
                },
                output_schema={"slides": "array", "speaker_notes": "array"},
                timeout_seconds=400,
            ),
            AgentCapability(
                name="draft_proposal",
                description="Draft risk-adjusted proposals",
                input_schema={"business_case": "object", "risk_assessment": "object"},
                output_schema={"proposal": "string", "risk_mitigation": "array"},
                timeout_seconds=300,
            ),
            AgentCapability(
                name="export_document",
                description="Export final document (requires human approval via GATE)",
                input_schema={
                    "document_type": "string",
                    "business_case_data": "object",
                    "format": "string",
                },
                output_schema={"success": "boolean", "download_url": "string"},
                timeout_seconds=600,
            ),
        ]

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute narrative generation through GATE-governed tools."""
        capability = task.get("capability")
        params = task.get("parameters", {})

        if capability == "generate_executive_summary":
            roi_data = params.get("roi_data", {})
            gap_data = params.get("gap_analysis", {})
            sections = []
            for section_name in [
                "executive_overview",
                "value_proposition",
                "roi_summary",
                "next_steps",
            ]:
                section = await _gate_execute(
                    context,
                    "generate_section",
                    {
                        "section_type": section_name,
                        "roi_data": roi_data,
                        "gap_analysis": gap_data,
                        "template": params.get("template", "c_suite_executive_summary"),
                    },
                )
                sections.append(section)
            assembled = await _gate_execute(
                context,
                "assemble_document",
                {"sections": sections, "template": params.get("template")},
            )
            payload = {
                "summary": assembled.get("content", ""),
                "key_points": assembled.get("key_points", []),
                "word_count": assembled.get("word_count", 0),
            }
            return _governed_result(payload, "business_case_generation", context)

        elif capability == "create_slide_deck":
            content = params.get("content", {})
            slides = []
            slide_count = params.get("slide_count", 10)
            for i in range(min(slide_count, 20)):
                chart = await _gate_execute(
                    context,
                    "create_chart",
                    {"chart_type": "auto", "data": content, "slide_index": i},
                )
                slides.append(chart)
            payload = {"slides": slides, "speaker_notes": []}
            return _governed_result(payload, "business_case_generation", context)

        elif capability == "draft_proposal":
            business_case = params.get("business_case", {})
            risk_assessment = params.get("risk_assessment", {})
            proposal = await _gate_execute(
                context,
                "generate_section",
                {
                    "section_type": "full_proposal",
                    "business_case": business_case,
                    "risk_assessment": risk_assessment,
                },
            )
            payload = {
                "proposal": proposal.get("content", ""),
                "risk_mitigation": proposal.get("risk_mitigation", []),
            }
            return _governed_result(payload, "business_case_generation", context)

        elif capability == "export_document":
            # export_document requires human approval per ABOM invariant.
            # Return result wrapped in governance envelope; customer_facing_allowed
            # remains False until the human gate is cleared.
            result = await _gate_execute(
                context,
                "export_document",
                {
                    "document_type": params.get("document_type", "business_case"),
                    "business_case_data": params.get("business_case_data", {}),
                    "format": params.get("format", "pdf"),
                },
            )
            return _governed_result(result, "business_case_generation", context)

        return _degraded_result(
            "business_case_generation",
            context,
            reason=f"unknown_capability:{capability}",
        )


# ============================================================================
# 5. COMPETITIVE INTEL AGENT
# ============================================================================


class CompetitiveIntelAgent(BaseAgent):
    """Gathers and analyzes competitive intelligence.

    Produces: CompetitiveIntelArtifact (competitor profiles,
    win/loss analysis, battlecards, market positioning).

    ABOM tools: query_graph, semantic_search, get_entity,
    get_relationships, find_paths, analyze_competition,
    validate_input, format_table, format_currency
    """

    agent_type = AgentType.COMPETITIVE_INTEL

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="analyze_competitors",
                description="Analyze competitive landscape for an account",
                input_schema={"account_id": "string", "competitors": "array"},
                output_schema={"analysis": "object", "battlecard": "object"},
                timeout_seconds=400,
            ),
            AgentCapability(
                name="win_loss_analysis",
                description="Perform win/loss analysis from historical deals",
                input_schema={"account_id": "string", "deal_ids": "array"},
                output_schema={"win_rate": "number", "factors": "array"},
                timeout_seconds=300,
            ),
            AgentCapability(
                name="market_positioning",
                description="Determine market positioning relative to competitors",
                input_schema={"product_id": "string", "market_segment": "string"},
                output_schema={"positioning": "object", "differentiators": "array"},
                timeout_seconds=300,
            ),
        ]

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute competitive intelligence through GATE-governed tools."""
        capability = task.get("capability")
        params = task.get("parameters", {})

        if capability == "analyze_competitors":
            competitors = []
            for comp_name in params.get("competitors", []):
                comp_data = await _gate_execute(
                    context,
                    "semantic_search",
                    {"query": f"competitor {comp_name}", "top_k": 5},
                )
                competitors.append(comp_data)
            analysis = await _gate_execute(
                context,
                "analyze_competition",
                {
                    "account_id": params["account_id"],
                    "competitor_data": competitors,
                },
            )
            payload = {
                "analysis": analysis,
                "battlecard": analysis.get("battlecard", {}),
            }
            return _governed_result(payload, "account_intelligence", context)

        elif capability == "win_loss_analysis":
            deals = await _gate_execute(
                context,
                "query_graph",
                {
                    "operation": "get_deal_outcomes",
                    "account_id": params["account_id"],
                    "deal_ids": params.get("deal_ids", []),
                },
            )
            payload = {
                "win_rate": deals.get("win_rate", 0.0),
                "factors": deals.get("contributing_factors", []),
            }
            return _governed_result(payload, "account_intelligence", context)

        elif capability == "market_positioning":
            positioning = await _gate_execute(
                context,
                "analyze_competition",
                {
                    "product_id": params["product_id"],
                    "market_segment": params["market_segment"],
                    "analysis_type": "positioning",
                },
            )
            payload = {
                "positioning": positioning.get("positioning", {}),
                "differentiators": positioning.get("differentiators", []),
            }
            return _governed_result(payload, "account_intelligence", context)

        return _degraded_result(
            "account_intelligence", context, reason=f"unknown_capability:{capability}"
        )


# ============================================================================
# 6. CONVERSATION AGENT (ValuePilot)
# ============================================================================


class ConversationAgent(BaseAgent):
    """User-facing copilot for the ValuePilot chat interface.

    Handles the outer loop: intent classification, context gathering,
    delegation to OrchestrationController for spine workflows, and
    streaming responses back to the user.

    ABOM tools: query_graph, semantic_search, get_entity,
    get_relationships, traverse_tree, find_paths, evaluate_formula,
    calculate_roi, compare_benchmarks, generate_section, create_chart,
    format_table, assemble_document, validate_input, format_currency,
    send_notification, create_task
    """

    agent_type = AgentType.CONVERSATION

    INTENT_CATEGORIES = [
        "account_inquiry",
        "value_analysis",
        "competitive_intel",
        "document_export",
        "workflow_status",
        "general_question",
    ]

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="chat",
                description="Process user chat message and generate response",
                input_schema={
                    "message": "string",
                    "session_id": "string",
                    "account_id": "string",
                },
                output_schema={
                    "response": "string",
                    "intent": "string",
                    "actions_taken": "array",
                },
                timeout_seconds=30,
            ),
            AgentCapability(
                name="classify_intent",
                description="Classify user intent from message",
                input_schema={"message": "string"},
                output_schema={
                    "intent": "string",
                    "confidence": "number",
                    "entities": "object",
                },
                timeout_seconds=5,
            ),
            AgentCapability(
                name="gather_context",
                description="Gather relevant context for user query",
                input_schema={
                    "intent": "string",
                    "entities": "object",
                    "account_id": "string",
                },
                output_schema={"context_data": "object", "sources": "array"},
                timeout_seconds=15,
            ),
        ]

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute conversation handling through GATE-governed tools."""
        capability = task.get("capability")
        params = task.get("parameters", {})

        if capability == "classify_intent":
            search = await _gate_execute(
                context,
                "semantic_search",
                {"query": params["message"], "top_k": 3, "index": "intent_patterns"},
            )
            top_match = search.get("results", [{}])[0] if search.get("results") else {}
            payload = {
                "intent": top_match.get("intent", "general_question"),
                "confidence": top_match.get("score", 0.0),
                "entities": top_match.get("entities", {}),
            }
            return _governed_result(
                payload,
                "account_intelligence",
                context,
                confidence=float(top_match.get("score", 0.8)),
            )

        elif capability == "gather_context":
            intent = params.get("intent", "general_question")
            account_id = params.get("account_id")
            context_data: dict[str, Any] = {}

            if account_id:
                account = await _gate_execute(
                    context,
                    "get_entity",
                    {"entity_type": "Account", "entity_id": account_id},
                )
                context_data["account"] = account

                if intent in ("value_analysis", "competitive_intel"):
                    rels = await _gate_execute(
                        context,
                        "get_relationships",
                        {"entity_id": account_id, "relationship_type": "ALL"},
                    )
                    context_data["relationships"] = rels

            payload = {
                "context_data": context_data,
                "sources": [
                    s.get("source", "graph")
                    for s in context_data.values()
                    if isinstance(s, dict)
                ],
            }
            return _governed_result(payload, "account_intelligence", context)

        elif capability == "chat":
            # Full chat pipeline: classify → gather → respond.
            # Sub-calls now return AgentResult dicts; extract payload for field access.
            intent_envelope = await self.execute(
                {
                    "capability": "classify_intent",
                    "parameters": {"message": params["message"]},
                },
                context,
            )
            intent_payload = intent_envelope.get("payload", intent_envelope)

            context_envelope = await self.execute(
                {
                    "capability": "gather_context",
                    "parameters": {
                        "intent": intent_payload.get("intent", "general_question"),
                        "entities": intent_payload.get("entities", {}),
                        "account_id": params.get("account_id"),
                    },
                },
                context,
            )
            context_payload = context_envelope.get("payload", context_envelope)

            response = await _gate_execute(
                context,
                "generate_section",
                {
                    "section_type": "chat_response",
                    "intent": intent_payload.get("intent", "general_question"),
                    "context_data": context_payload.get("context_data", {}),
                    "user_message": params["message"],
                },
            )
            payload = {
                "response": response.get("content", "I can help with that."),
                "intent": intent_payload.get("intent", "general_question"),
                "actions_taken": response.get("actions", []),
            }
            return _governed_result(payload, "account_intelligence", context)

        return _degraded_result(
            "account_intelligence", context, reason=f"unknown_capability:{capability}"
        )


# ============================================================================
# 7. ORCHESTRATION CONTROLLER
# ============================================================================


class OrchestrationController(BaseAgent):
    """Workflow scheduling and agent coordination.

    Manages the inner loop: receives workflow requests from
    ConversationAgent or API triggers, schedules spine agent
    execution in the correct order, handles failures and retries.

    ABOM tools: (all 20 tools — elevated privilege for cross-agent
    coordination). See orchestration_controller.abom.json.
    """

    agent_type = AgentType.ORCHESTRATION

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.agent_pool: dict[str, BaseAgent] = {}
        self.task_queue: list[dict[str, Any]] = []
        self.running_tasks: dict[str, Any] = {}
        self.scaling_config = {
            "min_instances": self.config.get("min_instances", 2),
            "max_instances": self.config.get("max_instances", 50),
            "scale_trigger": self.config.get("scale_trigger", "queue_depth > 100"),
        }
        self.scheduler = None

    async def _initialize_resources(self) -> None:
        """Initialize task scheduler."""
        try:
            from ..engine.scheduler import TaskScheduler

            self.scheduler = TaskScheduler(
                max_concurrent=self.config.get("max_concurrent_tasks", 100),
            )
        except ImportError:
            logger.info("TaskScheduler not available — using inline execution")

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="schedule_workflow",
                description="Schedule a value spine workflow for execution",
                input_schema={
                    "workflow_type": "string",
                    "inputs": "object",
                    "priority": "string",
                },
                output_schema={"schedule_id": "string", "estimated_start": "string"},
                timeout_seconds=60,
            ),
            AgentCapability(
                name="distribute_tasks",
                description="Distribute tasks to available spine agents",
                input_schema={"tasks": "array", "agent_requirements": "object"},
                output_schema={"assignments": "array", "agent_load": "object"},
                timeout_seconds=120,
            ),
            AgentCapability(
                name="recover_failure",
                description="Recover from agent or task failures",
                input_schema={"failed_task_id": "string", "failure_reason": "string"},
                output_schema={
                    "recovery_action": "string",
                    "retry_scheduled": "boolean",
                },
                timeout_seconds=180,
            ),
            AgentCapability(
                name="manage_resources",
                description="Manage agent pool scaling",
                input_schema={"metric": "string", "threshold": "number"},
                output_schema={
                    "scaling_action": "string",
                    "current_instances": "number",
                },
                timeout_seconds=60,
            ),
        ]

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute orchestration through GATE-governed tools."""
        capability = task.get("capability")
        params = task.get("parameters", {})

        if capability == "schedule_workflow":
            task_result = await _gate_execute(
                context,
                "create_task",
                {
                    "workflow_type": params["workflow_type"],
                    "inputs": params.get("inputs", {}),
                    "priority": params.get("priority", "normal"),
                },
            )
            payload = {
                "schedule_id": task_result.get("task_id", "unknown"),
                "estimated_start": task_result.get("estimated_start", "immediate"),
            }
            return _governed_result(payload, "account_intelligence", context)

        elif capability == "distribute_tasks":
            assignments = []
            for t in params.get("tasks", []):
                assignments.append(
                    {
                        "task_id": t.get("task_id"),
                        "assigned_agent": t.get("agent_type", "auto"),
                        "status": "queued",
                    }
                )
            payload = {
                "assignments": assignments,
                "agent_load": {
                    "active": len(self.running_tasks),
                    "queued": len(self.task_queue),
                },
            }
            return _governed_result(payload, "account_intelligence", context)

        elif capability == "recover_failure":
            await _gate_execute(
                context,
                "send_notification",
                {
                    "type": "agent_failure",
                    "task_id": params["failed_task_id"],
                    "reason": params["failure_reason"],
                },
            )
            payload = {"recovery_action": "retry_with_backoff", "retry_scheduled": True}
            return _governed_result(payload, "account_intelligence", context)

        elif capability == "manage_resources":
            payload = {
                "scaling_action": "no_change",
                "current_instances": len(self.agent_pool),
            }
            return _governed_result(payload, "account_intelligence", context)

        return _degraded_result(
            "account_intelligence", context, reason=f"unknown_capability:{capability}"
        )

    async def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the controller."""
        self.agent_pool[agent.agent_id] = agent

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self.agent_pool:
            del self.agent_pool[agent_id]


# ============================================================================
# BACKWARD COMPATIBILITY ALIASES
# ============================================================================
# These aliases allow existing imports to continue working.
# They are DEPRECATED and will be removed in a future release.
# See docs/platform-contract/DEPRECATION_MAP.md for migration timeline.

DocumentIngestionAgent = ContextExtractionAgent
"""Deprecated: Use ContextExtractionAgent instead."""

FinancialExtractionAgent = ContextExtractionAgent
"""Deprecated: Use ContextExtractionAgent instead."""

ValueTreeProjectionAgent = ValueModelAgent
"""Deprecated: Use ValueModelAgent instead."""

WhitespaceAnalysisAgent = ValueModelAgent
"""Deprecated: Use ValueModelAgent instead."""

ROICalculationAgent = ValueModelAgent
"""Deprecated: Use ValueModelAgent instead."""

NarrativeSynthesisAgent = NarrativeAgent
"""Deprecated: Use NarrativeAgent instead."""

ProvenanceTrackingAgent = IntegrityAgent
"""Deprecated: Use IntegrityAgent instead. Provenance is now a
cross-cutting concern handled by the GATE framework."""
