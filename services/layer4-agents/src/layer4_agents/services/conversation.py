from __future__ import annotations

"""ConversationService — ValuePilot backend orchestration.

Bridges the ConversationAgent (GATE-governed intent classification and
context gathering) with the Thesys C1 proxy (LLM response generation)
and the OrchestrationController (spine workflow delegation).

Architecture:
    Frontend (RightRail)
        → POST /agent-stream/chat
            → ConversationService.handle_message()
                1. ConversationAgent.classify_intent()   [GATE-governed]
                2. ConversationAgent.gather_context()     [GATE-governed]
                3. Route by intent:
                   a. Workflow intents → OrchestrationController.schedule_workflow()
                   b. All intents → C1 proxy for LLM generation (with enriched context)
                4. Emit audit event + return response
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from value_fabric.shared.audit import AuditAction, AuditOutcome
from value_fabric.shared.audit.emitter import emit_audit_event
from value_fabric.shared.models.typed_dict import TypedDictModel

try:
    from .degradation_evaluator import DegradationEvaluator
    from .thesys_provider import ThesysProvider
except (ImportError, ValueError):
    try:
        from layer4_agents.services.degradation_evaluator import (
            DegradationEvaluator,  # type: ignore[no-redef]
        )
        from layer4_agents.services.thesys_provider import (
            ThesysProvider,  # type: ignore[no-redef]
        )
    except (ImportError, ValueError):
        DegradationEvaluator = None  # type: ignore[assignment,misc]
        ThesysProvider = None  # type: ignore[assignment,misc]


class ConversationService_handle_messageResult(TypedDictModel):
    content: Any
    metadata: dict[str, Any]

class ConversationService__gather_contextResult(TypedDictModel):
    entities: Any
    entity_context: Any = None
    intent: Any

class ConversationService__heuristic_classifyResult(TypedDictModel):
    confidence: float
    entities: dict[str, Any]
    intent: str

class ConversationService__guardrailResult(TypedDictModel):
    reason: str
    message: str

logger = logging.getLogger(__name__)


class ConversationTenantValidationError(ValueError):
    """Raised when a required tenant identifier is missing or blank."""

# Semantic-contract validators are provided by packages/platform-contract.
# Layer 4 services can run in isolation during local development, so the
# import is intentionally best-effort and remains warning-only unless
# AGENT_SEMANTIC_CONTRACT_MODE=strict is configured.
_PLATFORM_CONTRACT_PYTHON = next(
    (parent / "packages" / "platform-contract" / "src" / "python" for parent in Path(__file__).resolve().parents if (parent / "packages" / "platform-contract" / "src" / "python").exists()),
    None,
)
if _PLATFORM_CONTRACT_PYTHON and str(_PLATFORM_CONTRACT_PYTHON) not in sys.path:
    sys.path.append(str(_PLATFORM_CONTRACT_PYTHON))

try:  # pragma: no cover - exercised by contract tests with PYTHONPATH configured
    from agent_contracts import build_agent_output_envelope, validate_agent_output
except asyncio.CancelledError:
    raise
except Exception:  # pragma: no cover - service remains available if package import is unavailable
    build_agent_output_envelope = None  # type: ignore[assignment]
    validate_agent_output = None  # type: ignore[assignment]

SEMANTIC_CONTRACT_VERSION = "2.0.0"

# Stable namespace for deterministic journey_id derivation.
# A journey represents the end-to-end progression of a single account through
# the ValuePilot workspaces (Intelligence → Value Studio → Narrative). Linking
# every audit event and spine artifact to a journey_id makes the full timeline
# reconstructable for traceability and replay.
JOURNEY_NAMESPACE = uuid.UUID("c4b1f7a2-9d3e-4a6b-8c2f-1e5a4d7b9c30")


def _resolve_journey_id(
    *,
    tenant_id: str,
    account_id: str | None,
    journey_id: str | None,
) -> str:
    """Resolve a stable journey_id scoped to (tenant_id, account_id).

    Precedence:
      1. Explicit journey_id passed by the caller (frontend/session).
      2. Deterministic uuid5 from (tenant_id, account_id) when an account is
         selected — stable across turns, tabs, and sessions for that account.
      3. Deterministic uuid5 from (tenant_id, "no-account") when no account is
         selected, so unscoped turns still carry a non-null journey link.

    The journey_id is always tenant-scoped: different tenants with the same
    account_id derive different journey_ids, preserving tenant isolation.
    """
    if journey_id and journey_id.strip():
        return journey_id.strip()
    account_key = account_id.strip() if isinstance(account_id, str) and account_id.strip() else "no-account"
    return str(uuid.uuid5(JOURNEY_NAMESPACE, f"{tenant_id}:{account_key}"))


# Tab-specific system prompts that provide workspace context to the LLM
TAB_SYSTEM_PROMPTS: dict[str, str] = {
    "signals": (
        "You are ValuePilot, an AI co-pilot in the Intelligence → Signals workspace. "
        "Help sales engineers analyze AI-surfaced pain signals for a prospect account. "
        "Summarize signals, compare them, explain confidence scores, suggest priorities, "
        "and recommend next steps. Keep responses concise (2-3 sentences) and actionable."
    ),
    "drivers": (
        "You are ValuePilot, an AI co-pilot in the Intelligence → Drivers workspace. "
        "Help sales engineers understand root cause analysis connecting pain signals "
        "to underlying business drivers. Explain hierarchies, suggest missing drivers, "
        "and map drivers to product capabilities. Keep responses concise and actionable."
    ),
    "evidence": (
        "You are ValuePilot, an AI co-pilot in the Intelligence → Evidence workspace. "
        "Help sales engineers validate claims with source documents, benchmarks, and "
        "case studies. Explain match scores, suggest sources, flag weak claims. "
        "Keep responses concise and actionable."
    ),
    "stakeholders": (
        "You are ValuePilot, an AI co-pilot in the Intelligence → Stakeholders workspace. "
        "Help sales engineers map buyer personas and stakeholder priorities. "
        "Suggest messaging angles, identify missing stakeholders, recommend engagement "
        "strategies. Keep responses concise and actionable."
    ),
    "action-plan": (
        "You are ValuePilot, an AI co-pilot in the Value Studio → Action Plan workspace. "
        "Help sales engineers build product-anchored recommendations mapping validated "
        "pain to product capabilities. Refine recommendations, adjust priorities, "
        "strengthen the 'why us' argument. Keep responses concise and actionable."
    ),
    "value-model": (
        "You are ValuePilot, an AI co-pilot in the Value Studio → Value Model workspace. "
        "Help sales engineers build and refine quantified business cases. Explain "
        "financial projections, adjust assumptions, compare scenarios, validate "
        "calculations. Keep responses concise and actionable."
    ),
    "narrative": (
        "You are ValuePilot, an AI co-pilot in the Value Studio → Narrative workspace. "
        "Help sales engineers package the value case for stakeholder presentations. "
        "Refine messaging, adjust tone for audiences, suggest narrative structures. "
        "Keep responses concise and actionable."
    ),
    "competitive": (
        "You are ValuePilot, an AI co-pilot in the Intelligence → Competitive workspace. "
        "Help sales engineers analyze competitive positioning, build battlecards, "
        "and identify differentiation opportunities. Keep responses concise and actionable."
    ),
    "enrichment": (
        "You are ValuePilot, an AI co-pilot in the Intelligence → Enrichment workspace. "
        "Help sales engineers review and validate enriched account data, identify gaps, "
        "and trigger re-enrichment. Keep responses concise and actionable."
    ),
    "hypotheses": (
        "You are ValuePilot, an AI co-pilot in the Intelligence → Hypotheses workspace. "
        "Help sales engineers evaluate and refine value hypotheses, test assumptions, "
        "and prioritize the strongest value angles. Keep responses concise and actionable."
    ),
    "roi": (
        "You are ValuePilot, an AI co-pilot in the Intelligence → ROI workspace. "
        "Help sales engineers build ROI models, validate assumptions, run sensitivity "
        "analysis, and compare scenarios. Keep responses concise and actionable."
    ),
}

# Intents that should trigger spine workflow delegation
WORKFLOW_INTENTS: dict[str, str] = {
    "value_analysis": "full_value_spine",
    "document_export": "narrative_export",
    "competitive_intel": "competitive_analysis",
}

# Intents that map directly to agent tools
MUTATION_INTENTS: dict[str, str] = {
    "promote_signal": "promote_signal",
    "validate_hypothesis": "validate_hypothesis",
}


class ConversationService:
    """Orchestrates the ValuePilot conversation pipeline.

    This service is stateless per-request — all state lives in the
    frontend message history and the GATE audit trail.
    """

    def __init__(
        self,
        conversation_agent: Any | None = None,
        orchestration_controller: Any | None = None,
        c1_enabled: bool = False,
        context_gatherer: Any | None = None,
        intent_classifier: Any | None = None,
        tool_registry: Any | None = None,
        retrieval_engine: Any | None = None,
        degradation_evaluator: DegradationEvaluator | None = None,
    ) -> None:
        self.conversation_agent = conversation_agent
        self.orchestration_controller = orchestration_controller
        self.c1_enabled = c1_enabled
        self.context_gatherer = context_gatherer
        self.intent_classifier = intent_classifier
        self.tool_registry = tool_registry
        self.retrieval_engine = retrieval_engine
        self.degradation_evaluator = (
            degradation_evaluator
            if degradation_evaluator is not None
            else DegradationEvaluator.from_task("conversation")
        )

    def _semantic_contract_mode(self) -> str:
        """Resolve semantic-contract mode for Phase 2 rollout."""

        mode = os.getenv("AGENT_SEMANTIC_CONTRACT_MODE", "warn").strip().lower()
        return "strict" if mode == "strict" else "warn"

    def _semantic_agent_metadata(
        self,
        *,
        agent_type: str,
        output: Any,
        tenant_id: str,
        trace_id: str,
        workflow_id: str | None,
        audit_event_id: str | None,
        active_tab: str,
        intent: str,
        confidence: float | None,
        source_node: str = "conversation.generate",
    ) -> dict[str, Any]:
        """Build and validate the semantic metadata envelope for AG-UI events."""

        contract_versions = {
            "semantic_contract": SEMANTIC_CONTRACT_VERSION,
            "agent_registry": "1.0.0",
            "prompt": "1.0.0",
            "workflow": "1.0.0",
        }
        if build_agent_output_envelope is None or validate_agent_output is None:
            return {
                "semanticContractVersion": SEMANTIC_CONTRACT_VERSION,
                "semanticContractValid": False,
                "semanticContractMode": self._semantic_contract_mode(),
                "semanticContractViolations": [
                    {
                        "code": "semantic_contract_validator_unavailable",
                        "message": "agent_contracts package is unavailable in this runtime",
                        "severity": "warning",
                        "path": "$",
                    }
                ],
                "contractVersions": {
                    "semanticContract": SEMANTIC_CONTRACT_VERSION,
                    "agentRegistry": "1.0.0",
                    "prompt": "1.0.0",
                    "workflow": "1.0.0",
                },
            }

        envelope = build_agent_output_envelope(
            agent_type=agent_type,
            output=output,
            tenant_id=tenant_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            audit_event_id=audit_event_id,
            source_node=source_node,
            prompt_id="conversation-system-prompts",
            prompt_version="1.0.0",
            reasoning_policy_id=f"valuepilot-{active_tab}",
            confidence=confidence,
            explainability={"intent": intent, "active_tab": active_tab},
            contract_versions=contract_versions,
        )
        validation = validate_agent_output(envelope, mode=self._semantic_contract_mode())
        normalized = validation.normalized or envelope
        provenance = normalized.get("provenance", {}) if isinstance(normalized, dict) else {}

        return {
            "semanticContractVersion": SEMANTIC_CONTRACT_VERSION,
            "semanticContractValid": validation.valid,
            "semanticContractMode": validation.mode.value if hasattr(validation.mode, "value") else str(validation.mode),
            "semanticContractViolations": [
                violation.model_dump() if hasattr(violation, "model_dump") else violation
                for violation in validation.violations
            ],
            "contractVersions": {
                "semanticContract": SEMANTIC_CONTRACT_VERSION,
                "agentRegistry": "1.0.0",
                "prompt": "1.0.0",
                "workflow": "1.0.0",
            },
            "provenance": {
                "tenantId": provenance.get("tenant_id") or provenance.get("tenantId") or tenant_id,
                "traceId": provenance.get("trace_id") or provenance.get("traceId") or trace_id,
                "workflowId": provenance.get("workflow_id") or provenance.get("workflowId") or workflow_id,
                "auditEventId": provenance.get("audit_event_id") or provenance.get("auditEventId") or audit_event_id,
                "sourceNode": provenance.get("source_node") or provenance.get("sourceNode") or source_node,
                "sourceLayer": provenance.get("source_layer") or provenance.get("sourceLayer") or "layer4-agents",
            },
        }

    # Expected steps for streaming mode
    STREAMING_STEPS = [
        {"id": "guardrails", "label": "Checking safety guardrails"},
        {"id": "classify", "label": "Classifying intent"},
        {"id": "gather", "label": "Gathering account context"},
        {"id": "generate", "label": "Generating response"},
    ]

    async def handle_message_streaming(
        self,
        *,
        user_message: str,
        messages: list[dict[str, str]],
        active_tab: str,
        account_id: str | None = None,
        account_name: str = "this account",
        account_tier: str | None = None,
        entity_context: dict[str, Any] | None = None,
        tenant_id: str,
        trace_id: str | None = None,
        journey_id: str | None = None,
    ):
        """Async generator that yields AG-UI events as the pipeline progresses.

        Yields dicts shaped like AG-UI events:
          {type: "RUN_STARTED", ...}
          {type: "STEP_STARTED", ...}
          {type: "STEP_FINISHED", ...}
          {type: "TEXT_MESSAGE_START", ...}
          {type: "TEXT_MESSAGE_CONTENT", ...}
          {type: "TEXT_MESSAGE_END", ...}
          {type: "RUN_FINISHED", ...}
          {type: "RUN_ERROR", ...}
        """
        tenant_id = self._require_tenant_id(tenant_id)
        trace_id = trace_id or str(uuid.uuid4())
        journey_id = _resolve_journey_id(
            tenant_id=tenant_id, account_id=account_id, journey_id=journey_id
        )
        workflow_id = str(uuid.uuid4())
        audit_event_id = f"audit_{uuid.uuid4().hex[:12]}"
        run_id = f"run-{trace_id[:8]}"
        def now() -> str:
            return datetime.now(UTC).isoformat()

        # ── RUN_STARTED ──
        yield {
            "type": "RUN_STARTED",
            "timestamp": now(),
            "runId": run_id,
            "description": f"Processing request for {account_name}",
            "expectedSteps": self.STREAMING_STEPS,
            "metadata": {
                "journeyId": journey_id,
                **self._semantic_agent_metadata(
                    agent_type="ConversationAgent",
                    output={"status": "started"},
                    tenant_id=tenant_id,
                    trace_id=trace_id,
                    workflow_id=workflow_id,
                    audit_event_id=None,
                    active_tab=active_tab,
                    intent="pending",
                    confidence=None,
                    source_node="conversation.start",
                ),
            },
        }

        try:
            # ── Guardrails ──
            yield {"type": "STEP_STARTED", "timestamp": now(), "runId": run_id, "stepId": "guardrails", "label": "Checking safety guardrails"}
            guardrail = self._detect_guardrail_violation(user_message, messages)
            yield {"type": "STEP_FINISHED", "timestamp": now(), "runId": run_id, "stepId": "guardrails", "status": "done" if not guardrail else "error"}

            if guardrail:
                yield {"type": "TEXT_MESSAGE_START", "timestamp": now(), "runId": run_id, "messageId": "msg-1", "role": "agent"}
                yield {"type": "TEXT_MESSAGE_CONTENT", "timestamp": now(), "runId": run_id, "messageId": "msg-1", "delta": guardrail["message"]}
                yield {"type": "TEXT_MESSAGE_END", "timestamp": now(), "runId": run_id, "messageId": "msg-1"}
                yield {
                    "type": "RUN_FINISHED",
                    "timestamp": now(),
                    "runId": run_id,
                    "metadata": {
                            "traceId": trace_id,
                            "workflowId": workflow_id,
                            "tenantId": tenant_id,
                            "journeyId": journey_id,
                            "intent": "refusal",
                            "confidence": 1.0,
                            **self._semantic_agent_metadata(
                                agent_type="ConversationAgent",
                                output={"content": guardrail["message"], "intent": "refusal"},
                                tenant_id=tenant_id,
                                trace_id=trace_id,
                                workflow_id=workflow_id,
                                audit_event_id=None,
                                active_tab=active_tab,
                                intent="refusal",
                                confidence=1.0,
                                source_node="conversation.guardrail",
                            ),
                        },
                }
                return

            # ── Classify ──
            yield {"type": "STEP_STARTED", "timestamp": now(), "runId": run_id, "stepId": "classify", "label": "Classifying intent"}
            gate_context = self._build_gate_context(
                tenant_id=tenant_id,
                trace_id=trace_id,
                workflow_id=workflow_id,
                audit_event_id=audit_event_id,
                journey_id=journey_id,
            )
            intent_result = await self._classify_intent(user_message, gate_context)
            intent = intent_result.get("intent", "general_question")
            confidence = intent_result.get("confidence", 0.0)
            entities = intent_result.get("entities", {})
            yield {"type": "STEP_FINISHED", "timestamp": now(), "runId": run_id, "stepId": "classify", "status": "done"}

            # ── Gather ──
            yield {"type": "STEP_STARTED", "timestamp": now(), "runId": run_id, "stepId": "gather", "label": "Gathering account context"}
            context_data = await self._gather_context(
                intent=intent,
                entities=entities,
                account_id=account_id,
                entity_context=entity_context or {},
                gate_context=gate_context,
                tenant_id=tenant_id,
            )
            yield {"type": "STEP_FINISHED", "timestamp": now(), "runId": run_id, "stepId": "gather", "status": "done"}

            # ── Generate ──
            yield {"type": "STEP_STARTED", "timestamp": now(), "runId": run_id, "stepId": "generate", "label": "Generating response"}
            generation_metadata: dict[str, object] = {}
            response_content = await self._generate_response(
                user_message=user_message,
                messages=messages,
                active_tab=active_tab,
                intent=intent,
                context_data=context_data,
                workflow_result=None,
                account_name=account_name,
                gate_context=gate_context,
                tenant_id=tenant_id,
                entities=entities,
                generation_metadata=generation_metadata,
            )
            yield {"type": "STEP_FINISHED", "timestamp": now(), "runId": run_id, "stepId": "generate", "status": "done"}

            # ── Text message ──
            message_id = f"msg-{trace_id[:8]}"
            yield {"type": "TEXT_MESSAGE_START", "timestamp": now(), "runId": run_id, "messageId": message_id, "role": "agent"}
            yield {"type": "TEXT_MESSAGE_CONTENT", "timestamp": now(), "runId": run_id, "messageId": message_id, "delta": response_content}
            yield {"type": "TEXT_MESSAGE_END", "timestamp": now(), "runId": run_id, "messageId": message_id}

            # ── RUN_FINISHED ──
            yield {
                "type": "RUN_FINISHED",
                "timestamp": now(),
                "runId": run_id,
                "metadata": {
                    "traceId": trace_id,
                    "workflowId": workflow_id,
                    "tenantId": tenant_id,
                    "journeyId": journey_id,
                    "intent": intent,
                    "confidence": confidence,
                    **generation_metadata,
                    **self._semantic_agent_metadata(
                        agent_type="ConversationAgent",
                        output={"content": response_content, "intent": intent},
                        tenant_id=tenant_id,
                        trace_id=trace_id,
                        workflow_id=workflow_id,
                        audit_event_id=None,
                        active_tab=active_tab,
                        intent=intent,
                        confidence=confidence,
                    ),
                },
            }

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Streaming pipeline error: %s", e, exc_info=True)
            yield {"type": "RUN_ERROR", "timestamp": now(), "runId": run_id, "message": "STREAMING_ERROR", "retryable": True}

    async def handle_message(
        self,
        *,
        user_message: str,
        messages: list[dict[str, str]],
        active_tab: str,
        account_id: str | None = None,
        account_name: str = "this account",
        account_tier: str | None = None,
        entity_context: dict[str, Any] | None = None,
        tenant_id: str,
        trace_id: str | None = None,
        journey_id: str | None = None,
    ) -> dict[str, Any]:
        """Process a user message through the full ValuePilot pipeline.

        Returns:
            Dict with 'content' and 'metadata' matching the AgentStreamResponse contract.
        """
        tenant_id = self._require_tenant_id(tenant_id)
        trace_id = trace_id or str(uuid.uuid4())
        journey_id = _resolve_journey_id(
            tenant_id=tenant_id, account_id=account_id, journey_id=journey_id
        )
        workflow_id = str(uuid.uuid4())
        audit_event_id = f"audit_{uuid.uuid4().hex[:12]}"

        guardrail = self._detect_guardrail_violation(user_message, messages)
        if guardrail:
            await self._emit_security_audit(
                trace_id=trace_id,
                workflow_id=workflow_id,
                audit_event_id=audit_event_id,
                tenant_id=tenant_id,
                active_tab=active_tab,
                account_id=account_id,
                reason=guardrail["reason"],
                journey_id=journey_id,
            )
            return ConversationService_handle_messageResult.model_validate({
                "content": guardrail["message"],
                "metadata": {
                    "trace_id": trace_id,
                    "workflow_id": workflow_id,
                    "tenant_id": tenant_id,
                    "journey_id": journey_id,
                    "tool_name": "valuepilot_conversation",
                    "audit_event_id": audit_event_id,
                    "emitted_at": datetime.now(UTC).isoformat(),
                    "intent": "refusal",
                    "confidence": 1.0,
                    "workflow_triggered": False,
                    "refusal_reason": guardrail["reason"],
                    **self._semantic_agent_metadata(
                        agent_type="ConversationAgent",
                        output={"content": guardrail["message"], "intent": "refusal"},
                        tenant_id=tenant_id,
                        trace_id=trace_id,
                        workflow_id=workflow_id,
                        audit_event_id=audit_event_id,
                        active_tab=active_tab,
                        intent="refusal",
                        confidence=1.0,
                        source_node="conversation.guardrail",
                    ),
                },
            })

        # Build the GATE execution context
        gate_context = self._build_gate_context(
            tenant_id=tenant_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            audit_event_id=audit_event_id,
            journey_id=journey_id,
        )

        # Step 1: Classify intent (GATE-governed)
        intent_result = await self._classify_intent(
            user_message, gate_context
        )
        intent = intent_result.get("intent", "general_question")
        confidence = intent_result.get("confidence", 0.0)
        entities = intent_result.get("entities", {})

        logger.info(
            "Intent classified: %s (confidence=%.2f) for tab=%s",
            intent, confidence, active_tab,
        )

        # Step 2: Gather context (GATE-governed)
        context_data = await self._gather_context(
            intent=intent,
            entities=entities,
            account_id=account_id,
            entity_context=entity_context or {},
            gate_context=gate_context,
            tenant_id=tenant_id,
        )

        # Step 3: Check if this intent should trigger a workflow
        workflow_result = None
        if intent in WORKFLOW_INTENTS and confidence >= 0.7:
            workflow_result = await self._delegate_to_orchestrator(
                intent=intent,
                entities=entities,
                account_id=account_id,
                gate_context=gate_context,
            )

        # Step 4: Generate response
        generation_metadata: dict[str, object] = {}
        response_content = await self._generate_response(
            user_message=user_message,
            messages=messages,
            active_tab=active_tab,
            intent=intent,
            context_data=context_data,
            workflow_result=workflow_result,
            account_name=account_name,
            gate_context=gate_context,
            tenant_id=tenant_id,
            entities=entities,
            generation_metadata=generation_metadata,
        )

        # Step 5: Emit audit event
        await self._emit_audit(
            trace_id=trace_id,
            workflow_id=workflow_id,
            audit_event_id=audit_event_id,
            tenant_id=tenant_id,
            intent=intent,
            confidence=confidence,
            active_tab=active_tab,
            account_id=account_id,
            has_workflow=workflow_result is not None,
            journey_id=journey_id,
        )

        return ConversationService_handle_messageResult.model_validate({
            "content": response_content,
            "metadata": {
                "trace_id": trace_id,
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
                "journey_id": journey_id,
                "tool_name": "valuepilot_conversation",
                "audit_event_id": audit_event_id,
                "emitted_at": datetime.now(UTC).isoformat(),
                "intent": intent,
                "confidence": confidence,
                "workflow_triggered": workflow_result is not None,
                "entity_context": entity_context or {},
                **generation_metadata,
                **self._semantic_agent_metadata(
                    agent_type="ConversationAgent",
                    output={"content": response_content, "intent": intent},
                    tenant_id=tenant_id,
                    trace_id=trace_id,
                    workflow_id=workflow_id,
                    audit_event_id=audit_event_id,
                    active_tab=active_tab,
                    intent=intent,
                    confidence=confidence,
                ),
            },
        })


    def _build_gate_context(
        self,
        tenant_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
        audit_event_id: str | None = None,
        journey_id: str | None = None,
    ) -> dict[str, Any]:
        """Build the GATE execution context for ConversationAgent."""
        ctx: dict[str, Any] = {}

        if self.tool_registry:
            ctx["tool_registry"] = self.tool_registry

        if self.retrieval_engine:
            ctx["retrieval_engine"] = self.retrieval_engine

        if tenant_id:
            ctx["tenant_id"] = tenant_id
        if trace_id:
            ctx["trace_id"] = trace_id
        if workflow_id:
            ctx["workflow_id"] = workflow_id
        if audit_event_id:
            ctx["audit_event_id"] = audit_event_id
        if journey_id:
            ctx["journey_id"] = journey_id

        return ctx

    async def _classify_intent(
        self,
        message: str,
        gate_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify user intent using ConversationAgent, LLM, or fallback heuristics."""
        # Strategy 1: GATE ConversationAgent
        if self.conversation_agent:
            try:
                return await self.conversation_agent.execute(
                    {"capability": "classify_intent", "parameters": {"message": message}},
                    gate_context,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("ConversationAgent intent classification failed, trying LLM")

        # Strategy 2: LLM-based classifier
        if self.intent_classifier:
            try:
                return await self.intent_classifier.classify(message)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("LLM intent classification failed, using heuristic")

        # Strategy 3: Heuristic fallback
        return self._heuristic_classify(message)

    async def _gather_context(
        self,
        *,
        intent: str,
        entities: dict[str, Any],
        account_id: str | None,
        entity_context: dict[str, Any],
        gate_context: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """Gather relevant context using ConversationAgent, ContextGatheringService, or minimal fallback."""
        tenant_id = self._require_tenant_id(tenant_id)
        # Strategy 1: GATE ConversationAgent
        if self.conversation_agent and account_id:
            try:
                result = await self.conversation_agent.execute(
                    {
                        "capability": "gather_context",
                        "parameters": {
                            "intent": intent,
                            "entities": entities,
                            "account_id": account_id,
                            "entity_context": entity_context,
                        },
                    },
                    gate_context,
                )
                context_data = result.get("context_data", {})
                if isinstance(context_data, dict):
                    context_data.setdefault("entity_context", entity_context)
                return context_data
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("ConversationAgent context gathering failed")

        # Strategy 2: ContextGatheringService (real DB/Neo4j queries)
        if self.context_gatherer and account_id:
            try:
                context_data = await self.context_gatherer.gather(
                    account_id=account_id,
                    tenant_id=tenant_id,
                    industry=entity_context.get("industry") if isinstance(entity_context, dict) else None,
                )
                context_data["intent"] = intent
                context_data["entities"] = entities
                context_data.setdefault("entity_context", entity_context)
                return context_data
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("ContextGatheringService failed, falling back to minimal")

        # Strategy 3: Minimal fallback
        return ConversationService__gather_contextResult.model_validate({
            "intent": intent,
            "entities": entities,
            "entity_context": entity_context,
        })

    async def _delegate_to_orchestrator(
        self,
        *,
        intent: str,
        entities: dict[str, Any],
        account_id: str | None,
        gate_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Delegate workflow-triggering intents to OrchestrationController."""
        if not self.orchestration_controller:
            logger.info("No OrchestrationController available — skipping workflow delegation")
            return None

        workflow_type = WORKFLOW_INTENTS.get(intent)
        if not workflow_type:
            return None

        try:
            result = await self.orchestration_controller.execute(
                {
                    "capability": "schedule_workflow",
                    "parameters": {
                        "workflow_type": workflow_type,
                        "inputs": {
                            "account_id": account_id,
                            "entities": entities,
                            "triggered_by": "valuepilot_conversation",
                        },
                        "priority": "high",
                    },
                },
                gate_context,
            )
            logger.info(
                "Workflow %s scheduled: %s",
                workflow_type, result.get("schedule_id"),
            )
            return result
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Workflow delegation failed for intent=%s", intent)
            return None

    async def _execute_mutation_tool(
        self,
        *,
        intent: str,
        entities: dict[str, Any],
        context_data: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Execute a mutation tool if intent matches and registry is available."""
        tenant_id = self._require_tenant_id(tenant_id)
        if not self.tool_registry:
            return None

        tool_name = MUTATION_INTENTS.get(intent)
        if not tool_name:
            return None

        account_id = context_data.get("account", {}).get("id") or entities.get("account_id")

        try:
            if tool_name == "promote_signal":
                signal_id = entities.get("signal_id")
                if not signal_id or not account_id:
                    return {"success": False, "error": "Missing signal_id or account_id"}
                return await self.tool_registry.promote_signal(
                    tenant_id=tenant_id,
                    account_id=str(account_id),
                    signal_id=str(signal_id),
                    value_path_category=entities.get("value_path_category"),
                )

            if tool_name == "validate_hypothesis":
                hypothesis_id = entities.get("hypothesis_id")
                new_status = entities.get("new_status")
                if not hypothesis_id or not new_status:
                    return {"success": False, "error": "Missing hypothesis_id or new_status"}
                return await self.tool_registry.validate_hypothesis(
                    tenant_id=tenant_id,
                    hypothesis_id=str(hypothesis_id),
                    new_status=str(new_status),
                    feedback=entities.get("feedback", ""),
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Mutation tool %s failed: %s", tool_name, e)
            return {"success": False, "error": "MUTATION_TOOL_ERROR"}

        return None

    async def _generate_response(
        self,
        *,
        user_message: str,
        messages: list[dict[str, str]],
        active_tab: str,
        intent: str,
        context_data: dict[str, Any],
        workflow_result: dict[str, Any] | None,
        account_name: str,
        gate_context: dict[str, Any],
        tenant_id: str,
        entities: dict[str, object] | None = None,
        generation_metadata: dict[str, object] | None = None,
    ) -> str:
        """Generate the response content.

        Priority:
        1. Execute mutation tool if intent matches
        2. ConversationAgent.execute(chat) if agent + tool_gateway available
        3. C1 proxy with enriched system prompt if C1 enabled
        4. Context-aware heuristic response (no LLM)
        """
        tenant_id = self._require_tenant_id(tenant_id)
        generation_metadata = generation_metadata if generation_metadata is not None else {}
        failed_tiers: list[str] = []

        tracker = self.degradation_evaluator.create_tracker(
            tenant_id=tenant_id,
            trace_id=str(gate_context.get("trace_id")) if gate_context.get("trace_id") else None,
            workflow_id=str(gate_context.get("workflow_id")) if gate_context.get("workflow_id") else None,
        )

        def mark_result(*, tier: str, provider: str | None = None) -> None:
            tracker.record_success(tier=tier, provider=provider)
            generation_metadata.update(tracker.build_generation_metadata())
            failed_tiers.extend(tracker.failed_tiers)

        # Strategy 0: Mutation tool execution
        tool_result = None
        if intent in MUTATION_INTENTS:
            tool_result = await self._execute_mutation_tool(
                intent=intent,
                entities=entities or {},
                context_data=context_data,
                tenant_id=tenant_id,
            )
            if tool_result:
                mark_result(tier="tool")
                context_data = {**context_data, "tool_result": tool_result}
                if tool_result.get("success"):
                    return self._append_workflow_notice(
                        f"✅ {tool_result.get('message', 'Action completed successfully.')}",
                        workflow_result,
                    )
                else:
                    return self._append_workflow_notice(
                        f"❌ I couldn't complete that action: {tool_result.get('error', 'Unknown error')}",
                        workflow_result,
                    )

        # Strategy 1: Full agent pipeline (uses generate_section tool via GATE)
        if self.conversation_agent and gate_context.get("tool_gateway"):
            try:
                result = await self.conversation_agent.execute(
                    {
                        "capability": "chat",
                        "parameters": {
                            "message": user_message,
                            "session_id": str(uuid.uuid4()),
                            "account_id": context_data.get("account", {}).get("entity_id"),
                        },
                    },
                    gate_context,
                )
                content = result.get("response", "")
                if content:
                    mark_result(tier="conversation_agent")
                    return self._append_workflow_notice(content, workflow_result)
                tracker.record_failure(
                    rung_kind="retry",
                    tier="conversation_agent",
                    reason="conversation_agent_empty",
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                tracker.record_failure(
                    rung_kind="retry",
                    tier="conversation_agent",
                    reason="conversation_agent_failed",
                )
                logger.warning("Full agent pipeline failed, falling back")

        # Strategy 2: C1 proxy with enriched context
        if self.c1_enabled:
            try:
                content = await self._generate_via_c1(
                    user_message=user_message,
                    messages=messages,
                    active_tab=active_tab,
                    context_data=context_data,
                    account_name=account_name,
                    tenant_id=tenant_id,
                )
                if content:
                    mark_result(tier="thesys_c1", provider="thesys")
                    if tracker.is_degraded:
                        await self._emit_degradation_audit(
                            gate_context=gate_context,
                            tenant_id=tenant_id,
                            selected_tier="thesys_c1",
                            reason=str(generation_metadata.get("degradation_reason")),
                        )
                    return self._append_workflow_notice(content, workflow_result)
                tracker.record_failure(
                    rung_kind="failover",
                    tier="thesys_c1",
                    reason="thesys_c1_unavailable",
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                tracker.record_failure(
                    rung_kind="failover",
                    tier="thesys_c1",
                    reason="thesys_c1_failed",
                )
                logger.warning("C1 generation failed, falling back to heuristic")

        # Strategy 3: Context-aware heuristic (always works)
        content = self._heuristic_response(
            user_message=user_message,
            active_tab=active_tab,
            intent=intent,
            context_data=context_data,
            account_name=account_name,
        )
        if not tracker.failed_tiers:
            tracker.record_failure(
                rung_kind="failover",
                tier="llm_tiers",
                reason="llm_tiers_unavailable",
            )
        mark_result(tier="heuristic")
        await self._emit_degradation_audit(
            gate_context=gate_context,
            tenant_id=tenant_id,
            selected_tier="heuristic",
            reason=str(generation_metadata.get("degradation_reason")),
        )
        return self._append_workflow_notice(content, workflow_result)

    async def _emit_degradation_audit(
        self,
        *,
        gate_context: dict[str, object],
        tenant_id: str,
        selected_tier: str,
        reason: str,
        tracker: Any | None = None,
    ) -> None:
        """Emit the first-class audit event required for an allowed fallback."""
        try:
            if tracker is not None:
                details = tracker.build_audit_details(selected_tier=selected_tier, reason=reason)
            else:
                details = {
                    "event_type": "llm_degradation_applied",
                    "tenant_id": tenant_id,
                    "run_id": gate_context.get("workflow_id"),
                    "trace_id": gate_context.get("trace_id"),
                    "selected_tier": selected_tier,
                    "reason": reason,
                    "degraded": True,
                }
            await emit_audit_event(
                AuditAction.AGENT_EXECUTION,
                outcome=AuditOutcome.SUCCESS,
                resource_type="llm_degradation",
                resource_id="conversation-agent",
                details=details,
                chain_id=f"conversation:{tenant_id}",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Failed to emit LLM degradation audit event", exc_info=True)

    def _require_tenant_id(self, tenant_id: str) -> str:
        normalized = tenant_id.strip() if isinstance(tenant_id, str) else ""
        if not normalized:
            raise ConversationTenantValidationError("tenant_id is required and must not be blank")
        return normalized

    async def _generate_via_c1(
        self,
        *,
        user_message: str,
        messages: list[dict[str, str]],
        active_tab: str,
        context_data: dict[str, object],
        account_name: str,
        tenant_id: str = "unknown",
        user_id: str = "unknown",
    ) -> str:
        """Generate response via ThesysProvider.

        Enriches the system prompt with gathered context data so the LLM
        has account-specific information to work with.
        """
        provider = ThesysProvider()
        if not provider.is_available():
            logger.info("Thesys C1 integration is not configured")
            return ""

        # Build enriched system prompt
        base_prompt = TAB_SYSTEM_PROMPTS.get(
            active_tab,
            "You are ValuePilot, an AI co-pilot for value selling. "
            "Keep responses concise and actionable.",
        )

        context_section = ""
        if context_data:
            context_section = (
                f"\n\nCurrent account context for {account_name}:\n"
                f"{json.dumps(context_data, indent=2, default=str)[:2000]}"
            )

        enriched_prompt = base_prompt + context_section

        # Build message list with enriched system prompt
        c1_messages: list[dict[str, Any]] = [{"role": "system", "content": enriched_prompt}]
        # Include recent conversation history (last 10 messages)
        for msg in messages[-10:]:
            role = msg.get("role", "user")
            if role == "system":
                continue  # Skip — we already have our enriched system prompt
            c1_messages.append({"role": role, "content": msg.get("content", "")})

        metadata = {
            "business_case_id": f"valuepilot_{active_tab}",
            "account_name": account_name,
        }
        if user_id:
            metadata["user_id"] = user_id

        response = await provider.complete_text(
            messages=c1_messages,
            metadata=metadata,
            tenant_id=tenant_id,
        )
        return response.content

    def _heuristic_classify(self, message: str) -> ConversationService__heuristic_classifyResult:
        """Rule-based intent classification fallback."""
        lower = message.lower()

        if any(w in lower for w in ("roi", "return", "payback", "cost", "savings", "value model")):
            return ConversationService__heuristic_classifyResult.model_validate({"intent": "value_analysis", "confidence": 0.75, "entities": {}})
        if any(w in lower for w in ("competitor", "competitive", "versus", "vs", "battlecard")):
            return ConversationService__heuristic_classifyResult.model_validate({"intent": "competitive_intel", "confidence": 0.75, "entities": {}})
        if any(w in lower for w in ("export", "document", "pdf", "slide", "deck", "proposal")):
            return ConversationService__heuristic_classifyResult.model_validate({"intent": "document_export", "confidence": 0.75, "entities": {}})
        if any(w in lower for w in ("status", "workflow", "progress", "running")):
            return ConversationService__heuristic_classifyResult.model_validate({"intent": "workflow_status", "confidence": 0.70, "entities": {}})
        if any(w in lower for w in ("account", "company", "prospect", "customer", "who")):
            return ConversationService__heuristic_classifyResult.model_validate({"intent": "account_inquiry", "confidence": 0.65, "entities": {}})

        return ConversationService__heuristic_classifyResult.model_validate({"intent": "general_question", "confidence": 0.50, "entities": {}})

    def _detect_guardrail_violation(
        self,
        user_message: str,
        messages: list[dict[str, str]],
    ) -> dict[str, str] | None:
        """Deterministically refuse unsafe agent requests before tools/LLMs run."""
        combined = "\n".join(
            [user_message]
            + [
                str(msg.get("content", ""))
                for msg in messages[-5:]
                if msg.get("role", "user").lower() in {"user", "document", "system"}
            ]
        ).lower()

        refusal = (
            "I can't help with that request because it would bypass Fabric's "
            "tenant, evidence, approval, or secret-handling controls. I can help "
            "with a grounded, tenant-scoped draft using approved evidence."
        )
        rules: list[tuple[str, tuple[str, ...]]] = [
            ("prompt_injection", ("ignore previous instructions", "system override", "remove approval gates", "delete approval gates")),
            ("cross_tenant_access", ("every tenant", "all tenants", "cross-tenant", "other tenant")),
            ("secret_exfiltration", ("reveal internal secret", "reveal secrets", "api key", "token", "password")),
            ("approval_bypass", ("bypass approval", "mark them approved", "export immediately", "approval gates")),
            ("unsupported_roi", ("guarantee", "without evidence", "unsupported roi", "900% roi")),
            ("fabricated_benchmark", ("fabricate benchmark", "invent benchmark", "fake benchmark", "invent a benchmark source", "fabricate a benchmark")),
            ("fabricated_citation", ("source that does not exist", "citation that does not exist", "fake citation", "create a fake citation")),
            ("unauthorized_tool", ("unauthorized tool", "tool i am not allowed", "invoke admin tool", "run admin tool")),
        ]
        for reason, tokens in rules:
            if any(token in combined for token in tokens):
                return ConversationService__guardrailResult.model_validate({
                    "reason": reason,
                    "message": refusal,
                })
        return None

    def _heuristic_response(
        self,
        *,
        user_message: str,
        active_tab: str,
        intent: str,
        context_data: dict[str, object],
        account_name: str,
    ) -> str:
        """Generate a context-aware response without LLM."""
        lower = user_message.lower()
        evidence_records = (
            context_data.get("evidence_records")
            or context_data.get("evidence")
            or context_data.get("truth_references")
            or []
        )

        if any(token in lower for token in ("cite", "evidence", "claim", "roi", "business case")):
            if evidence_records:
                citations = []
                for item in evidence_records:
                    if isinstance(item, dict):
                        citation_id = item.get("id") or item.get("evidence_id") or item.get("truth_object_id")
                        tenant = item.get("tenant_id")
                        if citation_id and (tenant in {None, context_data.get("tenant_id")}):
                            citations.append(str(citation_id))
                if citations:
                    return (
                        f"For {account_name} in {active_tab}: Fact: the value claim is supported "
                        f"by persisted evidence {', '.join(citations[:3])}. Inference: prioritize "
                        "the recommendation only after reviewer validation. Assumption: missing "
                        "inputs remain unverified. Benchmark: use benchmark figures only when a "
                        "persisted benchmark source is attached."
                    )
            return (
                f"For {account_name} in {active_tab}: I do not have persisted evidence for that "
                "factual value claim, so I cannot present it as verified. Assumption: it can be "
                "kept as a draft hypothesis until supporting evidence is attached."
            )

        # Account context enrichment
        account_info = context_data.get("account", {})
        account_detail = ""
        if account_info:
            name = account_info.get("name", account_name)
            industry = account_info.get("industry", "")
            if industry:
                account_detail = f" ({industry})"
            account_name = name

        if intent == "value_analysis":
            return (
                f"For {account_name}{account_detail} in the {active_tab} view: "
                "I recommend starting with the highest-confidence value drivers, "
                "validating the ROI assumptions with the prospect, and building "
                "the business case around measurable outcomes. "
                "I can help you run sensitivity analysis or compare scenarios."
            )

        if intent == "competitive_intel":
            return (
                f"For {account_name}{account_detail}: I can pull competitive "
                "positioning data, generate battlecard talking points, and "
                "identify differentiation opportunities. Which competitor "
                "would you like to focus on?"
            )

        if intent == "document_export":
            return (
                f"I can help export the {active_tab} analysis for {account_name} "
                "as a stakeholder-ready document. Options include executive summary, "
                "detailed business case, or slide deck format. Which would you prefer?"
            )

        if intent == "workflow_status":
            return (
                "I can check the status of running workflows. Currently monitoring "
                "active analysis pipelines. What specific workflow are you asking about?"
            )

        if intent == "account_inquiry":
            if account_info:
                return (
                    f"Here's what I know about {account_name}{account_detail}: "
                    f"I have context data available including relationships and "
                    f"intelligence signals. What specific aspect would you like to explore?"
                )
            return (
                f"I can help you explore {account_name}. Select an account in the "
                "workspace to see enriched intelligence data, or ask me about "
                "specific signals, drivers, or value opportunities."
            )

        # General / summarize / compare / recommend
        if "summar" in lower:
            return (
                f"Here's a summary for {account_name} in {active_tab}: "
                "focus on the top signals by confidence, tie each to measurable "
                "impact, and capture validation questions for the next touchpoint."
            )

        if "compare" in lower:
            return (
                f"Comparing items in the {active_tab} view for {account_name}: "
                "the top-ranked items show significantly higher confidence and "
                "impact scores. I can break down the comparison in more detail."
            )

        if any(w in lower for w in ("recommend", "suggest", "next")):
            return (
                f"For {account_name} in {active_tab}: (1) Validate the top signals "
                "with the prospect, (2) Map strongest drivers to product capabilities, "
                "(3) Build the action plan around highest-confidence items."
            )

        return (
            f"Got it — for {account_name} in {active_tab}, I can help analyze "
            "findings, prioritize actions, run calculations, or draft "
            "stakeholder-ready messaging. What direction would you like to go?"
        )

    def _append_workflow_notice(
        self,
        content: str,
        workflow_result: dict[str, object] | None,
    ) -> str:
        """Append workflow scheduling notice if a workflow was triggered."""
        if not workflow_result:
            return content

        schedule_id = workflow_result.get("schedule_id", "unknown")
        return (
            f"{content}\n\n"
            f"📋 I've also kicked off a background analysis workflow "
            f"(identifier {schedule_id}). I'll surface the results when it completes."
        )

    async def _emit_audit(
        self,
        *,
        trace_id: str,
        workflow_id: str,
        audit_event_id: str,
        tenant_id: str,
        intent: str,
        confidence: float,
        active_tab: str,
        account_id: str | None,
        has_workflow: bool,
        journey_id: str | None,
    ) -> None:
        """Emit a GATE audit event for the conversation interaction."""
        try:
            await emit_audit_event(
                AuditAction.AGENT_EXECUTION,
                outcome=AuditOutcome.SUCCESS,
                resource_type="agent",
                resource_id="conversation-agent",
                details={
                    "trace_id": trace_id,
                    "workflow_id": workflow_id,
                    "audit_event_id": audit_event_id,
                    "tenant_id": tenant_id,
                    "journey_id": journey_id,
                    "intent": intent,
                    "confidence": confidence,
                    "active_tab": active_tab,
                    "account_id": account_id,
                    "workflow_triggered": has_workflow,
                },
                chain_id=f"conversation:{tenant_id}:journey:{journey_id}" if journey_id else f"conversation:{tenant_id}",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Failed to emit conversation audit event", exc_info=True)

    async def _emit_security_audit(
        self,
        *,
        trace_id: str,
        workflow_id: str,
        audit_event_id: str,
        tenant_id: str,
        active_tab: str,
        account_id: str | None,
        reason: str,
        journey_id: str | None,
    ) -> None:
        """Emit an audit event for refused unsafe agent requests."""
        try:
            await emit_audit_event(
                AuditAction.POLICY_DECISION,
                outcome=AuditOutcome.FAILURE,
                resource_type="agent",
                resource_id="conversation-agent",
                details={
                    "trace_id": trace_id,
                    "workflow_id": workflow_id,
                    "audit_event_id": audit_event_id,
                    "tenant_id": tenant_id,
                    "journey_id": journey_id,
                    "active_tab": active_tab,
                    "account_id": account_id,
                    "reason": reason,
                },
                chain_id=f"conversation-security:{tenant_id}:journey:{journey_id}" if journey_id else f"conversation-security:{tenant_id}",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Failed to emit conversation security audit event", exc_info=True)
