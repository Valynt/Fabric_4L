"""Fixtures for MCP Gateway tests."""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Any
from uuid import uuid4

from value_fabric.shared.mcp_gateway.mcp_types import (
    ToolManifest,
    OAuthClientConfig,
    ToolRequest,
)
from value_fabric.shared.models.typed_dict import TypedDictModel


class sample_rsa_keypairResult(TypedDictModel):
    private: Any
    public: Any


@pytest.fixture
def sample_tool_manifest():
    """Sample tool manifest for testing."""
    return ToolManifest(
        tool_name="test_search",
        version="1.0.0",
        description="Test search tool",
        endpoint="https://tools.example.com/search",
        capabilities=["search", "read"],
        required_scopes=["tools:read"],
        tenant_scoped=True,
    )


@pytest.fixture
def sample_oauth_config():
    """Sample OAuth client configuration."""
    return OAuthClientConfig(
        client_id="test-client-123",
        client_secret="test-secret",
        authorization_endpoint="https://auth.example.com/authorize",
        token_endpoint="https://auth.example.com/token",
        redirect_uri="https://app.example.com/callback",
        scopes=["tools:read", "tools:write"],
    )


@pytest.fixture
def sample_tool_request():
    """Sample tool request."""
    return ToolRequest(
        tool_name="test_search",
        parameters={"query": "test"},
        tenant_id=uuid4(),
        user_id="user-123",
        request_id="req-456",
    )


@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient for testing."""
    mock = AsyncMock()
    mock.post = AsyncMock()
    mock.get = AsyncMock()
    return mock


@pytest.fixture
def sample_rsa_keypair():
    """Generate RSA key pair for testing manifest signing."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    
    return sample_rsa_keypairResult.model_validate({"private": private_pem, "public": public_pem})
