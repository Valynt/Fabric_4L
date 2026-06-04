import os
from unittest.mock import patch

import pytest

from value_fabric.shared.security.config import validate_database_config


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://app:pass@db.example.com:5432/fabric?sslmode=require",
        "postgresql://app:pass@db.example.com:5432/fabric?sslmode=verify-ca",
        "postgresql://app:pass@db.example.com:5432/fabric?sslmode=verify-full",
    ],
)
def test_production_accepts_supported_tls_sslmodes(database_url: str) -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DATABASE_URL": database_url,
        },
        clear=True,
    ):
        validate_database_config()


def test_production_rejects_missing_tls_requirement() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql://app:pass@db.example.com:5432/fabric",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="sslmode=require or stronger"):
            validate_database_config()


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://app:pass@db.example.com:5432/fabric?sslmode=",
        "postgresql://app:pass@db.example.com:5432/fabric?sslmode=prefer",
        "postgresql://app:pass@db.example.com:5432/fabric?sslmode=allow",
        "postgresql://app:pass@db.example.com:5432/fabric?sslmode=disable",
        "postgresql://app:pass@db.example.com:5432/fabric?sslmode=require&sslmode=disable",
    ],
)
def test_production_rejects_unsupported_tls_sslmodes(database_url: str) -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DATABASE_URL": database_url,
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="sslmode=require or stronger"):
            validate_database_config()


def test_staging_accepts_verify_full_tls() -> None:
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "staging",
            "DATABASE_URL": "postgresql://app:pass@db.example.com:5432/fabric?sslmode=verify-full",
        },
        clear=True,
    ):
        validate_database_config()
