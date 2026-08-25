"""
Tenant Context Contract Tests (Suite 1 Gaps).

Extends existing context tests with comprehensive negative-path scenarios
and contract validation across all API boundaries.

Test Strategy:
- Verify tenant context is required for all protected endpoints
- Test malformed, missing, and conflicting context scenarios
- Validate context propagation through middleware chain
- Test context extraction from JWT, API keys, and headers
- Verify context immutability and thread safety
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import (
    require_admin,
    require_authenticated,
    require_tenant,
    require_tenant_context,
)
from value_fabric.shared.identity.permissions import Permission
from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus

# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Context Extraction and Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestContextExtraction:
    """Verify tenant context is correctly extracted from various sources."""
    
    @pytest.mark.asyncio
    async def test_context_extracted_from_jwt_token(self):
        """Tenant context must be extracted from valid JWT token.
        
        Rationale: JWT is primary auth mechanism for user requests.
        """
        from value_fabric.shared.identity.context_builders import extract_context_from_jwt
        
        tenant_id = uuid4()
        user_id = uuid4()
        
        # Mock JWT payload
        jwt_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "permissions": ["read:health", "write:models"],
        }
        
        context = extract_context_from_jwt(jwt_payload)
        
        assert context.tenant_id == tenant_id
        assert context.user_id == user_id
        assert Permission.READ_HEALTH in context.permissions
        assert Permission.WRITE_MODELS in context.permissions
    
    @pytest.mark.asyncio
    async def test_context_extracted_from_api_key_header(self):
        """Tenant context must be extracted from API key header.
        
        Rationale: API keys are used for service-to-service auth.
        """
        from value_fabric.shared.identity.context_builders import extract_context_from_api_key
        
        tenant_id = uuid4()
        api_key = "sk_test_12345"
        
        # Mock API key lookup
        with patch("value_fabric.shared.identity.context_builders.lookup_api_key") as mock_lookup:
            mock_lookup.return_value = {
                "tenant_id": tenant_id,
                "permissions": ["api:read", "api:write"],
            }
            
            context = await extract_context_from_api_key(api_key)
            
            assert context.tenant_id == tenant_id
            assert "api:read" in context.permissions
    
    @pytest.mark.asyncio
    async def test_missing_tenant_id_in_jwt_raises_error(self):
        """JWT without tenant_id must be rejected.
        
        Rationale: All authenticated requests must have tenant context.
        """
        from value_fabric.shared.identity.context_builders import extract_context_from_jwt
        
        # JWT missing tenant_id
        jwt_payload = {
            "sub": str(uuid4()),
            # tenant_id missing
            "permissions": ["read"],
        }
        
        with pytest.raises(ValueError, match="tenant_id.*required"):
            extract_context_from_jwt(jwt_payload)
    
    @pytest.mark.asyncio
    async def test_malformed_tenant_id_in_jwt_raises_error(self):
        """JWT with malformed tenant_id must be rejected.
        
        Rationale: Invalid UUIDs could cause downstream errors.
        """
        from value_fabric.shared.identity.context_builders import extract_context_from_jwt
        
        # JWT with invalid UUID
        jwt_payload = {
            "sub": str(uuid4()),
            "tenant_id": "not-a-uuid",
            "permissions": ["read"],
        }
        
        with pytest.raises(ValueError, match="Invalid.*tenant_id"):
            extract_context_from_jwt(jwt_payload)

    @pytest.mark.parametrize(
        "env_overrides",
        [
            {"ENVIRONMENT": "staging", "ALLOW_LEGACY_TEST_TENANT_IDS": "true", "PYTEST_CURRENT_TEST": "x"},
            {"ENVIRONMENT": "production", "TESTING": "true", "PYTEST_CURRENT_TEST": "x"},
            {"ENVIRONMENT": "development", "ALLOW_LEGACY_TEST_TENANT_IDS": "false", "K_SERVICE": "svc", "PYTEST_CURRENT_TEST": "x"},
        ],
    )
    def test_non_uuid_tenant_rejected_in_prod_like_middleware_matrices(self, env_overrides):
        from value_fabric.shared.identity.context_builders import extract_context_from_jwt

        with patch.dict("os.environ", env_overrides, clear=False):
            with pytest.raises(ValueError, match="Invalid tenant_id"):
                extract_context_from_jwt({"sub": str(uuid4()), "tenant_id": "tenant-a"})
    
    @pytest.mark.asyncio
    async def test_conflicting_tenant_ids_in_headers_raises_error(self):
        """Conflicting tenant_id in JWT and header must be rejected.
        
        Attack scenario: Attacker provides different tenant_id in header
        to bypass authorization.
        """
        from value_fabric.shared.identity.context_builders import validate_context_consistency
        
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # JWT says tenant A
        jwt_context = RequestContext(tenant_id=tenant_a, user_id=uuid4())
        
        # Header says tenant B
        header_tenant_id = str(tenant_b)
        
        with pytest.raises(ValueError, match="Conflicting.*tenant_id"):
            validate_context_consistency(jwt_context, header_tenant_id)

    def test_conflicting_tenant_ids_emit_inconsistent_access_metric(self, monkeypatch):
        """Tenant-header spoofing rejections must emit the isolation alert metric."""
        from value_fabric.shared.identity import context_builders

        calls = []

        def record_metric(**labels):
            calls.append(labels)

        monkeypatch.setattr(
            "value_fabric.shared.identity.context_builders.record_inconsistent_tenant_context_access",
            record_metric,
        )

        tenant_a = uuid4()
        tenant_b = uuid4()
        jwt_context = RequestContext(tenant_id=tenant_a, user_id=uuid4())

        with pytest.raises(ValueError, match="Conflicting.*tenant_id"):
            context_builders.validate_context_consistency(
                jwt_context,
                str(tenant_b),
                route="/api/v1/entities",
            )

        assert calls == [
            {"route": "/api/v1/entities", "source": "header"}
        ]


class TestContextDependencies:
    """Verify FastAPI dependencies correctly enforce context requirements."""
    
    @pytest.mark.asyncio
    async def test_require_authenticated_allows_valid_context(self):
        """require_authenticated should allow requests with valid context."""
        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=["read"]
        )
        
        result = await require_authenticated(context=context)
        assert result == context
    
    @pytest.mark.asyncio
    async def test_require_authenticated_rejects_empty_context(self):
        """require_authenticated must reject requests with no auth.
        
        Rationale: Protected endpoints require authentication.
        """
        # require_authenticated checks auth_source validity; unknown/invalid auth_source fails.
        context = RequestContext(auth_source="unknown")
        
        with pytest.raises(HTTPException) as exc_info:
            await require_authenticated(context=context)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_require_tenant_context_allows_tenant_auth(self):
        """require_tenant_context should allow tenant-authenticated requests."""
        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4()
        )
        
        result = await require_tenant_context(context=context)
        assert result == context
    
    @pytest.mark.asyncio
    async def test_require_tenant_context_rejects_missing_tenant_id(self):
        """require_tenant_context must reject requests without tenant_id.
        
        Rationale: Tenant-scoped operations require tenant context.
        """
        context = RequestContext(user_id=uuid4())  # No tenant_id
        
        with pytest.raises(HTTPException) as exc_info:
            await require_tenant_context(context=context)
        
        # require_tenant_context returns 400 when tenant_id is missing
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "tenant" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_require_tenant_context_rejects_malformed_context_tenant_id(self):
        """A malformed tenant_id injected into RequestContext must fail closed."""
        context = RequestContext(
            tenant_id="../../../tenant-b",
            user_id=uuid4(),
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_tenant_context(context=context)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "tenant" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_require_tenant_rejects_malformed_requested_tenant_id(self):
        """Requested tenant IDs are validated before comparison."""
        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_tenant(
                tenant_id="tenant-b\x00injected",
                context=context,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "tenant" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_require_tenant_rejects_unauthorized_requested_tenant_id(self):
        """A valid but different requested tenant must be forbidden."""
        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_tenant(
                tenant_id=str(uuid4()),
                context=context,
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "tenant" in str(exc_info.value.detail).lower()
    
    @pytest.mark.asyncio
    async def test_require_admin_allows_admin_user(self):
        """require_admin should allow users with an explicit admin permission."""
        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=[Permission.ADMIN_USERS.value]
        )
        
        result = await require_admin(context=context)
        assert result == context
    
    @pytest.mark.asyncio
    async def test_require_admin_rejects_non_admin_user(self):
        """require_admin must reject users without admin permission.
        
        Rationale: Admin operations must be restricted.
        """
        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=["read", "write"]  # No admin
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(context=context)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Context Propagation
# ═══════════════════════════════════════════════════════════════════════════


class TestContextPropagation:
    """Verify context propagates correctly through middleware and async calls."""
    
    @pytest.mark.asyncio
    async def test_context_propagates_through_middleware_chain(self):
        """Context set by auth middleware must be available to route handlers.
        
        Rationale: Context must survive middleware chain.
        """
        from fastapi import FastAPI, Request
        from value_fabric.shared.identity.middleware import TenantContextMiddleware
        
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware)
        
        tenant_id = uuid4()
        captured_context = None
        
        @app.get("/test")
        async def test_route(request: Request):
            nonlocal captured_context
            captured_context = getattr(request.state, "governance_context", None)
            return {"ok": True}
        
        client = TestClient(app)
        
        # Mock JWT token in header
        token = f"Bearer mock_token_for_{tenant_id}"
        
        # The tenant kill switch fails closed (503) when Redis is absent
        # (RB-4, commit 493e63d2a); stub it ACTIVE so the request reaches the route.
        with (
            patch("value_fabric.shared.identity.resolvers.decode_jwt") as mock_decode,
            patch(
                "value_fabric.shared.identity.middleware.TenantKillSwitch"
            ) as mock_kill_switch,
        ):
            mock_decode.return_value = {
                "sub": str(uuid4()),
                "tenant_id": str(tenant_id),
                "permissions": ["read"],
            }
            mock_kill_switch.return_value.check_status = AsyncMock(
                return_value=TenantSuspensionStatus.ACTIVE
            )

            response = client.get("/test", headers={"Authorization": token})
            
            assert response.status_code == 200
            assert captured_context is not None
            assert captured_context.tenant_id == tenant_id
    
    @pytest.mark.asyncio
    async def test_context_propagates_to_background_tasks(self):
        """Context must propagate to FastAPI background tasks.
        
        Rationale: Background tasks must maintain tenant isolation.
        """
        from fastapi import BackgroundTasks
        from value_fabric.shared.identity.context import get_current_context, set_current_context
        
        tenant_id = uuid4()
        original_context = RequestContext(tenant_id=tenant_id, user_id=uuid4())
        
        captured_context = None
        
        async def background_task():
            nonlocal captured_context
            captured_context = get_current_context()
        
        # Set context
        set_current_context(original_context)
        
        # Execute background task
        tasks = BackgroundTasks()
        tasks.add_task(background_task)
        await tasks()
        
        # Verify context propagated
        assert captured_context is not None
        assert captured_context.tenant_id == tenant_id
    
    @pytest.mark.asyncio
    async def test_context_does_not_leak_between_requests(self):
        """Context from request A must not leak to request B.
        
        Rationale: Async context must be request-scoped, not global.
        """
        from value_fabric.shared.identity.context import (
            clear_current_context,
            get_current_context,
            set_current_context,
        )
        
        tenant_a = uuid4()
        tenant_b = uuid4()
        
        # Request A
        context_a = RequestContext(tenant_id=tenant_a, user_id=uuid4())
        set_current_context(context_a)
        
        retrieved_a = get_current_context()
        assert retrieved_a.tenant_id == tenant_a
        
        # Clear context (simulates request end)
        clear_current_context()
        
        # Request B
        context_b = RequestContext(tenant_id=tenant_b, user_id=uuid4())
        set_current_context(context_b)
        
        retrieved_b = get_current_context()
        assert retrieved_b.tenant_id == tenant_b
        assert retrieved_b.tenant_id != tenant_a


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Context Immutability
# ═══════════════════════════════════════════════════════════════════════════


class TestContextImmutability:
    """Verify context cannot be modified after creation."""
    
    def test_context_tenant_id_is_immutable(self):
        """tenant_id must not be modifiable after context creation.
        
        Rationale: Prevents privilege escalation by modifying context.
        """
        context = RequestContext(tenant_id=uuid4(), user_id=uuid4())
        original_tenant_id = context.tenant_id
        
        # Attempt to modify tenant_id
        with pytest.raises(AttributeError):
            context.tenant_id = uuid4()
        
        # Verify unchanged
        assert context.tenant_id == original_tenant_id
    
    def test_context_permissions_are_immutable(self):
        """Permissions list must not be modifiable after creation.
        
        Rationale: Prevents privilege escalation by adding permissions.
        """
        context = RequestContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            permissions=["read"]
        )
        
        # Attempt to add permission
        with pytest.raises((AttributeError, TypeError)):
            context.permissions.append("admin")
        
        # Verify unchanged
        assert "admin" not in context.permissions
        assert context.permissions == frozenset(["read"])


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Negative Path Scenarios
# ═══════════════════════════════════════════════════════════════════════════


class TestNegativePathContextScenarios:
    """Test context handling under adverse conditions."""
    
    @pytest.mark.asyncio
    async def test_expired_jwt_token_rejected(self):
        """Expired JWT tokens must be rejected.
        
        Rationale: Expired tokens should not grant access.
        """
        from jose import JWTError
        from value_fabric.shared.identity.jwt_wrapper import decode_jwt
        
        expired_token = "eyJ..."  # Mock expired token
        
        with pytest.raises(JWTError, match="expired"):
            decode_jwt(expired_token)
    
    @pytest.mark.asyncio
    async def test_tampered_jwt_token_rejected(self):
        """Tampered JWT tokens must be rejected.
        
        Attack scenario: Attacker modifies token payload.
        """
        from jose import JWTError
        from value_fabric.shared.identity.jwt_wrapper import decode_jwt
        
        tampered_token = "eyJ..."  # Mock tampered token
        
        with pytest.raises(JWTError, match="signature"):
            decode_jwt(tampered_token)
    
    @pytest.mark.asyncio
    async def test_revoked_api_key_rejected(self):
        """Revoked API keys must be rejected.
        
        Rationale: Revoked keys should not grant access.
        """
        from value_fabric.shared.identity.context_builders import extract_context_from_api_key
        
        revoked_api_key = "sk_test_revoked"
        
        with patch("value_fabric.shared.identity.context_builders.lookup_api_key") as mock_lookup:
            mock_lookup.return_value = None  # Key not found (revoked)
            
            with pytest.raises(HTTPException) as exc_info:
                await extract_context_from_api_key(revoked_api_key)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_sql_injection_in_tenant_id_rejected(self):
        """SQL injection attempts in tenant_id must be rejected.
        
        Attack scenario: Attacker provides SQL in tenant_id field.
        """
        from value_fabric.shared.identity.context_builders import extract_context_from_jwt
        
        # JWT with SQL injection attempt
        jwt_payload = {
            "sub": str(uuid4()),
            "tenant_id": "' OR '1'='1",  # SQL injection
            "permissions": ["read"],
        }
        
        with pytest.raises(ValueError, match="Invalid.*tenant_id"):
            extract_context_from_jwt(jwt_payload)
    
    @pytest.mark.asyncio
    async def test_xss_in_user_id_rejected(self):
        """XSS attempts in user_id must be rejected.
        
        Attack scenario: Attacker provides script tag in user_id.
        """
        from value_fabric.shared.identity.context_builders import extract_context_from_jwt
        
        # JWT with XSS attempt
        jwt_payload = {
            "sub": "<script>alert('xss')</script>",
            "tenant_id": str(uuid4()),
            "permissions": ["read"],
        }
        
        with pytest.raises(ValueError, match="Invalid.*user_id"):
            extract_context_from_jwt(jwt_payload)
    
    @pytest.mark.asyncio
    async def test_oversized_permissions_list_rejected(self):
        """Oversized permissions list must be rejected.
        
        Attack scenario: Attacker provides huge permissions list to DoS.
        """
        from value_fabric.shared.identity.context_builders import extract_context_from_jwt
        
        # JWT with 10,000 permissions
        jwt_payload = {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "permissions": [f"perm_{i}" for i in range(10000)],
        }
        
        with pytest.raises(ValueError, match="Too many permissions"):
            extract_context_from_jwt(jwt_payload)


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Cross-Layer Context Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossLayerContextValidation:
    """Verify context is validated consistently across all layers."""
    
    @pytest.mark.asyncio
    async def test_layer1_validates_tenant_context(self):
        """Layer 1 (ingestion) must validate tenant context.
        
        Rationale: Ingestion endpoints must enforce tenant isolation.
        """
        try:
            from layer1_ingestion.api.main import app
        except Exception as exc:
            pytest.skip(f"Layer 1 app unavailable in test environment: {exc}")
        
        client = TestClient(app)
        
        # Request without auth
        response = client.post("/v1/ingest", json={"url": "https://example.com"})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_layer2_validates_tenant_context(self):
        """Layer 2 (extraction) must validate tenant context.
        
        Rationale: Extraction endpoints must enforce tenant isolation.
        """
        try:
            from layer2_extraction.api.main import app
        except Exception as exc:
            pytest.skip(f"Layer 2 app unavailable in test environment: {exc}")
        
        client = TestClient(app)
        
        # Request without auth
        response = client.post("/v1/extract", json={"text": "test"})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_layer3_validates_tenant_context(self):
        """Layer 3 (knowledge) must validate tenant context.
        
        Rationale: Knowledge graph endpoints must enforce tenant isolation.
        """
        from src.api.main import app
        
        client = TestClient(app)
        
        # Request without auth
        response = client.get("/v1/entities")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_layer4_validates_tenant_context(self):
        """Layer 4 (agents) must validate tenant context.
        
        Rationale: Agent endpoints must enforce tenant isolation.
        """
        from services.layer4_agents.src.api.main import app
        
        client = TestClient(app)
        
        # Request without auth
        response = client.post("/v1/tools/invoke", json={"tool": "test"})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
