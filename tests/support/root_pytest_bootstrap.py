"""Repository-level pytest bootstrap kept out of root conftest.py.

DEPRECATED: This file is retained for backward compatibility but should be removed
once all sys.path manipulations are eliminated. The pytest.ini pythonpath configuration
now handles all service path resolution.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_TEST_ENV = {
    "ENVIRONMENT": "development",
    "LAYER1_API_URL": "http://layer1:8001",
    "LAYER2_API_URL": "http://layer2:8002",
    "LAYER3_API_URL": "http://layer3:8003",
    "LAYER5_API_URL": "http://layer5:8005",
    "LAYER6_API_URL": "http://layer6:8006",
    "ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT": "true",
    "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/fabric",
    "JWT_SECRET": "dummy_jwt_secret_for_tests_must_be_32_chars",
    "API_KEY_HMAC_SECRET": "dummy_api_key_secret_for_tests_must_be_32_chars",
    "SERVICE_AUTH_SECRET": "dummy_service_auth_secret_for_tests_32_chars",
}

_FAIL_CLOSED_TEST_DEFAULTS = {
    "DATABASE_URL_SYNC": "postgresql+psycopg://postgres:postgres@localhost:5432/fabric",
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_PASSWORD": "neo4j-test-password-123",
    "LAYER3_API_KEY": "layer3-test-api-key-0123456789",
    "LAYER5_API_KEY": "layer5-test-api-key-0123456789",
}


def bootstrap_root_pytest() -> None:
    """Install root test environment variables only.

    Service path resolution is now handled by pytest.ini pythonpath configuration.
    Legacy namespace installation removed as part of Phase 2 remediation.
    """
    _install_test_environment()


def _install_test_environment() -> None:
    for key, value in _TEST_ENV.items():
        os.environ[key] = value
    for key, value in _FAIL_CLOSED_TEST_DEFAULTS.items():
        os.environ.setdefault(key, value)
