from __future__ import annotations

"""Business Case Generator workflow implementation."""
import asyncio
import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any

try:
    from value_fabric.shared.identity.feature_flags import is_enabled
except ImportError:
    # Fallback if shared package not available
    def is_enabled(flag_key: str, tenant_id=None, user_id=None) -> bool:
        return False

from value_fabric.shared.models.typed_dict import TypedDictModel

from ..agents.base import AgentResult
from ..harness.prompt_registry import get_prompt_registry
from ..integration.claim_types import to_layer5_claim_type
from ..interfaces.business_case_ground_truth import (
    BusinessCaseGroundTruthClientFactory,
    BusinessCaseGroundTruthPort,
)
from ..models.agent_state import (
    BusinessCaseAgentState,
    BusinessCaseInputData,
    BusinessCaseSection,
    WorkflowStatus,
)
from ..models.workflow_config import BUSINESS_CASE_WORKFLOW_CONFIG
from ..services.governed_llm_client import GovernedLLMClient
from ..services.llm_output_parser import parse_llm_json
from ..services.llm_provider import get_llm_provider
from ..tools.registry import ToolRegistry, ToolResult
from .base import BaseWorkflow

# Backwards-compatible alias: the canonical implementation lives in
# layer4_agents.integration.claim_types.
_to_layer5_claim_type = to_layer5_claim_type


def _unwrap_tool_data(result: Any) -> dict[str, Any]:
    """Extract data dict from ToolResult or return dict fallback."""
    if isinstance(result, ToolResult) and result.status == "success":
        return result.data or {}
    if isinstance(result, dict):
        return result
    return {}
from .roi_calculator import ROICalculatorWorkflow


class BusinessCaseGeneratorWorkflow__execute_agentResult(TypedDictModel):
    status: str

class BusinessCaseGeneratorWorkflow__execute_llmResult(TypedDictModel):
    status: str

class BusinessCaseGeneratorWorkflow__execute_gather_inputsResult(TypedDictModel):
    account_id: Any | None = None
    error: str
    interactions: Any | None = None
    lead_score: Any | None = None
    output_format: Any | None = None
    prospect: Any | None = None
    sections_requested: Any | None = None

class BusinessCaseGeneratorWorkflow__execute_generate_sectionsResult(TypedDictModel):
    blocked: bool
    error: str
    remediation_items: Any
    section_count: Any | None = None
    sections: list[Any]
    truth_references: Any

class BusinessCaseGeneratorWorkflow__execute_roi_subworkflowResult(TypedDictModel):
    account_id: Any | None = None
    detailed_calculations: Any | None = None
    error: str | None = None
    roi_results: dict[str, Any]
    status: str

class BusinessCaseGeneratorWorkflow__execute_verify_truth_requirementsResult(TypedDictModel):
    error: str | None = None
    organization_id: Any
    passed: bool
    remediation_items: list[Any]
    requirements: list[Any]
    truth_references: list[Any]

class BusinessCaseGeneratorWorkflow__execute_assemble_documentResult(TypedDictModel):
    blocked: bool | None = None
    case_metadata: dict[str, Any] | None = None
    error: str
    remediation_items: Any | None = None
    truth_references: Any | None = None

class BusinessCaseGeneratorWorkflow__promote_case_claims_to_truth_objectsResult(TypedDictModel):
    claim_traceability: list[Any]
    threshold_decisions: list[Any]
    truth_object_ids: list[Any]

class BusinessCaseGeneratorWorkflow__sync_ground_truths_to_kgResult(TypedDictModel):
    error: Any
    failed: int
    synced: int

logger = logging.getLogger(__name__)


def _tenant_id_from_state(state: BusinessCaseAgentState) -> str:
    """Return the authenticated tenant id from workflow state."""
    return getattr(state, "tenant_id", None) or state.metadata.get("tenant_id") or state.input_data.get("tenant_id") or ""


class MissingTenantContextError(ValueError):
    """Raised when a tenant-scoped business case workflow has no authenticated tenant context."""


