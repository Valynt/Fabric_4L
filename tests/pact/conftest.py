"""Shared fixtures for Pact contract tests.

Environment Variables:
    LAYER4_API_URL: Layer 4 Agents API base URL (default: http://localhost:8004)
    PACT_DIR: Directory to write/read pact files (default: repo_root/pacts)
    PACT_BROKER_URL: Optional Pact Broker URL for publishing/fetching contracts
    PACT_BROKER_TOKEN: Token for authenticated Pact Broker access
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACT_DIR = REPO_ROOT / "pacts"
DEFAULT_LAYER4_URL = "http://localhost:8004"


def _get_env_url(env_var: str, default: str) -> str:
    """Get API URL from environment variable with fallback."""
    url = os.getenv(env_var, default)
    return url.rstrip("/")


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="session")
def pact_dir() -> Path:
    """Directory where pact files are written and read from."""
    path = Path(os.getenv("PACT_DIR", str(DEFAULT_PACT_DIR)))
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="session")
def layer4_provider_url() -> str:
    """Base URL for the Layer 4 provider under verification."""
    return _get_env_url("LAYER4_API_URL", DEFAULT_LAYER4_URL)


@pytest.fixture(scope="session")
def pact_broker_config() -> dict[str, str] | None:
    """Optional Pact Broker configuration for CI publishing."""
    url = os.getenv("PACT_BROKER_URL")
    token = os.getenv("PACT_BROKER_TOKEN")
    if url:
        return {"url": url, "token": token or ""}
    return None
