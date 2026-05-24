"""Fixtures for E2E tenant control plane tests."""

import os
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient

# Constants
DEFAULT_LAYER4_URL = "http://localhost:8004"
DEFAULT_TIMEOUT = 10.0


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for E2E tests.
    
    Uses LAYER4_API_URL environment variable, falls back to localhost:8004.
    """
    base_url = os.getenv("LAYER4_API_URL", DEFAULT_LAYER4_URL).rstrip("/")
    timeout = float(os.getenv("CONTRACT_TEST_TIMEOUT", DEFAULT_TIMEOUT))
    
    async with AsyncClient(base_url=base_url, timeout=timeout) as client:
        yield client
