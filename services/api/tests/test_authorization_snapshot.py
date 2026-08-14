from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException, Request, Response
from value_fabric.shared.identity.fabric_auth import AuthContext

from app.core.auth_directory import AuthDirectory
from app.routers.clerk_auth import get_authorization_snapshot


def _auth(*, tenant_id: str = "ten_1") -> AuthContext:
    now = int(datetime.now(UTC).timestamp())
    return AuthContext(
        clerk_user_id="user_1",
        clerk_org_id="org_1",
        user_id="u1",
        tenant_id=tenant_id,
        roles=frozenset(),
        permissions=frozenset(),
        request_id="req_1",
        iat=now,
        exp=now + 600,
        kid="test-key",
    )


def _directory() -> AuthDirectory:
    directory = AuthDirectory()
    directory.upsert_user(
        id="u1", clerk_user_id="user_1", email=None, display_name=None, status="active"
    )
    directory.upsert_tenant(
        id="ten_1", clerk_org_id="org_1", name="Acme", slug="acme", status="active"
    )
    directory.upsert_membership(
        clerk_org_id="org_1",
        clerk_user_id="user_1",
        clerk_membership_id="mem_1",
        role="tenant_admin",
        status="active",
    )
    directory.set_tenant_entitlements("ten_1", {"billing.manage"})
    directory.grant_account_access(tenant_id="ten_1", user_id="u1", account_id="acc_1")
    return directory


def _request() -> Request:
    request = Request(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/auth/authorization-snapshot",
            "headers": [],
        }
    )
    request.state.clerk_claims = {"sid": "sess_1", "exp": int(datetime.now(UTC).timestamp()) + 600}
    return request


@pytest.mark.asyncio
async def test_tenant_snapshot_is_backend_issued_and_no_store() -> None:
    response = Response()
    snapshot = await get_authorization_snapshot(
        request=_request(),
        response=response,
        x_account_id=None,
        auth=_auth(),
        directory=_directory(),
    )

    assert snapshot.source == "backend"
    assert snapshot.schema_version == "1"
    assert snapshot.identity.session_discriminator == "sess_1"
    assert snapshot.tenant.fabric_tenant_id == "ten_1"
    assert snapshot.account_scope.account_id is None
    assert snapshot.account_scope.scope_type == "tenant"
    assert snapshot.roles == ["tenant_admin"]
    assert snapshot.entitlements == ["billing.manage"]
    assert response.headers["Cache-Control"] == "private, no-store"
    issued = datetime.fromisoformat(snapshot.issued_at)
    expires = datetime.fromisoformat(snapshot.expires_at)
    assert 0 < (expires - issued).total_seconds() <= 300


@pytest.mark.asyncio
async def test_account_snapshot_echoes_exact_authorized_scope() -> None:
    snapshot = await get_authorization_snapshot(
        request=_request(),
        response=Response(),
        x_account_id="acc_1",
        auth=_auth(),
        directory=_directory(),
    )
    assert snapshot.account_scope.scope_type == "account"
    assert snapshot.account_scope.account_id == "acc_1"


@pytest.mark.asyncio
@pytest.mark.parametrize("account_id", ["missing", "foreign", "acc_1\ninvalid"])
async def test_account_denials_are_indistinguishable(account_id: str) -> None:
    directory = _directory()
    if account_id == "foreign":
        directory.grant_account_access(tenant_id="ten_2", user_id="u1", account_id="foreign")

    with pytest.raises(HTTPException) as exc_info:
        await get_authorization_snapshot(
            request=_request(),
            response=Response(),
            x_account_id=account_id,
            auth=_auth(),
            directory=directory,
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "code": "account_scope_denied",
        "message": "The requested account scope is not authorized.",
        "request_id": "req_1",
    }


@pytest.mark.asyncio
async def test_missing_session_discriminator_fails_closed() -> None:
    request = _request()
    request.state.clerk_claims = {"exp": int(datetime.now(UTC).timestamp()) + 600}
    with pytest.raises(HTTPException) as exc_info:
        await get_authorization_snapshot(
            request=request,
            response=Response(),
            x_account_id=None,
            auth=_auth(),
            directory=_directory(),
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_snapshot_expiry_is_bounded_by_entitlement_validity() -> None:
    now = int(datetime.now(UTC).timestamp())
    directory = _directory()
    directory.set_tenant_entitlements("ten_1", {"billing.manage"}, valid_until=now + 30)
    snapshot = await get_authorization_snapshot(
        request=_request(),
        response=Response(),
        x_account_id=None,
        auth=_auth(),
        directory=directory,
    )
    assert int(datetime.fromisoformat(snapshot.expires_at).timestamp()) == now + 30
