from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import ValidationError

"""Agent Stream route for RightRail conversational assistant (ValuePilot).

Wires the frontend RightRail chat to the ConversationService, which
orchestrates:
  1. Intent classification via ConversationAgent (GATE-governed)
  2. Context gathering via ConversationAgent (GATE-governed)
  3. Workflow delegation via OrchestrationController (when applicable)
  4. Response generation via C1 proxy (LLM) or heuristic fallback

The response contract is unchanged from the original stub:
  { content: str, metadata: AgentGovernanceMetadata }
"""


import json
import logging
import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling.middleware import get_request_id
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ..common.db import get_route_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models (unchanged from original contract)
# ---------------------------------------------------------------------------


class AgentStreamMessage(BaseModel):
    """Single chat message compatible with frontend request shape."""

    role: str = Field(..., description="Message role (system|user|assistant)")
    content: str = Field(..., min_length=1, description="Message text")


class AgentStreamAccountContext(BaseModel):
    """Account/workspace context from frontend."""

    account_name: str | None = Field(
        default=None, alias="accountName", description="Selected account display name"
    )
    account_id: str | None = Field(
        default=None, alias="accountId", description="Selected account identifier"
    )
    account_tier: str | None = Field(
        default=None, alias="accountTier", description="Optional account segment/tier"
    )

    model_config = ConfigDict(populate_by_name=True)


class AgentStreamRequest(BaseModel):
    """Request payload expected by RightRail frontend."""

    messages: list[AgentStreamMessage] = Field(..., min_length=1)
    active_tab: str = Field(..., alias="activeTab", min_length=1, description="Active UI tab key")
    account: AgentStreamAccountContext | None = Field(default=None)
    context_envelope: dict[str, object] | None = Field(default=None, alias="contextEnvelope")
    entity_context: dict[str, object] | None = Field(default=None, alias="entityContext")
    selected_signal_id: str | None = Field(default=None, alias="selectedSignalId")
    selected_value_path: str | None = Field(default=None, alias="selectedValuePath")
    selected_driver_tree_id: str | None = Field(default=None, alias="selectedDriverTreeId")
    selected_scenario_id: str | None = Field(default=None, alias="selectedScenarioId")
    selected_business_case_id: str | None = Field(default=None, alias="selectedBusinessCaseId")
    # Stable journey handle threaded across tabs/sessions for an account.
    # When omitted, the service derives a deterministic journey_id from
    # (tenant_id, account_id) so every turn remains journey-linked.
    journey_id: str | None = Field(default=None, alias="journeyId")

    model_config = ConfigDict(populate_by_name=True)


class AgentGovernanceMetadata(BaseModel):
    """Governance metadata surfaced to RightRail and trace/audit views."""

    trace_id: str
    workflow_id: str
    tenant_id: str
    tool_name: str
    audit_event_id: str
    emitted_at: str
    # Stable journey link — reconstruct the full account progression timeline.
    journey_id: str | None = None
    # New fields surfaced from ConversationService
    intent: str | None = None
    confidence: float | None = None
    workflow_triggered: bool | None = None
    # Authoritative tier degradation signals
    response_tier: str | None = None
    provider: str | None = None
    fallback: bool | None = None
    degraded: bool | None = None
    degradation_reason: str | None = None


class AgentStreamResponse(BaseModel):
    """Assistant response payload for RightRail."""

    content: str
    metadata: AgentGovernanceMetadata


# ---------------------------------------------------------------------------
# Singleton ConversationService (lazy-initialized)
# ---------------------------------------------------------------------------

_conversation_service = None


