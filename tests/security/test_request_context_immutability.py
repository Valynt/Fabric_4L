"""
Test RequestContext immutability invariants.

Verifies that tenant_id and permissions fields cannot be modified after construction,
preventing privilege escalation attacks.

Critical P0 test - immutability bypass could allow tenant context switching.
"""

from uuid import uuid4

import pytest
from value_fabric.shared.identity.context import (
    AUTH_SOURCE_JWT,
    ISOLATION_TIER_SHARED,
    RequestContext,
    clear_current_context,
    get_current_context,
    set_current_context,
)
from value_fabric.shared.identity.permissions import Permission, Role


class TestRequestContextImmutability:
    """Test suite for RequestContext immutability invariants."""

    def test_tenant_id_cannot_be_modified_after_construction(self):
        """
        NEGATIVE: tenant_id field should be immutable after construction.
        Tests for direct assignment attempts.
        """
        tenant_id = str(uuid4())
        context = RequestContext(tenant_id=tenant_id, user_id="user123")

        with pytest.raises(AttributeError) as exc_info:
            context.tenant_id = str(uuid4())

        assert "cannot assign to immutable RequestContext field 'tenant_id'" in str(exc_info.value)

    def test_permissions_cannot_be_modified_after_construction(self):
        """
        NEGATIVE: permissions field should be immutable after construction.
        Tests for permission escalation attempts.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            permissions={Permission.READ_HEALTH},
        )

        with pytest.raises(AttributeError) as exc_info:
            context.permissions = {Permission.READ_HEALTH, Permission.READ_METRICS}

        assert "cannot assign to immutable RequestContext field 'permissions'" in str(exc_info.value)

    def test_mutable_fields_can_be_modified(self):
        """
        POSITIVE: Non-immutable fields should remain mutable.
        Tests that only security-critical fields are immutable.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            roles=["user"],
        )

        # These fields should be mutable
        context.user_id = "different_user"
        context.roles = ["admin"]
        context.accessed_tenant_ids.add(str(uuid4()))

        assert context.user_id == "different_user"
        assert context.roles == ["admin"]

    def test_tenant_id_set_during_construction(self):
        """
        POSITIVE: tenant_id can be set during construction.
        Tests normal initialization flow.
        """
        tenant_id = str(uuid4())
        context = RequestContext(tenant_id=tenant_id, user_id="user123")

        assert context.tenant_id == tenant_id

    def test_permissions_set_during_construction(self):
        """
        POSITIVE: permissions can be set during construction.
        Tests normal initialization flow.
        """
        permissions = {Permission.READ_HEALTH, Permission.READ_METRICS}
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            permissions=permissions,
        )

        assert context.permissions == permissions

    def test_tenant_id_normalization_during_construction(self):
        """
        POSITIVE: tenant_id is normalized during construction.
        Tests UUID string handling.
        """
        tenant_uuid = uuid4()
        context = RequestContext(tenant_id=tenant_uuid, user_id="user123")

        assert str(context.tenant_id) == str(tenant_uuid)

    def test_permissions_converted_to_frozenset(self):
        """
        POSITIVE: permissions are converted to frozenset during construction.
        Tests immutability of the set itself.
        """
        permissions = {Permission.READ_HEALTH}
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            permissions=permissions,
        )

        assert isinstance(context.permissions, frozenset)

    def test_accessed_tenant_ids_is_mutable(self):
        """
        POSITIVE: accessed_tenant_ids should remain mutable for audit tracking.
        Tests that audit bookkeeping fields remain functional.
        """
        context = RequestContext(tenant_id=str(uuid4()), user_id="user123")

        tenant_id_1 = str(uuid4())
        tenant_id_2 = str(uuid4())

        context.accessed_tenant_ids.add(tenant_id_1)
        context.accessed_tenant_ids.add(tenant_id_2)

        assert tenant_id_1 in context.accessed_tenant_ids
        assert tenant_id_2 in context.accessed_tenant_ids

    def test_privileged_session_start_is_mutable(self):
        """
        POSITIVE: privileged_session_start should remain mutable for audit tracking.
        Tests that audit bookkeeping fields remain functional.
        """
        context = RequestContext(tenant_id=str(uuid4()), user_id="user123")

        import time
        start_time = time.time()
        context.privileged_session_start = start_time

        assert context.privileged_session_start == start_time


class TestContextVarIsolation:
    """Test suite for ContextVar isolation invariants."""

    @pytest.mark.asyncio
    async def test_context_var_isolation_between_tasks(self):
        """
        POSITIVE: ContextVar should be isolated between async tasks.
        Tests for context bleeding across concurrent operations.
        """
        import asyncio

        async def _set_context_and_return_tenant(context):
            set_current_context(context)
            await asyncio.sleep(0)  # force context switch
            ctx = get_current_context()
            return ctx.tenant_id if ctx is not None else None

        tenant_a = str(uuid4())
        tenant_b = str(uuid4())

        ctx_a = RequestContext(tenant_id=tenant_a, user_id="user_a")
        ctx_b = RequestContext(tenant_id=tenant_b, user_id="user_b")

        task_a = asyncio.create_task(_set_context_and_return_tenant(ctx_a))
        task_b = asyncio.create_task(_set_context_and_return_tenant(ctx_b))

        result_a, result_b = await asyncio.gather(task_a, task_b)

        assert result_a == tenant_a
        assert result_b == tenant_b
        assert get_current_context() is None

    def test_clear_current_context_removes_context(self):
        """
        POSITIVE: clear_current_context should remove the context.
        Tests for context cleanup.
        """
        context = RequestContext(tenant_id=str(uuid4()), user_id="user123")
        set_current_context(context)

        assert get_current_context() is not None

        clear_current_context()

        assert get_current_context() is None

    def test_set_current_context_overwrites_existing(self):
        """
        POSITIVE: set_current_context should overwrite existing context.
        Tests for context replacement.
        """
        tenant_id_1 = str(uuid4())
        tenant_id_2 = str(uuid4())

        context1 = RequestContext(tenant_id=tenant_id_1, user_id="user1")
        set_current_context(context1)

        context2 = RequestContext(tenant_id=tenant_id_2, user_id="user2")
        set_current_context(context2)

        current = get_current_context()
        assert current.tenant_id == tenant_id_2


