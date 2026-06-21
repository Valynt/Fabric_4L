from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError, ValidationError

"""Signal API routes for operational pain signal management.

Provides REST API endpoints for:
- Prospect setup and signal detection triggering
- Signal retrieval for accounts
- WebSocket streaming for real-time signal discovery
"""


import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from value_fabric.shared.audit import AuditAction, AuditEmitter, AuditOutcome
from value_fabric.shared.error_handling import sanitize_log_error
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.jwt import decode_jwt
from value_fabric.shared.observability.trace_context import resolve_trace_context

from ...config.settings import get_settings
from ...database import db_session_for_context
from ...interfaces.signal_review import SignalReviewPort
from ...models.account import Account
from ...startup.agent_composition import create_signal_detection_agent, create_signal_review_client

if TYPE_CHECKING:
    from ...agents.signal_detection import SignalDetectionAgent

logger = logging.getLogger(__name__)

router = APIRouter()


async def _tenant_owns_prospect(*, prospect_id: str, tenant_id: str) -> bool:
    """Return True when the tenant owns the prospect/account identifier."""
    filters = [
        Account.tenant_id == tenant_id,
        Account.provider_record_id == prospect_id,
    ]
    try:
        filters.append(Account.id == UUID(prospect_id))
    except ValueError:
        pass

    context = RequestContext(tenant_id=tenant_id)
    async with db_session_for_context(context) as session:
        query = select(Account.id).where(or_(*filters)).limit(1)
        result = await session.execute(query)
        return result.scalar_one_or_none() is not None


# ============================================================================
# Request/Response Models
# ============================================================================


class ProspectData(BaseModel):
    """Prospect setup input data."""

    account_id: str = Field(..., description="Account identifier")
    company_name: str = Field(..., description="Company name")
    industry: str | None = Field(default=None, description="Industry vertical")
    business_pains: list[str] = Field(default_factory=list, description="Reported business pains")
    friction_points: list[str] = Field(default_factory=list, description="Current friction points")
    desired_outcomes: list[str] = Field(default_factory=list, description="Desired outcomes")
    prompt_text: str = Field(..., description="Freeform prompt text")
    prompt_id: str | None = Field(default=None, description="Optional prompt identifier")
    attachments: list[dict[str, Any]] = Field(default_factory=list, description="Attached documents")


class ProspectSetupRequest(BaseModel):
    """Request to set up a prospect and detect signals."""

    prospect_data: ProspectData = Field(..., description="Prospect information")
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Detection options (include_evidence, quantify_impact)"
    )


class ProcessingMetadata(BaseModel):
    """Metadata about signal processing."""

    extraction_duration_ms: int = Field(default=0)
    enrichment_duration_ms: int = Field(default=0)
    persistence_duration_ms: int = Field(default=0)
    signals_found: int = Field(default=0)
    signals_with_evidence: int = Field(default=0)
    signals_quantified: int = Field(default=0)
    trace_id: str = Field(default="")


class ProspectSetupResponse(BaseModel):
    """Response from prospect setup with detected signals."""

    success: bool = Field(..., description="Whether detection succeeded")
    signals: list[dict[str, Any]] = Field(default_factory=list, description="Detected signals")
    processing_metadata: ProcessingMetadata = Field(default_factory=dict)
    message: str | None = Field(default=None, description="Status message")


class SignalListResponse(BaseModel):
    """Response with list of signals for an account."""

    account_id: str = Field(..., description="Account identifier")
    signals: list[dict[str, Any]] = Field(default_factory=list, description="Signals")
    total_count: int = Field(..., description="Total number of signals")
    category_filter: str | None = Field(default=None, description="Applied category filter")


class SignalStreamEvent(BaseModel):
    """WebSocket event for signal streaming."""

    event_type: str = Field(..., description="Event type (discovered, completed, failed, complete)")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    prospect_id: str = Field(..., description="Associated prospect/account ID")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event payload")


