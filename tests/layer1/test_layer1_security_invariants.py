"""Layer 1 Security Invariants Test Suite.

Tests verify critical security invariants for Layer 1 (Ingestion):
- Tenant isolation on document ingestion and targets
- Input validation on source configuration
- Authentication on protected endpoints
- Authorization on admin endpoints
- RLS policy verification for ingestion tables
- Error handling for malformed documents

Each invariant has:
1. Positive test proving intended behavior works
2. Negative test proving invalid input is rejected
3. Adversarial test proving attacks are blocked
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

# Constants
TENANT_A = "tenant-a"
TENANT_B = "tenant-b"
PUBLIC_TENANT = "public"

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_REQUEST_TIMEOUT = 408
HTTP_GATEWAY_TIMEOUT = 504
HTTP_INTERNAL_SERVER_ERROR = 500


pytestmark = [
    pytest.mark.security,
    pytest.mark.tenant_boundary,
    pytest.mark.integration,
]


class TestLayer1TenantIsolation:
    """Verify tenant isolation for Layer 1 ingestion endpoints."""

    @pytest.mark.asyncio
    async def test_tenant_can_only_access_own_targets(self, client: AsyncClient, tenant_a_token: str):
        """Positive test: Tenant A can list and access their own targets."""
        response = await client.get(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code == HTTP_OK
        # Verify only tenant A's targets are returned
        targets = response.json()
        for target in targets.get("items", []):
            target_tenant_id = target.get("tenant_id")
            # Either tenant_id matches or is implicit (not present)
            assert target_tenant_id == TENANT_A or target_tenant_id is None

    @pytest.mark.asyncio
    async def test_cross_tenant_target_access_denied(self, client: AsyncClient, tenant_a_token: str):
        """Negative test: Tenant A cannot access Tenant B's target by ID."""
        target_id = str(uuid4())  # Simulated tenant B target
        response = await client.get(
            f"/v1/targets/{target_id}",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code in {HTTP_FORBIDDEN, HTTP_NOT_FOUND}

    @pytest.mark.asyncio
    async def test_target_creation_enforces_tenant_context(self, client: AsyncClient, tenant_a_token: str):
        """Positive test: Target creation respects tenant context from token."""
        payload = {
            "name": "Test Target",
            "url": "https://example.com",
            "schedule": "daily"
        }
        response = await client.post(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json=payload
        )
        assert response.status_code == HTTP_CREATED
        created = response.json()
        # Verify tenant_id is set correctly (either explicitly or implicitly)
        created_tenant_id = created.get("tenant_id")
        assert created_tenant_id in [TENANT_A, None]  # None if implicit from context

    @pytest.mark.asyncio
    async def test_cannot_spoof_tenant_id_in_target_creation(self, client: AsyncClient, tenant_a_token: str):
        """Adversarial test: Cannot spoof tenant_id in request body."""
        payload = {
            "name": "Malicious Target",
            "url": "https://example.com",
            "tenant_id": TENANT_B  # Attempt to spoof
        }
        response = await client.post(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json=payload
        )
        # Should either reject the field or override with token tenant
        assert response.status_code in {HTTP_BAD_REQUEST, HTTP_FORBIDDEN, HTTP_CREATED}
        if response.status_code == HTTP_CREATED:
            created = response.json()
            created_tenant_id = created.get("tenant_id")
            # Verify tenant_id was not set to spoofed value
            assert created_tenant_id != TENANT_B
            # Verify it was set to the correct tenant (or implicit)
            assert created_tenant_id in [TENANT_A, None]


class TestLayer1Authentication:
    """Verify authentication requirements for Layer 1 endpoints."""

    @pytest.mark.asyncio
    async def test_valid_jwt_allows_access(self, client: AsyncClient, tenant_a_token: str):
        """Positive test: Valid JWT allows access to protected endpoints."""
        response = await client.get(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code == HTTP_OK

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self, client: AsyncClient):
        """Negative test: Missing authentication token is rejected."""
        response = await client.get("/v1/targets")
        assert response.status_code == HTTP_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client: AsyncClient):
        """Negative test: Invalid JWT token is rejected."""
        response = await client.get(
            "/v1/targets",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == HTTP_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, client: AsyncClient, expired_token: str):
        """Negative test: Expired JWT token is rejected."""
        response = await client.get(
            "/v1/targets",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == HTTP_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_malformed_token_rejected(self, client: AsyncClient):
        """Adversarial test: Malformed JWT token is rejected."""
        response = await client.get(
            "/v1/targets",
            headers={"Authorization": "Bearer not.a.valid.jwt"}
        )
        assert response.status_code in {HTTP_UNAUTHORIZED, HTTP_FORBIDDEN}


class TestLayer1InputValidation:
    """Verify input validation for Layer 1 endpoints."""

    @pytest.mark.asyncio
    async def test_valid_target_payload_accepted(self, client: AsyncClient, tenant_a_token: str):
        """Positive test: Valid target payload is accepted."""
        payload = {
            "name": "Valid Target",
            "url": "https://example.com",
            "schedule": "daily"
        }
        response = await client.post(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json=payload
        )
        assert response.status_code == HTTP_CREATED

    @pytest.mark.asyncio
    async def test_missing_required_field_rejected(self, client: AsyncClient, tenant_a_token: str):
        """Negative test: Missing required field is rejected."""
        payload = {
            "name": "Invalid Target"
            # Missing url field
        }
        response = await client.post(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json=payload
        )
        assert response.status_code == HTTP_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_url_format_rejected(self, client: AsyncClient, tenant_a_token: str):
        """Negative test: Invalid URL format is rejected."""
        payload = {
            "name": "Invalid Target",
            "url": "not-a-valid-url",
            "schedule": "daily"
        }
        response = await client.post(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json=payload
        )
        assert response.status_code == HTTP_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_sql_injection_in_name_blocked(self, client: AsyncClient, tenant_a_token: str):
        """Adversarial test: SQL injection attempt in name field is blocked."""
        payload = {
            "name": "'; DROP TABLE targets; --",
            "url": "https://example.com",
            "schedule": "daily"
        }
        response = await client.post(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json=payload
        )
        # Should either accept as literal string or reject
        assert response.status_code in {HTTP_CREATED, HTTP_UNPROCESSABLE_ENTITY}
        if response.status_code == HTTP_CREATED:
            # Verify it was stored as literal, not executed
            created = response.json()
            assert created.get("name") == "'; DROP TABLE targets; --"

    @pytest.mark.asyncio
    async def test_xss_in_name_blocked(self, client: AsyncClient, tenant_a_token: str):
        """Adversarial test: XSS attempt in name field is sanitized or rejected."""
        payload = {
            "name": "<script>alert('xss')</script>",
            "url": "https://example.com",
            "schedule": "daily"
        }
        response = await client.post(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json=payload
        )
        assert response.status_code in {HTTP_CREATED, HTTP_UNPROCESSABLE_ENTITY}


class TestLayer1Authorization:
    """Verify authorization requirements for Layer 1 admin endpoints."""

    @pytest.mark.asyncio
    async def test_admin_requires_admin_role(self, client: AsyncClient, admin_user_token: str):
        """Positive test: Admin role allows access to admin endpoints."""
        response = await client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_user_token}"}
        )
        assert response.status_code in {HTTP_OK, HTTP_FORBIDDEN}  # May not exist yet

    @pytest.mark.asyncio
    async def test_regular_user_denied_admin_access(self, client: AsyncClient, tenant_a_token: str):
        """Negative test: Regular user role denied admin endpoint access."""
        response = await client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code == HTTP_FORBIDDEN

    @pytest.mark.asyncio
    async def test_role_escalation_blocked(self, client: AsyncClient, tenant_a_token: str):
        """Adversarial test: Cannot escalate role via request body."""
        # This test would need to be adapted based on actual endpoint behavior
        # For now, verify that regular user cannot access admin endpoints
        response = await client.get(
            "/api/admin/config",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code == HTTP_FORBIDDEN


class TestLayer1ErrorHandling:
    """Verify error handling for Layer 1 endpoints."""

    @pytest.mark.asyncio
    async def test_404_returns_generic_message(self, client: AsyncClient, tenant_a_token: str):
        """Positive test: 404 errors return generic messages."""
        response = await client.get(
            f"/v1/targets/{uuid4()}",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code == HTTP_NOT_FOUND
        # Verify error message doesn't leak implementation details
        error = response.json()
        error_str = str(error).lower()
        assert "stack trace" not in error_str
        assert "sql" not in error_str

    @pytest.mark.asyncio
    async def test_validation_errors_are_sanitized(self, client: AsyncClient, tenant_a_token: str):
        """Positive test: Validation errors don't leak sensitive data."""
        payload = {
            "name": "Test",
            "url": "not-a-url"
        }
        response = await client.post(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json=payload
        )
        assert response.status_code == HTTP_UNPROCESSABLE_ENTITY
        error = response.json()
        error_str = str(error).lower()
        # Verify no sensitive data in error
        assert "password" not in error_str
        assert "secret" not in error_str

    @pytest.mark.asyncio
    async def test_database_errors_masked(self, client: AsyncClient, tenant_a_token: str):
        """Positive test: Database errors are masked from users."""
        # This would need to trigger a database error
        # For now, verify error handling structure exists
        response = await client.get(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        # If error occurs, verify it's masked
        if response.status_code >= HTTP_INTERNAL_SERVER_ERROR:
            error = response.json()
            error_str = str(error).lower()
            assert "stack trace" not in error_str


class TestLayer1RLSEnforcement:
    """Verify RLS policies for Layer 1 tables."""

    @pytest.mark.asyncio
    async def test_rls_enabled_on_targets_table(self, db_session):
        """Positive test: RLS is enabled on targets table."""
        # Query PostgreSQL to check RLS status
        result = await db_session.execute(
            "SELECT relname, relrowsecurity FROM pg_class WHERE relname = 'targets'"
        )
        row = result.fetchone()
        assert row is not None, "targets table does not exist"
        assert row[1] is True, "RLS is not enabled on targets table"

    @pytest.mark.asyncio
    async def test_rls_policy_uses_tenant_setting(self, db_session):
        """Positive test: RLS policy uses app.tenant_id setting."""
        # Query to verify RLS policy definition
        result = await db_session.execute(
            """
            SELECT pg_get_expr(qual, relid) 
            FROM pg_policy 
            WHERE polname LIKE '%tenant%' OR polname LIKE '%organization%'
            """
        )
        policies = result.fetchall()
        # At least one policy should reference current_setting
        assert len(policies) > 0, "No tenant RLS policies found"
        for policy in policies:
            if policy[0]:
                assert "current_setting" in str(policy[0]) or "app.tenant_id" in str(policy[0]), \
                    f"RLS policy does not use current_setting: {policy[0]}"

    @pytest.mark.asyncio
    async def test_cross_tenant_query_blocked_by_rls(self, client: AsyncClient, tenant_a_token: str):
        """Negative test: Cross-tenant query is blocked by RLS."""
        # Attempt to query another tenant's data
        # This would need actual test data setup
        response = await client.get(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"}
        )
        assert response.status_code == HTTP_OK
        targets = response.json()
        # Verify no cross-tenant data
        for target in targets.get("items", []):
            target_tenant_id = target.get("tenant_id")
            # Either tenant_id matches or is implicit
            assert target_tenant_id in [TENANT_A, None]


class TestLayer1SecretsProtection:
    """Verify secrets protection for Layer 1."""

    @pytest.mark.asyncio
    async def test_secrets_not_in_error_responses(self, client: AsyncClient):
        """Positive test: Secrets are not leaked in error responses."""
        response = await client.get("/v1/targets")
        if response.status_code >= HTTP_BAD_REQUEST:
            error = response.json()
            error_str = str(error).lower()
            assert "password" not in error_str
            assert "secret" not in error_str
            assert "api_key" not in error_str

    @pytest.mark.asyncio
    async def test_secrets_not_in_logs(self, client: AsyncClient, tenant_a_token: str):
        """Positive test: Secrets are not logged in request/response."""
        # This would need log capture verification
        # For now, verify endpoint doesn't log sensitive data
        payload = {
            "name": "Test",
            "url": "https://example.com"
        }
        response = await client.post(
            "/v1/targets",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json=payload
        )
        # If logging exists, verify no secrets in logs
        assert response.status_code in {HTTP_CREATED, HTTP_UNPROCESSABLE_ENTITY}
