from __future__ import annotations

"""I-02 production fail-closed regression tests for Layer 5.

Production-like Layer 5 deployments must reject insecure startup settings instead
of relying on developer auth fallbacks, wildcard CORS, weak JWT secrets, or local
SQLite/default database credentials.
"""


import pytest
from pydantic import ValidationError

from layer5_ground_truth.config import Settings

# RB-5 FIX: The blanket requires_postgres pytestmark was incorrectly applied
# to the entire file. TestLayer5ProductionSettingsFailClosed only tests
# Settings() validation (pydantic) — it does NOT require a live PostgreSQL
# instance. Applying requires_postgres only to TestLayer5GetCurrentUserHardening
# which exercises the actual database auth layer.

VALID_JWT_SECRET = "layer5-production-secret-with-more-than-32-characters"
VALID_DATABASE_URL = "postgresql://layer5_app:strong-password@layer5-db.internal:5432/layer5_prod"
VALID_CORS_ORIGINS = "https://fabric.example.com,https://admin.fabric.example.com"
VALID_LAYER3_BASE_URL = "https://layer3.internal"


VALID_SERVICE_AUTH_SECRET = "layer5-service-auth-secret-with-more-than-32-characters"


def _clear_layer5_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "ENVIRONMENT",
        "APP_ENV",
        "JWT_SECRET",
        "JWT_ISSUER",
        "JWT_AUDIENCE",
        "JWT_ALGORITHM",
        "JWT_FALLBACK_TO_QUERY_PARAM",
        "ALLOW_INSECURE_DEV_AUTH_BYPASS",
        "CORS_ORIGINS",
        "DATABASE_URL",
        "DATABASE_URL_SYNC",
        "DEFAULT_TENANT_ID",
        "SERVICE_AUTH_SECRET",
        "LAYER3_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    # Prevent pydantic from reading APP_ENV out of the local .env file.
    monkeypatch.setenv("APP_ENV", "development")


