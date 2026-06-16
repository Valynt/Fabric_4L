
import pytest
from pydantic import ValidationError

from layer1_ingestion.shared.config import Settings


class TestMinIOSecrets:
    def test_missing_s3_access_key_raises(self, monkeypatch):
        monkeypatch.delenv("LAYER1_S3_ACCESS_KEY", raising=False)
        monkeypatch.delenv("LAYER1_S3_SECRET_KEY", raising=False)
        with pytest.raises(ValidationError):
            Settings()

    def test_explicit_credentials_are_accepted(self, monkeypatch):
        monkeypatch.setenv("LAYER1_S3_ACCESS_KEY", "test-key")
        monkeypatch.setenv("LAYER1_S3_SECRET_KEY", "test-secret")
        settings = Settings()
        assert settings.s3_access_key == "test-key"
        assert settings.s3_secret_key == "test-secret"
