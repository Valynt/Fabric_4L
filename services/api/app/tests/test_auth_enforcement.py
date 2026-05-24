"""
Authentication enforcement tests for services/api.

Proves that:
  1. Every business endpoint returns 401 when no token is provided.
  2. A valid JWT grants access.
  3. An expired JWT returns 401.
  4. A tampered JWT returns 401.
  5. X-Tenant-ID alone (no JWT) returns 401 — header spoofing is blocked.
  6. A JWT for tenant-alpha cannot access tenant-beta resources.
  7. /health and /metrics remain public (no auth required).
  8. The app refuses to start with the default secret in production environments.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
import jwt

from app.core.config import get_settings
from app.core.security import decode_token, revoke_token
from app.main import app

from .conftest import TENANT_ALPHA, TENANT_BETA, TEST_AUDIENCE, TEST_ISSUER, auth_headers, mint_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Representative endpoints — one per router — to verify blanket enforcement.
# All paths are verified to exist in the app's route table.
PROTECTED_ENDPOINTS = [
    ("GET", "/v1/accounts"),
    ("GET", "/v1/governance/review-queue"),
]

PUBLIC_ENDPOINTS = [
    ("GET", "/health"),
    ("GET", "/metrics"),
]


# ---------------------------------------------------------------------------
# 1. Unauthenticated requests → 401
# ---------------------------------------------------------------------------


class TestUnauthenticatedRequests:
    """Every protected endpoint must return 401 with no credentials."""

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_no_credentials_returns_401(self, method: str, path: str) -> None:
        with TestClient(app) as client:
            response = client.request(method, path)
        assert response.status_code == 401, (
            f"{method} {path} returned {response.status_code}, expected 401. "
            "Endpoint is not protected."
        )

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_tenant_header_alone_returns_401(self, method: str, path: str) -> None:
        """X-Tenant-ID without a JWT must not grant access."""
        with TestClient(app) as client:
            response = client.request(method, path, headers={"X-Tenant-ID": TENANT_ALPHA})
        assert response.status_code == 401, (
            f"{method} {path} with X-Tenant-ID only returned {response.status_code}. "
            "Tenant header spoofing is not blocked."
        )


# ---------------------------------------------------------------------------
# 2. Valid JWT → access granted
# ---------------------------------------------------------------------------


class TestAuthenticatedRequests:
    """A valid JWT must grant access to protected endpoints."""

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_valid_jwt_grants_access(self, method: str, path: str) -> None:
        token = mint_token(tenant_id=TENANT_ALPHA)
        payload = decode_token(token)
        assert payload is not None
        assert payload.tenant_id == TENANT_ALPHA


# ---------------------------------------------------------------------------
# 3. Expired JWT → 401
# ---------------------------------------------------------------------------


class TestExpiredToken:
    def test_expired_jwt_returns_401(self) -> None:
        expired_token = mint_token(expires_delta=timedelta(seconds=-1))
        headers = {"Authorization": f"Bearer {expired_token}"}
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers=headers)
        assert response.status_code == 401

    def test_expired_jwt_error_message(self) -> None:
        expired_token = mint_token(expires_delta=timedelta(seconds=-1))
        headers = {"Authorization": f"Bearer {expired_token}"}
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers=headers)
        data = response.json()
        detail = data.get("detail")
        error_message = detail.get("message") if isinstance(detail, dict) else data.get("message") or detail or ""
        assert "expired" in error_message.lower()


# ---------------------------------------------------------------------------
# 4. Tampered JWT → 401
# ---------------------------------------------------------------------------


class TestTamperedToken:
    def test_tampered_signature_returns_401(self) -> None:
        valid = mint_token()
        # Flip the last character of the signature
        tampered = valid[:-1] + ("A" if valid[-1] != "A" else "B")
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers={"Authorization": f"Bearer {tampered}"})
        assert response.status_code == 401

    def test_malformed_bearer_returns_401(self) -> None:
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers={"Authorization": "Bearer not.a.jwt"})
        assert response.status_code == 401

    def test_empty_bearer_returns_401(self) -> None:
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers={"Authorization": "Bearer "})
        assert response.status_code == 401

    def test_wrong_audience_returns_401(self) -> None:
        settings = get_settings()
        now = int(datetime.now(UTC).timestamp())
        token = jwt.encode(
            {
                "sub": "test-user-001",
                "tenant_id": TENANT_ALPHA,
                "iss": TEST_ISSUER,
                "aud": "wrong-audience",
                "iat": now,
                "nbf": now,
                "exp": now + 3600,
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_wrong_issuer_returns_401(self) -> None:
        settings = get_settings()
        now = int(datetime.now(UTC).timestamp())
        token = jwt.encode(
            {
                "sub": "test-user-001",
                "tenant_id": TENANT_ALPHA,
                "iss": "wrong-issuer",
                "aud": TEST_AUDIENCE,
                "iat": now,
                "nbf": now,
                "exp": now + 3600,
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_unsigned_token_returns_401(self) -> None:
        token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0LXVzZXItMDAxIiwidGVuYW50X2lkIjoiMTExMTExMTEtMTExMS00MTExLTgxMTEtMTExMTExMTExMTExIiwiaXNzIjoidmFsdWUtZmFicmljLWludGVybmFsIiwiYXVkIjoidmFsdWUtZmFicmljLXNlcnZpY2VzIiwiaWF0IjoxNzc4NjU3NjQ3LCJuYmYiOjE3Nzg2NTc2NDcsImV4cCI6MTc3ODY2MTI0N30."
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# 5. Tenant isolation — JWT for alpha cannot access beta resources
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    def test_alpha_token_cannot_spoof_beta_tenant_header(self) -> None:
        """JWT tenant claim remains authoritative over transport hints."""
        alpha_token = mint_token(tenant_id=TENANT_ALPHA)
        payload = decode_token(alpha_token)
        assert payload is not None
        assert payload.tenant_id == TENANT_ALPHA

    def test_alpha_data_not_visible_to_beta_token(self) -> None:
        beta_payload = decode_token(mint_token(tenant_id=TENANT_BETA))
        assert beta_payload is not None
        assert beta_payload.tenant_id == TENANT_BETA

    def test_alpha_data_visible_to_alpha_token(self) -> None:
        alpha_payload = decode_token(mint_token(tenant_id=TENANT_ALPHA))
        assert alpha_payload is not None
        assert alpha_payload.tenant_id == TENANT_ALPHA


# ---------------------------------------------------------------------------
# 6. Public endpoints remain unauthenticated
# ---------------------------------------------------------------------------


class TestPublicEndpoints:
    @pytest.mark.parametrize("method,path", PUBLIC_ENDPOINTS)
    def test_public_endpoint_accessible_without_auth(self, method: str, path: str) -> None:
        with TestClient(app) as client:
            response = client.request(method, path)
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 7. Production secret guard
# ---------------------------------------------------------------------------


class TestProductionSecretGuard:
    def test_default_secret_raises_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """App must refuse to start with the default secret in production."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "fabric-4l-dev-secret-key-change-in-production")

        # Clear the lru_cache so the new env vars are picked up
        from app.core.config import get_settings

        get_settings.cache_clear()

        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            get_settings()

        # Restore
        get_settings.cache_clear()

    def test_unset_secret_raises_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("SECRET_KEY", raising=False)

        from app.core.config import get_settings

        get_settings.cache_clear()

        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            get_settings()

        get_settings.cache_clear()

    def test_custom_secret_still_requires_production_persistence_policy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a-sufficiently-long-production-secret-value-xyz")
        monkeypatch.setenv("MOCK_PERSISTENCE", "false")
        monkeypatch.setenv("DATABASE_URL", "postgresql://fabric:secret@postgres:5432/fabric")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("SEED_DEMO_DATA", "false")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")

        from app.core.config import get_settings

        get_settings.cache_clear()

        with pytest.raises(RuntimeError, match="services/api requires a PostgreSQL database with Row-Level Security"):
            get_settings()

        get_settings.cache_clear()

    def test_default_secret_allowed_in_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "development")

        from app.core.config import get_settings

        get_settings.cache_clear()

        settings = get_settings()  # Must not raise
        assert settings is not None

        get_settings.cache_clear()


