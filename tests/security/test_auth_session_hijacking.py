"""Authentication session hijacking regression tests.

These tests cover OIDC cookie-session behavior without introducing password
authentication. They assert that browser sessions rotate, fail closed on
tenant mismatch, and clear cookies on logout.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret-123456789012345678901234567890")

from layer4_agents.tenants.api.routes import oidc
from value_fabric.shared.identity.jwt import decode_jwt, encode_jwt
from value_fabric.shared.identity.middleware import GovernanceMiddleware

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_TENANT_ID = UUID("00000000-0000-4000-8000-000000000002")


def _set_cookie_values(response: Response) -> list[str]:
    return [
        value.decode("latin1")
        for key, value in response.raw_headers
        if key.decode("latin1").lower() == "set-cookie"
    ]


class _Result:
    def __init__(self, *, mapping: dict | None = None, scalar: object | None = None) -> None:
        self._mapping = mapping
        self._scalar = scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self._mapping

    def scalar_one_or_none(self):
        return self._scalar


class _Db:
    def __init__(self, results: list[_Result]) -> None:
        self.results = results
        self.calls = 0

    async def execute(self, _statement, _params=None):
        result = self.results[self.calls]
        self.calls += 1
        return result

    async def flush(self) -> None:
        return None


class _OIDCClient:
    async def discover(self, _issuer_url):
        return {"token_endpoint": "https://idp.example.com/token"}

    async def exchange_code(self, **_kwargs):
        return {"id_token": "id-token"}

    async def verify_id_token(self, **_kwargs):
        return {"nonce": "nonce-123", "email": "user@example.com", "name": "Test User"}


@pytest.mark.asyncio
async def test_oidc_callback_replaces_preexisting_session_cookie_and_adds_jti(monkeypatch: pytest.MonkeyPatch) -> None:
    """OIDC callback must issue a fresh session cookie, not preserve attacker-fixed cookies."""
    oidc._auth_preauth_buckets.clear()
    monkeypatch.setattr(oidc, "OIDCClient", _OIDCClient)
    monkeypatch.setattr(oidc, "_get_client_secret", AsyncMock(return_value="client-secret"))

    tenant = SimpleNamespace(
        id=TENANT_ID,
        settings={
            "oidc": {
                "issuer_url": "https://idp.example.com",
                "client_id": "client-id",
                "client_secret": "client-secret",
                "enabled": True,
                "auto_provision_users": False,
            }
        },
    )
    user = SimpleNamespace(id=uuid4(), email="user@example.com", role="analyst", status="active", last_login_at=None)
    session_row = {
        "tenant_id": TENANT_ID,
        "nonce": "nonce-123",
        "code_verifier": "verifier",
        "redirect_uri": "https://app.example.com/login/callback",
        "expires_at": datetime.now(UTC) + timedelta(minutes=5),
    }
    db = _Db([
        _Result(mapping=session_row),
        _Result(),
        _Result(scalar=tenant),
        _Result(scalar=user),
    ])
    fixed_token = encode_jwt(TENANT_ID, user_id=str(user.id), roles=["analyst"], extra_claims={"jti": "fixed"})
    request = SimpleNamespace(client=SimpleNamespace(host="198.51.100.10"), cookies={"vf_session": fixed_token})
    response = Response()

    result = await oidc.oidc_callback(request, response, state="state-123", code="code-123", db=db)

    assert result["email"] == "user@example.com"
    cookies = _set_cookie_values(response)
    session_cookie = next(cookie for cookie in cookies if cookie.startswith("vf_session="))
    csrf_cookie = next(cookie for cookie in cookies if cookie.startswith("vf_csrf_token="))
    assert fixed_token not in session_cookie
    issued_token = session_cookie.split(";", 1)[0].split("=", 1)[1]
    issued_claims = decode_jwt(issued_token)
    assert issued_claims is not None
    assert issued_claims.jti
    assert issued_claims.jti != "fixed"
    assert "HttpOnly" in session_cookie
    assert "SameSite=strict" in session_cookie
    assert "vf_csrf_token=" in csrf_cookie


@pytest.mark.asyncio
async def test_refresh_requires_valid_session_and_rotates_session_and_csrf_cookies() -> None:
    user_id = uuid4()
    old_token = encode_jwt(TENANT_ID, user_id=str(user_id), roles=["analyst"], extra_claims={"jti": "old"})
    user = SimpleNamespace(id=user_id, email="user@example.com", role="analyst", status="active")
    response = Response()

    result = await oidc.auth_refresh(response=response, vf_session=old_token, _csrf_ok=None, db=_Db([_Result(scalar=user)]))

    assert result["user_id"] == str(user_id)
    cookies = _set_cookie_values(response)
    new_session = next(cookie for cookie in cookies if cookie.startswith("vf_session="))
    new_csrf = next(cookie for cookie in cookies if cookie.startswith("vf_csrf_token="))
    new_token = new_session.split(";", 1)[0].split("=", 1)[1]
    assert new_token != old_token
    claims = decode_jwt(new_token)
    assert claims is not None
    assert claims.jti and claims.jti != "old"
    assert "vf_csrf_token=" in new_csrf


@pytest.mark.asyncio
async def test_refresh_rejects_expired_invalid_and_inactive_sessions() -> None:
    user_id = uuid4()
    expired = encode_jwt(TENANT_ID, user_id=str(user_id), roles=["analyst"], expires_in_seconds=-1)
    inactive = encode_jwt(TENANT_ID, user_id=str(user_id), roles=["analyst"])

    with pytest.raises(Exception) as expired_exc:
        await oidc.auth_refresh(response=Response(), vf_session=expired, _csrf_ok=None, db=_Db([]))
    assert getattr(expired_exc.value, "status_code", None) == 401

    with pytest.raises(Exception) as invalid_exc:
        await oidc.auth_refresh(response=Response(), vf_session="not-a-jwt", _csrf_ok=None, db=_Db([]))
    assert getattr(invalid_exc.value, "status_code", None) == 401

    inactive_user = SimpleNamespace(id=user_id, email="user@example.com", role="analyst", status="deactivated")
    with pytest.raises(Exception) as inactive_exc:
        await oidc.auth_refresh(response=Response(), vf_session=inactive, _csrf_ok=None, db=_Db([_Result(scalar=inactive_user)]))
    assert getattr(inactive_exc.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_logout_expires_session_and_csrf_cookies() -> None:
    response = Response()

    result = await oidc.auth_logout(response=response, _csrf_ok=None)

    assert result == {"detail": "Logged out"}
    cookies = _set_cookie_values(response)
    assert any(cookie.startswith("vf_session=") and "Max-Age=0" in cookie for cookie in cookies)
    assert any(cookie.startswith("vf_csrf_token=") and "Max-Age=0" in cookie for cookie in cookies)


def test_stolen_session_cookie_with_mismatched_tenant_header_fails_closed() -> None:
    app = FastAPI()

    @app.get("/protected")
    async def protected():
        return {"ok": True}

    app.add_middleware(GovernanceMiddleware, rate_limiter=None)
    client = TestClient(app)
    token = encode_jwt(TENANT_ID, user_id=str(uuid4()), roles=["analyst"])

    response = client.get(
        "/protected",
        cookies={"vf_session": token},
        headers={"X-Tenant-ID": str(OTHER_TENANT_ID)},
    )

    assert response.status_code == 403