class BusinessCaseGeneratorWorkflow(BaseWorkflow):
    """Workflow for generating comprehensive business case documents.

    Pipeline:
    1. Gather inputs from CRM and prior analyses
    2. Run ROI calculation (sub-workflow)
    3. Generate narrative sections using LLM
    4. Create charts and tables
    5. Assemble into final document

    Example:
        workflow = BusinessCaseGeneratorWorkflow(tool_registry)
        initial_state = workflow.create_initial_state({
            "account_id": "550e8400-e29b-41d4-a716-446655440000",
            "sections_requested": ["executive_summary", "roi_analysis"],
            "output_format": "pdf"
        })
        result = await workflow.run(initial_state)
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        checkpoint_saver=None,
        ground_truth_client_factory: BusinessCaseGroundTruthClientFactory | None = None,
    ):
        """Initialize Business Case Generator workflow."""
        super().__init__(
            config=BUSINESS_CASE_WORKFLOW_CONFIG,
            tool_registry=tool_registry,
            checkpoint_saver=checkpoint_saver,
        )
        self.roi_workflow = ROICalculatorWorkflow(tool_registry, checkpoint_saver)
        self._ground_truth_client_factory = ground_truth_client_factory

    def _get_state_type(self):
        """Return Business Case-specific state type."""
        return BusinessCaseAgentState

    def _get_ground_truth_client(self, organization_id: str) -> BusinessCaseGroundTruthPort | None:
        """Create a Ground Truth port for the authenticated organization."""
        if self._ground_truth_client_factory is None:
            return None
        return self._ground_truth_client_factory(organization_id)

    def create_initial_state(
        self,
        input_data: dict[str, Any],
        *,
        tenant_id: str,
        run_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> BusinessCaseAgentState:
        """Create initial state from input data."""
        from uuid import uuid4

        from ..models.run_envelope import RunEnvelope

        case_input = BusinessCaseInputData(**input_data)
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

        tenant_id_str = str(tenant_id) if tenant_id else ""
        return BusinessCaseAgentState(
            workflow_id=wf_id,
            run_id=r_id,
            trace_id=t_id,
            tenant_id=tenant_id_str,
            workflow_type=self.config.workflow_type,
            status=WorkflowStatus.PENDING,
            case_input=case_input,
            input_data=input_data,
            output_data={},
            errors=[],
            metadata={
                "workflow_name": self.name,
                "authenticated_tenant_id": tenant_id_str,
                "tenant_id": tenant_id_str,
                "trace_id": t_id,
                "run_id": r_id,
            },
            run_envelope=envelope,
        )

    async def _execute_tool(
        self, tool_name: str, state: BusinessCaseAgentState, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute tool with Business Case-specific input building."""

        if tool_name == "gather_case_inputs":
            return await self._execute_gather_inputs(state)
        elif tool_name == "verify_truth_requirements":
            return await self._execute_verify_truth_requirements(state)
        elif tool_name == "validate_claims":
            return await self._execute_validate_claims(state)
        elif tool_name == "assemble_document":
            return await self._execute_assemble_document(state)

        return await super()._execute_tool(tool_name, state, config)

    async def _execute_agent(self, node_config, state: BusinessCaseAgentState) -> dict[str, Any]:
        """Execute agent node (sub-workflow)."""
        if node_config.id == "run_roi":
            return await self._execute_roi_subworkflow(state)

        return BusinessCaseGeneratorWorkflow__execute_agentResult.model_validate({"status": "agent_not_implemented"})

    async def _execute_llm(self, node_config, state: BusinessCaseAgentState) -> dict[str, Any]:
        """Execute LLM node for section generation."""
        if node_config.id == "generate_narrative":
            return await self._execute_generate_sections(state)
        if node_config.id == "validate_claims":
            return await self._execute_validate_claims(state)

        return BusinessCaseGeneratorWorkflow__execute_llmResult.model_validate({"status": "llm_not_implemented"})

    async def _execute_gather_inputs(self, state: BusinessCaseAgentState) -> dict[str, Any]:
        """Gather all inputs needed for business case generation."""
        if not state.case_input:
            return BusinessCaseGeneratorWorkflow__execute_gather_inputsResult.model_validate({"error": "No business case input configured"})

        account_id = str(state.case_input.account_id)
        prospect_id = state.case_input.custom_inputs.get("provider_record_id", account_id)
        tenant_id = _tenant_id_from_state(state)
        tool_ctx = {
            "tenant_id": tenant_id,
            "trace_id": state.trace_id,
            "workflow_id": state.workflow_id,
            "run_id": state.run_id,
        }

        # Fetch prospect data
        prospect_data = await self.tool_registry.execute(
            "get_prospect_data",
            {
                "prospect_id": prospect_id,
                "data_types": ["profile", "interactions", "opportunities"],
                "prospect_data": state.input_data.get("prospect_data", {}),
                **tool_ctx,
            },
        )

        # Fetch interaction history
        interactions = await self.tool_registry.execute(
            "fetch_interaction_history", {"prospect_id": prospect_id, "limit": 10, **tool_ctx}
        )

        # Score lead for additional context
        lead_score = await self.tool_registry.execute(
            "score_lead", {"prospect_id": prospect_id, **tool_ctx}
        )

        return BusinessCaseGeneratorWorkflow__execute_gather_inputsResult.model_validate({
            "account_id": account_id,
            "prospect": prospect_data,
            "interactions": interactions,
            "lead_score": lead_score,
            "sections_requested": state.case_input.sections_requested,
            "output_format": state.case_input.output_format,
            "error": "",
        })


    async def _execute_roi_subworkflow(self, state: BusinessCaseAgentState) -> dict[str, Any]:
        """Execute ROI calculation as sub-workflow."""
        if not state.case_input:
            return BusinessCaseGeneratorWorkflow__execute_roi_subworkflowResult.model_validate({
                "error": "No business case input configured",
                "status": "failed",
                "roi_results": {},
            })

        account_id = str(state.case_input.account_id)
        prospect_id = state.case_input.custom_inputs.get("provider_record_id", account_id)
        try:
            value_driver_ids = await self._resolve_value_driver_ids(state, account_id)
        except ValueError:
            return BusinessCaseGeneratorWorkflow__execute_roi_subworkflowResult.model_validate({
                "status": "failed",
                "error": "ROI subworkflow failed",
                "error_code": "ROI_SUBWORKFLOW_ERROR",
                "roi_results": {},
            })

        # Create ROI workflow state
        tenant_id = _tenant_id_from_state(state)
        roi_input_data = {
            "prospect_id": prospect_id,
            "value_driver_ids": value_driver_ids,
            "use_benchmarks": True,
        }

        roi_initial_state = self.roi_workflow.create_initial_state(
            roi_input_data,
            tenant_id=tenant_id,
            trace_id=state.trace_id,
            workflow_id=state.workflow_id,
            run_id=f"{state.run_id}:roi",
        )

        # Run ROI workflow
        try:
            roi_result = await self.roi_workflow.run(roi_initial_state)

            aggregate = roi_result.output_data.get("aggregate", {}) or {}
            return BusinessCaseGeneratorWorkflow__execute_roi_subworkflowResult.model_validate({
                "status": "completed",
                "account_id": account_id,
                "roi_results": aggregate.get("aggregated", {}) if isinstance(aggregate, dict) else {},
                "detailed_calculations": roi_result.calculation_results,
            })


        except asyncio.CancelledError:
            raise
        except Exception:
            return BusinessCaseGeneratorWorkflow__execute_roi_subworkflowResult.model_validate({"status": "failed", "error": "ROI_SUBWORKFLOW_ERROR", "roi_results": {}})

    async def _resolve_value_driver_ids(
        self, state: BusinessCaseAgentState, account_id: str
    ) -> list[str]:
        """Resolve tenant/account value drivers without hardcoded sample IDs."""
        custom_value_driver_ids = state.case_input.custom_inputs.get("value_driver_ids")
        if isinstance(custom_value_driver_ids, list):
            resolved = [str(driver_id).strip() for driver_id in custom_value_driver_ids if str(driver_id).strip()]
            if resolved:
                return resolved

        env_defaults = os.getenv("LAYER4_DEFAULT_VALUE_DRIVER_IDS", "")
        if env_defaults:
            resolved = [driver_id.strip() for driver_id in env_defaults.split(",") if driver_id.strip()]
            if resolved:
                return resolved

        tenant_id = _tenant_id_from_state(state)
        query_result = await self.tool_registry.execute(
            "query_graph",
            {
                "cypher_query": """
                    MATCH (a {id: $account_id})-[:USES_VALUE_DRIVER|HAS_VALUE_DRIVER]->(v:ValueDriver)
                    WHERE coalesce(v.status, 'ACTIVE') IN ['ACTIVE', 'VALIDATED']
                    RETURN v.id AS id
                    LIMIT 25
                """,
                "parameters": {"account_id": account_id},
                "tenant_id": tenant_id,
                "trace_id": state.trace_id,
                "workflow_id": state.workflow_id,
                "run_id": state.run_id,
            },
        )
        drivers = []
        for row in _unwrap_tool_data(query_result).get("results", []):
            driver_id = row.get("id") or row.get("v.id")
            if driver_id:
                drivers.append(str(driver_id))
        if drivers:
            return drivers

        raise ValueError(
            "No value_driver_ids available for business case ROI calculation. "
            "Provide custom_inputs.value_driver_ids or configure graph-backed account drivers."
        )

    async def _execute_generate_sections(self, state: BusinessCaseAgentState) -> dict[str, Any]:
        """Generate all requested narrative sections.

        Feature flag 'enhanced_narrative_generation' controls whether to use
        the new LLM-powered section enhancement feature.
        """
        if not state.case_input:
            return BusinessCaseGeneratorWorkflow__execute_generate_sectionsResult.model_validate({
                "error": "No business case input configured",
                "sections": [],
                "blocked": False,
                "remediation_items": [],
                "truth_references": [],
            })

        gate_result = state.output_data.get("verify_truth_requirements", {})
        if gate_result and not gate_result.get("passed", True):
            return BusinessCaseGeneratorWorkflow__execute_generate_sectionsResult.model_validate({
                "error": "Narrative generation blocked by truth verification gate",
                "blocked": True,
                "sections": [],
                "remediation_items": gate_result.get("remediation_items", []),
                "truth_references": gate_result.get("truth_references", []),
            })


        # Check feature flag for enhanced narrative generation (Task 83: is_enabled usage)
        enhanced_mode = await is_enabled(
            "enhanced_narrative_generation",
            tenant_id=getattr(state, 'tenant_id', None),
            user_id=getattr(state, 'user_id', None),
        )
        if enhanced_mode:
            logger.info("Using enhanced narrative generation for business case")

        gathered = state.output_data.get("gather_inputs", {})
        roi_data = state.output_data.get("run_roi", {})

        prospect = gathered.get("prospect", {})
        profile = prospect.get("profile", {})
        roi_results = roi_data.get("roi_results", {})

        sections_generated: list[BusinessCaseSection] = []

        # Build context for section generation
        context = {
            "company_name": profile.get("name", "the prospect"),
            "industry": profile.get("industry", "their industry"),
            "annual_revenue": profile.get("annual_revenue", "unknown"),
            "pain_points": prospect.get("custom_fields", {}).get("pain_points", []),
            "roi_percent": roi_results.get("simple_roi_percent", 0),
            "payback_months": roi_results.get("payback_period_months", 0),
            "three_year_npv": roi_results.get("three_year_npv", 0),
        }

        requested_sections = state.case_input.sections_requested

        # Map section types to titles
        section_titles = {
            "executive_summary": "Executive Summary",
            "current_state": "Current State Analysis",
            "proposed_solution": "Proposed Solution",
            "roi_analysis": "ROI Analysis",
            "implementation": "Implementation Plan",
            "next_steps": "Recommended Next Steps",
        }

        trace_id = state.metadata.get("trace_id") or state.metadata.get("run_id") if state.metadata else None
        tenant_id_for_run = _tenant_id_from_state(state)

        # Build governed LLM client for section generation
        try:
            registry = get_prompt_registry()
            system_tmpl = registry.get("business_case", "system")
            section_tmpl = registry.get("business_case", "generate_sections")
            provider = get_llm_provider(self.config)
            harness_run = self._make_harness_run(
                "business_case_generation",
                tenant_id=tenant_id_for_run or "unknown",
                trace_id=trace_id,
            )
            llm_client = GovernedLLMClient(
                provider=provider,
                provider_name=self._resolve_provider_name(),
                run=harness_run,
            )
            system_msg = {"role": "system", "content": system_tmpl.body}
            use_llm = True
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Could not initialise LLM client for section generation: %s", exc)
            llm_client = None
            system_msg = None
            section_tmpl = None
            use_llm = False

        for section_type in requested_sections:
            title = section_titles.get(section_type, section_type.replace("_", " ").title())

            try:
                content = ""

                if use_llm and llm_client and section_tmpl:
                    # Use prompt registry + GovernedLLMClient for section content
                    brief = {
                        "section_type": section_type,
                        "company_name": context["company_name"],
                        "industry": context["industry"],
                        "roi_percent": context["roi_percent"],
                        "payback_months": context["payback_months"],
                        "three_year_npv": context["three_year_npv"],
                        "pain_points": context["pain_points"],
                    }
                    user_content = section_tmpl.render(
                        account_name=context["company_name"],
                        section_type=section_type,
                        brief_json=json.dumps(brief, indent=2),
                        section_context_json=json.dumps(context, indent=2),
                    )
                    llm_result = await llm_client.call(
                        model_task=section_tmpl.model_task,
                        messages=[system_msg, {"role": "user", "content": user_content}],
                        temperature=section_tmpl.temperature,
                        max_tokens=section_tmpl.max_tokens,
                        call_id=f"bc_section_{section_type}_{trace_id or 'unknown'}",
                    )
                    parsed = parse_llm_json(llm_result.content)
                    content = parsed.get("content", llm_result.content)
                else:
                    # Fallback: tool-based generation
                    section_result = await self.tool_registry.execute(
                        "generate_section",
                        {
                            "section_type": section_type,
                            "context": context,
                            "tone": "professional",
                            "max_length": 500,
                            "tenant_id": tenant_id_for_run,
                            "trace_id": trace_id,
                            "workflow_id": state.workflow_id,
                            "run_id": state.run_id,
                        },
                    )
                    content = _unwrap_tool_data(section_result).get("content", "")

                # Create charts for ROI section
                charts = []
                if section_type == "roi_analysis" and roi_results:
                    chart_result = await self.tool_registry.execute(
                        "create_chart",
                        {
                            "chart_type": "bar",
                            "data": [
                                {"label": "Investment", "value": roi_results.get("investment_required", 0)},
                                {"label": "Year 1 Value", "value": roi_results.get("total_annual_value", 0)},
                                {"label": "3-Year NPV", "value": roi_results.get("three_year_npv", 0)},
                            ],
                            "title": "ROI Summary",
                            "tenant_id": tenant_id_for_run,
                            "trace_id": trace_id,
                            "workflow_id": state.workflow_id,
                            "run_id": state.run_id,
                        },
                    )
                    charts.append(_unwrap_tool_data(chart_result).get("chart_data", {}))

                section = BusinessCaseSection(title=title, content=content, charts=charts, tables=[])
                sections_generated.append(section)

            except asyncio.CancelledError:
                raise
            except Exception:
                section = BusinessCaseSection(
                    title=title, content="Error generating section: SECTION_GENERATION_ERROR", charts=[], tables=[]
                )
                sections_generated.append(section)

        return BusinessCaseGeneratorWorkflow__execute_generate_sectionsResult.model_validate({
            "sections": [s.model_dump() for s in sections_generated],
            "section_count": len(sections_generated),
            "blocked": False,
            "error": "",
            "remediation_items": [],
            "truth_references": [],
        })


    async def _execute_verify_truth_requirements(
        self, state: BusinessCaseAgentState
    ) -> dict[str, Any]:
        """Verify required claims/metrics against Layer 5 TruthObjects."""
        if not state.case_input:
            return BusinessCaseGeneratorWorkflow__execute_verify_truth_requirementsResult.model_validate({
                "error": "No business case input configured",
                "passed": False,
                "organization_id": None,
                "requirements": [],
                "truth_references": [],
                "remediation_items": [],
            })

        # Local-development escape hatch: skip Layer-5 truth gating so the
        # business-case workflow can produce a full document against an empty
        # ground-truth database.  This must NOT be enabled in production.
        if os.getenv("LAYER4_BUSINESS_CASE_SKIP_TRUTH_GATE", "").lower() in ("true", "1", "yes"):
            logger.warning("Business case truth gate skipped via LAYER4_BUSINESS_CASE_SKIP_TRUTH_GATE")
            return BusinessCaseGeneratorWorkflow__execute_verify_truth_requirementsResult.model_validate({
                "passed": True,
                "requirements": [],
                "truth_references": [],
                "remediation_items": [],
                "organization_id": None,
                "skipped": True,
            })

        requirements = state.case_input.custom_inputs.get("truth_requirements", [])
        if not requirements:
            return BusinessCaseGeneratorWorkflow__execute_verify_truth_requirementsResult.model_validate({
                "passed": True,
                "requirements": [],
                "truth_references": [],
                "remediation_items": [],
                "organization_id": None,
            })

        organization_id = self._resolve_organization_id(state)
        min_maturity = min(
            [int(req.get("min_maturity", 0)) for req in requirements if req.get("min_maturity") is not None],
            default=0,
        )
        min_confidence = min(
            [float(req.get("min_confidence", 0.0)) for req in requirements if req.get("min_confidence") is not None],
            default=0.0,
        )

        client = self._get_ground_truth_client(organization_id)
        if client is None:
            return BusinessCaseGeneratorWorkflow__execute_verify_truth_requirementsResult.model_validate({
                "passed": False,
                "requirements": [],
                "truth_references": [],
                "remediation_items": [
                    {
                        "type": "ground_truth_unavailable",
                        "message": "Layer 5 Ground Truth client is not configured.",
                    }
                ],
                "organization_id": organization_id,
            })

        status_rank = {
            "proposed": 0,
            "validated": 3,
            "disputed": -1,
            "rejected": -1,
            "superseded": -1,
            "expired": -1,
            # Backward-compat aliases for old config files
            "extracted": 0,
            "supported": 1,
            "corroborated": 2,
            "approved": 3,
        }
        truth_references: list[dict[str, Any]] = []
        remediation_items: list[dict[str, Any]] = []
        requirement_results: list[dict[str, Any]] = []
        all_passed = True

        try:
            truths_result = await client.list_truths(
                organization_id=organization_id,
                min_maturity=min_maturity,
                min_confidence=min_confidence,
                applies_to_opportunity=state.case_input.opportunity_id,
                limit=200,
                offset=0,
            )
            truths = truths_result.get("items", []) if isinstance(truths_result, dict) else []

            for req in requirements:
                required_status = str(req.get("min_status", "validated")).lower()
                required_maturity = int(req.get("min_maturity", 3))
                required_confidence = float(req.get("min_confidence", 0.0))
                required_sources = int(req.get("min_sources", 2))
                label = req.get("label") or req.get("claim") or req.get("metric") or "required-claim"
                required = bool(req.get("required", True))

                def _match(truth: dict[str, Any], _req: dict = req) -> bool:
                    claim_q = str(_req.get("claim", "")).strip().lower()
                    metric_q = str(_req.get("metric", "")).strip().lower()
                    claim_text = str(truth.get("claim", "")).lower()
                    if claim_q and claim_q in claim_text:
                        return True
                    if metric_q and (
                        metric_q in claim_text
                        or metric_q == str(truth.get("claim_type", "")).lower()
                    ):
                        return True
                    return False

                matches = [t for t in truths if _match(t)]
                if not matches:
                    if required:
                        all_passed = False
                        remediation_items.append(
                            {
                                "type": "missing_evidence",
                                "requirement": label,
                                "message": "No matching TruthObject found. Add supporting evidence.",
                            }
                        )
                    requirement_results.append({"requirement": label, "passed": False, "match_count": 0})
                    continue

                best = sorted(
                    matches,
                    key=lambda t: (
                        status_rank.get(str(t.get("status", "")).lower(), -1),
                        int(t.get("maturity_level", 0)),
                        float(t.get("confidence", 0.0)),
                        int(t.get("source_count", 0)),
                    ),
                    reverse=True,
                )[0]

                status_ok = status_rank.get(str(best.get("status", "")).lower(), -1) >= status_rank.get(required_status, 2)
                maturity_ok = int(best.get("maturity_level", 0)) >= required_maturity
                confidence_ok = float(best.get("confidence", 0.0)) >= required_confidence
                sources_ok = int(best.get("source_count", 0)) >= required_sources
                passed = status_ok and maturity_ok and confidence_ok

                truth_references.append(
                    {
                        "requirement": label,
                        "truth_object_id": str(best.get("id")),
                        "claim": best.get("claim"),
                        "claim_type": best.get("claim_type"),
                        "status": best.get("status"),
                        "maturity_level": best.get("maturity_level"),
                        "confidence": best.get("confidence"),
                        "source_count": best.get("source_count", 0),
                        "freshness": best.get("freshness"),
                    }
                )
                requirement_results.append(
                    {
                        "requirement": label,
                        "passed": passed,
                        "status_ok": status_ok,
                        "maturity_ok": maturity_ok,
                        "confidence_ok": confidence_ok,
                        "sources_ok": sources_ok,
                        "truth_object_id": str(best.get("id")),
                    }
                )

                if required and not passed:
                    all_passed = False
                    if not sources_ok:
                        remediation_items.append(
                            {
                                "type": "insufficient_corroboration",
                                "requirement": label,
                                "message": "Evidence exists but corroboration is insufficient. Add independent sources.",
                            }
                        )
                    elif required_status in ("approved", "validated") and str(best.get("status", "")).lower() not in ("approved", "validated"):
                        remediation_items.append(
                            {
                                "type": "approval_pending",
                                "requirement": label,
                                "message": "Evidence is not yet validated. Complete governance validation in Layer 5.",
                            }
                        )
                    else:
                        remediation_items.append(
                            {
                                "type": "verification_gap",
                                "requirement": label,
                                "message": "Evidence does not meet required status/maturity/confidence thresholds.",
                            }
                        )

            return BusinessCaseGeneratorWorkflow__execute_verify_truth_requirementsResult.model_validate({
                "passed": all_passed,
                "requirements": requirement_results,
                "truth_references": truth_references,
                "remediation_items": remediation_items,
                "organization_id": organization_id,
            })


        finally:
            await client.close()

    async def _execute_assemble_document(self, state: BusinessCaseAgentState) -> dict[str, Any]:
        """Assemble sections into final document, then sync ground truths to KG."""
        if not state.case_input:
            return BusinessCaseGeneratorWorkflow__execute_assemble_documentResult.model_validate({"error": "No business case input configured"})

        gate_result = state.output_data.get("verify_truth_requirements", {})
        if gate_result and not gate_result.get("passed", True):
            return BusinessCaseGeneratorWorkflow__execute_assemble_documentResult.model_validate({
                "blocked": True,
                "error": "Final narrative/export blocked: required claims are not verified",
                "remediation_items": gate_result.get("remediation_items", []),
                "truth_references": gate_result.get("truth_references", []),
                "case_metadata": {
                    "account_id": str(state.case_input.account_id),
                    "truth_gate": {
                        "passed": False,
                        "requirements": gate_result.get("requirements", []),
                    },
                    "truth_references": gate_result.get("truth_references", []),
                },
            })


        sections_data = state.output_data.get("generate_narrative", {}).get("sections", [])

        if not sections_data:
            return BusinessCaseGeneratorWorkflow__execute_assemble_documentResult.model_validate({"error": "No sections generated"})

        # Prepare sections for assembly
        assembly_sections = []
        for s in sections_data:
            assembly_sections.append(
                {
                    "title": s.get("title", "Section"),
                    "content": s.get("content", ""),
                    "charts": s.get("charts", []),
                    "tables": s.get("tables", []),
                }
            )

        # Assemble document
        assemble_result: dict[str, Any] = {}
        try:
            tenant_id = _tenant_id_from_state(state)
            result = await self.tool_registry.execute(
                "assemble_document",
                {
                    "sections": assembly_sections,
                    "template": "business_case",
                    "output_format": state.case_input.output_format,
                    "branding": {
                        "company_name": state.case_input.custom_inputs.get(
                            "company_name", "Value Fabric"
                        ),
                        "date": state.case_input.custom_inputs.get("date", "2024"),
                    },
                    "tenant_id": tenant_id,
                    "trace_id": state.trace_id,
                    "workflow_id": state.workflow_id,
                    "run_id": state.run_id,
                },
            )
            tool_data = _unwrap_tool_data(result)
            roi_results = state.output_data.get("run_roi", {}).get("roi_results", {})
            sections_by_title = {s.get("title", ""): s for s in assembly_sections}
            executive = sections_by_title.get("Executive Summary", {})
            next_steps = sections_by_title.get("Recommended Next Steps", {})
            assemble_result = {
                "document_bytes": tool_data.get("document_bytes"),
                "document_url": tool_data.get("document_url"),
                "page_count": tool_data.get("page_count", len(assembly_sections)),
                "file_size_bytes": tool_data.get("file_size_bytes", 0),
                "format": state.case_input.output_format,
                "title": f"Business Case — {state.case_input.custom_inputs.get('company_name', 'Value Fabric')}",
                "summary": executive.get("content", "")[:2000],
                "total_value": roi_results.get("total_annual_value") or 0.0,
                "implementation_cost": roi_results.get("investment_required") or 0.0,
                "roi_ratio": (roi_results.get("simple_roi_percent") or 0.0) / 100.0,
                "payback_months": int(roi_results.get("payback_period_months") or 0),
                "confidence_score": roi_results.get("average_confidence") or 0.0,
                "recommendations": [next_steps.get("content", "")] if next_steps.get("content") else [],
                "created_at": datetime.now(UTC).isoformat(),
            }
        except asyncio.CancelledError:
            raise
        except Exception:
            assemble_result = {
                "error": "DOCUMENT_ASSEMBLE_ERROR",
                "document_bytes": None,
                "document_url": None,
            }

        # ── Layer 5 Ground Truth sync ──────────────────────────────────────
        # After the business case document is assembled, trigger a bulk sync
        # of all APPROVED TruthObjects for this tenant to the Layer 3
        # Knowledge Graph.  This is best-effort: a Layer 5 outage must not
        # block document delivery.  When the truth gate is explicitly skipped
        # (e.g. local e2e), skip the sync/promotion calls entirely to avoid
        # repeated 422s against a Layer 5 schema that does not accept the
        # legacy claim_type values.
        sdes_bundle = state.output_data.get("generate_sdes", {})
        if gate_result.get("skipped"):
            sync_result = {"synced": 0, "failed": 0, "skipped": True}
            claim_promotion = {"truth_object_ids": [], "claim_traceability": [], "threshold_decisions": []}
        else:
            sync_result = await self._sync_ground_truths_to_kg(state)
            try:
                claim_promotion = await self._promote_case_claims_to_truth_objects(
                    state=state,
                    sections_data=sections_data,
                )
            except Exception as exc:
                logger.warning(
                    "Claim promotion failed (non-blocking) for org=%s: %s",
                    gate_result.get("organization_id"),
                    exc,
                )
                claim_promotion = {
                    "truth_object_ids": [],
                    "claim_traceability": [],
                    "threshold_decisions": [],
                }
        assemble_result["ground_truth_sync"] = sync_result
        assemble_result["case_metadata"] = {
            "account_id": str(state.case_input.account_id),
            "truth_gate": {
                "passed": gate_result.get("passed", True),
                "requirements": gate_result.get("requirements", []),
                "remediation_items": gate_result.get("remediation_items", []),
            },
            "truth_references": gate_result.get("truth_references", []),
            "sdes_references": {
                "canonical_case_id": sdes_bundle.get("canonical_case_id"),
                "account_id": sdes_bundle.get("account_id"),
                "signal_count": len(sdes_bundle.get("signals", [])),
                "driver_count": len(sdes_bundle.get("drivers", [])),
                "evidence_count": len(sdes_bundle.get("evidence", [])),
                "stakeholder_count": len(sdes_bundle.get("stakeholders", [])),
            },
            "truth_object_ids": claim_promotion.get("truth_object_ids", []),
            "claim_traceability": claim_promotion.get("claim_traceability", []),
            "threshold_decisions": claim_promotion.get("threshold_decisions", []),
        }
        assemble_result["truth_object_ids"] = claim_promotion.get("truth_object_ids", [])
        assemble_result["claim_traceability"] = claim_promotion.get("claim_traceability", [])
        assemble_result["threshold_decisions"] = claim_promotion.get("threshold_decisions", [])

        return assemble_result

    def _extract_candidate_claims(
        self,
        sections_data: list[dict[str, Any]],
        roi_results: dict[str, Any],
        source_refs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Deterministically extract candidate claims and provenance pointers."""
        candidates: list[dict[str, Any]] = []
        for section_index, section in enumerate(sections_data):
            title = section.get("title", "Section")
            content = section.get("content", "") or ""
            for sentence in re.split(r"(?<=[.!?])\s+", content):
                sentence_clean = sentence.strip()
                if len(sentence_clean) < 20 or not re.search(r"(\d|%|\$)", sentence_clean):
                    continue
                start = content.find(sentence_clean)
                end = start + len(sentence_clean) if start >= 0 else -1
                candidates.append(
                    {
                        "claim": sentence_clean,
                        "claim_type": "metric",
                        "confidence": 0.62,
                        "evidence_count": len(source_refs),
                        "sources": source_refs,
                        "provenance": {
                            "section_title": title,
                            "section_index": section_index,
                            "content_span": {"start": max(start, 0), "end": max(end, 0)},
                            "source_ids": [str(ref.get("id")) for ref in source_refs if ref.get("id")],
                            "source_uris": [ref.get("uri") for ref in source_refs if ref.get("uri")],
                        },
                    }
                )

        roi_metric_map = {
            "simple_roi_percent": ("roi_assumption", "Projected simple ROI is {value:.2f}%."),
            "payback_period_months": ("metric", "Projected payback period is {value:.2f} months."),
            "three_year_npv": ("outcome", "Projected 3-year NPV is ${value:,.2f}."),
        }
        for metric_key, (claim_type, template) in roi_metric_map.items():
            value = roi_results.get(metric_key)
            if value is None:
                continue
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue
            candidates.append(
                {
                    "claim": template.format(value=numeric_value),
                    "claim_type": claim_type,
                    "confidence": 0.8,
                    "evidence_count": len(source_refs) + 1,
                    "sources": source_refs,
                    "provenance": {
                        "roi_metric_key": metric_key,
                        "roi_metric_value": numeric_value,
                        "source_ids": [str(ref.get("id")) for ref in source_refs if ref.get("id")],
                        "source_uris": [ref.get("uri") for ref in source_refs if ref.get("uri")],
                    },
                }
            )

        return candidates

    async def _promote_case_claims_to_truth_objects(
        self,
        state: BusinessCaseAgentState,
        sections_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create/promote deterministic claims to Layer 5 and persist traceability."""
        if not state.case_input:
            return BusinessCaseGeneratorWorkflow__promote_case_claims_to_truth_objectsResult.model_validate({"truth_object_ids": [], "claim_traceability": [], "threshold_decisions": []})

        thresholds = state.case_input.custom_inputs.get("claim_promotion_thresholds", {})
        min_confidence = float(thresholds.get("min_confidence", 0.75))
        min_evidence = int(thresholds.get("min_evidence_sources", 1))
        organization_id = self._resolve_organization_id(state)

        source_refs = state.case_input.custom_inputs.get("source_references", [])
        roi_results = state.output_data.get("run_roi", {}).get("roi_results", {})
        candidates = self._extract_candidate_claims(sections_data, roi_results, source_refs)

        client = self._get_ground_truth_client(organization_id)
        if client is None:
            return BusinessCaseGeneratorWorkflow__promote_case_claims_to_truth_objectsResult.model_validate({
                "truth_object_ids": [],
                "claim_traceability": [],
                "threshold_decisions": [
                    {
                        "decision": "skipped",
                        "reason": "Layer 5 Ground Truth client is not configured.",
                    }
                ],
            })

        truth_object_ids: list[str] = []
        claim_traceability: list[dict[str, Any]] = []
        threshold_decisions: list[dict[str, Any]] = []

        try:
            for candidate in candidates:
                confidence = float(candidate.get("confidence", 0.0))
                evidence_count = int(candidate.get("evidence_count", 0))
                claim_text = str(candidate.get("claim", "")).strip()

                eligible = confidence >= min_confidence and evidence_count >= min_evidence
                decision = {
                    "claim": claim_text,
                    "confidence": confidence,
                    "evidence_count": evidence_count,
                    "min_confidence": min_confidence,
                    "min_evidence_sources": min_evidence,
                    "decision": "promoted" if eligible else "skipped",
                    "reason": (
                        "meets confidence and evidence thresholds"
                        if eligible
                        else "failed confidence/evidence threshold"
                    ),
                }

                truth_id: str | None = None
                if eligible and claim_text:
                    layer4_claim_type = str(candidate.get("claim_type", "metric"))
                    layer5_claim_type = _to_layer5_claim_type(layer4_claim_type)
                    decision["layer4_claim_type"] = layer4_claim_type
                    decision["layer5_claim_type"] = layer5_claim_type
                    existing_truths = await client.list_truths(
                        organization_id=organization_id,
                        claim_type=layer5_claim_type,
                        limit=100,
                        offset=0,
                    )
                    existing_items = existing_truths.get("items", []) if isinstance(existing_truths, dict) else []
                    existing_match = next(
                        (
                            item for item in existing_items
                            if str(item.get("claim", "")).strip().lower() == claim_text.lower()
                        ),
                        None,
                    )

                    if existing_match:
                        truth_id = str(existing_match.get("id"))
                        decision["reason"] = "already exists in Layer 5"
                        decision["decision"] = "existing"
                    else:
                        created = await client.submit_truth(
                            claim=claim_text,
                            claim_type=layer5_claim_type,
                            confidence=confidence,
                            organization_id=organization_id,
                            applies_to={"opportunity_id": state.case_input.opportunity_id},
                            sources=candidate.get("sources", []),
                            raw_extraction_data={"provenance": candidate.get("provenance", {})},
                        )
                        truth_id = str(created.get("id")) if isinstance(created, dict) and created.get("id") else None
                        # Auto-advance on creation handles PROPOSED → VALIDATED
                        # when confidence/sources thresholds are met.
                        pass

                if truth_id:
                    truth_object_ids.append(truth_id)

                claim_traceability.append(
                    {
                        "claim": claim_text,
                        "truth_object_id": truth_id,
                        "layer4_claim_type": candidate.get("claim_type"),
                        "layer5_claim_type": (
                            _to_layer5_claim_type(candidate.get("claim_type"))
                            if candidate.get("claim_type") is not None
                            else None
                        ),
                        "provenance": candidate.get("provenance", {}),
                        "sources": candidate.get("sources", []),
                    }
                )
                threshold_decisions.append(decision)

            return BusinessCaseGeneratorWorkflow__promote_case_claims_to_truth_objectsResult.model_validate({
                "truth_object_ids": sorted(set(truth_object_ids)),
                "claim_traceability": claim_traceability,
                "threshold_decisions": threshold_decisions,
            })


        finally:
            await client.close()

    # -----------------------------------------------------------------------
    # LLM claim validation
    # -----------------------------------------------------------------------
    async def _execute_validate_claims(self, state: BusinessCaseAgentState) -> dict[str, Any]:
        """Extract claims from generated sections and validate against Layer 5.

        Uses the ``business_case/validate_claims`` prompt to extract structured
        claims from section content, then submits each claim to the live L5
        validator.  Returns an ``AgentResult`` with:
        - ``validated_claims``: list of claims with validation status
        - ``unverified_claims``: claims that could not be validated
        - ``human_review_required``: True if any claim is unverified

        The human gate in ``harness.runtime.yaml`` (``VALIDATE_CLAIMS``) is
        triggered when ``human_review_required=True``.
        """
        if os.getenv("LAYER4_BUSINESS_CASE_SKIP_TRUTH_GATE", "").lower() in ("true", "1", "yes"):
            return AgentResult(
                payload={
                    "validated_claims": [],
                    "unverified_claims": [],
                    "claim_count": 0,
                    "skipped": True,
                },
                workflow_type="business_case",
                tenant_id=str(state.metadata.get("authenticated_tenant_id")) if state.metadata and state.metadata.get("authenticated_tenant_id") else "",
                trace_id=state.metadata.get("trace_id") or state.metadata.get("run_id") if state.metadata else None,
            ).to_dict()

        trace_id = state.metadata.get("trace_id") or state.metadata.get("run_id") if state.metadata else None
        account_name = (
            state.case_input.custom_inputs.get("account_name", "")
            if state.case_input
            else state.input_data.get("account_name", "Unknown Account")
        )

        # AgentResult is constructed with an empty tenant_id initially; it is
        # populated after tenant resolution inside the try block below.
        agent_result = AgentResult(
            payload={},
            workflow_type="business_case",
            tenant_id="",
            trace_id=trace_id,
        )

        sections_prior = state.output_data.get("generate_narrative", {})
        sections = sections_prior.get("sections", [])

        if not sections:
            agent_result.payload = {
                "validated_claims": [],
                "unverified_claims": [],
                "claim_count": 0,
            }
            agent_result.degraded_reason = "no_sections_to_validate"
            return agent_result.to_dict()

        try:
            # Resolve tenant first — MissingTenantContextError must degrade, not crash.
            organization_id = self._resolve_organization_id(state)
            agent_result.tenant_id = organization_id

            registry = get_prompt_registry()
            system_tmpl = registry.get("business_case", "system")
            validate_tmpl = registry.get("business_case", "validate_claims")

            provider = get_llm_provider(self.config)
            harness_run = self._make_harness_run(
                "business_case_generation",
                tenant_id=organization_id,
                trace_id=trace_id,
            )
            llm_client = GovernedLLMClient(
                provider=provider,
                provider_name=self._resolve_provider_name(),
                run=harness_run,
            )

            user_content = validate_tmpl.render(
                account_name=account_name,
                sections_json=json.dumps(sections, indent=2),
            )
            llm_result = await llm_client.call(
                model_task=validate_tmpl.model_task,
                messages=[
                    {"role": "system", "content": system_tmpl.body},
                    {"role": "user", "content": user_content},
                ],
                temperature=validate_tmpl.temperature,
                max_tokens=validate_tmpl.max_tokens,
                call_id=f"bc_validate_{trace_id or 'unknown'}",
            )
            parsed = parse_llm_json(llm_result.content)
            extracted_claims = parsed.get("claims", [])

            # Validate each claim against Layer 5 (best-effort)
            validated: list[dict] = []
            unverified: list[dict] = []
            ground_truth_client = self._get_ground_truth_client(organization_id)

            if ground_truth_client is None:
                # L5 unavailable due to missing config — mark all claims as unavailable.
                logger.warning("Layer 5 Ground Truth client not configured; skipping L5 claim validation")
                for claim in extracted_claims[:20]:
                    claim_text = claim.get("claim_text", "")
                    if claim_text:
                        unverified.append({
                            **claim,
                            "l5_status": "unavailable",
                            "reason": "Layer 5 validator unavailable: missing configuration",
                        })
            else:
                try:
                    for claim in extracted_claims[:20]:  # cap at 20 claims per run
                        claim_text = claim.get("claim_text", "")
                        if not claim_text:
                            continue
                        try:
                            result = await ground_truth_client.validate_claim(
                                tenant_id=organization_id,
                                claim_id=claim.get("claim_id", claim_text[:64]),
                                claim_text=claim_text,
                                evidence_refs=claim.get("evidence_refs", []),
                                account_id=str(state.case_input.opportunity_id) if state.case_input else None,
                                value_pack_id="business_case",
                            )
                            validation_status = str(result.get("status", "unavailable"))
                            if validation_status == "passed":
                                validated.append({**claim, "l5_status": "validated", "evidence": result.get("evidence_refs", [])})
                            else:
                                unverified.append({**claim, "l5_status": validation_status, "reason": result.get("reason")})
                        except asyncio.CancelledError:
                            raise
                        except Exception as val_exc:
                            logger.debug("L5 validation unavailable for claim: %s", val_exc)
                            unverified.append({**claim, "l5_status": "unavailable"})
                finally:
                    await ground_truth_client.close()

            has_unverified = len(unverified) > 0
            confidence = (
                len(validated) / len(extracted_claims)
                if extracted_claims
                else 0.5
            )

            agent_result.payload = {
                "validated_claims": validated,
                "unverified_claims": unverified,
                "claim_count": len(extracted_claims),
                "validated_count": len(validated),
                "unverified_count": len(unverified),
            }
            # Force human review if any claims are unverified — business case
            # must not publish unvalidated claims (harness.runtime.yaml: on_l5_unavailable: block)
            agent_result.mark_llm_enriched(
                model=llm_result.model,
                prompt_tokens=llm_result.prompt_tokens,
                completion_tokens=llm_result.completion_tokens,
                confidence=confidence,
            )
            if has_unverified:
                agent_result.human_review_required = True
                agent_result.customer_facing_allowed = False
                agent_result.degraded_reason = f"unverified_claims:{len(unverified)}"

            logger.info(
                "Business case claim validation: %d validated, %d unverified",
                len(validated), len(unverified),
            )

        except MissingTenantContextError as exc:
            logger.warning("Business case claim validation: missing tenant context: %s", exc)
            agent_result.payload = {
                "validated_claims": [],
                "unverified_claims": [],
                "claim_count": 0,
            }
            agent_result.degraded_reason = "missing_tenant_context"
            agent_result.human_review_required = True
            agent_result.customer_facing_allowed = False

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Business case claim validation failed", extra={"code": "llm_failed"})
            agent_result.payload = {
                "validated_claims": [],
                "unverified_claims": [],
                "claim_count": 0,
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

    def _resolve_organization_id(self, state: BusinessCaseAgentState) -> str:
        """Resolve tenant/organization ID from authenticated workflow state.

        Only the authenticated tenant claim set by the workflow runtime is
        trusted. The raw ``state.tenant_id`` must not be used as a fallback
        because request body or metadata values can be forged.
        """
        organization_id = state.metadata.get("authenticated_tenant_id") if state.metadata else None

        if organization_id:
            return str(organization_id)

        raise MissingTenantContextError(
            "Missing authenticated tenant context for business case workflow execution."
        )

    async def _sync_ground_truths_to_kg(self, state: BusinessCaseAgentState) -> dict[str, Any]:
        """Best-effort sync of validated TruthObjects to the KG via Layer 5.

        Resolves tenant/organization ID exclusively from authenticated
        workflow state metadata set during workflow initialization.

        Returns a dict with sync statistics or an ``error`` key.
        """
        organization_id = self._resolve_organization_id(state)

        client = self._get_ground_truth_client(organization_id)
        if client is None:
            return BusinessCaseGeneratorWorkflow__sync_ground_truths_to_kgResult.model_validate({
                "error": "Ground-truth sync unavailable",
                "error_code": "GROUND_TRUTH_SYNC_UNAVAILABLE",
                "synced": 0,
                "failed": 0,
            })

        try:
            sync_result = await client.sync_validated_truths(organization_id=organization_id)
            logger.info(
                "Business case ground-truth sync complete for org=%s: %s",
                organization_id,
                sync_result,
            )
            return BusinessCaseGeneratorWorkflow__sync_ground_truths_to_kgResult.model_validate({
                "synced": sync_result.get("synced", 0) if isinstance(sync_result, dict) else 0,
                "failed": sync_result.get("failed", 0) if isinstance(sync_result, dict) else 0,
                "error": sync_result.get("error", "") if isinstance(sync_result, dict) else "",
            })
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "Ground-truth sync failed (non-blocking) for org=%s: %s",
                organization_id,
                exc,
            )
            return BusinessCaseGeneratorWorkflow__sync_ground_truths_to_kgResult.model_validate({"error": "Ground-truth sync failed", "error_code": "GROUND_TRUTH_SYNC_ERROR", "synced": 0, "failed": 0})
        finally:
            await client.close()
