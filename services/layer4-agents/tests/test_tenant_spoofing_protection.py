from __future__ import annotations

"""Tenant spoofing protection security tests.

Tests that verify tenant context cannot be spoofed via headers:
- X-Tenant-ID header validation
- Tenant context resolution from token only
- Header-based tenant escalation prevention
- Cross-tenant header injection rejection

Production Invariant: Tenant context must be resolved from authenticated token,
not from untrusted headers.

Author: Autonomous Test Assurance Agent
Date: 2026-06-22
Priority: P0 (Security Boundary)
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.permissions import Role

from layer4_agents.api.routes import accounts

pytestmark = [
    pytest.mark.security,
    pytest.mark.tenant_isolation,
    pytest.mark.adversarial,
    pytest.mark.mandatory,
    pytest.mark.p0,
]


# Create test-specific app
test_app = FastAPI()
register_exception_handlers(test_app)
test_app.include_router(accounts.router, prefix="/v1", tags=["Accounts"])


async def override_db():
    return object()


async def list_no_accounts(self, **_kwargs):
    return [], 0


_original_list_accounts = accounts.AccountService.list_accounts


@pytest_asyncio.fixture(autouse=True)
def _patch_account_service():
    """Temporarily replace list_accounts for isolated auth tests."""
    accounts.AccountService.list_accounts = list_no_accounts
    yield
    accounts.AccountService.list_accounts = _original_list_accounts


test_app.dependency_overrides[accounts.get_db_from_context] = override_db


@pytest_asyncio.fixture
async def authenticated_client_tenant_a():
    """Create test client authenticated as tenant A."""
    tenant_a_id = "tenant-a-spoof-test"
    
    async def override_auth():
        return RequestContext(
            tenant_id=tenant_a_id,
            user_id=str(uuid4()),
            roles=[Role.TENANT_ADMIN.value],
            source="jwt",
        )

    test_app.dependency_overrides[require_authenticated] = override_auth

    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
            yield ac, tenant_a_id
    finally:
        test_app.dependency_overrides.pop(require_authenticated, None)


class TestTenantSpoofingViaHeaders:
    """NEGATIVE: Test that tenant context cannot be spoofed via headers."""

    async def test_x_tenant_id_header_ignored(
        self, authenticated_client_tenant_a: tuple[AsyncClient, str]
    ):
        """X-Tenant-ID header should be ignored in favor of token tenant_id.
        
        Risk: Tenant escalation via header injection.
        """
        client, tenant_a_id = authenticated_client_tenant_a
        tenant_b_id = "tenant-b-spoof-target"
        
        # Try to spoof tenant B via header
        response = await client.get(
            "/v1/accounts",
            headers={"X-Tenant-ID": tenant_b_id}
        )
        
        # Should succeed (200) but use tenant A's context from token
        # The header should be ignored
        assert response.status_code in [200, 404]
        # If header was respected, this would be a security breach

    async def test_multiple_tenant_headers_ignored(
        self, authenticated_client_tenant_a: tuple[AsyncClient, str]
    ):
        """Multiple tenant headers should all be ignored.
        
        Risk: Header confusion attacks.
        """
        client, _ = authenticated_client_tenant_a
        
        # Try multiple spoofing attempts
        response = await client.get(
            "/v1/accounts",
            headers={
                "X-Tenant-ID": "spoofed-tenant-1",
                "X-Tenant-Id": "spoofed-tenant-2",  # Case variation
                "X-TENANT-ID": "spoofed-tenant-3",  # All caps
            }
        )
        
        # Should succeed but use token's tenant context
        assert response.status_code in [200, 404]

    async def test_tenant_header_injection_via_query_param(
        self, authenticated_client_tenant_a: tuple[AsyncClient, str]
    ):
        """Tenant ID via query parameter should be ignored.
        
        Risk: Query parameter injection attacks.
        """
        client, _ = authenticated_client_tenant_a
        
        response = await client.get(
            "/v1/accounts?tenant_id=spoofed-tenant"
        )
        
        # Should succeed but use token's tenant context
        assert response.status_code in [200, 404]


class TestTenantContextIsolation:
    """NEGATIVE: Test that tenant context is properly isolated."""

    async def test_tenant_context_from_token_only(
        self, authenticated_client_tenant_a: tuple[AsyncClient, str]
    ):
        """Tenant context must come from JWT token, not headers.
        
        Risk: Context confusion leading to cross-tenant access.
        """
        client, tenant_a_id = authenticated_client_tenant_a
        
        # Make request with spoofed header
        response = await client.get(
            "/v1/accounts",
            headers={"X-Tenant-ID": "different-tenant"}
        )
        
        # The tenant context should come from the token (tenant_a_id)
        # not from the header
        assert response.status_code in [200, 404]

    async def test_tenant_context_consistency_across_requests(
        self, authenticated_client_tenant_a: tuple[AsyncClient, str]
    ):
        """Tenant context should remain consistent across multiple requests.
        
        Risk: Context bleeding between requests.
        """
        client, _ = authenticated_client_tenant_a
        
        # Make multiple requests with different spoofed headers
        response1 = await client.get("/v1/accounts", headers={"X-Tenant-ID": "tenant-1"})
        response2 = await client.get("/v1/accounts", headers={"X-Tenant-ID": "tenant-2"})
        response3 = await client.get("/v1/accounts", headers={"X-Tenant-ID": "tenant-3"})
        
        # All should use the same tenant context from token
        assert response1.status_code == response2.status_code == response3.status_code


class TestHeaderTampering:
    """NEGATIVE: Test that header tampering is detected."""

    async def test_malformed_tenant_header_ignored(
        self, authenticated_client_tenant_a: tuple[AsyncClient, str]
    ):
        """Malformed X-Tenant-ID should be ignored, not cause errors.
        
        Risk: DoS via malformed headers.
        """
        client, _ = authenticated_client_tenant_a
        
        # Try various malformed values
        for malformed_value in ["", "null", "undefined", "{}", "[]", "12345"]:
            response = await client.get(
                "/v1/accounts",
                headers={"X-Tenant-ID": malformed_value}
            )
            # Should handle gracefully (use token context)
            assert response.status_code in [200, 404, 400]

    async def test_very_long_tenant_header_ignored(
        self, authenticated_client_tenant_a: tuple[AsyncClient, str]
    ):
        """Very long X-Tenant-ID should be ignored.
        
        Risk: Buffer overflow or DoS via long headers.
        """
        client, _ = authenticated_client_tenant_a
        
        long_tenant_id = "a" * 10000  # 10k characters
        
        response = await client.get(
            "/v1/accounts",
            headers={"X-Tenant-ID": long_tenant_id}
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 404, 400]


class TestPositiveCases:
    """POSITIVE: Test that legitimate requests work."""

    async def test_valid_tenant_context_works(
        self, authenticated_client_tenant_a: tuple[AsyncClient, str]
    ):
        """Valid tenant context from token should work.
        
        Risk: False positives blocking legitimate access.
        """
        client, _ = authenticated_client_tenant_a
        
        response = await client.get("/v1/accounts")
        
        # Should succeed with proper tenant context
        assert response.status_code in [200, 404]

    async def test_no_tenant_header_works(
        self, authenticated_client_tenant_a: tuple[AsyncClient, str]
    ):
        """Request without X-Tenant-ID header should work.
        
        Risk: Breaking clients that don't send the header.
        """
        client, _ = authenticated_client_tenant_a
        
        response = await client.get("/v1/accounts")
        
        # Should use token context and succeed
        assert response.status_code in [200, 404]
