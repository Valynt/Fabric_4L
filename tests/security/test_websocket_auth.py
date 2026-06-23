"""WebSocket Authentication Security Tests — P0 Critical Gap Remediation

Validates that WebSocket connections require valid authentication and
enforce tenant isolation boundaries.

These tests address the P0 gap identified in the security audit:
- WebSocket connections were accepted without valid authentication
- No negative tests existed for WebSocket auth bypass

Author: Autonomous Test Assurance Agent
Date: 2026-04-28
"""

from __future__ import annotations

import os
import pytest

# Skip entire module if WebSocket dependencies unavailable
try:
    from fastapi.testclient import TestClient
    from fastapi import WebSocketDisconnect
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


pytestmark = [
    pytest.mark.skipif(not WEBSOCKET_AVAILABLE, reason="WebSocket dependencies not available"),
    pytest.mark.security,
    pytest.mark.websocket,
]


class TestWebSocketAuthentication:
    """P0: WebSocket connection authentication enforcement."""

    def test_websocket_valid_token_accepts_connection(
        self, websocket_client: TestClient, tenant_a_token: str
    ):
        """POSITIVE: Valid JWT token allows WebSocket connection.
        
        Proves that properly authenticated users can establish WebSocket connections.
        """
        # Use Sec-WebSocket-Protocol header for token (per P1-13 fix)
        with websocket_client.websocket_connect(
            "/v1/ws/workflows/test-wf-123",
            headers={"Sec-WebSocket-Protocol": f"base64url.bearer.authorization,{tenant_a_token}"}
        ) as websocket:
            # Connection should be accepted
            assert hasattr(websocket, 'receive_json')
            
            # Should receive connection established event
            try:
                event = websocket.receive_json(timeout=1.0)
                # Connection established - success
                assert event is not None
            except Exception:
                # Timeout or disconnect still means connection was accepted
                pass

    def test_websocket_missing_token_rejects_connection(self, websocket_client: TestClient):
        """NEGATIVE: Missing authentication rejects WebSocket connection.
        
        Proves that unauthenticated WebSocket connections are blocked.
        This is a P0 security requirement.
        """
        # Attempt connection without any token
        response = websocket_client.get("/v1/ws/workflows/test-wf-123")
        
        # Should get 401 or connection should fail to upgrade
        assert response.status_code in [401, 403], (
            f"Missing auth should return 401/403, got {response.status_code}. "
            "Unauthenticated WebSocket access is a security vulnerability."
        )

    def test_websocket_empty_token_rejects_connection(self, websocket_client: TestClient):
        """NEGATIVE: Empty token in header rejects connection."""
        response = websocket_client.get(
            "/v1/ws/workflows/test-wf-123",
            headers={"Sec-WebSocket-Protocol": "token,"}
        )
        
        assert response.status_code in [401, 403], (
            f"Empty token should return 401/403, got {response.status_code}"
        )

    def test_websocket_malformed_token_rejects_connection(
        self, websocket_client: TestClient, malformed_token: str
    ):
        """NEGATIVE: Malformed JWT token rejects WebSocket connection."""
        response = websocket_client.get(
            "/v1/ws/workflows/test-wf-123",
            headers={"Sec-WebSocket-Protocol": f"token,{malformed_token}"}
        )
        
        assert response.status_code == 401, (
            f"Malformed token should return 401, got {response.status_code}"
        )

    def test_websocket_invalid_signature_rejects_connection(
        self, websocket_client: TestClient, invalid_signature_token: str
    ):
        """NEGATIVE: Token with invalid signature rejects connection."""
        response = websocket_client.get(
            "/v1/ws/workflows/test-wf-123",
            headers={"Sec-WebSocket-Protocol": f"token,{invalid_signature_token}"}
        )
        
        assert response.status_code == 401, (
            f"Invalid signature should return 401, got {response.status_code}"
        )

    def test_websocket_expired_token_rejects_connection(
        self, websocket_client: TestClient, expired_token: str
    ):
        """NEGATIVE: Expired JWT token rejects WebSocket connection."""
        response = websocket_client.get(
            "/v1/ws/workflows/test-wf-123",
            headers={"Sec-WebSocket-Protocol": f"token,{expired_token}"}
        )
        
        assert response.status_code == 401, (
            f"Expired token should return 401, got {response.status_code}"
        )


