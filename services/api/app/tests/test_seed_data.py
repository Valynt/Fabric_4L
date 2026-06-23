"""Tests for seed_data production guards."""

from __future__ import annotations

import pytest

from app.services.seed_data import seed_users
from app.tests.conftest import TENANT_ALPHA, TENANT_BETA


class TestSeedUsersProductionGuard:
    def test_seed_users_blocked_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """seed_users must raise RuntimeError in production-like environments."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET", "strong-production-secret-minimum-32-chars-long")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
        monkeypatch.setenv("SECRET_KEY", "strong-production-secret-minimum-32-chars-long")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        monkeypatch.setenv("DEV_SEED_ADMIN_PASSWORD", "explicit-dev-admin-password")
        monkeypatch.setenv("DEV_SEED_ANALYST_PASSWORD", "explicit-dev-analyst-password")

        with pytest.raises(RuntimeError, match="seed_users is disabled in production-like environments"):
            seed_users([TENANT_ALPHA])

    def test_seed_users_requires_explicit_dev_passwords(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Demo seed user passwords must not have production-code defaults."""
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("JWT_SECRET", "dev-local-secret-do-not-use-in-production-minimum-32-chars")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
        monkeypatch.setenv("SECRET_KEY", "dev-local-secret-minimum-32-chars")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
        monkeypatch.delenv("DEV_SEED_ADMIN_PASSWORD", raising=False)
        monkeypatch.delenv("DEV_SEED_ANALYST_PASSWORD", raising=False)

        with pytest.raises(RuntimeError, match="DEV_SEED_ADMIN_PASSWORD"):
            seed_users([TENANT_ALPHA, TENANT_BETA])

    def test_seed_users_allowed_in_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """seed_users succeeds in non-production environments."""
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("JWT_SECRET", "dev-local-secret-do-not-use-in-production-minimum-32-chars")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
        monkeypatch.setenv("SECRET_KEY", "dev-local-secret-minimum-32-chars")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
        monkeypatch.setenv("DEV_SEED_ADMIN_PASSWORD", "explicit-dev-admin-password")
        monkeypatch.setenv("DEV_SEED_ANALYST_PASSWORD", "explicit-dev-analyst-password")

        # Should not raise; returns list of users
        users = seed_users([TENANT_ALPHA, TENANT_BETA])
        assert len(users) == 2
        assert users[0].email == "admin@alpha.com"
        assert users[1].email == "analyst@beta.com"
