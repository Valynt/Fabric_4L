"""WebSocket routes for real-time workflow streaming.

Provides a WebSocket endpoint for subscribing to workflow events with
automatic reconnection support and event replay.

Authentication transport (SEC-L3-012 — Sprint 3 cutover):
    The ONLY accepted authentication vector is the Sec-WebSocket-Protocol
    header in canonical bearer format:
        Sec-WebSocket-Protocol: base64url.bearer.authorization, <jwt>

    Query-parameter authentication (?token=) has been removed. Any connection
    that omits or malforms the header is rejected immediately with close
    code 1008 (Policy Violation).

Reconnection:
    Pass ``last_event_id`` query parameter to replay missed events.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from value_fabric.shared.observability.trace_context import resolve_trace_context

from .auth import (
    WebSocketAuthError,
    decode_ws_token,
    extract_token_from_protocol_header,
)
from .manager import get_ws_manager

logger = logging.getLogger(__name__)
websocket_router = APIRouter()


async def _verify_workflow_ownership(workflow_id: str, tenant_id: str) -> bool:
    """Verify that a workflow belongs to the given tenant.

    Queries the executor's in-memory + persisted metadata. Returns True when
    the workflow exists and its tenant matches. Returns False when the workflow
    is not found (treat as denied to avoid enumeration). Raises on unexpected
    errors so the caller can fail closed.

    Args:
        workflow_id: Workflow instance ID from the WebSocket path.
        tenant_id: Tenant extracted from the authenticated JWT.

    Returns:
        True if the workflow is owned by the tenant, False otherwise.
    """
    try:
        # Local import — avoids circular dependency at module load time.
        from ...api.routes.workflows import get_executor

        executor = get_executor()
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            logger.warning(
                "Workflow ownership check: workflow not found",
                extra={"workflow_id": workflow_id, "tenant_id": tenant_id},
            )
            return False
        workflow_tenant = status.get("tenant_id")
        if not workflow_tenant:
            logger.warning(
                "Workflow ownership check: workflow has no tenant_id",
                extra={"workflow_id": workflow_id},
            )
            return False
        return str(workflow_tenant) == str(tenant_id)
    except Exception:
        logger.exception(
            "Workflow ownership check raised unexpectedly — denying connection",
            extra={"workflow_id": workflow_id},
        )
        return False


@websocket_router.websocket("/ws/workflows/{workflow_id}")
async def workflow_websocket(
    websocket: WebSocket,
    workflow_id: str,
    last_event_id: str | None = Query(
        None, description="Last seen event ID for replay on reconnect"
    ),
) -> None:
    """WebSocket endpoint for real-time workflow streaming.

    **Authentication**

    Pass the JWT bearer token via the ``Sec-WebSocket-Protocol`` header:

    ```
    Sec-WebSocket-Protocol: base64url.bearer.authorization, <jwt>
    ```

    Connections that omit the header are rejected immediately with close
    code 1008. Query-parameter auth was removed in SEC-L3-012.

    **Event Types**
    - `connection_established`: Initial confirmation with replay count
    - `state_update`: Workflow status, progress, current node
    - `node_transition`: Node-to-node transition
    - `pause_point`: Human-in-the-loop pause with required actions
    - `workflow_complete`: Final completion/failure event
    - `ping`: Server heartbeat (respond with `pong`)

    **Client Messages**
    ```json
    {"type": "ack",               "event_id": "evt-123"}
    {"type": "pong"}
    {"type": "subscribe_history"}
    ```

    **Reconnection**
    Store the last `event_id` received. On reconnect pass it as
    `last_event_id` to receive all missed events.
    """
    # OBS-L4-004: Resolve correlation ID at the HTTP upgrade stage.
    trace_ctx = resolve_trace_context(websocket.headers)
    correlation_id = trace_ctx.trace_id
    _log: dict = {"workflow_id": workflow_id, "correlation_id": correlation_id}

    # --- Token extraction (canonical header only — SEC-L3-012) ---------------
    protocol_header = websocket.headers.get("sec-websocket-protocol", "")
    ws_token = extract_token_from_protocol_header(protocol_header)

    # --- Authentication (fail-closed) ----------------------------------------
    try:
        tenant_id, user_id = decode_ws_token(ws_token)
    except WebSocketAuthError as exc:
        logger.warning(
            "WebSocket authentication failed: %s",
            exc.code,
            extra={"auth_code": exc.code, **_log},
        )
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Bind tenant context to the log dict now that we have it.
    _log["tenant_id"] = tenant_id

    # SEC-L4-WS-001: Verify the requested workflow belongs to the authenticated tenant.
    owned = await _verify_workflow_ownership(workflow_id, tenant_id)
    if not owned:
        logger.warning("WebSocket workflow ownership check failed", extra=_log)
        await websocket.close(code=1008, reason="Workflow not found or access denied")
        return

    logger.info("WebSocket workflow session started", extra=_log)

    ws_manager = get_ws_manager()

    try:
        await ws_manager.connect(
            websocket,
            workflow_id,
            last_event_id,
            tenant_id=tenant_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        while True:
            try:
                message = await websocket.receive_json()
                await ws_manager.handle_client_message(websocket, workflow_id, message)
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected", extra=_log)
                break
            except Exception as exc:
                logger.warning(
                    "WebSocket client message error",
                    extra={**_log, "error": str(exc)},
                )
                # Continue rather than break to keep connection alive

    except Exception as exc:
        logger.error("WebSocket session error", extra={**_log, "error": str(exc)})
    finally:
        logger.info("WebSocket workflow session ended", extra=_log)
        await ws_manager.disconnect(websocket, workflow_id)
