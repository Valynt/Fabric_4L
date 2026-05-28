"""Tests for FastAPI identity dependencies (shared/identity/dependencies.py)."""

from uuid import uuid4

import pytest

from ..context import AUTH_SOURCE_JWT, RequestContext, RequestContextManager
from ..dependencies import require_admin, require_super_admin
from ..permissions import Permission, Role


_TENANT = uuid4()


def _admin_ctx(**kwargs):
    """Build a RequestContext with a valid auth source for admin tests."""
    defaults = dict(tenant_id=_TENANT, auth_source=AUTH_SOURCE_JWT)
    defaults.update(kwargs)
    return RequestContext(**defaults)


class TestRequireAdmin:
    """Regression tests for require_admin wildcard rejection (PROD-P0-006)."""

    @pytest.mark.asyncio
    async def test_super_admin_role_succeeds(self):
        ctx = _admin_ctx(roles=[Role.SUPER_ADMIN.value])
        result = await require_admin(context=ctx)
        assert result is ctx

    @pytest.mark.asyncio
    async def test_tenant_admin_role_succeeds(self):
        ctx = _admin_ctx(roles=[Role.TENANT_ADMIN.value])
        result = await require_admin(context=ctx)
        assert result is ctx

    @pytest.mark.asyncio
    async def test_content_admin_role_succeeds(self):
        ctx = _admin_ctx(roles=[Role.CONTENT_ADMIN.value])
        result = await require_admin(context=ctx)
        assert result is ctx

    @pytest.mark.asyncio
    async def test_analyst_role_is_rejected(self):
        ctx = _admin_ctx(roles=[Role.ANALYST.value])
        with pytest.raises(Exception) as exc_info:
            await require_admin(context=ctx)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_explicit_admin_permission_succeeds(self):
        ctx = _admin_ctx(
            roles=[Role.ANALYST.value],
            permissions=frozenset({Permission.ADMIN_SYSTEM.value}),
        )
        result = await require_admin(context=ctx)
        assert result is ctx

    @pytest.mark.asyncio
    async def test_wildcard_all_permission_is_rejected(self):
        """P0 regression: 'all' must not grant admin access."""
        ctx = _admin_ctx(
            roles=[Role.ANALYST.value],
            permissions=frozenset({"all"}),
        )
        with pytest.raises(Exception) as exc_info:
            await require_admin(context=ctx)
        assert exc_info.value.status_code == 403
        assert "not permitted" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_synthetic_admin_prefix_is_rejected(self):
        """P0 regression: arbitrary 'admin:*' must not grant admin access."""
        ctx = _admin_ctx(
            roles=[Role.ANALYST.value],
            permissions=frozenset({"admin:fake"}),
        )
        with pytest.raises(Exception) as exc_info:
            await require_admin(context=ctx)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_is_rejected(self):
        with pytest.raises(Exception) as exc_info:
            await require_admin(context=None)
        assert exc_info.value.status_code == 401


class TestRequireSuperAdmin:
    """Regression tests for require_super_admin (P1-004)."""

    @pytest.mark.asyncio
    async def test_super_admin_role_succeeds(self):
        ctx = _admin_ctx(roles=[Role.SUPER_ADMIN.value])
        result = await require_super_admin(context=ctx)
        assert result is ctx

    @pytest.mark.asyncio
    async def test_tenant_admin_role_is_rejected(self):
        ctx = _admin_ctx(roles=[Role.TENANT_ADMIN.value])
        with pytest.raises(Exception) as exc_info:
            await require_super_admin(context=ctx)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_content_admin_role_is_rejected(self):
        ctx = _admin_ctx(roles=[Role.CONTENT_ADMIN.value])
        with pytest.raises(Exception) as exc_info:
            await require_super_admin(context=ctx)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_analyst_role_is_rejected(self):
        ctx = _admin_ctx(roles=[Role.ANALYST.value])
        with pytest.raises(Exception) as exc_info:
            await require_super_admin(context=ctx)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_permission_is_rejected(self):
        """Super-admin gate must reject permission-only admin access."""
        ctx = _admin_ctx(
            roles=[Role.ANALYST.value],
            permissions=frozenset({Permission.ADMIN_SYSTEM.value}),
        )
        with pytest.raises(Exception) as exc_info:
            await require_super_admin(context=ctx)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_is_rejected(self):
        with pytest.raises(Exception) as exc_info:
            await require_super_admin(context=None)
        assert exc_info.value.status_code == 401
