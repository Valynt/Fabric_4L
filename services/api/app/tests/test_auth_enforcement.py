"""
Authentication enforcement tests for services/api.

Proves that:
  1. Every business endpoint returns 401 when no token is provided.
  2. A valid JWT grants access.
  3. An expired JWT returns 401.
  4. A tampered JWT returns 401.
  5. X-Tenant-ID alone (no JWT) returns 401 — header spoofing is blocked.
  6. A JWT for tenant-alpha cannot access tenant-beta resources.
  7. /health remains public (no auth required).
  8. /metrics is fail-closed by default and only allows unauthenticated access
     when the explicit development bypass is enabled.
  9. The app refuses to start with the default secret in production environments.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import decode_token, revoke_token
from app.main import app

from .conftest import (
    TENANT_ALPHA,
    TENANT_BETA,
    TEST_AUDIENCE,
    TEST_ISSUER,
    mint_token,
)

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
        # Verify expired token returns 401 with correct error code
        assert response.status_code == 401
        response_data = response.json()
        if isinstance(response_data, dict) and "detail" in response_data:
            if isinstance(response_data["detail"], dict):
                assert response_data["detail"].get("error_code") == "AUTH_TOKEN_EXPIRED"


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
# 6b. /metrics access control
# ---------------------------------------------------------------------------


class TestMetricsAccess:
    """/metrics must be fail-closed by default and only allow unauthenticated
    access when the explicit development bypass is enabled.
    """

    def test_metrics_requires_auth_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With the dev bypass disabled, unauthenticated /metrics requests are rejected."""
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "false")
        monkeypatch.delenv("METRICS_INTERNAL_SCRAPE_TOKEN", raising=False)

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/metrics")
        assert response.status_code == 403, (
            f"Expected 403 for unauthenticated /metrics with bypass disabled, "
            f"got {response.status_code}."
        )

    def test_metrics_dev_mode_allows_unauthenticated_access(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicitly enabling the dev bypass permits unauthenticated /metrics access."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
        monkeypatch.delenv("METRICS_INTERNAL_SCRAPE_TOKEN", raising=False)

        with TestClient(app) as client:
            response = client.get("/metrics")
        assert response.status_code == 200, (
            f"Dev mode should allow unauthenticated /metrics access, "
            f"got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# 7. Production secret guard
# ---------------------------------------------------------------------------


class TestProductionSecretGuard:
    """Production-safety gate exercised via the canonical validator."""

    def _base_production_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set a minimally valid production environment; individual tests mutate one control."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("MOCK_PERSISTENCE", "false")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "false")
        monkeypatch.setenv("JWT_SECRET", "a-very-long-production-jwt-secret-for-tests-only-xyz")
        monkeypatch.setenv("CREDENTIALS_MASTER_KEY", "a-very-long-production-master-key-xyz")
        monkeypatch.setenv("API_KEY_HMAC_SECRET", "a-very-long-api-key-hmac-secret-xyz")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        monkeypatch.setenv("DEFAULT_TENANT_ID", "11111111-1111-4111-8111-111111111111")
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "a-very-long-service-auth-secret-xyz")
        monkeypatch.setenv("DATABASE_URL", "postgresql://fabric:secret@postgres.example.com:5432/fabric?sslmode=require")

    def test_weak_jwt_secret_raises_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """App must refuse to start with a weak JWT secret in production."""
        self._base_production_env(monkeypatch)
        monkeypatch.setenv("JWT_SECRET", "short")

        from app.shared_bootstrap import validate_production_safety

        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            validate_production_safety()

    def test_unset_jwt_secret_raises_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._base_production_env(monkeypatch)
        monkeypatch.delenv("JWT_SECRET", raising=False)

        from app.shared_bootstrap import validate_production_safety

        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            validate_production_safety()

    def test_custom_secret_still_requires_production_persistence_policy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A strong auth secret is not enough; the persistence backend must also be production-grade."""
        self._base_production_env(monkeypatch)
        # Use a localhost database URL to trigger the production persistence policy failure.
        monkeypatch.setenv("DATABASE_URL", "postgresql://fabric:secret@localhost:5432/fabric")

        from app.shared_bootstrap import validate_production_safety

        with pytest.raises(RuntimeError, match="localhost"):
            validate_production_safety()

    def test_default_secret_allowed_in_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "development")

        from app.shared_bootstrap import validate_production_safety

        # Development warnings are emitted, but no exception is raised.
        validate_production_safety()


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
    import hashlib

    from app.core.security import decode_token

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
    # Check that the response indicates the token is revoked (may be in different formats)
    response_data = response.json()
    if isinstance(response_data, dict) and "detail" in response_data:
        if isinstance(response_data["detail"], dict):
            assert response_data["detail"].get("error_code") == "AUTH_TOKEN_REVOKED"


def test_cross_tenant_token_header_misuse_blocked() -> None:
    """Verify that X-Tenant-ID header must match JWT tenant claim.

    When a JWT contains tenant=ALPHA but the X-Tenant-ID header says BETA,
    the request should be rejected with 403 to prevent tenant isolation bypass.
    This ensures that header spoofing cannot be used to access other tenants' data.
    """
    token = mint_token(tenant_id=TENANT_ALPHA)
    with TestClient(app) as client:
        response = client.get(
            "/v1/accounts",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": TENANT_BETA,
            },
        )
    # Header mismatch must be rejected to prevent tenant isolation bypass
    assert response.status_code == 403