def _get_conversation_service(context_gatherer=None, tool_registry=None):
    """Lazy-initialize the ConversationService singleton.

    The service is created once and reused across requests. Agent
    instances are optional — the service degrades gracefully when
    they are not available (e.g., during early startup or testing).
    """
    global _conversation_service
    if _conversation_service is not None:
        # If dependencies were provided but the cached service doesn't have them,
        # update it. This handles the first request that has DB/Neo4j access.
        if context_gatherer and _conversation_service.context_gatherer is None:
            _conversation_service.context_gatherer = context_gatherer
        if tool_registry and _conversation_service.tool_registry is None:
            _conversation_service.tool_registry = tool_registry
        return _conversation_service

    from ..services.conversation import ConversationService

    # Attempt to instantiate agents — fail gracefully
    conversation_agent = None
    orchestration_controller = None

    try:
        from ..agents.taxonomy import ConversationAgent

        conversation_agent = ConversationAgent(
            config={"manifest_path": "services/layer4-agents/manifests/conversation_agent.abom.json"},
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.info("ConversationAgent not available — using heuristic mode")

    try:
        from ..agents.taxonomy import OrchestrationController

        orchestration_controller = OrchestrationController(
            config={"manifest_path": "services/layer4-agents/manifests/orchestration_controller.abom.json"},
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.info("OrchestrationController not available — no workflow delegation")

    c1_enabled = bool(os.getenv("THESYS_API_KEY"))

    # LLM intent classifier (lightweight, uses OpenAI directly)
    intent_classifier = None
    if os.getenv("OPENAI_API_KEY"):
        from ...services.llm_intent_classifier import LLMIntentClassifier
        intent_classifier = LLMIntentClassifier()

    _conversation_service = ConversationService(
        conversation_agent=conversation_agent,
        orchestration_controller=orchestration_controller,
        c1_enabled=c1_enabled,
        context_gatherer=context_gatherer,
        intent_classifier=intent_classifier,
        tool_registry=tool_registry,
    )

    logger.info(
        "ConversationService initialized: agent=%s, orchestrator=%s, c1=%s, context=%s, llm_intent=%s, tools=%s",
        conversation_agent is not None,
        orchestration_controller is not None,
        c1_enabled,
        context_gatherer is not None,
        intent_classifier is not None,
        tool_registry is not None,
    )

    return _conversation_service


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post("/agent-stream/chat", response_model=AgentStreamResponse)
async def agent_stream_chat(
    payload: AgentStreamRequest,
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_route_db),
) -> AgentStreamResponse:
    """Handle RightRail chat payload through the ConversationService pipeline.

    The pipeline:
    1. Extract user message and account context from payload
    2. Resolve trace ID from request correlation or OpenTelemetry
    3. Delegate to ConversationService.handle_message()
    4. Return response with governance metadata
    """
    if not ctx.tenant_id:
        raise ValidationError(message = "Validated tenant context required for agent requests")

    # Extract the last user message
    last_user_message = next(
        (msg.content for msg in reversed(payload.messages) if msg.role.lower() == "user"),
        payload.messages[-1].content,
    )

    # Extract account context
    account_name = (
        payload.account.account_name
        if payload.account and payload.account.account_name
        else "this account"
    )
    account_id = (
        payload.account.account_id
        if payload.account and payload.account.account_id
        else None
    )
    account_tier = (
        payload.account.account_tier
        if payload.account and payload.account.account_tier
        else None
    )
    entity_context = payload.entity_context or {}
    if payload.context_envelope:
        entity_context.setdefault("contextEnvelope", payload.context_envelope)
    entity_context.setdefault("accountId", account_id)
    entity_context.setdefault("activeTab", payload.active_tab)
    if payload.selected_signal_id:
        entity_context.setdefault("selectedSignalId", payload.selected_signal_id)
    if payload.selected_value_path:
        entity_context.setdefault("selectedValuePath", payload.selected_value_path)
    if payload.selected_driver_tree_id:
        entity_context.setdefault("selectedDriverTreeId", payload.selected_driver_tree_id)
    if payload.selected_scenario_id:
        entity_context.setdefault("selectedScenarioId", payload.selected_scenario_id)
    if payload.selected_business_case_id:
        entity_context.setdefault("selectedBusinessCaseId", payload.selected_business_case_id)

    # Resolve trace ID
    request_trace_id = get_request_id(request)
    span = trace.get_current_span()
    span_context = span.get_span_context()
    trace_id = (
        f"{span_context.trace_id:032x}"
        if span_context is not None and span_context.trace_id != 0
        else request_trace_id
    )

    tenant_id = str(ctx.tenant_id)

    # Build message list for context
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]

    # Build context gatherer with real DB + Neo4j access
    neo4j_driver = getattr(request.app.state, "neo4j_driver", None)
    context_gatherer = None
    tool_registry = None
    if neo4j_driver or db:
        from ...services.agent_tools import AgentToolRegistry
        from ...services.context_gatherer import ContextGatheringService
        context_gatherer = ContextGatheringService(neo4j_driver=neo4j_driver, db=db)
        tool_registry = AgentToolRegistry(neo4j_driver=neo4j_driver, db=db)

    # Delegate to ConversationService
    service = _get_conversation_service(context_gatherer=context_gatherer, tool_registry=tool_registry)
    result = await service.handle_message(
        user_message=last_user_message,
        messages=messages,
        active_tab=payload.active_tab,
        account_id=account_id,
        account_name=account_name,
        account_tier=account_tier,
        entity_context=entity_context,
        tenant_id=tenant_id,
        trace_id=trace_id,
        journey_id=payload.journey_id,
    )

    # Map result to response contract
    metadata = result.get("metadata", {})
    return AgentStreamResponse(
        content=result["content"],
        metadata=AgentGovernanceMetadata(
            trace_id=metadata.get("trace_id", trace_id),
            workflow_id=metadata.get("workflow_id", str(uuid.uuid4())),
            tenant_id=metadata.get("tenant_id", tenant_id),
            tool_name=metadata.get("tool_name", "valuepilot_conversation"),
            audit_event_id=metadata.get("audit_event_id", f"audit_{uuid.uuid4().hex[:12]}"),
            emitted_at=metadata.get("emitted_at", datetime.now(UTC).isoformat()),
            journey_id=metadata.get("journey_id"),
            intent=metadata.get("intent"),
            confidence=metadata.get("confidence"),
            workflow_triggered=metadata.get("workflow_triggered"),
            response_tier=metadata.get("response_tier"),
            provider=metadata.get("provider"),
            fallback=metadata.get("fallback"),
            degraded=metadata.get("degraded"),
            degradation_reason=metadata.get("degradation_reason"),
        ),
    )


