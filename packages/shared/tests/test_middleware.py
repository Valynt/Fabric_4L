"""Comprehensive tests for GovernanceMiddleware refactored methods.

This test file provides direct coverage for the middleware.py source file,
addressing the untested hotspot issue identified in health analysis.
"""

import asyncio
import os
from typing import Any
from contextvars import Token
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from value_fabric.shared.identity.context import (
    AUTH_SOURCE_SERVICE_ACCOUNT,
    RequestContext,
)
from value_fabric.shared.identity.constants import (
    EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST,
    SESSION_COOKIE_NAME,
    TENANT_ID_HEADER,
)
from value_fabric.shared.identity.middleware import (
    GovernanceMiddleware,
    _current_context,
)
from value_fabric.shared.identity.permissions import Permission, Role


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request."""
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.path = "/api/test"
    request.headers = {}
    request.cookies = {}
    request.state = MagicMock()
    request.method = "GET"
    return request


@pytest.fixture
def sample_context():
    """Create a sample RequestContext for testing."""
    return RequestContext(
        tenant_id=uuid4(),
        user_id=uuid4(),
        roles=[Role.TENANT_ADMIN.value],
        permissions=frozenset([Permission.READ_HEALTH, Permission.WRITE_ANALYTICS]),
        source="jwt",
        raw={"sub": "user123"},
    )


@pytest.fixture
def middleware():
    """Create a GovernanceMiddleware instance for testing."""
    return GovernanceMiddleware(
        app=MagicMock(),
        api_key_resolver=None,
        rate_limiter=None,
        enforce_authentication=True,
        require_tenant_context=True,
    )


class TestResolveIdentityRefactoring:
    """Tests for refactored _resolve_identity and its helper methods."""

    @pytest.mark.asyncio
    async def test_resolve_identity_returns_prepopulated_context(
        self, middleware, mock_request, sample_context
    ):
        """Test that prepopulated context is returned immediately."""
        mock_request.state.governance_context = sample_context
        ctx = await middleware._resolve_identity(mock_request)
        assert ctx == sample_context

    @pytest.mark.asyncio
    async def test_resolve_identity_returns_none_when_no_auth(
        self, middleware, mock_request
    ):
        """Test that None is returned when no authentication is provided."""
        ctx = await middleware._resolve_identity(mock_request)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_bearer_jwt_returns_none_for_non_bearer(
        self, middleware, mock_request
    ):
        """Test that non-Bearer auth header returns None."""
        mock_request.headers = {"Authorization": "Basic abc123"}
        ctx = await middleware._resolve_bearer_jwt(mock_request)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_bearer_jwt_raises_on_invalid_token(
        self, middleware, mock_request
    ):
        """Test that invalid JWT raises HTTPException."""
        mock_request.headers = {"Authorization": "Bearer invalid.token.here"}
        with patch(
            "value_fabric.shared.identity.middleware.decode_jwt",
            side_effect=Exception("Invalid"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await middleware._resolve_bearer_jwt(mock_request)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_resolve_session_cookie_returns_none_when_missing(
        self, middleware, mock_request
    ):
        """Test that missing session cookie returns None."""
        ctx = await middleware._resolve_session_cookie(mock_request)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_session_cookie_raises_on_invalid_session(
        self, middleware, mock_request
    ):
        """Test that invalid session cookie raises HTTPException."""
        mock_request.cookies = {SESSION_COOKIE_NAME: "invalid.session.token"}
        with patch(
            "value_fabric.shared.identity.middleware.decode_jwt",
            side_effect=Exception("Invalid"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await middleware._resolve_session_cookie(mock_request)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_resolve_api_key_returns_none_when_missing(
        self, middleware, mock_request
    ):
        """Test that missing API key returns None."""
        ctx = await middleware._resolve_api_key(mock_request)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_api_key_returns_none_when_resolver_missing(
        self, middleware, mock_request
    ):
        """Test that API key returns None when resolver is not configured."""
        middleware._api_key_resolver = None
        mock_request.headers = {"X-API-Key": "test-key"}
        ctx = await middleware._resolve_api_key(mock_request)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_api_key_with_valid_resolver(self, mock_request):
        """Test API key resolution with valid resolver."""
        tenant_id = uuid4()
        user_id = uuid4()

        async def mock_resolver(key: str):
            return {
                "tenant_id": str(tenant_id),
                "user_id": str(user_id),
                "key_id": "key-123",
                "role": Role.READ_ONLY.value,
                "enabled": True,
            }

        middleware = GovernanceMiddleware(
            app=MagicMock(),
            api_key_resolver=mock_resolver,
            rate_limiter=None,
        )
        mock_request.headers = {"X-API-Key": "test-key"}

        ctx = await middleware._resolve_api_key(mock_request)
        assert ctx is not None
        assert ctx.tenant_id == tenant_id
        assert ctx.user_id == str(user_id)
        assert ctx.api_key_id == "key-123"

    @pytest.mark.asyncio
    async def test_resolve_api_key_returns_none_for_disabled_key(self, mock_request):
        """Test that disabled API key returns None."""

        async def mock_resolver(key: str):
            return {"tenant_id": str(uuid4()), "enabled": False}

        middleware = GovernanceMiddleware(
            app=MagicMock(),
            api_key_resolver=mock_resolver,
            rate_limiter=None,
        )
        mock_request.headers = {"X-API-Key": "test-key"}

        ctx = await middleware._resolve_api_key(mock_request)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_service_to_service_returns_none_when_missing_header(
        self, middleware, mock_request
    ):
        """Test that missing X-Tenant-ID returns None."""
        ctx = await middleware._resolve_service_to_service(mock_request)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_service_to_service_returns_none_when_secret_missing(
        self, middleware, mock_request
    ):
        """Test that missing SERVICE_AUTH_SECRET returns None."""
        mock_request.headers = {TENANT_ID_HEADER: str(uuid4())}
        with patch.dict(os.environ, {}, clear=True):
            ctx = await middleware._resolve_service_to_service(mock_request)
            assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_service_to_service_returns_none_for_short_secret(
        self, middleware, mock_request
    ):
        """Test that short SERVICE_AUTH_SECRET returns None."""
        mock_request.headers = {TENANT_ID_HEADER: str(uuid4())}
        with patch.dict(os.environ, {"SERVICE_AUTH_SECRET": "short"}):
            ctx = await middleware._resolve_service_to_service(mock_request)
            assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_service_to_service_returns_none_for_invalid_secret(
        self, middleware, mock_request
    ):
        """Test that invalid X-Service-Auth returns None."""
        tenant_id = str(uuid4())
        mock_request.headers = {
            TENANT_ID_HEADER: tenant_id,
            "X-Service-Auth": "wrong-secret",
        }
        with patch.dict(
            os.environ, {"SERVICE_AUTH_SECRET": "correct-secret-32chars-minimum-32-chars"}
        ):
            ctx = await middleware._resolve_service_to_service(mock_request)
            assert ctx is None

    @pytest.mark.asyncio
    async def test_resolve_service_to_service_success(self, middleware, mock_request):
        """Test successful service-to-service resolution."""
        tenant_id = str(uuid4())
        mock_request.headers = {
            TENANT_ID_HEADER: tenant_id,
            "X-Service-Auth": "correct-secret-32chars-minimum-32-chars",
        }
        with patch.dict(
            os.environ, {"SERVICE_AUTH_SECRET": "correct-secret-32chars-minimum-32-chars"}
        ):
            ctx = await middleware._resolve_service_to_service(mock_request)
            assert ctx is not None
            assert ctx.tenant_id == UUID(tenant_id)
            assert Role.SYSTEM.value in ctx.roles
            assert ctx.source == AUTH_SOURCE_SERVICE_ACCOUNT


class TestDispatchRefactoring:
    """Tests for refactored dispatch and its helper methods."""

    @pytest.mark.asyncio
    async def test_handle_authentication_returns_none_for_public_path(
        self, middleware, mock_request
    ):
        """Test that public paths skip authentication."""
        mock_request.url.path = "/health"
        ctx = await middleware._handle_authentication(mock_request)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_handle_authentication_returns_none_when_disabled(
        self, middleware, mock_request
    ):
        """Test that disabled authentication returns None."""
        middleware._enforce_authentication = False
        ctx = await middleware._handle_authentication(mock_request)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_handle_authentication_raises_on_missing_credentials(
        self, middleware, mock_request
    ):
        """Test that missing credentials raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            await middleware._handle_authentication(mock_request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_handle_authentication_raises_on_invalid_context(
        self, middleware, mock_request, sample_context
    ):
        """Test that invalid auth source raises HTTPException."""
        with patch.object(sample_context, "is_auth_source_valid", return_value=False):
            with patch.object(
                middleware, "_resolve_identity", return_value=sample_context
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await middleware._handle_authentication(mock_request)
                assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_handle_authentication_raises_on_missing_tenant(
        self, middleware, mock_request
    ):
        """Test that missing tenant context raises HTTPException when required."""
        ctx_no_tenant = RequestContext(
            tenant_id=None,
            user_id=uuid4(),
            roles=[Role.TENANT_ADMIN.value],
            permissions=frozenset(),
            source="jwt",
            raw={},
        )
        with patch.object(middleware, "_resolve_identity", return_value=ctx_no_tenant):
            with pytest.raises(HTTPException) as exc_info:
                await middleware._handle_authentication(mock_request)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_handle_authentication_returns_valid_context(
        self, middleware, mock_request, sample_context
    ):
        """Test that valid context is returned."""
        with patch.object(middleware, "_resolve_identity", return_value=sample_context):
            ctx = await middleware._handle_authentication(mock_request)
            assert ctx == sample_context

    @pytest.mark.asyncio
    async def test_check_rate_limit_before_request_returns_none_when_no_context(
        self, middleware, mock_request
    ):
        """Test that rate limit check returns None when no context."""
        response = await middleware._check_rate_limit_before_request(mock_request, None)
        assert response is None

    @pytest.mark.asyncio
    async def test_check_rate_limit_before_request_returns_none_when_no_limiter(
        self, middleware, mock_request, sample_context
    ):
        """Test that rate limit check returns None when no limiter configured."""
        middleware._rate_limiter = None
        response = await middleware._check_rate_limit_before_request(
            mock_request, sample_context
        )
        assert response is None

    @pytest.mark.asyncio
    async def test_check_rate_limit_before_request_returns_none_when_allowed(
        self, middleware, mock_request, sample_context
    ):
        """Test that rate limit check returns None when request is allowed."""
        mock_rate_limiter = AsyncMock()
        mock_rate_limiter.check.return_value = MagicMock(
            allowed=True, remaining=100, reset_at=1234567890
        )
        middleware._rate_limiter = mock_rate_limiter

        with patch.object(
            middleware, "_check_rate_limit", return_value=MagicMock(allowed=True)
        ):
            response = await middleware._check_rate_limit_before_request(
                mock_request, sample_context
            )
            assert response is None

    @pytest.mark.asyncio
    async def test_check_rate_limit_before_request_returns_429_when_exceeded(
        self, middleware, mock_request, sample_context
    ):
        """Test that rate limit check returns 429 when limit exceeded."""
        mock_rate_limiter = AsyncMock()
        mock_rate_limiter.check.return_value = MagicMock(
            allowed=False, remaining=0, reset_at=1234567890, retry_after=60
        )
        middleware._rate_limiter = mock_rate_limiter

        with patch.object(
            middleware,
            "_check_rate_limit",
            return_value=MagicMock(allowed=False, retry_after=60),
        ):
            with patch.object(
                middleware,
                "_resolve_rate_limit_config",
                return_value=MagicMock(
                    requests_per_minute=100, scope=MagicMock(value="tenant")
                ),
            ):
                response = await middleware._check_rate_limit_before_request(
                    mock_request, sample_context
                )
                assert response is not None
                assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_add_rate_limit_headers_skips_when_no_context(
        self, middleware, mock_request
    ):
        """Test that rate limit headers are skipped when no context."""
        response = MagicMock(spec=Response)
        response.headers = {}
        await middleware._add_rate_limit_headers(response, mock_request, None)
        assert "X-RateLimit-Limit" not in response.headers

    @pytest.mark.asyncio
    async def test_add_rate_limit_headers_skips_when_no_limiter(
        self, middleware, mock_request, sample_context
    ):
        """Test that rate limit headers are skipped when no limiter."""
        middleware._rate_limiter = None
        response = MagicMock(spec=Response)
        response.headers = {}
        await middleware._add_rate_limit_headers(response, mock_request, sample_context)
        assert "X-RateLimit-Limit" not in response.headers

    @pytest.mark.asyncio
    async def test_add_rate_limit_headers_adds_headers(
        self, middleware, mock_request, sample_context
    ):
        """Test that rate limit headers are added correctly."""
        mock_rate_limiter = AsyncMock()
        mock_rate_limiter.check.return_value = MagicMock(
            remaining=50, reset_at=1234567890
        )
        middleware._rate_limiter = mock_rate_limiter

        mock_request.state.rate_limit_config = MagicMock(
            requests_per_minute=100, scope=MagicMock(value="tenant")
        )
        mock_request.state.rate_limit_result = MagicMock(
            remaining=50, reset_at=1234567890
        )

        response = MagicMock(spec=Response)
        response.headers = {}

        await middleware._add_rate_limit_headers(response, mock_request, sample_context)

        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "50"
        assert response.headers["X-RateLimit-Reset"] == "1234567890"
        assert response.headers["X-RateLimit-Scope"] == "tenant"


class TestBuildContextFromClaims:
    """Tests for _build_context_from_claims helper method."""

    def test_build_context_from_dict_claims(self, middleware, mock_request):
        """Test building context from dict claims."""
        claims = {
            "tenant_id": str(uuid4()),
            "sub": str(uuid4()),
            "roles": [Role.TENANT_ADMIN.value],
            "permissions": ["read", "write"],
        }
        mock_request.headers = {}

        with patch(
            "value_fabric.shared.identity.middleware.extract_context_from_jwt"
        ) as mock_extract:
            mock_extract.return_value = MagicMock()
            result = middleware._build_context_from_claims(claims, mock_request)
            assert result is not None
            mock_extract.assert_called_once()

    def test_build_context_from_object_claims(self, middleware, mock_request):
        """Test building context from object claims."""
        claims = MagicMock()
        claims.tenant_id = uuid4()
        claims.user_id = uuid4()
        claims.roles = [Role.TENANT_ADMIN.value]
        claims.extra_claims = {}

        mock_request.headers = {}

        with patch(
            "value_fabric.shared.identity.middleware._build_context_from_role"
        ) as mock_build:
            mock_build.return_value = MagicMock()
            result = middleware._build_context_from_claims(claims, mock_request)
            assert result is not None
            mock_build.assert_called_once()

    def test_build_context_raises_on_validation_error(self, middleware, mock_request):
        """Test that validation errors raise HTTPException."""
        claims = {"tenant_id": str(uuid4())}
        mock_request.headers = {}

        with patch(
            "value_fabric.shared.identity.middleware.extract_context_from_jwt",
            side_effect=ValueError("Invalid"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                middleware._build_context_from_claims(claims, mock_request)
            assert exc_info.value.status_code == 403


class TestSetRequestContext:
    """Tests for _set_request_context helper method."""

    def test_set_request_context_resets_prior_token_and_sets_new_context(
        self, middleware, sample_context
    ):
        """The prior token is reset and the new context becomes current."""
        # A ContextVar Token can only be produced by ContextVar.set, so obtain a
        # real one instead of faking it.
        token = _current_context.set(None)
        try:
            new_token = middleware._set_request_context(sample_context, token)

            assert isinstance(new_token, Token)
            assert _current_context.get() is sample_context
        finally:
            _current_context.set(None)

    def test_set_request_context_returns_token_from_set_request_context(
        self, middleware, sample_context
    ):
        """The returned token comes from the canonical set_request_context helper."""
        token = _current_context.set(None)
        try:
            with patch(
                "value_fabric.shared.identity.middleware.set_request_context",
                return_value="new-token",
            ):
                assert middleware._set_request_context(sample_context, token) == "new-token"
        finally:
            _current_context.set(None)


class TestExternalAuthBootstrapAllowlist:
    """Tests for EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST."""

    def test_health_path_in_allowlist(self):
        """Test that health paths are in allowlist."""
        assert "/health" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST
        assert "/health/detailed" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST
        assert "/health/live" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST

    def test_docs_paths_in_allowlist(self):
        """Test that docs paths are in allowlist."""
        assert "/docs" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST
        assert "/openapi.json" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST
        assert "/redoc" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST

    def test_auth_bootstrap_paths_in_allowlist(self):
        """Test that auth bootstrap paths are in allowlist."""
        assert "/v1/auth/login" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST
        assert "/v1/auth/signup" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST
        assert "/v1/auth/accept-invite" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST

    def test_webhook_paths_in_allowlist(self):
        """Test that webhook paths are in allowlist."""
        assert "/v1/billing/webhook" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST
        assert "/internal/webhooks/clerk" in EXTERNAL_AUTH_BOOTSTRAP_ALLOWLIST


class TestRateLimitIntegration:
    """Integration tests for rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_not_added_when_result_is_none(
        self, middleware, mock_request, sample_context
    ):
        """Test that rate limit headers are not added when result is None (no redundant check)."""
        middleware._rate_limiter = AsyncMock()
        response = MagicMock(spec=Response)
        response.headers = {}

        # Simulate case where rate limit check was skipped (result is None)
        mock_request.state.rate_limit_config = MagicMock(
            requests_per_minute=100, scope=MagicMock(value="tenant")
        )
        mock_request.state.rate_limit_result = None

        await middleware._add_rate_limit_headers(response, mock_request, sample_context)

        # Headers should NOT be added when result is None
        assert "X-RateLimit-Limit" not in response.headers
        assert "X-RateLimit-Remaining" not in response.headers
        # Verify no redundant check was performed
        middleware._rate_limiter.check.assert_not_called()

    @pytest.mark.asyncio
    async def test_rate_limit_headers_added_when_result_exists(
        self, middleware, mock_request, sample_context
    ):
        """Test that rate limit headers are added when result exists from prior check."""
        middleware._rate_limiter = AsyncMock()
        response = MagicMock(spec=Response)
        response.headers = {}

        # Simulate case where rate limit check was performed (result exists)
        mock_request.state.rate_limit_config = MagicMock(
            requests_per_minute=100, scope=MagicMock(value="tenant")
        )
        mock_request.state.rate_limit_result = MagicMock(
            remaining=50, reset_at=1234567890
        )

        await middleware._add_rate_limit_headers(response, mock_request, sample_context)

        # Headers should be added when result exists
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "50"
        # Verify no redundant check was performed
        middleware._rate_limiter.check.assert_not_called()


class TestRedisExceptionHandling:
    """Integration tests for Redis exception handling."""

    @pytest.mark.asyncio
    async def test_tenant_kill_switch_unknown_returns_503(
        self, middleware, sample_context
    ):
        """RB-4: When Redis is unavailable, check_status() returns UNKNOWN.

        The middleware MUST return HTTP 503 (not None/allow) when the kill
        switch cannot confirm tenant status. Returning None would be a
        fail-open vulnerability: a suspended tenant could bypass the kill
        switch during a Redis outage.
        """
        from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus

        with patch(
            "value_fabric.shared.identity.middleware.TenantKillSwitch"
        ) as MockKillSwitch:
            mock_kill_switch = MagicMock()
            # check_status() is now called instead of is_suspended()
            mock_kill_switch.check_status = AsyncMock(
                return_value=TenantSuspensionStatus.UNKNOWN
            )
            MockKillSwitch.return_value = mock_kill_switch

            result = await middleware._enforce_tenant_status(sample_context)

            # MUST return 503, not None (fail-open)
            assert result is not None, (
                "Middleware must NOT return None (allow) when kill switch status is "
                "UNKNOWN. A Redis outage must not allow suspended tenants through."
            )
            assert result.status_code == 503
            import json
            body = json.loads(result.body)
            assert body["error"] == "tenant_status_unavailable"

    @pytest.mark.asyncio
    async def test_tenant_kill_switch_no_redis_returns_503(
        self, middleware, sample_context
    ):
        """RB-4: When no Redis client is configured, check_status() returns UNKNOWN.

        A missing Redis client is the most common production misconfiguration.
        The middleware must fail safe (503) rather than silently allowing all
        requests through.
        """
        from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus

        with patch(
            "value_fabric.shared.identity.middleware.TenantKillSwitch"
        ) as MockKillSwitch:
            mock_kill_switch = MagicMock()
            mock_kill_switch.check_status = AsyncMock(
                return_value=TenantSuspensionStatus.UNKNOWN
            )
            MockKillSwitch.return_value = mock_kill_switch

            result = await middleware._enforce_tenant_status(sample_context)

            assert result is not None
            assert result.status_code == 503

    @pytest.mark.asyncio
    async def test_tenant_kill_switch_active_allows_request(
        self, middleware, sample_context
    ):
        """RB-4: When Redis confirms tenant is ACTIVE, request proceeds normally."""
        from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus

        with patch(
            "value_fabric.shared.identity.middleware.TenantKillSwitch"
        ) as MockKillSwitch:
            mock_kill_switch = MagicMock()
            mock_kill_switch.check_status = AsyncMock(
                return_value=TenantSuspensionStatus.ACTIVE
            )
            MockKillSwitch.return_value = mock_kill_switch

            result = await middleware._enforce_tenant_status(sample_context)

            # ACTIVE status: no blocking response
            assert result is None

    @pytest.mark.asyncio
    async def test_tenant_kill_switch_suspended_returns_403(
        self, middleware, sample_context
    ):
        """RB-4: When Redis confirms tenant is SUSPENDED, middleware returns 403."""
        from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus

        with patch(
            "value_fabric.shared.identity.middleware.TenantKillSwitch"
        ) as MockKillSwitch:
            mock_kill_switch = MagicMock()
            mock_kill_switch.check_status = AsyncMock(
                return_value=TenantSuspensionStatus.SUSPENDED
            )
            MockKillSwitch.return_value = mock_kill_switch

            result = await middleware._enforce_tenant_status(sample_context)

            assert result is not None
            assert result.status_code == 403
            import json
            body = json.loads(result.body)
            assert body["error"] == "tenant_suspended"

    @pytest.mark.asyncio
    async def test_tenant_kill_switch_handles_redis_error(
        self, middleware, sample_context
    ):
        """RB-4 (updated): Redis errors now produce UNKNOWN → 503, not None → allow.

        Previously this test asserted result is None (fail-open). The correct
        behavior after the RB-4 fix is to return 503 when Redis is unavailable.
        """
        from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus

        with patch(
            "value_fabric.shared.identity.middleware.TenantKillSwitch"
        ) as MockKillSwitch:
            mock_kill_switch = MagicMock()
            # check_status() returns UNKNOWN on any Redis error
            mock_kill_switch.check_status = AsyncMock(
                return_value=TenantSuspensionStatus.UNKNOWN
            )
            MockKillSwitch.return_value = mock_kill_switch

            result = await middleware._enforce_tenant_status(sample_context)

            # Must be 503, not None (fail-open)
            assert result is not None
            assert result.status_code == 503

    @pytest.mark.asyncio
    async def test_tenant_kill_switch_handles_network_error(
        self, middleware, sample_context
    ):
        """RB-4 (updated): Network errors now produce UNKNOWN → 503, not None → allow."""
        from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus

        with patch(
            "value_fabric.shared.identity.middleware.TenantKillSwitch"
        ) as MockKillSwitch:
            mock_kill_switch = MagicMock()
            mock_kill_switch.check_status = AsyncMock(
                return_value=TenantSuspensionStatus.UNKNOWN
            )
            MockKillSwitch.return_value = mock_kill_switch

            result = await middleware._enforce_tenant_status(sample_context)

            assert result is not None
            assert result.status_code == 503

    @pytest.mark.asyncio
    async def test_tenant_kill_switch_re_raises_unexpected_exception(
        self, middleware, sample_context
    ):
        """Unexpected exceptions from check_status() are handled via UNKNOWN → 503.

        The new check_status() implementation catches all exceptions internally
        and returns UNKNOWN. The middleware no longer receives raw exceptions
        from the kill switch. This test verifies the middleware handles UNKNOWN
        correctly (503) rather than re-raising.
        """
        from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus

        with patch(
            "value_fabric.shared.identity.middleware.TenantKillSwitch"
        ) as MockKillSwitch:
            mock_kill_switch = MagicMock()
            # check_status() absorbs all exceptions and returns UNKNOWN
            mock_kill_switch.check_status = AsyncMock(
                return_value=TenantSuspensionStatus.UNKNOWN
            )
            MockKillSwitch.return_value = mock_kill_switch

            result = await middleware._enforce_tenant_status(sample_context)
            assert result is not None
            assert result.status_code == 503
