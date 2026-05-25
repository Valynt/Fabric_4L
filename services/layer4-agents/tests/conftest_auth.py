"""Auth and governance test infrastructure for Layer 4 Agents tests.

This module provides reusable fixtures and utilities for testing auth/governance
behavior without bypassing security or weakening production middleware.
"""

from __future__ import annotations

from typing import Any, Callable, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from value_fabric.shared.identity.context import (
    RequestContext,
    RequestContextManager,
)
from value_fabric.shared.identity.middleware import GovernanceMiddleware
from value_fabric.shared.identity.permissions import Role


# =============================================================================
# Test-Specific Middleware Factory
# =============================================================================


class TestGovernanceMiddleware(GovernanceMiddleware):
    """Test-specific GovernanceMiddleware that accepts test context.

    This allows tests to provide a pre-configured RequestContext without
    requiring full JWT validation or external auth providers.
    """

    def __init__(
        self,
        app: Any,
        test_context: Optional[RequestContext] = None,
        **kwargs: Any,
    ) -> None:
        # Always disable auth enforcement in tests to allow test context injection
        super().__init__(app, enforce_authentication=False, **kwargs)
        self._test_context = test_context

    async def _resolve_identity(self, request: Request) -> Optional[RequestContext]:
        """Return test context if provided, otherwise use parent logic."""
        if self._test_context:
            return self._test_context
        return await super()._resolve_identity(request)


# =============================================================================
# Auth Context Fixtures
# =============================================================================


@pytest.fixture
def mock_auth_context():
    """Fixture that provides a mock RequestContext with full auth context.

    This fixture uses RequestContextManager to set a test RequestContext
    with tenant, user, and role information for auth-dependent tests.
    """
    ctx = RequestContext(
        tenant_id="test-tenant-001",
        user_id="test-user-001",
        roles=[Role.TENANT_ADMIN.value],
    )
    with RequestContextManager(ctx):
        yield ctx


@pytest.fixture
def mock_tenant_context():
    """Fixture that provides a mock RequestContext with tenant context only.

    This is a simpler fixture for tests that only need tenant isolation
    without full role-based authorization.
    """
    ctx = RequestContext(
        tenant_id="test-tenant-001",
        user_id="test-user-001",
        roles=[Role.TENANT_ADMIN.value],
    )
    with RequestContextManager(ctx):
        yield


@pytest.fixture
def mock_permission_context():
    """Fixture that provides a mock RequestContext with specific permissions.

    Use this fixture for tests that need to verify role-based authorization.
    """
    ctx = RequestContext(
        tenant_id="test-tenant-001",
        user_id="test-user-001",
        roles=[Role.TENANT_ADMIN.value, Role.TENANT_USER.value],
    )
    with RequestContextManager(ctx):
        yield ctx


@pytest.fixture
def mock_system_context():
    """Fixture that provides a mock RequestContext for system-level operations.

    This is for tests that require system identity rather than tenant identity.
    """
    ctx = RequestContext(
        tenant_id=None,  # System operations are not tenant-scoped
        user_id="system-001",
        roles=[Role.SYSTEM.value],
    )
    with RequestContextManager(ctx):
        yield


# =============================================================================
# Request Builder Fixture
# =============================================================================


@pytest.fixture
def mock_request_builder():
    """Fixture that builds mock FastAPI Request objects with auth headers.

    This is useful for testing route-level auth without full HTTP stack.
    """

    def _build_request(
        tenant_id: str = "test-tenant-001",
        user_id: str = "test-user-001",
        roles: list[str] = None,
        headers: dict[str, str] = None,
    ) -> Request:
        """Build a mock Request with auth context."""
        if roles is None:
            roles = [Role.TENANT_ADMIN.value]

        if headers is None:
            headers = {}

        # Add standard auth headers
        headers["X-Tenant-ID"] = tenant_id
        headers["X-User-ID"] = user_id
        headers["X-Roles"] = ",".join(roles)

        # Create mock request
        request = MagicMock(spec=Request)
        request.headers = headers
        request.url = MagicMock()
        request.url.path = "/test"
        request.method = "GET"

        return request

    return _build_request


# =============================================================================
# Middleware Fixture
# =============================================================================


@pytest.fixture
def test_governance_middleware():
    """Fixture that creates a TestGovernanceMiddleware instance.

    This fixture provides a test-specific middleware that can be configured
    with custom test context for auth/governance testing.
    """

    def _create_middleware(
        app: Any,
        test_context: Optional[RequestContext] = None,
        **kwargs: Any,
    ) -> TestGovernanceMiddleware:
        """Create a TestGovernanceMiddleware with optional test context."""
        return TestGovernanceMiddleware(
            app,
            test_context=test_context,
            **kwargs,
        )

    return _create_middleware
