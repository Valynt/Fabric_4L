"""Security-focused tests for WebSocket authentication (SEC-L3-012 / ARCH-L4-008).

Covers:
- Canonical Sec-WebSocket-Protocol bearer format
- Legacy query-parameter path is absent (SEC-L3-012 removal)
- Fail-closed behaviour on all auth error codes
- Success path: ws_manager.connect receives correct claims
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.websockets import WebSocketDisconnect

from value_fabric.layer4.api.websocket.auth import (
    WebSocketAuthError,
    decode_ws_token,
    extract_token_from_protocol_header,
)
from value_fabric.layer4.api.websocket.routes import workflow_websocket


# ---------------------------------------------------------------------------
# extract_token_from_protocol_header
# ---------------------------------------------------------------------------


def test_canonical_header_extracts_token():
    header = "base64url.bearer.authorization, eyJhbGciOiJSUzI1NiJ9.payload.sig"
    token = extract_token_from_protocol_header(header)
    assert token == "eyJhbGciOiJSUzI1NiJ9.payload.sig"


def test_canonical_header_case_insensitive():
    header = "Base64url.Bearer.Authorization, mytoken"
    token = extract_token_from_protocol_header(header)
    assert token == "mytoken"


def test_canonical_header_missing_returns_none():
    assert extract_token_from_protocol_header("") is None
    assert extract_token_from_protocol_header("some-other-protocol") is None


def test_canonical_header_single_part_returns_none():
    # A bare subprotocol name must not be treated as a token (SEC-L3-012).
    assert extract_token_from_protocol_header("graphql-ws") is None
    assert extract_token_from_protocol_header("token") is None


# ---------------------------------------------------------------------------
# decode_ws_token
# ---------------------------------------------------------------------------


def test_decode_ws_token_missing_raises():
    with pytest.raises(WebSocketAuthError) as exc:
        decode_ws_token(None)
    assert exc.value.code == "AUTH_TOKEN_MISSING"


def test_decode_ws_token_jwt_unavailable_raises(monkeypatch):
    monkeypatch.setattr("value_fabric.layer4.api.websocket.auth._JWT_AVAILABLE", False)
    with pytest.raises(WebSocketAuthError) as exc:
        decode_ws_token("some.token")
    assert exc.value.code == "AUTH_JWT_UNAVAILABLE"


def test_decode_ws_token_maps_decode_exceptions_to_stable_code(monkeypatch):
    monkeypatch.setattr("value_fabric.layer4.api.websocket.auth._JWT_AVAILABLE", True)

    def _boom(_token):
        raise ValueError("sensitive parser message")

    monkeypatch.setattr("value_fabric.layer4.api.websocket.auth.decode_jwt", _boom)

    with pytest.raises(WebSocketAuthError) as exc:
        decode_ws_token("token-value")

    assert exc.value.code == "AUTH_TOKEN_DECODE_FAILED"


def test_decode_ws_token_missing_tenant_claim_raises(monkeypatch):
    monkeypatch.setattr("value_fabric.layer4.api.websocket.auth._JWT_AVAILABLE", True)
    monkeypatch.setattr(
        "value_fabric.layer4.api.websocket.auth.decode_jwt",
        lambda _t: {"sub": "user-1"},
    )
    with pytest.raises(WebSocketAuthError) as exc:
        decode_ws_token("token")
    assert exc.value.code == "AUTH_TENANT_CLAIM_INVALID"


def test_decode_ws_token_missing_user_claim_raises(monkeypatch):
    monkeypatch.setattr("value_fabric.layer4.api.websocket.auth._JWT_AVAILABLE", True)
    monkeypatch.setattr(
        "value_fabric.layer4.api.websocket.auth.decode_jwt",
        lambda _t: {"tenant_id": "tenant-abc"},
    )
    with pytest.raises(WebSocketAuthError) as exc:
        decode_ws_token("token")
    assert exc.value.code == "AUTH_USER_CLAIM_INVALID"


def test_decode_ws_token_success(monkeypatch):
    monkeypatch.setattr("value_fabric.layer4.api.websocket.auth._JWT_AVAILABLE", True)
    monkeypatch.setattr(
        "value_fabric.layer4.api.websocket.auth.decode_jwt",
        lambda _t: {"tenant_id": "tenant-abc", "sub": "user-xyz"},
    )
    tenant_id, user_id = decode_ws_token("valid.token")
    assert tenant_id == "tenant-abc"
    assert user_id == "user-xyz"


# ---------------------------------------------------------------------------
# SEC-L3-012: query-parameter auth is absent from the endpoint signature
# ---------------------------------------------------------------------------


def test_workflow_websocket_has_no_token_query_param():
    """The 'token' query parameter must not exist on workflow_websocket (SEC-L3-012)."""
    sig = inspect.signature(workflow_websocket)
    assert "token" not in sig.parameters, (
        "Legacy 'token' query parameter still present. SEC-L3-012 requires its removal."
    )


def test_workflow_websocket_has_no_auth_query_param():
    """The 'auth' query parameter must not exist on workflow_websocket."""
    sig = inspect.signature(workflow_websocket)
    assert "auth" not in sig.parameters


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_websocket(protocol_header: str = "") -> MagicMock:
    ws = MagicMock()
    headers: dict[str, str] = {}
    if protocol_header:
        headers["sec-websocket-protocol"] = protocol_header
    ws.headers = headers
    ws.close = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# Route-level: rejection paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_route_rejects_missing_token(caplog):
    ws = _make_websocket()
    await workflow_websocket(websocket=ws, workflow_id="wf-1")
    ws.close.assert_awaited_once_with(code=1008, reason="Authentication failed")
    assert "AUTH_TOKEN_MISSING" in caplog.text


@pytest.mark.asyncio
async def test_route_rejects_bare_subprotocol_name(caplog):
    """A bare subprotocol name (no canonical prefix) must be rejected with 1008."""
    ws = _make_websocket("graphql-ws")
    await workflow_websocket(websocket=ws, workflow_id="wf-bare")
    ws.close.assert_awaited_once_with(code=1008, reason="Authentication failed")
    assert "AUTH_TOKEN_MISSING" in caplog.text


@pytest.mark.asyncio
async def test_route_does_not_leak_token_in_logs(caplog):
    """Auth failure logs must not contain the raw token value."""
    import logging

    ws = _make_websocket("base64url.bearer.authorization, super.secret.jwt")

    with caplog.at_level(logging.WARNING):
        with patch(
            "value_fabric.layer4.api.websocket.routes.decode_ws_token",
            side_effect=WebSocketAuthError("AUTH_TOKEN_DECODE_FAILED"),
        ):
            await workflow_websocket(websocket=ws, workflow_id="wf-leak")

    assert "super.secret.jwt" not in caplog.text
    assert "AUTH_TOKEN_DECODE_FAILED" in caplog.text
    ws.close.assert_awaited_once_with(code=1008, reason="Authentication failed")


# ---------------------------------------------------------------------------
# Route-level: success path — ws_manager.connect receives correct claims
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_route_accepts_canonical_header_and_connects_with_correct_claims(
    monkeypatch,
):
    """Valid canonical header → ws_manager.connect called with tenant_id and user_id."""
    monkeypatch.setattr("value_fabric.layer4.api.websocket.auth._JWT_AVAILABLE", True)
    monkeypatch.setattr(
        "value_fabric.layer4.api.websocket.auth.decode_jwt",
        lambda _t: {"tenant_id": "tenant-abc", "sub": "user-xyz"},
    )

    ws = _make_websocket("base64url.bearer.authorization, valid.jwt.token")
    mock_manager = MagicMock()
    mock_manager.connect = AsyncMock()
    mock_manager.disconnect = AsyncMock()
    ws.receive_json = AsyncMock(side_effect=WebSocketDisconnect())

    with patch(
        "value_fabric.layer4.api.websocket.routes.get_ws_manager",
        return_value=mock_manager,
    ), patch(
        "value_fabric.layer4.api.websocket.routes._verify_workflow_ownership",
        return_value=True,
    ):
        await workflow_websocket(
            websocket=ws, workflow_id="wf-success", last_event_id="evt-001"
        )

    ws.close.assert_not_awaited()
    mock_manager.connect.assert_awaited_once()
    call_kwargs = mock_manager.connect.call_args
    assert call_kwargs.kwargs["tenant_id"] == "tenant-abc"
    assert call_kwargs.kwargs["user_id"] == "user-xyz"
    mock_manager.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_route_rejects_when_workflow_not_owned_by_tenant(monkeypatch):
    """Ownership check failure → 1008, connection not established."""
    monkeypatch.setattr("value_fabric.layer4.api.websocket.auth._JWT_AVAILABLE", True)
    monkeypatch.setattr(
        "value_fabric.layer4.api.websocket.auth.decode_jwt",
        lambda _t: {"tenant_id": "tenant-a", "sub": "user-1"},
    )

    ws = _make_websocket("base64url.bearer.authorization, valid.jwt.token")
    mock_manager = MagicMock()
    mock_manager.connect = AsyncMock()

    with patch(
        "value_fabric.layer4.api.websocket.routes.get_ws_manager",
        return_value=mock_manager,
    ), patch(
        "value_fabric.layer4.api.websocket.routes._verify_workflow_ownership",
        return_value=False,
    ):
        await workflow_websocket(websocket=ws, workflow_id="wf-other-tenant")

    ws.close.assert_awaited_once_with(
        code=1008, reason="Workflow not found or access denied"
    )
    mock_manager.connect.assert_not_awaited()
