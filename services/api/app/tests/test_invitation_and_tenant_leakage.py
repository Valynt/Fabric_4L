"""Regression tests for invitation flow and cross-tenant data leakage.

These tests verify:
1. Invitation lifecycle (invite -> accept -> login) bound to a single-use
   invite token — accepting an invitation REQUIRES the token; knowledge of
   the invitee's email alone must never be sufficient (account-takeover fix).
2. Cross-tenant data access is blocked (fail-closed)
3. Audit middleware logs state-changing requests
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from app.core.database import db
from app.core.security import create_access_token
from app.main import app
from app.tests.conftest import (
    TENANT_ALPHA,
    TENANT_BETA,
    TEST_ALGORITHM,
    TEST_AUDIENCE,
    TEST_ISSUER,
    TEST_SECRET,
)

client = TestClient(app)

# Uniform rejection contract for accept-invite: every token failure mode must
# return the same status and the same sanitized error envelope so the endpoint
# cannot be used as a cross-tenant email census or invitation-state oracle.
# (The platform error sanitizer already renders all 401s identically.)
UNIFORM_REJECT_STATUS = 401
UNIFORM_REJECT_CODE = "AUTHENTICATION_ERROR"
UNIFORM_REJECT_MESSAGE = "Request could not be completed"


def _assert_uniform_reject(response) -> None:
    """Assert the response is the uniform invalid-invite rejection."""
    assert response.status_code == UNIFORM_REJECT_STATUS
    body = response.json()
    error = body.get("error", {})
    assert error.get("code") == UNIFORM_REJECT_CODE
    assert error.get("message") == UNIFORM_REJECT_MESSAGE
    assert "access_token" not in body


def _decode(token: str) -> dict:
    return jwt.decode(
        token,
        TEST_SECRET,
        algorithms=[TEST_ALGORITHM],
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
    )


def _seed_admin(user_id: str = "user-admin") -> str:
    """Seed a tenant_admin in TENANT_ALPHA and return a bearer token."""
    from app.models.schemas import User

    db.users.insert(user_id, User(
        id=user_id,
        tenant_id=TENANT_ALPHA,
        email=f"{user_id}@alpha.com",
        name="Admin",
        role="tenant_admin",
        status="active",
        password_hash="$2b$12$dummy",
    ))
    return create_access_token(
        subject=user_id,
        tenant_id=TENANT_ALPHA,
        extra_claims={"roles": ["tenant_admin"]},
    )


def _invite(admin_token: str, email: str, name: str = "Invited User") -> dict:
    """Invite a user via the API and return the JSON body (incl. invite_token)."""
    resp = client.post(
        "/v1/auth/invite",
        json={"email": email, "name": name, "role": "analyst"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _find_user_by_email(tenant_id: str, email: str):
    """Read back a user from the store within a single tenant scope."""
    users = db.users.list(tenant_id=tenant_id, filter_fn=lambda u: u.email == email)
    assert len(users) == 1
    return users[0]


class TestInvitationFlow:
    """End-to-end invitation lifecycle tests."""

    def test_invite_requires_authentication(self):
        response = client.post("/v1/auth/invite", json={
            "email": "new@example.com",
            "name": "New User",
            "role": "analyst",
        })
        assert response.status_code == 401

    def test_invite_requires_admin_role(self):
        from app.models.schemas import User

        # Seed non-admin user in DB so token resolves
        db.users.insert("user-editor", User(
            id="user-editor",
            tenant_id=TENANT_ALPHA,
            email="editor@editor.com",
            name="Editor",
            role="analyst",
            status="active",
            password_hash="$2b$12$dummy",
        ))

        editor_token = create_access_token(
            subject="user-editor",
            tenant_id=TENANT_ALPHA,
            extra_claims={"roles": ["analyst"]},
        )
        response = client.post(
            "/v1/auth/invite",
            json={"email": "new@example.com", "name": "New User", "role": "analyst"},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
        assert response.status_code == 403

    def test_invite_and_accept_lifecycle(self):
        """Full lifecycle: invite issues a single-use token; accepting requires it.

        This test replaces the previous tokenless lifecycle test, which
        incorrectly codified that POST /v1/auth/accept-invite needs only the
        invitee's email. That behaviour was the account-takeover vulnerability:
        accept-invite is unauthenticated (it precedes first login), so binding
        acceptance to the email alone let anyone who knew an invited address
        set the password and receive a JWT for the victim's tenant.
        """
        admin_token = _seed_admin()

        invite_data = _invite(admin_token, "invited@alpha.com")
        assert invite_data["status"] == "invited"
        assert invite_data["tenant_id"] == TENANT_ALPHA
        # The plaintext invite token is returned exactly once, at creation.
        invite_token = invite_data["invite_token"]
        assert isinstance(invite_token, str) and len(invite_token) >= 32

        # Only the token hash is persisted — never the plaintext token.
        invited = _find_user_by_email(TENANT_ALPHA, "invited@alpha.com")
        assert invited.invite_token_hash == hashlib.sha256(invite_token.encode()).hexdigest()
        assert invited.invite_token_hash != invite_token
        assert invited.invite_token_expires_at is not None

        # Invited user cannot login before accepting
        login_resp = client.post("/v1/auth/login", json={
            "email": "invited@alpha.com",
            "password": "password123",
        })
        assert login_resp.status_code == 403
        body = login_resp.json()
        detail = body.get("detail", "")
        assert "pending activation" in detail or "activation" in login_resp.text.lower()

        # Accept invitation with the single-use token
        accept_resp = client.post("/v1/auth/accept-invite", json={
            "token": invite_token,
            "password": "SecurePass123!",
            "name": "Invited User",
        })
        assert accept_resp.status_code == 200
        access_token = accept_resp.json()["access_token"]

        # The issued JWT is scoped to the invited user's tenant only.
        claims = _decode(access_token)
        assert claims["tenant_id"] == TENANT_ALPHA
        assert claims["sub"] == invited.id

        # The user is now active and the token has been consumed.
        accepted = _find_user_by_email(TENANT_ALPHA, "invited@alpha.com")
        assert accepted.status == "active"
        assert accepted.invite_token_hash is None
        assert accepted.invite_token_expires_at is None

        # Now login works
        login_resp2 = client.post("/v1/auth/login", json={
            "email": "invited@alpha.com",
            "password": "SecurePass123!",
        })
        assert login_resp2.status_code == 200


class TestAcceptInviteTokenEnforcement:
    """Regression tests for the tokenless accept-invite account takeover.

    Endpoint context: POST /v1/auth/accept-invite is intentionally public (the
    invitee has no session yet). Security therefore comes from possession of
    the single-use token, not from knowledge of the invitee's email.
    """

    def test_accept_invite_without_token_rejected(self):
        """No token (the old exploit payload shape) -> rejected, nothing changes."""
        admin_token = _seed_admin("user-admin-notoken")
        _invite(admin_token, "notoken@alpha.com")

        response = client.post("/v1/auth/accept-invite", json={
            "email": "notoken@alpha.com",
            "password": "AttackerPass123!",
            "name": "Attacker",
        })
        assert response.status_code in (400, 401, 422)
        assert "access_token" not in response.json()

        invited = _find_user_by_email(TENANT_ALPHA, "notoken@alpha.com")
        assert invited.status == "invited"
        assert invited.password_hash is None
        assert invited.invite_token_hash is not None

    def test_accept_invite_with_garbage_token_rejected(self):
        """Wrong/garbage token -> same uniform 401 as an unknown token."""
        admin_token = _seed_admin("user-admin-garbage")
        _invite(admin_token, "garbage@alpha.com")

        response = client.post("/v1/auth/accept-invite", json={
            "token": "not-a-real-token",
            "password": "AttackerPass123!",
            "name": "Attacker",
        })
        _assert_uniform_reject(response)

        invited = _find_user_by_email(TENANT_ALPHA, "garbage@alpha.com")
        assert invited.status == "invited"
        assert invited.password_hash is None

    def test_accept_invite_rejection_is_uniform(self):
        """A token that matches no invitation and a token for a real invitation
        (but wrong value) must be indistinguishable — no census oracle."""
        admin_token = _seed_admin("user-admin-uniform")
        _invite(admin_token, "uniform@alpha.com")

        wrong_for_real_invite = client.post("/v1/auth/accept-invite", json={
            "token": "wrong-token-for-existing-invite",
            "password": "AttackerPass123!",
            "name": "Attacker",
        })
        unknown_everything = client.post("/v1/auth/accept-invite", json={
            "token": "token-when-nothing-was-invited-here",
            "password": "AttackerPass123!",
            "name": "Attacker",
        })
        _assert_uniform_reject(wrong_for_real_invite)
        _assert_uniform_reject(unknown_everything)
        # Bodies are identical apart from the per-request correlation id.
        def _shape(body: dict) -> dict:
            error = dict(body.get("error", {}))
            error.pop("request_id", None)
            return error
        assert _shape(wrong_for_real_invite.json()) == _shape(unknown_everything.json())

    def test_accept_invite_token_is_single_use(self):
        """A consumed token can never be replayed."""
        admin_token = _seed_admin("user-admin-reuse")
        invite_data = _invite(admin_token, "reuse@alpha.com")
        token = invite_data["invite_token"]

        first = client.post("/v1/auth/accept-invite", json={
            "token": token,
            "password": "SecurePass123!",
            "name": "Invited User",
        })
        assert first.status_code == 200

        replay = client.post("/v1/auth/accept-invite", json={
            "token": token,
            "password": "DifferentPass123!",
            "name": "Invited User",
        })
        _assert_uniform_reject(replay)

    def test_accept_invite_expired_token_rejected(self):
        """An expired (but never used) token is rejected deterministically."""
        from app.models.schemas import User

        expired_token = "expired-test-token-0123456789abcdef"
        db.users.insert("user-expired-invite", User(
            id="user-expired-invite",
            tenant_id=TENANT_ALPHA,
            email="expired@alpha.com",
            name="Expired Invite",
            role="analyst",
            status="invited",
            invite_token_hash=hashlib.sha256(expired_token.encode()).hexdigest(),
            invite_token_expires_at=(datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        ))

        response = client.post("/v1/auth/accept-invite", json={
            "token": expired_token,
            "password": "SecurePass123!",
            "name": "Expired Invite",
        })
        _assert_uniform_reject(response)

        invited = _find_user_by_email(TENANT_ALPHA, "expired@alpha.com")
        assert invited.status == "invited"
        assert invited.password_hash is None

    def test_attacker_knowing_email_cannot_takeover_account(self):
        """The original exploit narrative, now as a regression test.

        Victim is invited to TENANT_BETA. An unauthenticated attacker knows the
        victim's email but has no invite token. Neither the old tokenless
        payload nor a guessed token may activate the account or yield a JWT.
        """
        from app.models.schemas import User

        # Victim invited to TENANT_BETA by Beta's admin (seeded directly).
        db.users.insert("victim-beta", User(
            id="victim-beta",
            tenant_id=TENANT_BETA,
            email="victim@beta.com",
            name="Victim",
            role="analyst",
            status="invited",
            invite_token_hash=hashlib.sha256(b"the-real-secret-token").hexdigest(),
            invite_token_expires_at=(datetime.now(UTC) + timedelta(days=7)).isoformat(),
        ))

        # Old exploit payload: email + attacker-chosen password, no token.
        old_shape = client.post("/v1/auth/accept-invite", json={
            "email": "victim@beta.com",
            "password": "AttackerPass123!",
            "name": "Victim",
        })
        assert old_shape.status_code in (400, 401, 422)

        # Guessed token for the same victim.
        guessed = client.post("/v1/auth/accept-invite", json={
            "token": "attacker-guessed-token",
            "password": "AttackerPass123!",
            "name": "Victim",
        })
        _assert_uniform_reject(guessed)

        # The victim account is untouched and the attacker's password does not work.
        victim = _find_user_by_email(TENANT_BETA, "victim@beta.com")
        assert victim.status == "invited"
        assert victim.password_hash is None
        login = client.post("/v1/auth/login", json={
            "email": "victim@beta.com",
            "password": "AttackerPass123!",
        })
        assert login.status_code in (401, 403)


class TestCrossTenantLeakage:
    """Verify that Tenant A cannot access Tenant B data under any path."""

    def test_tenant_a_token_cannot_list_tenant_b_accounts(self):
        from app.models.schemas import User
        db.users.insert("user-a", User(
            id="user-a", tenant_id=TENANT_ALPHA, email="a@a.com",
            name="User A", role="tenant_admin", status="active",
            password_hash="$2b$12$dummy",
        ))
        token_a = create_access_token(
            subject="user-a",
            tenant_id=TENANT_ALPHA,
            extra_claims={"roles": ["tenant_admin"]},
        )
        response = client.get(
            "/v1/accounts",
            headers={
                "Authorization": f"Bearer {token_a}",
                "X-Tenant-ID": TENANT_BETA,
            },
        )
        # GovernanceMiddleware should reject conflicting tenant headers
        assert response.status_code in (401, 403)

    def test_tenant_a_token_with_matching_header_succeeds(self):
        from app.models.schemas import User
        db.users.insert("user-a2", User(
            id="user-a2", tenant_id=TENANT_ALPHA, email="a2@a.com",
            name="User A2", role="tenant_admin", status="active",
            password_hash="$2b$12$dummy",
        ))
        token_a = create_access_token(
            subject="user-a2",
            tenant_id=TENANT_ALPHA,
            extra_claims={"roles": ["tenant_admin"]},
        )
        response = client.get(
            "/v1/accounts",
            headers={
                "Authorization": f"Bearer {token_a}",
                "X-Tenant-ID": TENANT_ALPHA,
            },
        )
        # Should succeed (200) or 404 if no accounts seeded
        assert response.status_code in (200, 404)

    def test_missing_tenant_claim_returns_401(self):
        token_no_tenant = create_access_token(
            subject="user-no-tenant",
            tenant_id="",
            extra_claims={"roles": ["tenant_admin"]},
        )
        response = client.get(
            "/v1/accounts",
            headers={"Authorization": f"Bearer {token_no_tenant}"},
        )
        assert response.status_code == 401

    def test_deactivated_user_cannot_login(self):
        from app.models.schemas import User
        db.users.insert("user-deactivated", User(
            id="user-deactivated",
            tenant_id=TENANT_ALPHA,
            email="deactivated@alpha.com",
            name="Deactivated",
            role="analyst",
            status="deactivated",
            password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        ))
        response = client.post("/v1/auth/login", json={
            "email": "deactivated@alpha.com",
            "password": "password",
        })
        assert response.status_code == 403
        body = response.json()
        detail = body.get("detail", "")
        assert "deactivated" in detail or "deactivated" in response.text.lower()