def _set_valid_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_layer5_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
    monkeypatch.setenv("JWT_FALLBACK_TO_QUERY_PARAM", "false")
    monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "false")
    monkeypatch.setenv("CORS_ORIGINS", VALID_CORS_ORIGINS)
    monkeypatch.setenv("DATABASE_URL", VALID_DATABASE_URL)
    monkeypatch.setenv("DATABASE_URL_SYNC", VALID_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://"))
    monkeypatch.setenv("JWT_ALGORITHM", "RS256")
    monkeypatch.setenv("LAYER3_BASE_URL", VALID_LAYER3_BASE_URL)
    monkeypatch.setenv("DEFAULT_TENANT_ID", "11111111-1111-4111-8111-111111111111")
    monkeypatch.setenv("SERVICE_AUTH_SECRET", VALID_SERVICE_AUTH_SECRET)
    monkeypatch.setenv("JWT_ISSUER", "value-fabric-internal")
    monkeypatch.setenv("JWT_AUDIENCE", "value-fabric-services")


def _validation_message(exc_info: pytest.ExceptionInfo[ValidationError]) -> str:
    return "\n".join(error["msg"] for error in exc_info.value.errors())


class TestLayer5ProductionSettingsFailClosed:
    def test_effective_environment_prefers_app_env_when_non_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_layer5_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)

        settings = Settings()

        assert settings.effective_environment == "development"

    def test_app_env_production_overrides_development_and_remains_fail_closed(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _clear_layer5_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET", "")
        monkeypatch.setenv("CORS_ORIGINS", "")
        monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/layer5_test")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://postgres:postgres@localhost:5432/layer5_test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        message = _validation_message(exc_info)
        assert "Layer 5 production configuration is not fail-closed for production" in message
        assert "JWT_SECRET must be a non-placeholder value of at least 32 characters" in message

    @pytest.mark.parametrize("app_env_alias", ["stage", "staging"])
    def test_app_env_staging_aliases_enforce_fail_closed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        app_env_alias: str,
    ) -> None:
        _clear_layer5_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("APP_ENV", app_env_alias)
        monkeypatch.setenv("JWT_SECRET", "")
        monkeypatch.setenv("CORS_ORIGINS", "")
        monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/layer5_test")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://postgres:postgres@localhost:5432/layer5_test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        message = _validation_message(exc_info)
        assert f"Layer 5 production configuration is not fail-closed for {app_env_alias}" in message
        assert "CORS_ORIGINS must list exact trusted origins" in message

    def test_valid_production_settings_are_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)

        settings = Settings()

        assert settings.effective_environment == "production"
        assert settings.cors_origin_list == [
            "https://fabric.example.com",
            "https://admin.fabric.example.com",
        ]
        assert settings.jwt_fallback_to_query_param is False
        assert settings.allow_insecure_dev_auth_bypass is False

    def test_app_env_marks_runtime_as_production_like_when_environment_absent(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("APP_ENV", "staging")

        assert Settings().effective_environment == "staging"

    def test_production_rejects_wildcard_cors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "*")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "CORS_ORIGINS must not contain wildcard '*' origins" in _validation_message(exc_info)

    def test_production_requires_explicit_cors_origins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.setenv("CORS_ORIGINS", "")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "CORS_ORIGINS must list exact trusted origins" in _validation_message(exc_info)

    def test_production_requires_explicit_jwt_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.setenv("JWT_SECRET", "")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        message = _validation_message(exc_info)
        assert "JWT_SECRET must be a non-placeholder value of at least 32 characters" in message
        assert "Layer 5 production configuration is not fail-closed for production" in message

    def test_production_rejects_query_param_jwt_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.setenv("JWT_FALLBACK_TO_QUERY_PARAM", "true")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "JWT_FALLBACK_TO_QUERY_PARAM must be false" in _validation_message(exc_info)

    def test_production_rejects_insecure_dev_auth_bypass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "ALLOW_INSECURE_DEV_AUTH_BYPASS must be false" in _validation_message(exc_info)

    def test_production_rejects_local_or_default_database_credentials(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/layer5_test")
        monkeypatch.setenv("DATABASE_URL_SYNC", "postgresql://postgres:postgres@localhost:5432/layer5_test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        message = _validation_message(exc_info)
        assert "DATABASE_URL must point to non-local PostgreSQL with non-default credentials" in message
        assert "DATABASE_URL_SYNC must point to non-local PostgreSQL with non-default credentials" in message

    def test_production_rejects_localhost_layer3_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.setenv("LAYER3_BASE_URL", "http://localhost:8003")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert (
            "LAYER3_BASE_URL must not point to localhost in production-like environments"
            in _validation_message(exc_info)
        )

    def test_non_production_logs_warning_when_jwt_secret_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        _clear_layer5_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("JWT_SECRET", "")

        with caplog.at_level("WARNING"):
            Settings()

        assert "weak or missing JWT_SECRET" in caplog.text
        assert "set JWT_SECRET to at least 32 random characters" in caplog.text

    def test_development_still_allows_test_friendly_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_layer5_env(monkeypatch)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
        monkeypatch.setenv("JWT_FALLBACK_TO_QUERY_PARAM", "true")
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./layer5.db")
        monkeypatch.setenv("DATABASE_URL_SYNC", "sqlite:///./layer5.db")
        monkeypatch.setenv("DEFAULT_TENANT_ID", "11111111-1111-4111-8111-111111111111")

        settings = Settings()

        assert settings.effective_environment == "development"
        assert settings.jwt_fallback_to_query_param is True
        assert settings.allow_insecure_dev_auth_bypass is True
        assert settings.cors_origin_list == ["*"]

    # --- Sprint 2 credential remediation: SERVICE_AUTH_SECRET fail-closed ---

    def test_production_requires_service_auth_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert (
            "SERVICE_AUTH_SECRET must be set to a value of at least 32 characters"
            in _validation_message(exc_info)
        )

    def test_production_rejects_short_service_auth_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "too-short")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert (
            "SERVICE_AUTH_SECRET must be set to a value of at least 32 characters"
            in _validation_message(exc_info)
        )

    def test_production_rejects_placeholder_service_auth_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_valid_production_env(monkeypatch)
        # 40 chars to clear the length check; stripped/lowercased → "changeme",
        # which matches the WEAK_JWT_SECRETS denylist shared with JWT_SECRET.
        monkeypatch.setenv(
            "SERVICE_AUTH_SECRET",
            "changeme                                ",
        )

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert (
            "SERVICE_AUTH_SECRET must not be a known placeholder value"
            in _validation_message(exc_info)
        )


@pytest.mark.requires_postgres
class TestLayer5GetCurrentUserHardening:
    """Regression coverage for ``get_current_user`` adapter.

    The dependency must derive identity only from canonical middleware context
    and fail closed otherwise.
    """

    @staticmethod
    def _fake_request(headers: dict[str, str] | None = None, ctx=None):
        """Build a Request-like stub with ``state.governance_context``."""
        from types import SimpleNamespace

        state = SimpleNamespace(governance_context=ctx, context=ctx)
        return SimpleNamespace(state=state, headers=headers or {}, query_params={}, url=SimpleNamespace(path="/test-auth"))

    def _build_settings(self, monkeypatch: pytest.MonkeyPatch, *, runtime_mode: str):
        _clear_layer5_env(monkeypatch)
        if runtime_mode in {"prod", "staging"}:
            _set_valid_production_env(monkeypatch)
            monkeypatch.setenv("ENVIRONMENT", runtime_mode)
        else:
            monkeypatch.setenv("ENVIRONMENT", runtime_mode)
            monkeypatch.setenv("JWT_SECRET", VALID_JWT_SECRET)
        monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "false")
        monkeypatch.setenv("JWT_FALLBACK_TO_QUERY_PARAM", "false")
        return Settings()

    def test_derives_identity_from_governance_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from uuid import uuid4

        from layer5_ground_truth.api.auth import get_current_user

        settings = self._build_settings(monkeypatch, runtime_mode="prod")

        tenant = uuid4()

        class _Ctx:
            tenant_id = tenant
            user_id = "user-123"
            roles = ["admin"]
            permissions = frozenset()
            raw = {"source": "jwt"}

        request = self._fake_request(ctx=_Ctx())

        claims = get_current_user(
            request=request,
            settings=settings,
        )

        assert claims.tenant_id == tenant
        assert claims.user_id == "user-123"
        assert claims.roles == ["admin"]

    def test_production_without_governance_context_is_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi import HTTPException

        from layer5_ground_truth.api.auth import get_current_user

        settings = self._build_settings(monkeypatch, runtime_mode="prod")
        request = self._fake_request(ctx=None)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                request=request,
                settings=settings,
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "AUTH_CONTEXT_REQUIRED"

    def test_header_tenant_hint_does_not_establish_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi import HTTPException

        from layer5_ground_truth.api.auth import get_current_user

        settings = self._build_settings(monkeypatch, runtime_mode="prod")
        tenant = "11111111-1111-4111-8111-111111111111"
        request = self._fake_request(ctx=None, headers={"X-Tenant-ID": tenant})

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                request=request,
                settings=settings,
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "AUTH_TENANT_HINT_REJECTED"

    def test_dev_bypass_disabled_without_context_is_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi import HTTPException

        from layer5_ground_truth.api.auth import get_current_user

        # Non-production but bypass flag OFF: must still fail closed when no
        # middleware context is present, so unit tests that forget to override
        # the dependency cannot accidentally grant auth.
        settings = self._build_settings(monkeypatch, runtime_mode="dev")
        request = self._fake_request(ctx=None)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                request=request,
                settings=settings,
            )

        assert exc_info.value.status_code == 401

    def test_query_tenant_hint_does_not_establish_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi import HTTPException
        from layer5_ground_truth.api.auth import get_current_user

        settings = self._build_settings(monkeypatch, runtime_mode="dev")
        request = self._fake_request(ctx=None)
        request.query_params = {"tenant_id": "11111111-1111-4111-8111-111111111111"}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(
                request=request,
                settings=settings,
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "AUTH_TENANT_HINT_REJECTED"

    @pytest.mark.parametrize(
        "runtime_mode",
        ["prod", "staging", "dev", "test"],
    )
    def test_runtime_mode_missing_context_fails_closed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        runtime_mode: str,
    ) -> None:
        from fastapi import HTTPException

        from layer5_ground_truth.api.auth import get_current_user

        settings = self._build_settings(
            monkeypatch,
            runtime_mode=runtime_mode,
        )
        request = self._fake_request(ctx=None)
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(request=request, settings=settings)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error_code"] == "AUTH_CONTEXT_REQUIRED"

    def test_conflicting_hint_with_context_is_ignored_for_resolution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from uuid import uuid4
        from layer5_ground_truth.api.auth import get_current_user

        settings = self._build_settings(monkeypatch, runtime_mode="test")
        canonical_tenant = uuid4()
        request = self._fake_request(
            ctx=type(
                "_Ctx",
                (),
                {
                    "tenant_id": canonical_tenant,
                    "user_id": "user-123",
                    "roles": ["admin"],
                    "permissions": frozenset(),
                    "raw": {"source": "governance_context"},
                },
            )(),
            headers={"X-Tenant-ID": "22222222-2222-4222-8222-222222222222"},
        )

        claims = get_current_user(request=request, settings=settings)
        assert claims.tenant_id == canonical_tenant
