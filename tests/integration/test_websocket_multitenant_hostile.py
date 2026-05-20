"""Hostile multi-tenant WebSocket test suite (TEST-SEC-005).

Regression protection for SEC-L4-WS-001 and SEC-L4-WS-002.

Covers:
- Workflow WebSocket: cross-tenant BOLA/IDOR via workflow_id
- Signals WebSocket: cross-tenant access via prospect_id
- Auth transport: query-param token rejection on both endpoints
- Fail-closed behaviour: missing/invalid/expired tokens

These tests use unit-level mocking so they run in CI without live
infrastructure. The intent is to lock the security contracts in place so
any future regression is caught immediately.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest

# ---------------------------------------------------------------------------
# Constants — deterministic tenant / user identifiers
# ---------------------------------------------------------------------------

TENANT_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
USER_A_ID = "user-alpha-001"
USER_B_ID = "user-bravo-002"

WORKFLOW_A = "wf-tenant-a-001"
WORKFLOW_B = "wf-tenant-b-002"
PROSPECT_A = "prospect-tenant-a-001"
PROSPECT_B = "prospect-tenant-b-002"

TEST_JWT_SECRET = "test-secret-key"
TEST_JWT_ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token(
    tenant_id: str,
    user_id: str = USER_A_ID,
    expires_in: int = 3600,
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "sub": user_id,
        "iat": now,
        "exp": now + expires_in,
    }
    if extra:
        payload.update(extra)
    return pyjwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)


def _make_websocket(
    *,
    protocol_header: str | None = None,
    query_token: str | None = None,
) -> MagicMock:
    """Build a minimal WebSocket mock matching FastAPI's interface."""
    ws = MagicMock()
    ws.close = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock(side_effect=Exception("disconnect"))

    headers: dict[str, str] = {}
    if protocol_header is not None:
        headers["sec-websocket-protocol"] = protocol_header
    ws.headers = headers

    params: dict[str, str] = {}
    if query_token is not None:
        params["token"] = query_token
    ws.query_params = params

    return ws


# ---------------------------------------------------------------------------
# Workflow WebSocket — SEC-L4-WS-001
# ---------------------------------------------------------------------------

