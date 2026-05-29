import os

import pytest

_TEST_ENV_DEFAULTS = {
    "ENVIRONMENT": "test",
    "APP_ENV": "test",
    "TESTING": "true",
    "AUTH_REQUIRED": "true",
    "PORT": "8006",
    "API_PORT": "8006",
    "API_HOST": "0.0.0.0",
    "LOG_LEVEL": "INFO",
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "test_password",
    "NEO4J_DATABASE": "neo4j",
    "NEO4J_MAX_POOL_SIZE": "10",
    # P0-008: Dev auth bypass flags removed — no longer needed
    # Match root conftest.py secret defaults so L6 service venv can boot the FastAPI
    # app without a live Infisical / vault. Mirrors the canonical test-secret values
    # required by value_fabric.shared.secrets.infisical._validate_required_secrets.
    "JWT_SECRET": "dummy_jwt_secret_for_tests_must_be_32_chars",
    "API_KEY_HMAC_SECRET": "dummy_api_key_secret_for_tests_must_be_32_chars",
    "SERVICE_AUTH_SECRET": "dummy_service_auth_secret_for_tests_32_chars",
    "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/fabric",
    "DATABASE_URL_SYNC": "postgresql+psycopg2://postgres:postgres@localhost:5432/fabric",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "fabric",
    "DB_USER": "postgres",
    "DB_PASSWORD": "postgres_test_password",
    "LAYER3_API_KEY": "layer3_test_api_key_1234567890",
    "LAYER5_API_KEY": "layer5_test_api_key_1234567890",
    "LAYER6_SERVICE_NAME": "layer6-benchmarks",
    "LAYER6_VERSION": "test",
    "LAYER6_BUILD_SHA": "test-sha",
}
for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

import layer6_benchmarks.database as database
from value_fabric.shared.identity.middleware import GovernanceMiddleware


@pytest.fixture(autouse=True)
def mock_governance_middleware(monkeypatch):
    """Bypass the actual JWT validation in GovernanceMiddleware for tests.
    We rely on app.dependency_overrides[get_request_context] in the test client
    to control the actual tenant_id seen by the endpoints."""
    async def mock_dispatch(self, request, call_next):
        from uuid import uuid4

        from value_fabric.shared.identity.context import RequestContext
        
        # Give it a fallback context just in case, though get_request_context should override it
        ctx = RequestContext(
            tenant_id="system",
            user_id=uuid4(),
            org_id=uuid4(),
            roles=["admin"],
            permissions=[],
            auth_source="mock",
            tenant_role="admin",
            isolation_tier="shared",
            request_id="test"
        )
        request.state.governance_context = ctx
        from value_fabric.shared.identity.context import set_request_context
        set_request_context(ctx)
        return await call_next(request)
        
    monkeypatch.setattr(GovernanceMiddleware, "dispatch", mock_dispatch)

@pytest.fixture(autouse=True)
def mock_neo4j_health(monkeypatch):
    """Mock Neo4j health check to avoid real DB connections."""
    async def mock_health(*args, **kwargs):
        return {"status": "healthy"}
    
    monkeypatch.setattr(database, "health_check", mock_health)
    # Also patch the actual neo4j_health_check imported in main
    import layer6_benchmarks.api.main as main_module
    monkeypatch.setattr(main_module, "neo4j_health_check", mock_health)

