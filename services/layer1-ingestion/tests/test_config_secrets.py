import pytest
from pydantic import ValidationError

from layer1_ingestion.shared.config import Settings


class TestMinIOSecrets:
    def test_missing_s3_keys_allowed_in_development(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("LAYER1_S3_ACCESS_KEY", raising=False)
        monkeypatch.delenv("LAYER1_S3_SECRET_KEY", raising=False)
        settings = Settings()
        assert settings.s3_access_key is None
        assert settings.s3_secret_key is None

    def test_missing_s3_keys_raises_in_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "a" * 48)
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db/db")
        monkeypatch.setenv("REDIS_URL", "rediss://redis:6379/0")
        monkeypatch.delenv("LAYER1_S3_ACCESS_KEY", raising=False)
        monkeypatch.delenv("LAYER1_S3_SECRET_KEY", raising=False)
        with pytest.raises(ValidationError):
            Settings()

    def test_explicit_credentials_are_accepted(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LAYER1_S3_ACCESS_KEY", "test-key")
        monkeypatch.setenv("LAYER1_S3_SECRET_KEY", "test-secret")
        settings = Settings()
        assert settings.s3_access_key == "test-key"
        assert settings.s3_secret_key == "test-secret"
