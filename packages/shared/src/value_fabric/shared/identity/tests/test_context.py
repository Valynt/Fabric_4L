"""Tests for RequestContext and ContextVar helpers (shared/identity/context.py)."""

from uuid import uuid4

import pytest

from ..context import (
    RequestContext,
    RequestContextManager,
    get_request_context,
    require_context,
    set_request_context,
)
from ..permissions import Permission, Role


_TENANT = uuid4()


class TestRequestContext:
    """Tests for the RequestContext dataclass."""

    def test_minimal_creation(self):
        """Only tenant_id is required."""
        ctx = RequestContext(tenant_id=_TENANT)
        assert ctx.tenant_id == _TENANT
        assert ctx.user_id is None
        assert ctx.roles == []
        assert ctx.permissions == frozenset()
        assert ctx.source == "jwt_claim"

    def test_has_role_with_enum(self):
        ctx = RequestContext(tenant_id=_TENANT, roles=["analyst"])
        assert ctx.has_role(Role.ANALYST) is True
        assert ctx.has_role(Role.SUPER_ADMIN) is False

    def test_has_role_with_string(self):
        ctx = RequestContext(tenant_id=_TENANT, roles=["analyst"])
        assert ctx.has_role("analyst") is True
        assert ctx.has_role("super_admin") is False

    def test_has_any_role(self):
        ctx = RequestContext(tenant_id=_TENANT, roles=["analyst"])
        assert ctx.has_any_role(Role.ANALYST, Role.CONTENT_ADMIN) is True
        assert ctx.has_any_role(Role.SUPER_ADMIN, Role.SYSTEM) is False

    def test_has_permission(self):
        perms = frozenset({Permission.READ_SEARCH, Permission.READ_HEALTH})
        ctx = RequestContext(tenant_id=_TENANT, permissions=perms)
        assert ctx.has_permission(Permission.READ_SEARCH) is True
        assert ctx.has_permission(Permission.WRITE_INGESTION) is False

    def test_has_any_permission(self):
        perms = frozenset({Permission.READ_SEARCH})
        ctx = RequestContext(tenant_id=_TENANT, permissions=perms)
        assert ctx.has_any_permission(Permission.READ_SEARCH, Permission.WRITE_AGENTS) is True
        assert ctx.has_any_permission(Permission.WRITE_AGENTS) is False

    def test_has_all_permissions(self):
        perms = frozenset({Permission.READ_SEARCH, Permission.READ_HEALTH})
        ctx = RequestContext(tenant_id=_TENANT, permissions=perms)
        assert ctx.has_all_permissions(Permission.READ_SEARCH, Permission.READ_HEALTH) is True
        assert ctx.has_all_permissions(Permission.READ_SEARCH, Permission.WRITE_AGENTS) is False

    def test_to_log_dict_excludes_raw(self):
        ctx = RequestContext(
            tenant_id=_TENANT,
            user_id="user-1",
            roles=["analyst"],
            api_key_id="key-1",
            source="jwt",
            raw={"secret": "should-not-appear"},
        )
        d = ctx.to_log_dict()
        assert "raw" not in d
        assert d["tenant_id"] == str(_TENANT)
        assert d["user_id"] == "user-1"
        assert d["roles"] == ["analyst"]
        assert d["source"] == "jwt_claim"


class TestContextVarHelpers:
    """Tests for get/set/require_context."""

    def setup_method(self):
        """Ensure a clean context before each test."""
        set_request_context(None)

    def test_default_is_none(self):
        assert get_request_context() is None

    def test_set_and_get(self):
        ctx = RequestContext(tenant_id=_TENANT)
        set_request_context(ctx)
        assert get_request_context() is ctx

    def test_require_context_raises_when_unset(self):
        set_request_context(None)
        with pytest.raises(RuntimeError, match="No RequestContext is set"):
            require_context()

    def test_require_context_returns_when_set(self):
        ctx = RequestContext(tenant_id=_TENANT)
        set_request_context(ctx)
        assert require_context() is ctx

    def test_set_returns_token_for_reset(self):
        ctx1 = RequestContext(tenant_id=_TENANT, user_id="user-1")
        ctx2 = RequestContext(tenant_id=_TENANT, user_id="user-2")
        set_request_context(ctx1)
        token = set_request_context(ctx2)
        assert get_request_context() is ctx2
        # Reset using the token (low-level ContextVar API)
        # Just verify token was returned
        assert token is not None


class TestRequestContextManager:
    """Tests for RequestContextManager context manager."""

    def setup_method(self):
        set_request_context(None)

    def test_sets_and_resets_context(self):
        ctx = RequestContext(tenant_id=_TENANT, user_id="user-cm")
        assert get_request_context() is None
        with RequestContextManager(ctx):
            assert get_request_context() is ctx
        assert get_request_context() is None

    def test_nested_context_managers(self):
        ctx1 = RequestContext(tenant_id=_TENANT, user_id="outer")
        ctx2 = RequestContext(tenant_id=_TENANT, user_id="inner")
        with RequestContextManager(ctx1):
            assert get_request_context().user_id == "outer"
            with RequestContextManager(ctx2):
                assert get_request_context().user_id == "inner"
            assert get_request_context().user_id == "outer"
        assert get_request_context() is None