class TestRequestContextRoleMethods:
    """Test suite for RequestContext role and permission methods."""

    def test_has_role_with_valid_role(self):
        """
        POSITIVE: has_role should return True for valid role.
        Tests role checking functionality.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            roles=["tenant_admin"],
        )

        assert context.has_role("tenant_admin") is True
        assert context.has_role(Role.TENANT_ADMIN) is True

    def test_has_role_with_invalid_role(self):
        """
        NEGATIVE: has_role should return False for invalid role.
        Tests role checking rejection.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            roles=["read_only"],
        )

        assert context.has_role("tenant_admin") is False
        assert context.has_role(Role.TENANT_ADMIN) is False

    def test_has_any_role_with_multiple_roles(self):
        """
        POSITIVE: has_any_role should return True if any role matches.
        Tests multiple role checking.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            roles=["read_only"],
        )

        assert context.has_any_role("tenant_admin", "read_only", "super_admin") is True

    def test_is_super_admin_with_super_admin_role(self):
        """
        POSITIVE: is_super_admin should return True for super_admin role.
        Tests super-admin detection.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            roles=["super_admin"],
        )

        assert context.is_super_admin() is True

    def test_is_super_admin_without_super_admin_role(self):
        """
        NEGATIVE: is_super_admin should return False without super_admin role.
        Tests super-admin rejection.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            roles=["tenant_admin"],
        )

        assert context.is_super_admin() is False

    def test_has_permission_with_valid_permission(self):
        """
        POSITIVE: has_permission should return True for valid permission.
        Tests permission checking functionality.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            permissions={Permission.READ_HEALTH},
        )

        assert context.has_permission(Permission.READ_HEALTH) is True
        assert context.has_permission("read:health") is True

    def test_has_permission_with_invalid_permission(self):
        """
        NEGATIVE: has_permission should return False for invalid permission.
        Tests permission checking rejection.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            permissions={Permission.READ_HEALTH},
        )

        assert context.has_permission(Permission.READ_METRICS) is False
        assert context.has_permission("read:metrics") is False


class TestRequestContextAuthSourceNormalization:
    """Test suite for auth source normalization invariants."""

    @pytest.mark.temporary_compat
    def test_auth_source_normalization_jwt(self):
        """
        POSITIVE: Auth source 'jwt' should be normalized to 'jwt_claim'.
        Tests legacy alias handling.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            source="jwt",
        )

        assert context.auth_source == AUTH_SOURCE_JWT

    @pytest.mark.temporary_compat
    def test_auth_source_normalization_bearer(self):
        """
        POSITIVE: Auth source 'bearer' should be normalized to 'jwt_claim'.
        Tests legacy alias handling.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            source="bearer",
        )

        assert context.auth_source == AUTH_SOURCE_JWT

    @pytest.mark.temporary_compat
    def test_auth_source_normalization_api_key(self):
        """
        POSITIVE: Auth source 'api-key' should be normalized to 'api_key'.
        Tests legacy alias handling.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            source="api-key",
        )

        assert context.auth_source == "api_key"

    def test_auth_source_normalization_unknown(self):
        """
        POSITIVE: Unknown auth source should remain as-is (no normalization).
        Tests fallback handling - actual behavior is to preserve unknown sources.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            source="invalid_source",
        )

        # Unknown sources are preserved as-is in actual implementation
        assert context.auth_source == "invalid_source"


class TestRequestContextIsolationTier:
    """Test suite for isolation tier invariants."""

    def test_default_isolation_tier_is_shared(self):
        """
        POSITIVE: Default isolation tier should be 'shared'.
        Tests default configuration.
        """
        context = RequestContext(tenant_id=str(uuid4()), user_id="user123")

        assert context.isolation_tier == ISOLATION_TIER_SHARED

    def test_isolation_tier_can_be_set(self):
        """
        POSITIVE: Isolation tier can be set during construction.
        Tests tier configuration.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            isolation_tier="schema",
        )

        assert context.isolation_tier == "schema"

    def test_isolation_tier_is_mutable(self):
        """
        POSITIVE: Isolation tier should remain mutable.
        Tests tier reconfiguration capability.
        """
        context = RequestContext(
            tenant_id=str(uuid4()),
            user_id="user123",
            isolation_tier=ISOLATION_TIER_SHARED,
        )

        context.isolation_tier = "database"

        assert context.isolation_tier == "database"
