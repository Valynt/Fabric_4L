"""Regression tests for P1-13: WebSocket JWT authentication.

These tests verify that JWT tokens in query parameters are rejected
and tokens must be passed via Sec-WebSocket-Protocol header.
"""

import pytest
from fastapi import WebSocketDisconnect
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch


class TestWebSocketJWTAuth:
    """Test WebSocket JWT authentication security."""

    @pytest.mark.asyncio
    async def test_token_in_query_param_is_rejected(self):
        """JWT in query parameter must be rejected with 1008 code."""
        from src.api.websocket.routes import (
            workflow_websocket,
        )

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.query_params = {"token": "malicious-jwt-token"}
        mock_ws.headers = {}  # No Sec-WebSocket-Protocol header

        await workflow_websocket(
            websocket=mock_ws,
            workflow_id="wf-test-123",
            last_event_id=None,
            token="malicious-jwt-token",
        )

        # Should close with 1008
        mock_ws.close.assert_called_once()
        call_args = mock_ws.close.call_args
        assert call_args.kwargs.get("code") == 1008
        assert "query param" in call_args.kwargs.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_token_in_header_is_accepted(self):
        """JWT in Sec-WebSocket-Protocol header should be accepted."""
        from src.api.websocket.routes import (
            workflow_websocket,
        )

        mock_ws = AsyncMock()
        mock_ws.query_params = {}  # No token in query
        mock_ws.headers = {"sec-websocket-protocol": "token,valid-jwt"}
        mock_ws.receive_json.side_effect = WebSocketDisconnect
        tenant_id = str(uuid4())
        user_id = str(uuid4())

        with patch(
            "src.api.websocket.routes.get_ws_manager"
        ) as mock_manager, patch(
            "src.api.websocket.routes.decode_jwt",
            return_value={"tenant_id": tenant_id, "sub": user_id},
        ):
            mock_manager.return_value.connect = AsyncMock()
            mock_manager.return_value.disconnect = AsyncMock()

            await workflow_websocket(
                websocket=mock_ws,
                workflow_id="wf-test-123",
                last_event_id=None,
                token=None,
            )

            # Should NOT close
            mock_ws.close.assert_not_called()

    def test_extract_tenant_from_token_parses_protocol_header(self):
        """Token extraction should handle Sec-WebSocket-Protocol format."""
        from src.api.websocket.routes import (
            _extract_tenant_from_token,
            WebSocketAuthError,
        )

        with pytest.raises(WebSocketAuthError):
            _extract_tenant_from_token(None)
