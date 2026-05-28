from __future__ import annotations

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


import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from value_fabric.shared.error_handling import sanitize_log_error
from value_fabric.shared.observability.trace_context import resolve_trace_context

from .auth import (
    WebSocketAuthError,
    decode_ws_token,
    extract_token_from_protocol_header,
)
from .manager import get_ws_manager

logger = logging.getLogger(__name__)
websocket_router = APIRouter()


async def _resolve_workflow_authorization(
    workflow_id: str, tenant_id: str, user_id: str | None
) -> tuple[bool, str]:
    """Verify workflow ownership against workflow status metadata source.

    Queries the executor's in-memory + persisted metadata. Returns True when
    the workflow exists and its tenant matches. Returns False when the workflow
    is not found (treat as denied to avoid enumeration). Raises on unexpected
    errors so the caller can fail closed.

    Args:
        workflow_id: Workflow instance ID from the WebSocket path.
        tenant_id: Tenant extracted from the authenticated JWT.

    Returns:
        Tuple of (is_authorized, auth_code). User-level authorization is
        conditional: only when both status.user_id and authenticated user_id are
        present must they match; if either side is missing, validation remains
        tenant-only.
    """
    try:
        # Local import — avoids circular dependency at module load time.
        from ...api.routes.workflows import get_executor

        executor = get_executor()
        status = await executor.get_workflow_status(workflow_id)
        if not status:
            return False, "AUTHZ_WORKFLOW_NOT_FOUND"
        workflow_tenant = status.get("tenant_id")
        if not workflow_tenant:
            return False, "AUTHZ_WORKFLOW_TENANT_MISSING"
        if str(workflow_tenant) != str(tenant_id):
            return False, "AUTHZ_WORKFLOW_TENANT_MISMATCH"

        workflow_user_id = status.get("user_id")
        if workflow_user_id and user_id and str(workflow_user_id) != str(user_id):
            return False, "AUTHZ_WORKFLOW_USER_MISMATCH"
        return True, "AUTHZ_OK"
    except Exception:
        logger.exception("Workflow ownership check raised unexpectedly")
        return False, "AUTHZ_WORKFLOW_LOOKUP_ERROR"


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
    connection_trace_id = trace_ctx.trace_id or str(uuid.uuid4())
    trace_id = connection_trace_id
    correlation_id = connection_trace_id
    _log: dict = {
        "workflow_id": workflow_id,
        "trace_id": trace_id,
        "correlation_id": correlation_id,
        "request_id": trace_id,
    }

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
        import json
        await websocket.close(code=1008, reason=json.dumps({"code": exc.code}))
        return

    # Bind tenant context to the log dict now that we have it.
    _log["tenant_id"] = tenant_id

    # SEC-L4-WS-001: Verify the requested workflow belongs to the authenticated tenant.
    authorized, auth_code = await _resolve_workflow_authorization(
        workflow_id, tenant_id, user_id
    )
    if not authorized:
        logger.warning(
            "WebSocket workflow authorization failed",
            extra={**_log, "auth_code": auth_code},
        )
        await websocket.close(code=1008, reason=f'{{"code":"{auth_code}"}}')
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
            trace_id=connection_trace_id,
            correlation_id=correlation_id,
            x_request_id=connection_trace_id,
            request_id=connection_trace_id,
        )

        while True:
            try:
                message = await websocket.receive_json()
                await ws_manager.handle_client_message(
                    websocket, workflow_id, message, trace_id=connection_trace_id
                )
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected", extra=_log)
                break
            except Exception as exc:
                logger.warning(
                    "WebSocket client message error",
                    extra={**_log, "error_code": "WEBSOCKET_MESSAGE_ERROR", "error": sanitize_log_error(exc)},
                )
                # Continue rather than break to keep connection alive

    except Exception as exc:
        logger.error("WebSocket session error", extra={**_log, "error_code": "WEBSOCKET_SESSION_ERROR", "error": sanitize_log_error(exc)})
    finally:
        logger.info("WebSocket workflow session ended", extra=_log)
        await ws_manager.disconnect(websocket, workflow_id, trace_id=connection_trace_id)
