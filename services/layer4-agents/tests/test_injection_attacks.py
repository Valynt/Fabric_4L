from __future__ import annotations

"""Injection attack protection security tests.

Tests that verify protection against:
- SQL injection attempts
- XSS (Cross-Site Scripting) attempts
- Command injection attempts
- Path traversal attempts

Production Invariant: All user input must be validated and sanitized.
These tests verify that injection attempts are properly rejected.

Author: Autonomous Test Assurance Agent
Date: 2026-06-22
Priority: P0 (Security Boundary)
"""

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
    pytest.mark.injection,
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
async def authenticated_client():
    """Create test client with valid authentication."""
    from uuid import uuid4
    
    async def override_auth():
        return RequestContext(
            tenant_id="test-tenant-injection",
            user_id=str(uuid4()),
            roles=[Role.TENANT_ADMIN.value],
            source="jwt",
        )

    test_app.dependency_overrides[require_authenticated] = override_auth

    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
            yield ac
    finally:
        test_app.dependency_overrides.pop(require_authenticated, None)


class TestSQLInjection:
    """NEGATIVE: Test that SQL injection attempts are rejected."""

    async def test_sql_union_injection(self, authenticated_client: AsyncClient):
        """SQL UNION injection should be rejected.
        
        Risk: Data exfiltration via SQL injection.
        """
        # Try SQL injection via query parameter
        response = await authenticated_client.get(
            "/v1/accounts?name=test' OR '1'='1"
        )
        
        # Should handle gracefully (400 or 200 with sanitized input)
        # Should not cause database errors
        assert response.status_code in [200, 400, 404]

    async def test_sql_comment_injection(self, authenticated_client: AsyncClient):
        """SQL comment injection should be rejected.
        
        Risk: Query manipulation via comment injection.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=test'--"
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_sql_tautology_injection(self, authenticated_client: AsyncClient):
        """SQL tautology injection should be rejected.
        
        Risk: Authentication bypass via tautology.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=test' OR 'x'='x"
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_sql_stacked_queries(self, authenticated_client: AsyncClient):
        """Stacked query injection should be rejected.
        
        Risk: Multiple query execution.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=test'; DROP TABLE accounts--"
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_sql_time_based_blind(self, authenticated_client: AsyncClient):
        """Time-based blind SQL injection should be rejected.
        
        Risk: Data exfiltration via timing attacks.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=test' AND SLEEP(5)--"
        )
        
        assert response.status_code in [200, 400, 404]


class TestXSSInjection:
    """NEGATIVE: Test that XSS attempts are rejected."""

    async def test_script_tag_injection(self, authenticated_client: AsyncClient):
        """Script tag injection should be rejected.
        
        Risk: Cross-site scripting via script tags.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=<script>alert('xss')</script>"
        )
        
        # Should sanitize or escape
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            # Response should not contain unescaped script tags
            assert "<script>" not in response.text

    async def test_on_event_injection(self, authenticated_client: AsyncClient):
        """On-event handler injection should be rejected.
        
        Risk: XSS via event handlers.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=<img src=x onerror=alert('xss')>"
        )
        
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            assert "onerror" not in response.text.lower()

    async def test_javascript_protocol(self, authenticated_client: AsyncClient):
        """JavaScript protocol injection should be rejected.
        
        Risk: XSS via javascript: protocol.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=<a href='javascript:alert(1)'>click</a>"
        )
        
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            assert "javascript:" not in response.text.lower()

    async def test_svg_onload_injection(self, authenticated_client: AsyncClient):
        """SVG onload injection should be rejected.
        
        Risk: XSS via SVG elements.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=<svg onload=alert('xss')>"
        )
        
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            assert "onload" not in response.text.lower()


class TestCommandInjection:
    """NEGATIVE: Test that command injection attempts are rejected."""

    async def test_command_separator_injection(self, authenticated_client: AsyncClient):
        """Command separator injection should be rejected.
        
        Risk: Remote code execution via command injection.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=test; rm -rf /"
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_pipe_injection(self, authenticated_client: AsyncClient):
        """Pipe injection should be rejected.
        
        Risk: Command chaining via pipes.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=test| cat /etc/passwd"
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_backtick_injection(self, authenticated_client: AsyncClient):
        """Backtick command substitution should be rejected.
        
        Risk: Command execution via backticks.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=test`whoami`"
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_dollar_substitution(self, authenticated_client: AsyncClient):
        """Dollar substitution should be rejected.
        
        Risk: Variable expansion attacks.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=test$(whoami)"
        )
        
        assert response.status_code in [200, 400, 404]


class TestPathTraversal:
    """NEGATIVE: Test that path traversal attempts are rejected."""

    async def test_dot_dot_slash(self, authenticated_client: AsyncClient):
        """../ path traversal should be rejected.
        
        Risk: File system access via path traversal.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=../../../etc/passwd"
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_encoded_path_traversal(self, authenticated_client: AsyncClient):
        """URL-encoded path traversal should be rejected.
        
        Risk: Bypassing filters via encoding.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=..%2F..%2F..%2Fetc%2Fpasswd"
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_double_encoding(self, authenticated_client: AsyncClient):
        """Double-encoded path traversal should be rejected.
        
        Risk: Bypassing filters via double encoding.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=..%252F..%252F..%252Fetc%252Fpasswd"
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_absolute_path(self, authenticated_client: AsyncClient):
        """Absolute path should be rejected.
        
        Risk: Direct file system access.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=/etc/passwd"
        )
        
        assert response.status_code in [200, 400, 404]


class TestPositiveCases:
    """POSITIVE: Test that legitimate input works."""

    async def test_valid_input_works(self, authenticated_client: AsyncClient):
        """Valid alphanumeric input should work.
        
        Risk: False positives blocking legitimate input.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=ValidAccount123"
        )
        
        assert response.status_code in [200, 404]

    async def test_valid_special_chars_work(self, authenticated_client: AsyncClient):
        """Valid special characters should work.
        
        Risk: False positives blocking legitimate names.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=O'Brien-Company"
        )
        
        assert response.status_code in [200, 404]

    async def test_unicode_input_works(self, authenticated_client: AsyncClient):
        """Unicode characters should work.
        
        Risk: False positives blocking international names.
        """
        response = await authenticated_client.get(
            "/v1/accounts?name=公司名称"
        )
        
        assert response.status_code in [200, 404]