class SignalReviewRequest(BaseModel):
    """Request payload for reviewing a signal."""

    account_id: str = Field(..., description="Account identifier for scope validation")
    review_status: str = Field(..., description="Review decision status: approved|rejected")
    decision_note: str | None = Field(default=None, description="Optional reviewer rationale")


class SignalReviewResponse(BaseModel):
    """Response payload for signal review mutations."""

    signal_id: str
    account_id: str
    review_status: str
    reviewed_by: str
    reviewed_at: str
    decision_note: str | None = None




class EvidenceDecisionRequest(BaseModel):
    account_id: str
    case_id: str
    decision: str
    decision_note: str | None = None


class EvidenceDriverLinkRequest(BaseModel):
    account_id: str
    case_id: str


class EvidenceDecisionResponse(BaseModel):
    evidence_id: str
    account_id: str
    case_id: str
    decision: str
    reviewed_by: str
    reviewed_at: str
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
# ============================================================================
# API Endpoints
# ============================================================================


def get_signal_agent() -> SignalDetectionAgent:
    """Get or create signal detection agent instance."""
    # In production, this would be a dependency injection or singleton
    # For now, create fresh instance per request
    return create_signal_detection_agent(
        {
            "max_signals_per_request": 3,
            "evidence_match_limit": 5,
        }
    )


def get_signal_review_client() -> SignalReviewPort:
    """Return the signal/evidence review adapter for route operations."""

    settings = get_settings()
    return create_signal_review_client(str(settings.layer3_api_url))


@router.post("/prospects/setup", response_model=ProspectSetupResponse)
async def setup_prospect(
    request: ProspectSetupRequest,
    ctx: RequestContext = Depends(require_authenticated),
    audit: AuditEmitter = Depends(AuditEmitter),
) -> ProspectSetupResponse:
    """Submit prospect setup data and detect operational signals.

    This endpoint triggers the complete signal detection pipeline:
    1. Layer 2: LLM extraction of operational signals
    2. Layer 3: Evidence matching and impact quantification
    3. Layer 3: Persistence to knowledge graph

    Args:
        request: Prospect setup data with options
        ctx: Request context with tenant_id and user info
        audit: Audit emitter for compliance logging

    Returns:
        ProspectSetupResponse with detected signals and metadata
    """
    _start_time = datetime.now(UTC)

    try:
        # Initialize agent
        agent = get_signal_agent()
        await agent.initialize()

        # Set default options
        options = request.options or {}
        options.setdefault("include_evidence", True)
        options.setdefault("quantify_impact", True)
        options.setdefault("stream_results", False)

        # Prepare task
        task = {
            "capability": "detect_operational_signals",
            "parameters": {
                "prospect_data": request.prospect_data.model_dump(),
                "options": options,
            },
        }

        # Prepare context
        context = {
            "tenant_id": ctx.tenant_id,
            "user_id": ctx.user_id,
            "trace_id": ctx.trace_id,
        }

        # Execute detection
        result = await agent.execute(task, context)

        # Emit audit event
        await audit.emit(
            AuditAction.CREATE,
            resource_type="signals",
            resource_id=request.prospect_data.account_id,
            outcome=AuditOutcome.SUCCESS,
            metadata={
                "signals_found": result.get("processing_metadata", {}).get("signals_found", 0),
                "trace_id": ctx.trace_id,
            },
        )

        # Calculate total duration
        processing_metadata = result.get("processing_metadata", {})

        return ProspectSetupResponse(
            success=True,
            signals=result.get("signals", []),
            processing_metadata=ProcessingMetadata(
                extraction_duration_ms=processing_metadata.get("extraction_duration_ms", 0),
                enrichment_duration_ms=processing_metadata.get("enrichment_duration_ms", 0),
                persistence_duration_ms=processing_metadata.get("persistence_duration_ms", 0),
                signals_found=processing_metadata.get("signals_found", 0),
                signals_with_evidence=processing_metadata.get("signals_with_evidence", 0),
                signals_quantified=processing_metadata.get("signals_quantified", 0),
                trace_id=ctx.trace_id or "",
            ),
            message=f"Detected {processing_metadata.get('signals_found', 0)} operational signals",
        )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(
            f"Prospect setup failed: {e}",
            extra={"tenant_id": ctx.tenant_id, "trace_id": ctx.trace_id},
        )

        # Emit audit event for failure
        await audit.emit(
            AuditAction.CREATE,
            resource_type="signals",
            resource_id=request.prospect_data.account_id,
            outcome=AuditOutcome.FAILURE,
            metadata={"error": "Signal detection failed", "error_code": "SIGNAL_DETECTION_ERROR", "trace_id": ctx.trace_id},
        )

        raise ServiceUnavailableError(message="Signal detection failed")


