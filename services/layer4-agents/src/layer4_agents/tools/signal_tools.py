from __future__ import annotations

"""Value Signal tools for L4 agents.

Provides tenant-scoped tools for agents to retrieve and create ValueSignals
from the L2.5 Signal Refinery. All tools enforce tenant boundaries and audit
invocations.

Agents MUST NOT invent signals without creating evidence/provenance records.
Use create_signal() to emit new signals with traceable provenance.
"""
import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.error_handling.exceptions import AuthenticationError
from value_fabric.shared.identity.context import RequestContext, get_request_context
from value_fabric.shared.identity.policy_registry import authorize_action

logger = logging.getLogger(__name__)

_SIGNAL_REFINERY_BASE_URL = os.getenv("LAYER2_5_BASE_URL", "http://localhost:8007")
_HTTP_TIMEOUT = 15.0

# Shared client — reused across all tool calls to enable connection pooling.
# Instantiated lazily on first use; closed by the application lifespan handler.
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=_HTTP_TIMEOUT)
    return _http_client


async def close_http_client() -> None:
    """Close the shared HTTP client. Call during application shutdown."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


def _require_tool_context(context: RequestContext | None = None) -> RequestContext:
    """Resolve the explicit or ambient request context. Fail closed if missing."""
    ctx = context or get_request_context()
    if ctx is None or not getattr(ctx, "tenant_id", None):
        raise AuthenticationError(message = "Tenant-scoped tool execution requires authenticated context")
    return ctx


def _signal_headers(
    tenant_id: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, str]:
    headers = {"X-Tenant-ID": tenant_id}
    if request_id:
        headers["X-Request-ID"] = request_id
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id
    elif request_id:
        headers["X-Correlation-ID"] = request_id
    return headers


async def get_account_signals(
    account_id: str,
    *,
    signal_types: list[str] | None = None,
    lifecycle_states: list[str] | None = None,
    min_confidence: float = 0.5,
    limit: int = 50,
    context: RequestContext | None = None,
) -> list[dict[str, Any]]:
    """Retrieve ValueSignals for an account from the L2.5 Signal Refinery.

    Agents use this to get validated signals before generating hypotheses,
    ROI assumptions, business cases, renewal risk, or expansion recommendations.

    Args:
        account_id: Account to retrieve signals for.
        signal_types: Optional filter by type (e.g. ["pain", "opportunity"]).
        lifecycle_states: Optional filter by state. Defaults to ["validated", "promoted"].
        min_confidence: Minimum confidence threshold (0–1). Default 0.5.
        limit: Maximum signals to return.
        context: RequestContext — resolved from ambient context if not provided.

    Returns:
        List of ValueSignal dicts. Empty list on failure.
    """
    _ctx = _require_tool_context(context)
    ctx = authorize_action("layer4.tool.signals.read", _ctx)
    if not isinstance(ctx, RequestContext) or not getattr(ctx, "tenant_id", None):
        raise AuthenticationError(message = "Tenant-scoped tool execution requires authenticated context")
    tenant_id = str(ctx.tenant_id)

    states = lifecycle_states or ["validated", "promoted"]
    params: dict[str, Any] = {
        "account_id": account_id,
        "min_confidence": min_confidence,
        "limit": limit,
        "lifecycle_state": states,
    }
    if signal_types:
        params["types"] = signal_types

    outcome = AuditOutcome.FAILURE
    reason = "error"

    try:
        req_id = getattr(ctx, "request_id", None) or getattr(ctx, "trace_id", None)
        response = await _get_http_client().get(
            f"{_SIGNAL_REFINERY_BASE_URL}/api/v1/signals",
            params=params,
            headers=_signal_headers(tenant_id, request_id=req_id),
        )
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            outcome = AuditOutcome.SUCCESS
            reason = "ok"
            return items
        logger.warning(
            "get_account_signals returned %s for account=%s tenant=%s",
            response.status_code, account_id, tenant_id,
        )
        return []
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "get_account_signals failed for account=%s tenant=%s", account_id, tenant_id
        )
        return []
    finally:
        emit_audit_event(
            action=AuditAction.KG_NODE_UPDATED,
            outcome=outcome,
            resource_type="value_signal",
            resource_id=account_id,
            tenant_id=ctx.tenant_id,
            details={
                "operation": "get_account_signals",
                "account_id": account_id,
                "reason": reason,
                "signal_types": signal_types,
                "lifecycle_states": states,
            },
        )


async def create_signal(
    account_id: str,
    signal_type: str,
    content: str,
    evidence: list[dict[str, Any]],
    confidence: float,
    *,
    provenance_method: str = "agent_inference",
    provenance_model: str | None = None,
    run_id: str | None = None,
    impact_area: str | None = None,
    estimated_value: float | None = None,
    source_refs: list[str] | None = None,
    context: RequestContext | None = None,
) -> dict[str, Any] | None:
    """Create a new ValueSignal with evidence and provenance.

    Agents MUST call this when emitting new signals. Signals without
    evidence/provenance records are not accepted by the Value Signal Layer.

    Args:
        account_id: Account this signal is scoped to.
        signal_type: ValueSignalType (e.g. "pain", "opportunity", "risk").
        content: Human-readable signal content.
        evidence: List of evidence dicts with source_ref and confidence.
        confidence: Extraction confidence (0–1).
        provenance_method: How the signal was derived (default: "agent_inference").
        provenance_model: LLM model identifier if AI-generated.
        run_id: Workflow run ID for traceability.
        impact_area: "revenue" | "cost" | "risk" | "strategic".
        estimated_value: Estimated monetary value if known.
        source_refs: Source document references.
        context: RequestContext — resolved from ambient context if not provided.

    Returns:
        Created ValueSignal dict, or None on failure.
    """
    _ctx = _require_tool_context(context)
    ctx = authorize_action("layer4.tool.signals.write", _ctx)
    if not isinstance(ctx, RequestContext) or not getattr(ctx, "tenant_id", None):
        raise AuthenticationError(message = "Tenant-scoped tool execution requires authenticated context")
    tenant_id = str(ctx.tenant_id)

    now = datetime.now(UTC).isoformat()

    # Ensure evidence items have IDs
    for item in evidence:
        if not item.get("id"):
            item["id"] = str(uuid.uuid4())

    payload: dict[str, Any] = {
        "account_id": account_id,
        "type": signal_type,
        "content": content,
        "confidence": confidence,
        "evidence": evidence,
        "provenance": {
            "extractor": "ai",
            "method": provenance_method,
            "model": provenance_model,
            "run_id": run_id,
            "source_system": "layer4_agents",
            "extracted_at": now,
        },
        "source_refs": source_refs or [],
    }
    if impact_area:
        payload["impact_area"] = impact_area
    if estimated_value is not None:
        payload["estimated_value"] = estimated_value

    outcome = AuditOutcome.FAILURE
    reason = "error"
    signal_id = None

    try:
        req_id = getattr(ctx, "request_id", None) or getattr(ctx, "trace_id", None)
        response = await _get_http_client().post(
            f"{_SIGNAL_REFINERY_BASE_URL}/api/v1/signals",
            json=payload,
            headers=_signal_headers(tenant_id, request_id=req_id, correlation_id=run_id),
        )
        if response.status_code in (200, 201):
            created = response.json()
            signal_id = created.get("id")
            outcome = AuditOutcome.SUCCESS
            reason = "ok"
            return created
        logger.warning(
            "create_signal returned %s for account=%s tenant=%s",
            response.status_code, account_id, tenant_id,
        )
        return None
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "create_signal failed for account=%s tenant=%s", account_id, tenant_id
        )
        return None
    finally:
        emit_audit_event(
            action=AuditAction.KG_NODE_UPDATED,
            outcome=outcome,
            resource_type="value_signal",
            resource_id=signal_id or account_id,
            tenant_id=ctx.tenant_id,
            details={
                "operation": "create_signal",
                "account_id": account_id,
                "signal_type": signal_type,
                "reason": reason,
            },
        )


async def get_signals_for_business_case(
    account_id: str,
    context: RequestContext | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Retrieve signals grouped by impact area for business case generation.

    Returns a dict keyed by impact_area with lists of promoted/validated signals.
    L4 business case workflows use this to populate ROI assumptions.
    """
    ctx = _require_tool_context(context)
    all_signals = await get_account_signals(
        account_id,
        lifecycle_states=["validated", "promoted"],
        min_confidence=0.4,
        limit=200,
        context=ctx,
    )

    grouped: dict[str, list[dict[str, Any]]] = {
        "revenue": [],
        "cost": [],
        "risk": [],
        "strategic": [],
        "unclassified": [],
    }
    for signal in all_signals:
        area = signal.get("impact_area") or "unclassified"
        if area in grouped:
            grouped[area].append(signal)
        else:
            grouped["unclassified"].append(signal)

    return grouped


async def get_renewal_risk_signals(
    account_id: str,
    context: RequestContext | None = None,
) -> list[dict[str, Any]]:
    """Retrieve risk and renewal signals for renewal risk scoring.

    L4 renewal risk workflows use this to assess churn probability.
    """
    ctx = _require_tool_context(context)
    return await get_account_signals(
        account_id,
        signal_types=["risk", "renewal"],
        lifecycle_states=["validated", "promoted"],
        min_confidence=0.3,
        limit=100,
        context=ctx,
    )


async def get_expansion_signals(
    account_id: str,
    context: RequestContext | None = None,
) -> list[dict[str, Any]]:
    """Retrieve expansion and opportunity signals for expansion recommendations.

    L4 expansion workflows use this to identify upsell/cross-sell opportunities.
    """
    ctx = _require_tool_context(context)
    return await get_account_signals(
        account_id,
        signal_types=["expansion", "opportunity", "revenue_uplift"],
        lifecycle_states=["validated", "promoted"],
        min_confidence=0.4,
        limit=100,
        context=ctx,
    )