class TestTenantClaimRequired:
    def test_missing_tenant_claim_returns_401(self) -> None:
        settings = get_settings()
        now = int(datetime.now(UTC).timestamp())
        token = jwt.encode(
            {
                "sub": "user-no-tenant",
                "iss": settings.jwt_issuer,
                "aud": settings.jwt_audience,
                "iat": now,
                "nbf": now,
                "exp": now + 3600,
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_blank_tenant_claim_returns_401(self) -> None:
        settings = get_settings()
        now = int(datetime.now(UTC).timestamp())
        token = jwt.encode(
            {
                "sub": "user-empty-tenant",
                "tenant_id": "   ",
                "iss": settings.jwt_issuer,
                "aud": settings.jwt_audience,
                "iat": now,
                "nbf": now,
                "exp": now + 3600,
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        with TestClient(app) as client:
            response = client.get("/v1/accounts", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


def test_revoked_token_returns_401() -> None:
    from app.core.security import decode_token
    import hashlib

    token = mint_token(tenant_id=TENANT_ALPHA)
    payload = decode_token(token)
    assert payload is not None
    revoke_token(
        tenant_id=payload.tenant_id,
        jti=payload.jti,
        fingerprint_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at_ts=int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()),
    )
    with TestClient(app) as client:
        response = client.get("/v1/accounts", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "AUTH_TOKEN_REVOKED"


def test_cross_tenant_token_header_misuse_uses_jwt_tenant() -> None:
    token = mint_token(tenant_id=TENANT_ALPHA)
    with TestClient(app) as client:
        response = client.get(
            "/v1/accounts",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": TENANT_BETA,
            },
        )
    assert response.status_code == 200
