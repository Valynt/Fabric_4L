"""Tests for tenant lifecycle status enforcement and fail-closed behavior."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import status
from fastapi.responses import JSONResponse
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.tenant_status import enforce_tenant_status
from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus


@pytest.fixture
def test_tenant_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def make_ctx(test_tenant_id: UUID):
    def _builder(raw: dict | None = None) -> RequestContext:
        return RequestContext(
            tenant_id=test_tenant_id,
            user_id="user_123",
            roles=["member"],
            raw=raw or {},
        )

    return _builder


# ---------------------------------------------------------------------------
# Resolver Status Enforcement Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enforce_tenant_status_resolver_suspended(make_ctx) -> None:
    """When tenant_status_resolver returns 'suspended', returns 403."""
    ctx = make_ctx()
    resolver = AsyncMock(return_value="suspended")

    response = await enforce_tenant_status(ctx, tenant_status_resolver=resolver)
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    body = json.loads(response.body)
    assert body["error"] == "tenant_suspended"
    assert body["tenant_id"] == str(ctx.tenant_id)
    resolver.assert_called_once_with(str(ctx.tenant_id))


@pytest.mark.asyncio
async def test_enforce_tenant_status_resolver_pending(make_ctx) -> None:
    """When tenant_status_resolver returns 'pending', returns 403."""
    ctx = make_ctx()
    resolver = AsyncMock(return_value="pending")

    response = await enforce_tenant_status(ctx, tenant_status_resolver=resolver)
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    body = json.loads(response.body)
    assert body["error"] == "tenant_pending"


@pytest.mark.asyncio
async def test_enforce_tenant_status_resolver_deleted(make_ctx) -> None:
    """When tenant_status_resolver returns 'deleted', returns 404."""
    ctx = make_ctx()
    resolver = AsyncMock(return_value="deleted")

    response = await enforce_tenant_status(ctx, tenant_status_resolver=resolver)
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_404_NOT_FOUND

    body = json.loads(response.body)
    assert body["error"] == "tenant_not_found"


@pytest.mark.asyncio
async def test_enforce_tenant_status_resolver_active(make_ctx) -> None:
    """When tenant_status_resolver returns 'active', returns None (allow request)."""
    ctx = make_ctx()
    resolver = AsyncMock(return_value="active")

    response = await enforce_tenant_status(ctx, tenant_status_resolver=resolver)
    assert response is None


# ---------------------------------------------------------------------------
# Context Claims Fallback Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("status_claim", "expected_code", "expected_err"),
    [
        ("suspended", status.HTTP_403_FORBIDDEN, "tenant_suspended"),
        ("pending", status.HTTP_403_FORBIDDEN, "tenant_pending"),
        ("deleted", status.HTTP_404_NOT_FOUND, "tenant_not_found"),
    ],
)
@pytest.mark.asyncio
async def test_enforce_tenant_status_fallback_to_context_claims(
    make_ctx, status_claim: str, expected_code: int, expected_err: str
) -> None:
    """When resolver fails or is absent, fallback to ctx.raw claims."""
    ctx = make_ctx(raw={"tenant_status": status_claim})
    resolver = AsyncMock(side_effect=RuntimeError("DB unreachable"))

    response = await enforce_tenant_status(ctx, tenant_status_resolver=resolver)
    assert isinstance(response, JSONResponse)
    assert response.status_code == expected_code

    body = json.loads(response.body)
    assert body["error"] == expected_err


# ---------------------------------------------------------------------------
# Redis Kill-Switch Tri-State & Fail-Closed Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enforce_tenant_status_kill_switch_suspended(make_ctx) -> None:
    """When kill switch reports SUSPENDED, returns 403."""
    ctx = make_ctx()
    mock_ks = MagicMock()
    mock_ks.check_status = AsyncMock(return_value=TenantSuspensionStatus.SUSPENDED)

    with patch("value_fabric.shared.identity.tenant_status.TenantKillSwitch", return_value=mock_ks):
        response = await enforce_tenant_status(ctx, redis_client=MagicMock())
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        body = json.loads(response.body)
        assert body["error"] == "tenant_suspended"


@pytest.mark.asyncio
async def test_enforce_tenant_status_kill_switch_unknown_fails_closed_with_503(make_ctx) -> None:
    """When kill switch reports UNKNOWN (Redis unavailable), fail closed with 503."""
    ctx = make_ctx()
    mock_ks = MagicMock()
    mock_ks.check_status = AsyncMock(return_value=TenantSuspensionStatus.UNKNOWN)

    with patch("value_fabric.shared.identity.tenant_status.TenantKillSwitch", return_value=mock_ks):
        response = await enforce_tenant_status(ctx, redis_client=MagicMock())
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        body = json.loads(response.body)
        assert body["error"] == "tenant_status_unavailable"


@pytest.mark.asyncio
async def test_enforce_tenant_status_kill_switch_active(make_ctx) -> None:
    """When kill switch reports ACTIVE, allows request to proceed (None)."""
    ctx = make_ctx()
    mock_ks = MagicMock()
    mock_ks.check_status = AsyncMock(return_value=TenantSuspensionStatus.ACTIVE)

    with patch("value_fabric.shared.identity.tenant_status.TenantKillSwitch", return_value=mock_ks):
        response = await enforce_tenant_status(ctx, redis_client=MagicMock())
        assert response is None


@pytest.mark.asyncio
async def test_enforce_tenant_status_with_rate_limiter_redis_client(make_ctx) -> None:
    """Passes redis_client from rate_limiter when rate_limiter is provided."""
    ctx = make_ctx()
    mock_redis = MagicMock()
    mock_rate_limiter = MagicMock(redis_client=mock_redis)

    mock_ks = MagicMock()
    mock_ks.check_status = AsyncMock(return_value=TenantSuspensionStatus.ACTIVE)

    with patch("value_fabric.shared.identity.tenant_status.TenantKillSwitch", return_value=mock_ks) as ks_class:
        response = await enforce_tenant_status(ctx, rate_limiter=mock_rate_limiter)
        assert response is None
        ks_class.assert_called_once_with(mock_redis)