class TestWorkflowWebSocketOwnership:
    """Workflow WebSocket must verify workflow ownership before accepting."""

    @pytest.mark.asyncio
    async def test_tenant_a_can_connect_to_own_workflow(self):
        """POSITIVE: Tenant A connects to a workflow they own.

        The WebSocket loop exits when the client disconnects (WebSocketDisconnect).
        We verify the connection was accepted and not closed with an error code.
        """
        from fastapi import WebSocketDisconnect
        from value_fabric.layer4.api.websocket.routes import workflow_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(protocol_header=f"token,{token_a}")
        # Simulate immediate client disconnect so the loop exits cleanly
        ws.receive_json = AsyncMock(side_effect=WebSocketDisconnect())

        with patch(
            "value_fabric.layer4.api.websocket.routes.decode_jwt",
            return_value={"tenant_id": TENANT_A_ID, "sub": USER_A_ID},
        ):
            with patch(
                "value_fabric.layer4.api.websocket.routes._verify_workflow_ownership",
                new=AsyncMock(return_value=True),
            ):
                with patch(
                    "value_fabric.layer4.api.websocket.routes.get_ws_manager"
                ) as mock_mgr:
                    mock_mgr.return_value.connect = AsyncMock()
                    mock_mgr.return_value.disconnect = AsyncMock()
                    mock_mgr.return_value.handle_client_message = AsyncMock()

                    await workflow_websocket(
                        websocket=ws,
                        workflow_id=WORKFLOW_A,
                        last_event_id=None,
                        token=None,
                    )

        # Connection was accepted (ws_manager.connect was called)
        mock_mgr.return_value.connect.assert_awaited_once()
        assert mock_mgr.return_value.connect.await_args.kwargs["correlation_id"]
        # No error close was issued
        for call in ws.close.call_args_list:
            code = call.kwargs.get("code") or (call.args[0] if call.args else None)
            assert code not in (1008, 1011), (
                f"Tenant A should not be denied their own workflow, got close code {code}"
            )

    @pytest.mark.asyncio
    async def test_tenant_a_denied_tenant_b_workflow(self):
        """NEGATIVE (BOLA): Tenant A cannot subscribe to Tenant B's workflow.

        This is the primary regression test for SEC-L4-WS-001.
        A valid JWT from Tenant A must not grant access to Tenant B's stream.
        """
        from value_fabric.layer4.api.websocket.routes import workflow_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(protocol_header=f"token,{token_a}")

        # Ownership check returns False — workflow belongs to Tenant B
        with patch(
            "value_fabric.layer4.api.websocket.routes._verify_workflow_ownership",
            new=AsyncMock(return_value=False),
        ):
            await workflow_websocket(
                websocket=ws,
                workflow_id=WORKFLOW_B,
                last_event_id=None,
                token=None,
            )

        ws.close.assert_awaited_once()
        close_code = ws.close.call_args.kwargs.get("code") or ws.close.call_args.args[0]
        assert close_code == 1008, (
            f"Cross-tenant workflow access must be closed with 1008, got {close_code}. "
            "SEC-L4-WS-001 regression."
        )
        # Connection must never have been accepted
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_nonexistent_workflow_denied(self):
        """NEGATIVE: Workflow not found must be denied (prevents enumeration)."""
        from value_fabric.layer4.api.websocket.routes import workflow_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(protocol_header=f"token,{token_a}")

        with patch(
            "value_fabric.layer4.api.websocket.routes._verify_workflow_ownership",
            new=AsyncMock(return_value=False),
        ):
            await workflow_websocket(
                websocket=ws,
                workflow_id="wf-does-not-exist",
                last_event_id=None,
                token=None,
            )

        ws.close.assert_awaited_once()
        close_code = ws.close.call_args.kwargs.get("code") or ws.close.call_args.args[0]
        assert close_code == 1008
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_ownership_check_uses_authenticated_tenant_not_path(self):
        """INVARIANT: Ownership check receives tenant from JWT, not from the URL path.

        Ensures an attacker cannot bypass the check by crafting a workflow_id
        that embeds a different tenant identifier.
        """
        captured: dict[str, str] = {}

        async def _capture(workflow_id: str, tenant_id: str) -> bool:
            captured["workflow_id"] = workflow_id
            captured["tenant_id"] = tenant_id
            return False  # deny — we only care about what was passed

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(protocol_header=f"token,{token_a}")

        with patch(
            "value_fabric.layer4.api.websocket.routes.decode_jwt",
            return_value={"tenant_id": TENANT_A_ID, "sub": USER_A_ID},
        ):
            with patch(
                "value_fabric.layer4.api.websocket.routes._verify_workflow_ownership",
                new=_capture,
            ):
                from value_fabric.layer4.api.websocket.routes import workflow_websocket
                await workflow_websocket(
                    websocket=ws,
                    workflow_id=WORKFLOW_B,
                    last_event_id=None,
                    token=None,
                )

        assert captured.get("tenant_id") == TENANT_A_ID, (
            "Ownership check must receive tenant_id from the JWT, not from the URL. "
            f"Got: {captured.get('tenant_id')!r}"
        )
        assert captured.get("workflow_id") == WORKFLOW_B