@router.post("/agent-stream/chat/stream")
async def agent_stream_chat_sse(
    payload: AgentStreamRequest,
    request: Request,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_route_db),
) -> StreamingResponse:
    """SSE streaming version of the agent chat endpoint.

    Emits AG-UI protocol events as server-sent events:
      RUN_STARTED → STEP_STARTED/STEP_FINISHED → TEXT_MESSAGE_* → RUN_FINISHED
    """
    if not ctx.tenant_id:
        raise ValidationError(message = "Validated tenant context required for agent requests")

    last_user_message = next(
        (msg.content for msg in reversed(payload.messages) if msg.role.lower() == "user"),
        payload.messages[-1].content,
    )

    account_name = (
        payload.account.account_name
        if payload.account and payload.account.account_name
        else "this account"
    )
    account_id = (
        payload.account.account_id
        if payload.account and payload.account.account_id
        else None
    )
    account_tier = (
        payload.account.account_tier
        if payload.account and payload.account.account_tier
        else None
    )

    entity_context = payload.entity_context or {}
    if payload.context_envelope:
        entity_context.setdefault("contextEnvelope", payload.context_envelope)
    entity_context.setdefault("accountId", account_id)
    entity_context.setdefault("activeTab", payload.active_tab)
    if payload.selected_signal_id:
        entity_context.setdefault("selectedSignalId", payload.selected_signal_id)
    if payload.selected_value_path:
        entity_context.setdefault("selectedValuePath", payload.selected_value_path)
    if payload.selected_driver_tree_id:
        entity_context.setdefault("selectedDriverTreeId", payload.selected_driver_tree_id)
    if payload.selected_scenario_id:
        entity_context.setdefault("selectedScenarioId", payload.selected_scenario_id)
    if payload.selected_business_case_id:
        entity_context.setdefault("selectedBusinessCaseId", payload.selected_business_case_id)

    request_trace_id = get_request_id(request)
    span = trace.get_current_span()
    span_context = span.get_span_context()
    trace_id = (
        f"{span_context.trace_id:032x}"
        if span_context is not None and span_context.trace_id != 0
        else request_trace_id
    )

    tenant_id = str(ctx.tenant_id)
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]

    # Build context gatherer and tool registry
    neo4j_driver = getattr(request.app.state, "neo4j_driver", None)
    context_gatherer = None
    tool_registry = None
    if neo4j_driver or db:
        from ...services.agent_tools import AgentToolRegistry
        from ...services.context_gatherer import ContextGatheringService
        context_gatherer = ContextGatheringService(neo4j_driver=neo4j_driver, db=db)
        tool_registry = AgentToolRegistry(neo4j_driver=neo4j_driver, db=db)

    service = _get_conversation_service(context_gatherer=context_gatherer, tool_registry=tool_registry)

    async def _event_generator():
        try:
            async for event in service.handle_message_streaming(
                user_message=last_user_message,
                messages=messages,
                active_tab=payload.active_tab,
                account_id=account_id,
                account_name=account_name,
                account_tier=account_tier,
                entity_context=entity_context,
                tenant_id=tenant_id,
                trace_id=trace_id,
                journey_id=payload.journey_id,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("SSE stream error")
            yield f"data: {json.dumps({'type': 'RUN_ERROR', 'message': 'Streaming error', 'retryable': True})}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