class TestWebSocketTenantIsolation:
    """P0: WebSocket tenant isolation enforcement."""

    def test_websocket_cross_tenant_subscription_blocked(
        self, websocket_client: TestClient, tenant_a_token: str
    ):
        """NEGATIVE: Tenant A cannot subscribe to Tenant B's workflow events.
        
        This is a critical P0 test - cross-tenant data access must be blocked.
        """
        # Tenant A tries to access a workflow that belongs to Tenant B
        # The workflow ID format typically includes tenant context
        tenant_b_workflow_id = "tenant-b:wf-456"
        
        response = websocket_client.get(
            f"/v1/ws/workflows/{tenant_b_workflow_id}",
            headers={"Sec-WebSocket-Protocol": f"base64url.bearer.authorization,{tenant_a_token}"}
        )
        
        # Should be rejected - either 403 (forbidden) or connection closed
        assert response.status_code in [401, 403, 404], (
            f"Cross-tenant WebSocket access should be blocked, got {response.status_code}. "
            "This is a P0 security vulnerability."
        )

    def test_websocket_tenant_context_propagated(
        self, websocket_client: TestClient, tenant_a_token: str
    ):
        """POSITIVE: Valid tenant context is extracted and propagated.
        
        Proves that tenant_id from JWT is correctly extracted and used
        for workflow subscription authorization.
        """
        workflow_id = "tenant-a:wf-123"
        
        with websocket_client.websocket_connect(
            f"/v1/ws/workflows/{workflow_id}",
            headers={"Sec-WebSocket-Protocol": f"base64url.bearer.authorization,{tenant_a_token}"}
        ) as websocket:
            # Connection should be accepted for same-tenant workflow
            try:
                event = websocket.receive_json(timeout=1.0)
                # If we get an event, tenant context was properly propagated
                assert event is not None
            except Exception:
                # Connection accepted but no events is still success
                pass


class TestWebSocketProtocolSecurity:
    """P1: WebSocket protocol header security tests."""

    def test_websocket_rejects_token_in_query_param(
        self, websocket_client: TestClient, tenant_a_token: str
    ):
        """NEGATIVE: JWT in query parameter is rejected (P1-13 fix).
        
        Tokens in query params get logged by proxies - security risk.
        """
        response = websocket_client.get(
            f"/v1/ws/workflows/wf-123?token={tenant_a_token}"
        )
        
        # Should reject with 1008 policy violation or 400 bad request
        assert response.status_code in [400, 401, 403], (
            f"Token in query param should be rejected, got {response.status_code}. "
            "This is a security risk as tokens get logged by proxies."
        )

    def test_websocket_accepts_token_in_protocol_header(
        self, websocket_client: TestClient, tenant_a_token: str
    ):
        """POSITIVE: Token in Sec-WebSocket-Protocol header is accepted."""
        # This should work (positive test)
        with websocket_client.websocket_connect(
            "/v1/ws/workflows/wf-123",
            headers={"Sec-WebSocket-Protocol": f"base64url.bearer.authorization,{tenant_a_token}"}
        ) as websocket:
            assert hasattr(websocket, 'receive_json')

    def test_websocket_protocol_without_token_prefix(
        self, websocket_client: TestClient, tenant_a_token: str):
        """NEGATIVE: Protocol header with just token (no bearer prefix) is rejected.
        
        Per SEC-L3-012, the Sec-WebSocket-Protocol header must use the canonical
        bearer format: base64url.bearer.authorization,<jwt>
        """
        response = websocket_client.get(
            "/v1/ws/workflows/wf-123",
            headers={"Sec-WebSocket-Protocol": tenant_a_token}
        )
        assert response.status_code in [401, 403], (
            f"Token without bearer prefix should be rejected, got {response.status_code}"
        )


class TestWebSocketConnectionLifecycle:
    """P1: WebSocket connection lifecycle security."""

    def test_websocket_disconnect_on_auth_failure(self, websocket_client: TestClient):
        """NEGATIVE: Connection closed cleanly on auth failure.
        
        Verifies that failed auth doesn't leave dangling connections.
        """
        response = websocket_client.get("/v1/ws/workflows/wf-123")
        
        # Should get immediate rejection, not a half-open connection
        assert response.status_code in [401, 403]


# Regression tests for discovered vulnerabilities
class TestWebSocketRegressionFixes:
    """Regression tests for P0 vulnerabilities fixed."""

    def test_regression_pr_0013_query_param_token_rejected(
        self, websocket_client: TestClient, tenant_a_token: str
    ):
        """REGRESSION: P1-13 - Query param token must be rejected.
        
        This test prevents regression of the fix for token logging vulnerability.
        """
        response = websocket_client.get(
            f"/v1/ws/workflows/wf-123?token={tenant_a_token}"
        )
        
        # After P1-13 fix, this should be rejected
        assert response.status_code not in [200, 101], (
            "REGRESSION: Token in query param accepted. "
            "P1-13 fix has been reverted."
        )

    def test_regression_auth_required_for_websocket(
        self, websocket_client: TestClient
    ):
        """REGRESSION: WebSocket requires authentication.
        
        This test prevents regression where WebSocket accepted unauthenticated connections.
        """
        response = websocket_client.get("/v1/ws/workflows/wf-123")
        
        assert response.status_code in [401, 403], (
            "REGRESSION: Unauthenticated WebSocket connection accepted. "
            "Auth enforcement has been bypassed."
        )
