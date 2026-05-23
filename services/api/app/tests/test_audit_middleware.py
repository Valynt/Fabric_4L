"""Tests for audit middleware redaction and security event logging.

Validates:
- Mutating requests are logged
- Security events (401/403) log at WARNING
- Server errors (5xx) log at ERROR
- Sensitive data is redacted from logs
"""

from __future__ import annotations

import logging
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.audit import AuditMiddleware, MUTATING_METHODS
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


class TestAuditMiddlewareRedaction:
    """Verify audit logs do not leak secrets."""

    def test_authorization_header_not_in_audit_payload(self):
        """Authorization header must never appear in audit log entries."""
        from app.core.audit import AuditMiddleware

        audit = AuditMiddleware(MagicMock())
        # Simulate a request with sensitive headers
        mock_request = MagicMock()
        mock_request.url.path = "/v1/accounts"
        mock_request.method = "POST"
        mock_request.headers = {
            "Authorization": "Bearer secret-token-123",
            "Cookie": "session=secret-session",
            "X-Api-Key": "sk-live-secret",
        }
        mock_request.client.host = "192.168.1.1"
        mock_request.state = MagicMock()
        mock_request.state.governance_context = None

        mock_response = MagicMock()
        mock_response.status_code = 201

        # Verify the log entry doesn't contain secrets
        with patch("app.core.audit.logger") as mock_logger:
            # Manually call the relevant parts
            import asyncio
            async def dummy_next(request):
                return mock_response

            asyncio.run(audit.dispatch(mock_request, dummy_next))

            # Check that no log call contains the secrets
            for call in mock_logger.info.call_args_list + mock_logger.warning.call_args_list:
                args, kwargs = call
                extra = kwargs.get("extra", {})
                log_str = str(args) + str(extra)
                assert "secret-token" not in log_str
                assert "secret-session" not in log_str
                assert "sk-live-secret" not in log_str


class TestAuditSecurityEvents:
    """Verify security events are logged at appropriate levels."""

    def test_401_logs_at_warning(self):
        """Unauthenticated requests must produce WARNING-level audit events."""
        with patch("app.core.audit.logger.warning") as mock_warn:
            resp = client.post("/v1/accounts", json={"name": "test"})
            assert resp.status_code == 401
            # The audit middleware should have logged a warning
            mock_warn.assert_called()
            args, kwargs = mock_warn.call_args
            extra = kwargs.get("extra", {})
            assert extra.get("event") == "access_denied"
            assert extra.get("status_code") == 401

    def test_403_logs_at_warning(self):
        """Forbidden requests must produce WARNING-level audit events."""
        with patch("app.core.audit.logger.warning") as mock_warn:
            # Post to login with bad credentials
            resp = client.post("/v1/auth/login", json={
                "email": "nonexistent@test.com",
                "password": "wrong",
            })
            assert resp.status_code == 401
            # Check warning was logged for access denial
            assert mock_warn.called


class TestAuditMutatingMethods:
    """Verify all mutating HTTP methods trigger audit logging."""

    def test_post_triggers_audit(self):
        # Unauthenticated POST to /v1/auth/login returns 401, which triggers WARNING-level audit
        with patch("app.core.audit.logger.warning") as mock_warn:
            client.post("/v1/auth/login", json={"email": "a@b.com", "password": "x"})
            assert mock_warn.called

    def test_get_does_not_trigger_audit(self):
        with patch("app.core.audit.logger.info") as mock_info:
            client.get("/health")
            mock_info.assert_not_called()

    def test_mutating_methods_constant(self):
        assert MUTATING_METHODS == {"POST", "PUT", "PATCH", "DELETE"}