class TestWorkflowWebSocketOwnershipUnit:
    """Unit tests for _verify_workflow_ownership directly.

    _verify_workflow_ownership imports get_executor locally from
    value_fabric.layer4.api.routes.workflows, so we patch it there.
    """

    @pytest.mark.asyncio
    async def test_returns_true_when_tenant_matches(self):
        from value_fabric.layer4.api.websocket.routes import _verify_workflow_ownership

        mock_executor = AsyncMock()
        mock_executor.get_workflow_status.return_value = {
            "tenant_id": TENANT_A_ID,
            "workflow_id": WORKFLOW_A,
        }

        with patch(
            "value_fabric.layer4.api.routes.workflows.get_executor",
            return_value=mock_executor,
        ):
            result = await _verify_workflow_ownership(WORKFLOW_A, TENANT_A_ID)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_tenant_mismatches(self):
        from value_fabric.layer4.api.websocket.routes import _verify_workflow_ownership

        mock_executor = AsyncMock()
        mock_executor.get_workflow_status.return_value = {
            "tenant_id": TENANT_B_ID,
            "workflow_id": WORKFLOW_B,
        }

        with patch(
            "value_fabric.layer4.api.routes.workflows.get_executor",
            return_value=mock_executor,
        ):
            result = await _verify_workflow_ownership(WORKFLOW_B, TENANT_A_ID)

        assert result is False, "Tenant A must not own Tenant B's workflow"

    @pytest.mark.asyncio
    async def test_returns_false_when_workflow_not_found(self):
        from value_fabric.layer4.api.websocket.routes import _verify_workflow_ownership

        mock_executor = AsyncMock()
        mock_executor.get_workflow_status.return_value = None

        with patch(
            "value_fabric.layer4.api.routes.workflows.get_executor",
            return_value=mock_executor,
        ):
            result = await _verify_workflow_ownership("wf-ghost", TENANT_A_ID)

        assert result is False, "Missing workflow must deny to prevent enumeration"

    @pytest.mark.asyncio
    async def test_returns_false_when_workflow_has_no_tenant(self):
        from value_fabric.layer4.api.websocket.routes import _verify_workflow_ownership

        mock_executor = AsyncMock()
        mock_executor.get_workflow_status.return_value = {
            "workflow_id": WORKFLOW_A,
            # tenant_id absent — should deny
        }

        with patch(
            "value_fabric.layer4.api.routes.workflows.get_executor",
            return_value=mock_executor,
        ):
            result = await _verify_workflow_ownership(WORKFLOW_A, TENANT_A_ID)

        assert result is False, "Workflow with no tenant_id must deny"

    @pytest.mark.asyncio
    async def test_returns_false_on_executor_exception(self):
        """Fail-closed: any unexpected error must deny the connection."""
        from value_fabric.layer4.api.websocket.routes import _verify_workflow_ownership

        mock_executor = AsyncMock()
        mock_executor.get_workflow_status.side_effect = RuntimeError("db unavailable")

        with patch(
            "value_fabric.layer4.api.routes.workflows.get_executor",
            return_value=mock_executor,
        ):
            result = await _verify_workflow_ownership(WORKFLOW_A, TENANT_A_ID)

        assert result is False, "Executor failure must fail closed"


# ---------------------------------------------------------------------------
# Workflow WebSocket — Auth transport (regression for P1-13)
# ---------------------------------------------------------------------------