@router.get("/accounts/{account_id}/signals", response_model=SignalListResponse)
async def get_account_signals(
    account_id: str,
    category: str | None = None,
    ctx: RequestContext = Depends(require_authenticated),
) -> SignalListResponse:
    """Get signals for an account.

    Retrieves persisted pain signals with optional category filtering.

    Args:
        account_id: Account identifier
        category: Optional category filter (e.g., "Operational")
        ctx: Request context with tenant_id

    Returns:
        SignalListResponse with signals for the account
    """
    try:
        agent = get_signal_agent()
        await agent.initialize()

        signals = await agent.get_account_signals(
            account_id=account_id,
            tenant_id=ctx.tenant_id,
            category=category,
        )

        return SignalListResponse(
            account_id=account_id,
            signals=[s.model_dump() for s in signals],
            total_count=len(signals),
            category_filter=category,
        )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to retrieve account signals: {e}",
            extra={"tenant_id": ctx.tenant_id, "account_id": account_id},
        )
        raise ServiceUnavailableError(message="Failed to retrieve signals")


@router.get("/signals/{signal_id}")
async def get_signal_by_id(
    signal_id: str,
    ctx: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Get a specific signal by ID.

    Args:
        signal_id: Signal identifier
        ctx: Request context with tenant_id

    Returns:
        Signal data
    """
    # This would typically call Layer 3 to fetch the signal
    # For now, return a placeholder that Layer 3 will implement
    raise ServiceUnavailableError(message="Signal retrieval by ID - implement in Layer 3 integration")


@router.patch("/signals/{signal_id}/review", response_model=SignalReviewResponse)
async def review_signal(
    signal_id: str,
    request: SignalReviewRequest,
    ctx: RequestContext = Depends(require_authenticated),
    review_client: SignalReviewPort = Depends(get_signal_review_client),
) -> SignalReviewResponse:
    """Review a signal and persist reviewer metadata/timestamp."""
    if request.review_status not in {"approved", "rejected"}:
        raise ValidationError(message = "review_status must be approved or rejected")

    reviewed_at = datetime.now(UTC).isoformat()
    response = await review_client.review_signal(
        signal_id=signal_id,
        account_id=request.account_id,
        review_status=request.review_status,
        reviewer_id=ctx.user_id,
        decision_note=request.decision_note,
        tenant_id=str(ctx.tenant_id),
    )
    return SignalReviewResponse(
        signal_id=signal_id,
        account_id=request.account_id,
        review_status=response.get("review_status", request.review_status),
        reviewed_by=response.get("reviewed_by", ctx.user_id),
        reviewed_at=response.get("reviewed_at", reviewed_at),
        decision_note=response.get("decision_note", request.decision_note),
    )


# ============================================================================
# WebSocket Streaming
# ============================================================================


@router.websocket("/signals/stream/{prospect_id}")
async def signal_stream_websocket(
    websocket: WebSocket,
    prospect_id: str,
) -> None:
    """WebSocket endpoint for real-time signal streaming.

    Streams signal discovery events as they are detected:
    - signal_discovered: New signal found during extraction
    - signal_completed: Signal fully processed with evidence
    - signal_failed: Processing error for a signal
    - stream_complete: All signals processed

    Authentication: JWT must be supplied via the ``Sec-WebSocket-Protocol``
    header in canonical format ``base64url.bearer.authorization, <jwt>``.
    Query-parameter tokens are rejected
    to prevent credential logging by proxies.

    Args:
        websocket: WebSocket connection
        prospect_id: Prospect/account ID to stream signals for
    """
    # OBS-L4-004: Resolve correlation ID at the HTTP upgrade stage.
    # Inherits X-Request-ID / X-Correlation-ID from the client if present,
    # otherwise generates a new one. All subsequent log calls in this session
    # include this ID so WebSocket events are traceable end-to-end.
    trace_ctx = resolve_trace_context(websocket.headers)
    correlation_id = trace_ctx.trace_id
    _log: dict = {"prospect_id": prospect_id, "correlation_id": correlation_id}

    # SEC-L4-WS-002: Reject JWT in query parameter (mirrors workflow WebSocket fix).
    # Tokens in query params are written to proxy/access logs.
    if websocket.query_params.get("token"):
        logger.warning(
            "Signals WebSocket rejected: token in query param",
            extra={"auth_code": "AUTH_QUERY_TOKEN_FORBIDDEN", **_log},
        )
        await websocket.close(
            code=1008,
            reason="Authentication via query param is forbidden; use Sec-WebSocket-Protocol header",
        )
        return

    # SEC-L4-WS-002: Extract JWT from Sec-WebSocket-Protocol header.
    protocol_header = websocket.headers.get("sec-websocket-protocol", "")
    ws_token: str | None = None
    if protocol_header:
        parts = [p.strip() for p in protocol_header.split(",")]
        if len(parts) >= 2 and parts[0].lower() == "base64url.bearer.authorization":
            ws_token = parts[1] or None

    if not ws_token:
        logger.warning(
            "Signals WebSocket rejected: missing/invalid Sec-WebSocket-Protocol bearer header",
            extra={"auth_code": "AUTH_HEADER_INVALID_OR_MISSING", **_log},
        )
        await websocket.close(code=1008, reason='{"code":"AUTH_HEADER_INVALID_OR_MISSING"}')
        return

    try:
        payload = decode_jwt(ws_token)
        if not payload:
            await websocket.close(code=1008, reason='{"code":"AUTH_TOKEN_INVALID"}')
            return
        # decode_jwt returns TokenClaims (dataclass) or dict depending on version
        if isinstance(payload, dict):
            tenant_id: str | None = payload.get("tenant_id", None)
            user_id: str | None = (
                payload["sub"]
                if "sub" in payload
                else payload.get("user_id", None)
            )
        else:
            tenant_id = getattr(payload, "tenant_id", None)
            user_id = getattr(payload, "sub", None) or getattr(payload, "user_id", None)

        if not tenant_id:
            await websocket.close(code=1008, reason='{"code":"AUTH_TENANT_CLAIM_INVALID"}')
            return
        tenant_id = str(tenant_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("Signals WebSocket JWT decode failed", extra=_log)
        await websocket.close(code=1008, reason='{"code":"AUTH_TOKEN_DECODE_FAILED"}')
        return

    # Bind tenant context to the log dict now that we have it
    _log["tenant_id"] = tenant_id

    # SEC-L4-WS-002: Verify the prospect belongs to the authenticated tenant.
    # Missing records and cross-tenant IDs both fail closed with a generic denial.
    try:
        prospect_found = await _tenant_owns_prospect(
            prospect_id=prospect_id,
            tenant_id=tenant_id,
        )
        if not prospect_found:
            logger.warning("Signals WebSocket: prospect not found for tenant", extra=_log)
            await websocket.close(code=1008, reason="Authorization failed")
            return
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "Signals WebSocket: prospect ownership check failed — denying connection",
            extra=_log,
        )
        await websocket.close(code=1008, reason="Authorization failed")
        return

    await websocket.accept()
    active = True

    logger.info("Signals WebSocket session started", extra={**_log, "user_id": user_id})

    try:
        # Send connection confirmation
        await websocket.send_json({
            "event_type": "connected",
            "prospect_id": prospect_id,
            "correlation_id": correlation_id,
            "timestamp": datetime.now(UTC).isoformat(),
        })

        # Keep connection alive and wait for client messages
        while active:
            try:
                # Receive messages from client (ping/keepalive or configuration)
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({
                        "event_type": "pong",
                        "correlation_id": correlation_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                    })
                else:
                    await websocket.send_json({
                        "event_type": "ack",
                        "received": data,
                        "correlation_id": correlation_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                    })

            except WebSocketDisconnect:
                active = False
                logger.info("Signals WebSocket client disconnected", extra=_log)

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("Signals WebSocket session error", extra={**_log, "error_code": "WEBSOCKET_SESSION_ERROR", "error": sanitize_log_error(e)})
        await websocket.close(code=1011, reason="Server error")
    finally:
        logger.info("Signals WebSocket session ended", extra=_log)


async def stream_signals_to_websocket(
    websocket: WebSocket,
    prospect_data: ProspectData,
    tenant_id: str,
    trace_id: str,
) -> None:
    """Stream signal detection results to WebSocket.

    This is the actual streaming implementation called by the prospect setup endpoint
    when stream_results=True.

    Args:
        websocket: Active WebSocket connection
        prospect_data: Prospect setup data
        tenant_id: Tenant identifier
        trace_id: Trace ID for observability
    """
    agent = get_signal_agent()
    await agent.initialize()

    # Set up streaming callback
    async def emit_event(event_data: dict[str, Any]) -> None:
        try:
            event_data.setdefault("correlation_id", trace_id)
            await websocket.send_json(event_data)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Failed to send WebSocket event: {e}")

    # Configure task with streaming
    task = {
        "capability": "stream_signal_detection",
        "parameters": {
            "prospect_data": prospect_data.model_dump(),
            "stream_callback": emit_event,
            "options": {"include_evidence": True, "quantify_impact": True},
        },
    }

    context = {
        "tenant_id": tenant_id,
        "trace_id": trace_id,
    }

    # Execute with streaming
    await agent.execute(task, context)


@router.patch("/evidence/{evidence_id}/decision", response_model=EvidenceDecisionResponse)
async def decide_evidence(
    evidence_id: str,
    request: EvidenceDecisionRequest,
    ctx: RequestContext = Depends(require_authenticated),
    review_client: SignalReviewPort = Depends(get_signal_review_client),
) -> EvidenceDecisionResponse:
    if request.decision not in {"accepted", "rejected"}:
        raise ValidationError(message = "decision must be accepted or rejected")
    now = datetime.now(UTC).isoformat()
    response = await review_client.decide_evidence(
        evidence_id=evidence_id,
        account_id=request.account_id,
        case_id=request.case_id,
        decision=request.decision,
        reviewer_id=ctx.user_id,
        decision_note=request.decision_note,
        tenant_id=str(ctx.tenant_id),
    )
    return EvidenceDecisionResponse(
        evidence_id=evidence_id,
        account_id=request.account_id,
        case_id=request.case_id,
        decision=response.get("decision", request.decision),
        reviewed_by=response.get("reviewed_by", ctx.user_id),
        reviewed_at=response.get("reviewed_at", now),
        provenance=response.get("provenance", {}),
        confidence=response.get("confidence"),
    )


@router.post("/evidence/{evidence_id}/drivers/{driver_id}")
async def link_evidence_driver(
    evidence_id: str,
    driver_id: str,
    request: EvidenceDriverLinkRequest,
    ctx: RequestContext = Depends(require_authenticated),
    review_client: SignalReviewPort = Depends(get_signal_review_client),
) -> dict[str, Any]:
    response = await review_client.link_evidence_driver(
        evidence_id=evidence_id,
        driver_id=driver_id,
        account_id=request.account_id,
        case_id=request.case_id,
        tenant_id=str(ctx.tenant_id),
    )
    return {"evidence_id": evidence_id, "driver_id": driver_id, **(response or {})}
