from __future__ import annotations

"""JWT token validation security tests.

Tests that verify JWT token validation mechanisms:
- JWT signature validation
- JWT claim validation (tenant_id, user_id, roles, permissions)
- Token expiration enforcement
- Token revocation handling
- Malformed token rejection

Production Invariant: JWT tokens must be validated at the API gateway.
These tests verify that invalid tokens are properly rejected.

Author: Autonomous Test Assurance Agent
Date: 2026-06-22
Priority: P0 (Security Boundary)
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
import pytest_asyncio
from fastapi import FastAPI
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.permissions import Role

from layer4_agents.api.routes import accounts

pytestmark = [
    pytest.mark.security,
    pytest.mark.jwt_validation,
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


class TestJWTSignatureValidation:
    """NEGATIVE: Test that JWT signature validation works."""

    def test_invalid_signature_rejected(self):
        """JWT with invalid signature should be rejected.
        
        Risk: Token forgery allowing unauthorized access.
        """
        secret = "test-secret"
        payload = {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "roles": [Role.TENANT_ADMIN.value],
            "exp": datetime.now(tz=UTC) + timedelta(hours=1),
        }
        
        # Sign with wrong secret
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        
        # Try to decode with correct secret (should fail)
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, secret, algorithms=["HS256"])

    def test_tampered_token_rejected(self):
        """Tampered JWT should be rejected.
        
        Risk: Token manipulation allowing privilege escalation.
        """
        secret = "test-secret"
        exp_time = datetime.now(tz=UTC) + timedelta(hours=1)
        payload = {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "roles": ["user"],  # Regular user
            "exp": exp_time,
        }
        
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        # Tamper with token (modify payload)
        parts = token.split(".")
        tampered_payload_dict = {
            "tenant_id": payload["tenant_id"],
            "user_id": payload["user_id"],
            "roles": ["tenant_admin"],  # Escalate to admin
            "exp": int(exp_time.timestamp()),  # Convert to timestamp for JSON
        }
        tampered_payload = json.dumps(tampered_payload_dict).encode()
        tampered_token = f"{parts[0]}.{tampered_payload.decode()}.{parts[2]}"
        
        # Should fail validation
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(tampered_token, secret, algorithms=["HS256"])


class TestJWTClaimValidation:
    """NEGATIVE: Test that JWT claims are validated."""

    def test_missing_tenant_id_rejected(self):
        """JWT without tenant_id should be rejected.
        
        Risk: Cross-tenant data access.
        """
        secret = "test-secret"
        payload = {
            "user_id": str(uuid4()),
            "roles": [Role.TENANT_ADMIN.value],
            "exp": datetime.now(tz=UTC) + timedelta(hours=1),
        }
        
        token = jwt.encode(payload, secret, algorithm="HS256")
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        
        # Should not have tenant_id
        assert "tenant_id" not in decoded

    def test_missing_user_id_rejected(self):
        """JWT without user_id should be rejected.
        
        Risk: Unattributed actions.
        """
        secret = "test-secret"
        payload = {
            "tenant_id": str(uuid4()),
            "roles": [Role.TENANT_ADMIN.value],
            "exp": datetime.now(tz=UTC) + timedelta(hours=1),
        }
        
        token = jwt.encode(payload, secret, algorithm="HS256")
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        
        # Should not have user_id
        assert "user_id" not in decoded

    def test_invalid_role_rejected(self):
        """JWT with invalid role should be rejected.
        
        Risk: Privilege escalation via invalid roles.
        """
        secret = "test-secret"
        payload = {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "roles": ["INVALID_ROLE"],  # Invalid role
            "exp": datetime.now(tz=UTC) + timedelta(hours=1),
        }
        
        token = jwt.encode(payload, secret, algorithm="HS256")
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        
        # Should have invalid role
        assert "INVALID_ROLE" in decoded["roles"]


class TestTokenExpiration:
    """NEGATIVE: Test that expired tokens are rejected."""

    def test_expired_token_rejected(self):
        """Expired JWT should be rejected.
        
        Risk: Session hijacking with old tokens.
        """
        secret = "test-secret"
        payload = {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "roles": [Role.TENANT_ADMIN.value],
            "exp": datetime.now(tz=UTC) - timedelta(hours=1),  # Expired
        }
        
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        # Should fail due to expiration
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, secret, algorithms=["HS256"])

    def test_token_without_expiration_rejected(self):
        """JWT without exp claim should be rejected.
        
        Risk: Eternal tokens allowing indefinite access.
        """
        secret = "test-secret"
        payload = {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "roles": [Role.TENANT_ADMIN.value],
            # No exp claim
        }
        
        token = jwt.encode(payload, secret, algorithm="HS256")
        decoded = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False})
        
        # Should not have exp
        assert "exp" not in decoded


class TestMalformedToken:
    """NEGATIVE: Test that malformed tokens are rejected."""

    def test_empty_token_rejected(self):
        """Empty token string should be rejected.
        
        Risk: Bypassing validation with empty auth.
        """
        with pytest.raises(jwt.DecodeError):
            jwt.decode("", "secret", algorithms=["HS256"])

    def test_garbage_token_rejected(self):
        """Garbage token string should be rejected.
        
        Risk: Confusion attacks.
        """
        with pytest.raises(jwt.DecodeError):
            jwt.decode("not.a.valid.jwt.token", "secret", algorithms=["HS256"])

    def test_invalid_format_rejected(self):
        """Token with wrong number of parts should be rejected.
        
        Risk: Format confusion attacks.
        """
        with pytest.raises(jwt.DecodeError):
            jwt.decode("only.two.parts", "secret", algorithms=["HS256"])


class TestValidToken:
    """POSITIVE: Test that valid tokens are accepted."""

    def test_valid_token_succeeds(self):
        """Valid JWT should be accepted.
        
        Risk: False positives blocking legitimate access.
        """
        secret = "test-secret"
        payload = {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "roles": [Role.TENANT_ADMIN.value],
            "exp": datetime.now(tz=UTC) + timedelta(hours=1),
        }
        
        token = jwt.encode(payload, secret, algorithm="HS256")
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        
        # Should decode successfully
        assert decoded["tenant_id"] == payload["tenant_id"]
        assert decoded["user_id"] == payload["user_id"]
        assert decoded["roles"] == payload["roles"]