class TestWorkflowWebSocketAuthTransport:
    """Auth transport security for the workflow WebSocket."""

    @pytest.mark.asyncio
    async def test_query_param_token_rejected(self):
        """REGRESSION P1-13: Token in query param must be rejected."""
        from value_fabric.layer4.api.websocket.routes import workflow_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(query_token=token_a)

        await workflow_websocket(
            websocket=ws,
            workflow_id=WORKFLOW_A,
            last_event_id=None,
            token=token_a,
        )

        ws.close.assert_awaited_once()
        close_code = ws.close.call_args.kwargs.get("code") or ws.close.call_args.args[0]
        assert close_code == 1008, "Query-param token must be rejected with 1008"
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self):
        """NEGATIVE: No token at all must be rejected."""
        from value_fabric.layer4.api.websocket.routes import workflow_websocket

        ws = _make_websocket()  # no token anywhere

        await workflow_websocket(
            websocket=ws,
            workflow_id=WORKFLOW_A,
            last_event_id=None,
            token=None,
        )

        ws.close.assert_awaited_once()
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self):
        """NEGATIVE: Expired JWT must be rejected before ownership check."""
        from value_fabric.layer4.api.websocket.routes import workflow_websocket

        expired = _make_token(TENANT_A_ID, USER_A_ID, expires_in=-3600)
        ws = _make_websocket(protocol_header=f"token,{expired}")

        with patch(
            "value_fabric.layer4.api.websocket.routes._verify_workflow_ownership",
            new=AsyncMock(return_value=True),
        ):
            await workflow_websocket(
                websocket=ws,
                workflow_id=WORKFLOW_A,
                last_event_id=None,
                token=None,
            )

        ws.close.assert_awaited_once()
        ws.accept.assert_not_called()


# ---------------------------------------------------------------------------
# Signals WebSocket — SEC-L4-WS-002
# ---------------------------------------------------------------------------

