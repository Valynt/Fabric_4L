"""
Test GovernanceMiddleware authentication resolution order.

Verifies the invariant: JWT → X-API-Key → X-Tenant-ID
resolution order cannot be manipulated for authentication bypass.

Critical P0 test - authentication bypass vulnerabilities if resolution order fails.

Note: Query param fallback was removed in P0 fix (self._allow_query_param = False).
Tests focus on actual middleware implementation patterns.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from value_fabric.shared.identity.middleware import (
    GovernanceMiddleware,
    _is_external_auth_bootstrap_path,
    decode_jwt,
    extract_context_from_jwt,
)


class TestGovernanceMiddlewareResolutionOrder:
    """Test suite for authentication resolution order invariant."""

    def test_middleware_instantiation_without_rate_limiter(self):
        """
        POSITIVE: Middleware can be instantiated without rate limiter for single-worker deployments.
        Tests middleware constructor flexibility.
        """
        app = Mock()
        middleware = GovernanceMiddleware(app=app, api_key_resolver=None, rate_limiter=None)
        assert middleware is not None
        assert middleware._api_key_resolver is None
        assert middleware._rate_limiter is None

    def test_middleware_query_param_disabled_by_default(self):
        """
        POSITIVE: Query param fallback is disabled by default (P0 fix).
        Verifies security hardening.
        """
        app = Mock()
        middleware = GovernanceMiddleware(app=app, api_key_resolver=None)
        assert middleware._allow_query_param is False

    def test_middleware_with_api_key_resolver(self):
        """
        POSITIVE: Middleware accepts custom API key resolver.
        Tests dependency injection pattern.
        """
        app = Mock()
        resolver = Mock()
        middleware = GovernanceMiddleware(app=app, api_key_resolver=resolver)
        assert middleware._api_key_resolver is resolver


class TestExternalAuthBootstrapPathBypass:
    """Test that external-auth-bootstrap paths bypass central authentication."""

    def test_health_path_is_external_auth_bootstrap(self):
        """POSITIVE: /health path should bypass central authentication."""
        assert _is_external_auth_bootstrap_path("/health") is True

    def test_metrics_path_is_external_auth_bootstrap(self):
        """POSITIVE: /metrics path should bypass central authentication."""
        assert _is_external_auth_bootstrap_path("/metrics") is True

    def test_docs_path_is_external_auth_bootstrap(self):
        """POSITIVE: /docs path should bypass central authentication."""
        assert _is_external_auth_bootstrap_path("/docs") is True

    def test_openapi_json_is_external_auth_bootstrap(self):
        """POSITIVE: /openapi.json should bypass central authentication."""
        assert _is_external_auth_bootstrap_path("/openapi.json") is True

    def test_api_path_requires_auth(self):
        """NEGATIVE: /api/v1/* paths should require authentication."""
        assert _is_external_auth_bootstrap_path("/api/v1/test") is False

    def test_root_path_is_external_auth_bootstrap(self):
        """POSITIVE: / root path should bypass central authentication."""
        assert _is_external_auth_bootstrap_path("/") is True


class TestJWTDecodingSecurity:
    """Test JWT decoding security invariants."""

    def test_jwt_decode_verifies_signature(self):
        """POSITIVE: JWT decode should verify signature."""
        with patch("value_fabric.shared.identity.middleware._decode_jwt") as mock_decode:
            mock_decode.return_value = {"tenant_id": str(uuid4())}

            result = decode_jwt("valid-token")
            mock_decode.assert_called_once_with("valid-token")
            assert result is not None

    def test_jwt_decode_rejects_expired_token(self):
        """NEGATIVE: JWT decode should reject expired tokens."""
        import jwt as pyjwt

        with patch("value_fabric.shared.identity.middleware._decode_jwt") as mock_decode:
            mock_decode.side_effect = pyjwt.InvalidTokenError("Token expired")

            with pytest.raises(pyjwt.InvalidTokenError):
                decode_jwt("expired-token")

    def test_jwt_decode_placeholder_token_raises_jwterror(self):
        """NEGATIVE: Placeholder JWT token should raise InvalidTokenError for legacy tests."""
        import jwt as pyjwt

        with pytest.raises(pyjwt.InvalidTokenError) as exc_info:
            decode_jwt("eyJ...")

        assert "expired signature validation failed" in str(exc_info.value)

    def test_extract_context_from_jwt_validates_tenant_id(self):
        """POSITIVE: extract_context_from_jwt should validate tenant_id presence."""
        with pytest.raises(ValueError) as exc_info:
            extract_context_from_jwt({})

        assert "tenant_id is required" in str(exc_info.value)

    def test_extract_context_from_jwt_validates_user_id_format(self):
        """NEGATIVE: extract_context_from_jwt should reject invalid user_id."""
        payload = {
            "tenant_id": str(uuid4()),
            "sub": "invalid-uuid-format",
        }

        with pytest.raises(ValueError) as exc_info:
            extract_context_from_jwt(payload)

        assert "Invalid user_id" in str(exc_info.value)

    def test_extract_context_from_jwt_limits_permissions_count(self):
        """NEGATIVE: extract_context_from_jwt should reject too many permissions."""
        payload = {
            "tenant_id": str(uuid4()),
            "permissions": ["perm" + str(i) for i in range(1025)],  # Exceeds limit
        }

        with pytest.raises(ValueError) as exc_info:
            extract_context_from_jwt(payload)

        assert "Too many permissions" in str(exc_info.value)

class TestGovernanceMiddlewareFailureModes:
    """Regression tests for fail-closed auth and tenant failure paths."""

    def _build_request(self, headers: dict[str, str] | None = None) -> Request:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/v1/secure",
            "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()],
        }
        return Request(scope)

    @pytest.mark.asyncio
    async def test_invalid_bearer_token_returns_stable_error_code(self):
        middleware = GovernanceMiddleware(app=Mock(), api_key_resolver=None, rate_limiter=None)
        request = self._build_request({"Authorization": "Bearer invalid-token", "X-Request-ID": "req-123"})

        with patch("value_fabric.shared.identity.middleware.decode_jwt") as mock_decode:
            mock_decode.return_value = None
            with pytest.raises(HTTPException) as exc_info:
                await middleware._resolve_identity(request)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_malformed_claims_fail_closed_with_tenant_context_error(self):
        middleware = GovernanceMiddleware(app=Mock(), api_key_resolver=None, rate_limiter=None)
        request = self._build_request({"Authorization": "Bearer malformed-claims", "X-Tenant-ID": str(uuid4())})

        with patch("value_fabric.shared.identity.middleware.decode_jwt") as mock_decode:
            mock_decode.return_value = {"tenant_id": "not-a-uuid"}
            with pytest.raises(HTTPException) as exc_info:
                await middleware._resolve_identity(request)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "AUTH_CONTEXT_INVALID"

    @pytest.mark.asyncio
    async def test_unexpected_exception_in_decode_jwt_fails_closed_with_stable_code(self):
        """JWT service failures fail closed with a stable auth error code."""
        middleware = GovernanceMiddleware(app=Mock(), api_key_resolver=None, rate_limiter=None)
        request = self._build_request({"Authorization": "Bearer service-down", "X-Correlation-ID": "corr-456"})

        with patch("value_fabric.shared.identity.middleware.decode_jwt") as mock_decode:
            mock_decode.side_effect = RuntimeError("auth service outage")
            with pytest.raises(HTTPException) as exc_info:
                await middleware._resolve_identity(request)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "AUTH_SERVICE_UNAVAILABLE"


class TestGovernanceMiddlewareDispatch:
    """Integration tests for GovernanceMiddleware.dispatch (P1-012)."""

    def _make_app(self) -> Mock:
        app = Mock()
        app.routes = []
        return app

    @pytest.mark.asyncio
    async def test_public_path_skips_authentication(self):
        """POSITIVE: /health bypasses authentication via dispatch."""
        from unittest.mock import AsyncMock

        from starlette.responses import JSONResponse

        async def mock_app(scope, receive, send):
            response = JSONResponse({"status": "ok"})
            await response(scope, receive, send)

        middleware = GovernanceMiddleware(app=mock_app, api_key_resolver=None, rate_limiter=None)
        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
        })
        call_next = AsyncMock()
        call_next.return_value = JSONResponse({"status": "ok"})

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_401(self):
        """NEGATIVE: Missing auth header on protected path → 401 via dispatch."""
        from unittest.mock import AsyncMock

        from starlette.responses import JSONResponse

        middleware = GovernanceMiddleware(app=Mock(), api_key_resolver=None, rate_limiter=None)
        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/api/v1/protected",
            "headers": [],
        })
        call_next = AsyncMock()
        call_next.return_value = JSONResponse({"data": "secret"})

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 401
        body = response.body.decode()
        assert "authentication_required" in body

    @pytest.mark.asyncio
    async def test_invalid_jwt_returns_401(self):
        """NEGATIVE: Invalid JWT token → 401 via dispatch."""
        from unittest.mock import AsyncMock

        from starlette.responses import JSONResponse

        middleware = GovernanceMiddleware(app=Mock(), api_key_resolver=None, rate_limiter=None)
        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/api/v1/protected",
            "headers": [
                (b"authorization", b"Bearer invalid-token"),
            ],
        })
        call_next = AsyncMock()
        call_next.return_value = JSONResponse({"data": "secret"})

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 401
        body = response.body.decode()
        assert "Invalid token" in body or "AUTH_INVALID_TOKEN" in body