class TestSignalsWebSocketOwnership:
    """Signals WebSocket must verify prospect ownership before accepting."""

    @pytest.mark.asyncio
    async def test_tenant_a_can_stream_own_prospect(self):
        """POSITIVE: Tenant A can stream signals for their own prospect."""
        from fastapi import WebSocketDisconnect
        from value_fabric.layer4.api.routes.signals import signal_stream_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(protocol_header=f"token,{token_a}")
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        with patch(
            "value_fabric.layer4.api.routes.signals.decode_jwt",
            return_value={"tenant_id": TENANT_A_ID, "sub": USER_A_ID},
        ):
            with patch(
                "value_fabric.layer4.api.routes.signals.Layer3Client"
            ) as mock_l3_cls:
                mock_l3 = AsyncMock()
                mock_l3.get_entity = AsyncMock(return_value={"id": PROSPECT_A})
                mock_l3_cls.return_value.__aenter__ = AsyncMock(return_value=mock_l3)
                mock_l3_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                await signal_stream_websocket(websocket=ws, prospect_id=PROSPECT_A)

        # Connection was accepted (not closed with error before accept)
        ws.accept.assert_awaited_once()
        connected_event = ws.send_json.await_args_list[0].args[0]
        assert connected_event["event_type"] == "connected"
        assert connected_event.get("correlation_id")

    @pytest.mark.asyncio
    async def test_tenant_a_denied_tenant_b_prospect(self):
        """NEGATIVE (BOLA): Tenant A cannot stream Tenant B's prospect signals.

        This is the primary regression test for SEC-L4-WS-002.
        """
        from value_fabric.layer4.api.routes.signals import signal_stream_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(protocol_header=f"token,{token_a}")

        with patch(
            "value_fabric.layer4.api.routes.signals.decode_jwt",
            return_value={"tenant_id": TENANT_A_ID, "sub": USER_A_ID},
        ):
            with patch(
                "value_fabric.layer4.api.routes.signals.Layer3Client"
            ) as mock_l3_cls:
                # Layer 3 returns None — prospect not found for this tenant
                mock_l3 = AsyncMock()
                mock_l3.get_entity = AsyncMock(return_value=None)
                mock_l3_cls.return_value.__aenter__ = AsyncMock(return_value=mock_l3)
                mock_l3_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                await signal_stream_websocket(websocket=ws, prospect_id=PROSPECT_B)

        ws.close.assert_awaited_once()
        close_code = ws.close.call_args.kwargs.get("code") or ws.close.call_args.args[0]
        assert close_code == 1008, (
            f"Cross-tenant prospect access must be closed with 1008, got {close_code}. "
            "SEC-L4-WS-002 regression."
        )
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_nonexistent_prospect_denied(self):
        """NEGATIVE: Prospect not found must be denied (prevents enumeration)."""
        from value_fabric.layer4.api.routes.signals import signal_stream_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(protocol_header=f"token,{token_a}")

        with patch(
            "value_fabric.layer4.api.routes.signals.decode_jwt",
            return_value={"tenant_id": TENANT_A_ID, "sub": USER_A_ID},
        ):
            with patch(
                "value_fabric.layer4.api.routes.signals.Layer3Client"
            ) as mock_l3_cls:
                mock_l3 = AsyncMock()
                mock_l3.get_entity = AsyncMock(return_value=None)
                mock_l3_cls.return_value.__aenter__ = AsyncMock(return_value=mock_l3)
                mock_l3_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                await signal_stream_websocket(websocket=ws, prospect_id="prospect-ghost")

        ws.close.assert_awaited_once()
        close_code = ws.close.call_args.kwargs.get("code") or ws.close.call_args.args[0]
        assert close_code == 1008
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_layer3_exception_fails_closed(self):
        """NEGATIVE: Layer 3 unavailability must deny the connection (fail-closed)."""
        from value_fabric.layer4.api.routes.signals import signal_stream_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(protocol_header=f"token,{token_a}")

        with patch(
            "value_fabric.layer4.api.routes.signals.decode_jwt",
            return_value={"tenant_id": TENANT_A_ID, "sub": USER_A_ID},
        ):
            with patch(
                "value_fabric.layer4.api.routes.signals.Layer3Client"
            ) as mock_l3_cls:
                mock_l3_cls.return_value.__aenter__ = AsyncMock(
                    side_effect=RuntimeError("layer3 unreachable")
                )
                mock_l3_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                await signal_stream_websocket(websocket=ws, prospect_id=PROSPECT_A)

        ws.close.assert_awaited_once()
        close_code = ws.close.call_args.kwargs.get("code") or ws.close.call_args.args[0]
        assert close_code == 1008, "Layer 3 failure must fail closed with 1008"
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_ownership_check_uses_jwt_tenant_not_path(self):
        """INVARIANT: Layer 3 lookup uses tenant from JWT, not from the URL path."""
        from value_fabric.layer4.api.routes.signals import signal_stream_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(protocol_header=f"token,{token_a}")

        captured_tenant: list[str] = []

        async def _capture_get_entity(entity_id: str, tenant_id: str | None = None) -> None:
            if tenant_id:
                captured_tenant.append(tenant_id)
            return None  # deny — we only care about what was passed

        with patch(
            "value_fabric.layer4.api.routes.signals.decode_jwt",
            return_value={"tenant_id": TENANT_A_ID, "sub": USER_A_ID},
        ):
            with patch(
                "value_fabric.layer4.api.routes.signals.Layer3Client"
            ) as mock_l3_cls:
                mock_l3 = AsyncMock()
                mock_l3.get_entity = _capture_get_entity
                mock_l3_cls.return_value.__aenter__ = AsyncMock(return_value=mock_l3)
                mock_l3_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                await signal_stream_websocket(websocket=ws, prospect_id=PROSPECT_B)

        assert captured_tenant, "get_entity must be called with a tenant_id"
        assert captured_tenant[0] == TENANT_A_ID, (
            "Ownership check must use tenant_id from JWT, not from the URL. "
            f"Got: {captured_tenant[0]!r}"
        )


class TestSignalsWebSocketAuthTransport:
    """Auth transport security for the signals WebSocket."""

    @pytest.mark.asyncio
    async def test_query_param_token_rejected(self):
        """REGRESSION: Token in query param must be rejected on signals endpoint."""
        from value_fabric.layer4.api.routes.signals import signal_stream_websocket

        token_a = _make_token(TENANT_A_ID, USER_A_ID)
        ws = _make_websocket(query_token=token_a)

        await signal_stream_websocket(websocket=ws, prospect_id=PROSPECT_A)

        ws.close.assert_awaited_once()
        close_code = ws.close.call_args.kwargs.get("code") or ws.close.call_args.args[0]
        assert close_code == 1008, "Query-param token must be rejected with 1008"
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self):
        """NEGATIVE: No token must be rejected."""
        from value_fabric.layer4.api.routes.signals import signal_stream_websocket

        ws = _make_websocket()

        await signal_stream_websocket(websocket=ws, prospect_id=PROSPECT_A)

        ws.close.assert_awaited_once()
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_jwt_rejected(self):
        """NEGATIVE: Malformed JWT must be rejected before ownership check."""
        from value_fabric.layer4.api.routes.signals import signal_stream_websocket

        ws = _make_websocket(protocol_header="token,not.a.valid.jwt")

        with patch(
            "value_fabric.layer4.api.routes.signals.decode_jwt",
            side_effect=Exception("decode error"),
        ):
            await signal_stream_websocket(websocket=ws, prospect_id=PROSPECT_A)

        ws.close.assert_awaited_once()
        ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_token_without_tenant_claim_rejected(self):
        """NEGATIVE: JWT with no tenant_id claim must be rejected."""
        from value_fabric.layer4.api.routes.signals import signal_stream_websocket

        ws = _make_websocket(protocol_header="token,some.jwt.value")

        with patch(
            "value_fabric.layer4.api.routes.signals.decode_jwt",
            return_value={"sub": USER_A_ID},  # no tenant_id
        ):
            await signal_stream_websocket(websocket=ws, prospect_id=PROSPECT_A)

        ws.close.assert_awaited_once()
        ws.accept.assert_not_called()


# ---------------------------------------------------------------------------
# Cross-endpoint matrix: both endpoints enforce the same security contract
# ---------------------------------------------------------------------------

class TestCrossTenantMatrix:
    """Matrix asserting both WebSocket endpoints share the same security posture."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,workflow_or_prospect", [
        ("workflow", WORKFLOW_B),
        ("signals", PROSPECT_B),
    ])
    async def test_tenant_a_token_denied_tenant_b_resource(
        self, endpoint: str, workflow_or_prospect: str
    ):
        """NEGATIVE: Tenant A's valid JWT must not grant access to Tenant B's resources
        on either WebSocket endpoint.
        """
        token_a = _make_token(TENANT_A_ID, USER_A_ID)

        if endpoint == "workflow":
            from value_fabric.layer4.api.websocket.routes import workflow_websocket
            ws = _make_websocket(protocol_header=f"token,{token_a}")

            with patch(
                "value_fabric.layer4.api.websocket.routes._verify_workflow_ownership",
                new=AsyncMock(return_value=False),
            ):
                await workflow_websocket(
                    websocket=ws,
                    workflow_id=workflow_or_prospect,
                    last_event_id=None,
                    token=None,
                )
        else:
            from value_fabric.layer4.api.routes.signals import signal_stream_websocket
            ws = _make_websocket(protocol_header=f"token,{token_a}")

            with patch(
                "value_fabric.layer4.api.routes.signals.decode_jwt",
                return_value={"tenant_id": TENANT_A_ID, "sub": USER_A_ID},
            ):
                with patch(
                    "value_fabric.layer4.api.routes.signals.Layer3Client"
                ) as mock_l3_cls:
                    mock_l3 = AsyncMock()
                    mock_l3.get_entity = AsyncMock(return_value=None)
                    mock_l3_cls.return_value.__aenter__ = AsyncMock(return_value=mock_l3)
                    mock_l3_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                    await signal_stream_websocket(
                        websocket=ws, prospect_id=workflow_or_prospect
                    )

        ws.close.assert_awaited_once()
        close_code = ws.close.call_args.kwargs.get("code") or ws.close.call_args.args[0]
        assert close_code == 1008, (
            f"[{endpoint}] Cross-tenant access must be denied with 1008, got {close_code}"
        )
        ws.accept.assert_not_called()
