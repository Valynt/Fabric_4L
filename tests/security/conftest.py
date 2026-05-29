"""Shared fixtures for security tests."""

import os
import sys
from pathlib import Path
from typing import Callable, Generator

import pytest
import jwt
from unittest.mock import MagicMock, AsyncMock

# Layer 3 source root is needed by tests that import layer3_knowledge.*
# (e.g. test_neo4j_cross_tenant_write_isolation.py).  The value_fabric.layer3
# shim appends services/layer3-knowledge/src to its __path__, but bare
# intra-package imports inside that tree (e.g. ``from api.dependencies import
# ...``) still require the src root to be on sys.path directly.
# Scoped here rather than in the root conftest to avoid the ``src`` namespace
# collision documented in conftest.py.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_L3_SRC = str(_REPO_ROOT / "services" / "layer3-knowledge" / "src")
if _L3_SRC not in sys.path:
    sys.path.insert(0, _L3_SRC)

# Lazy imports for optional dependencies
def _get_psycopg2():
    try:
        import psycopg2
        return psycopg2
    except ImportError:
        return None

def _get_redis():
    try:
        import redis
        return redis
    except ImportError:
        return None

def _get_testclient():
    try:
        from fastapi.testclient import TestClient
        return TestClient
    except ImportError:
        return None

# Test configuration constants
# JWT_SECRET is the canonical env var name used across CI and all layers
# SECURITY: Use a 32+ byte secret so PyJWT HS256 does not emit InsecureKeyLengthWarning.
TEST_JWT_SECRET = os.getenv(
    "JWT_SECRET",
    os.getenv("TEST_JWT_SECRET", "test-secret-key-must-be-at-least-32-bytes!!"),
)
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0

# Ensure legacy non-UUID tenant IDs are accepted during security test execution.
# This matches the pytest.ini intent (TESTING=true) when pytest-env is absent.
os.environ.setdefault("TESTING", "true")

# SECURITY: Auth boundary tests verify role/access control, not rate limits.
# Process-local rate limit state persists across tests and causes spurious 429s.
# Patch the two rate-limit paths to always allow so tests don't contaminate each other.
try:
    from value_fabric.shared.identity.rate_limiter import RedisRateLimiter

    _orig_rl_check = RedisRateLimiter.check

    async def _patched_rl_check(self, *args, **kwargs):
        return type("FakeResult", (), {
            "allowed": True, "remaining": 999, "reset_at": 0.0, "retry_after": None
        })()

    RedisRateLimiter.check = _patched_rl_check
except Exception:
    pass

try:
    from value_fabric.shared.identity import middleware

    _orig_tenant_rl_check = middleware._check_tenant_rate_limit

    def _patched_tenant_rl_check(tenant_id, requests_per_minute):
        return True, 0

    middleware._check_tenant_rate_limit = _patched_tenant_rl_check
except Exception:
    pass


@pytest.fixture
def jwt_encoder() -> Callable[[dict], str]:
    """JWT encoding fixture for creating test tokens.

    Tokens include ``iat``, ``exp``, ``iss``, and ``aud`` so they pass
    ``decode_jwt`` validation in both dev and test environments.
    """
    import time

    def encode(payload: dict) -> str:
        now = int(time.time())
        claims = {
            "iat": now,
            "exp": now + 3600,
            "iss": os.getenv("JWT_ISSUER", "value-fabric-internal"),
            "aud": os.getenv("JWT_AUDIENCE", "value-fabric-services"),
        }
        claims.update(payload)
        return jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")
    return encode


@pytest.fixture
def standard_user_token(jwt_encoder) -> str:
    """Standard user JWT token with limited permissions."""
    return jwt_encoder({
        "sub": "user-123",
        "tenant_id": "tenant-a",
        "role": "standard",
    })


@pytest.fixture
def admin_user_token(jwt_encoder) -> str:
    """Admin user JWT token with full permissions."""
    return jwt_encoder({
        "sub": "admin-456",
        "tenant_id": "tenant-a",
        "role": "admin",
    })


@pytest.fixture
def tenant_a_token(jwt_encoder) -> str:
    """JWT token for Tenant A user."""
    return jwt_encoder({
        "sub": "user-123",
        "tenant_id": "tenant-a",
        "role": "standard",
        "email": "user@tenant-a.com",
    })


@pytest.fixture
def tenant_b_token(jwt_encoder) -> str:
    """JWT token for Tenant B user."""
    return jwt_encoder({
        "sub": "user-456",
        "tenant_id": "tenant-b",
        "role": "standard",
        "email": "user@tenant-b.com",
    })


def check_db() -> bool:
    """Check if database is available."""
    psycopg2 = _get_psycopg2()
    if psycopg2 is None:
        return False
    db_url = os.getenv("TEST_DATABASE_URL", "postgresql://localhost:5432/test_value_fabric")
    try:
        conn = psycopg2.connect(db_url)
        conn.close()
        return True
    except psycopg2.OperationalError:
        return False


def check_redis() -> bool:
    """Check if Redis is available."""
    redis = _get_redis()
    if redis is None:
        return False
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    try:
        client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=False)
        client.ping()
        client.close()
        return True
    except redis.ConnectionError:
        return False


@pytest.fixture(scope="session")
def require_security_deps():
    """Ensure security test dependencies are available - hard fail in CI."""
    if os.getenv("CI") == "true":
        # In CI, hard requirements
        assert check_db(), "Security tests require DB in CI"
        assert check_redis(), "Security tests require Redis in CI"
    # Return silently in non-CI mode


@pytest.fixture
def db_connection() -> Generator:
    """Database connection for RLS policy testing."""
    psycopg2 = _get_psycopg2()
    if psycopg2 is None:
        pytest.skip("psycopg2 not installed")
    
    db_url = os.getenv("TEST_DATABASE_URL", "postgresql://localhost:5432/test_value_fabric")

    if os.getenv("CI") == "true":
        # In CI, hard fail
        if not check_db():
            raise RuntimeError("Security tests require DB. Run: docker-compose up postgres")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        yield conn
    except psycopg2.OperationalError as e:
        if os.getenv("CI") == "true":
            raise RuntimeError(f"Security tests require DB in CI: {e}")
        pytest.skip(f"Database not available for RLS testing: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@pytest.fixture
def redis_client() -> Generator:
    """Redis client for cache isolation testing."""
    redis = _get_redis()
    if redis is None:
        pytest.skip("redis not installed")
    
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", DEFAULT_REDIS_PORT))
    redis_db = int(os.getenv("REDIS_DB", DEFAULT_REDIS_DB))

    if os.getenv("CI") == "true" and not check_redis():
        raise RuntimeError("Security tests require Redis. Run: docker-compose up redis")

    try:
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False,
        )
        # Test connection before yielding
        client.ping()
        yield client
    except redis.ConnectionError as e:
        if os.getenv("CI") == "true":
            raise RuntimeError(f"Security tests require Redis in CI: {e}")
        pytest.skip(f"Redis not available for cache isolation testing: {e}")
    finally:
        if 'client' in locals() and client:
            client.close()


class _CallableString(str):
    """String proxy that also supports legacy ``response.text()`` calls."""

    def __call__(self) -> str:
        return str(self)


class _AwaitableResponse:
    """Proxy an HTTP response for both sync and legacy async security tests."""

    def __init__(self, response):
        self._response = response

    def __await__(self):
        async def _return_self():
            return self

        return _return_self().__await__()

    def __getattr__(self, name: str):
        if name == "text":
            return _CallableString(self._response.text)
        return getattr(self._response, name)


class _HybridTestClient:
    """Expose TestClient methods that work with or without ``await``."""

    def __init__(self, client):
        self._client = client

    def __getattr__(self, name: str):
        return getattr(self._client, name)

    def _wrap(self, response):
        return _AwaitableResponse(response)

    def get(self, *args, **kwargs):
        return self._wrap(self._client.get(*args, **kwargs))

    def post(self, *args, **kwargs):
        return self._wrap(self._client.post(*args, **kwargs))

    def put(self, *args, **kwargs):
        return self._wrap(self._client.put(*args, **kwargs))

    def patch(self, *args, **kwargs):
        return self._wrap(self._client.patch(*args, **kwargs))

    def delete(self, *args, **kwargs):
        return self._wrap(self._client.delete(*args, **kwargs))

    def options(self, *args, **kwargs):
        return self._wrap(self._client.options(*args, **kwargs))


@pytest.fixture
def client():
    """Hybrid L1 ingestion API client for sync and async security tests."""
    from fastapi.testclient import TestClient
    
    try:
        from layer1_ingestion.api.app_monolith import app
        return _HybridTestClient(TestClient(app))
    except ImportError:
        pytest.skip("FastAPI app not available for testing")


@pytest.fixture
def expired_token(jwt_encoder) -> str:
    """Expired JWT token for negative testing."""
    import time
    return jwt_encoder({
        "sub": "user-123",
        "tenant_id": "tenant-a",
        "role": "standard",
        "exp": int(time.time()) - 3600,  # Expired 1 hour ago
    })


@pytest.fixture
def invalid_signature_token() -> str:
    """Token with invalid signature for negative testing."""
    # Create a valid-looking token but sign with wrong secret
    payload = {
        "sub": "user-123",
        "tenant_id": "tenant-a",
        "role": "standard",
    }
    return jwt.encode(payload, "wrong-secret", algorithm="HS256")


@pytest.fixture
def malformed_token() -> str:
    """Completely malformed token."""
    return "not.a.valid.jwt.token"


@pytest.fixture
def auth_headers(auth_headers_a):
    """Legacy alias for Tenant A JWT auth headers used by older security suites."""
    return dict(auth_headers_a)


@pytest.fixture
def user_headers(auth_headers_a):
    """Legacy alias for standard-user JWT auth headers used by older security suites."""
    return dict(auth_headers_a)


@pytest.fixture
def admin_headers(auth_headers_admin):
    """Legacy alias for admin JWT auth headers used by older security suites."""
    return dict(auth_headers_admin)


@pytest.fixture
def websocket_client(monkeypatch):
    """TestClient fixture for L4 WebSocket testing."""
    TestClient = _get_testclient()
    if TestClient is None:
        pytest.skip("fastapi not installed")
    
    try:
        # Try to import L4 app - may not be available without dependencies
        from services.layer4_agents.src.api.main import app
    except ImportError:
        pytest.skip("Layer 4 FastAPI app not available for WebSocket testing")
    
    # Mock the workflow executor so WebSocket auth tests don't fail
    # due to uninitialized executor (503 error).
    # The mock returns a status that matches any tenant so auth tests pass.
    mock_executor = AsyncMock()
    
    async def _mock_get_status(workflow_id):
        # Extract tenant from workflow_id if it contains one, else default
        if ":" in workflow_id:
            tenant_id = workflow_id.split(":")[0]
        else:
            tenant_id = "tenant-a"
        return {
            "tenant_id": tenant_id,
            "user_id": "user-123",
            "status": "running",
        }
    
    mock_executor.get_workflow_status = _mock_get_status
    
    def _mock_get_executor():
        return mock_executor
    
    # Patch get_executor in the websocket routes module
    try:
        import services.layer4_agents.src.api.routes.workflows as _wf_mod
        monkeypatch.setattr(_wf_mod, "get_executor", _mock_get_executor)
    except Exception:
        pass
    
    # Also patch at the websocket routes import location
    try:
        import services.layer4_agents.src.api.websocket.routes as _ws_mod
        # The websocket routes import get_executor locally, so we need to patch
        # the workflows module it imports from
        import services.layer4_agents.src.api.routes.workflows as _wf_mod2
        monkeypatch.setattr(_wf_mod2, "get_executor", _mock_get_executor)
    except Exception:
        pass
    
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_rate_limit_buckets():
    """Clear process-local rate limit buckets before each test.

    The GovernanceMiddleware fallback rate limiter uses a module-level dict
    that persists across tests in the same process. Without clearing it,
    subsequent tests can spuriously hit 429 rate-limit responses.
    """
    import gc
    from value_fabric.shared.identity import middleware
    from value_fabric.shared.rate_limiting.tenant_rate_limiter import SlidingWindowAdapter

    middleware._tenant_rate_limit_buckets.clear()
    for adapter in gc.get_objects():
        if isinstance(adapter, SlidingWindowAdapter):
            adapter._memory_windows.clear()
    yield


@pytest.fixture
def mock_neo4j_driver():
    """Create a mock Neo4j driver with async session support for tenant query tests.
    
    Returns a tuple of (mock_driver, mock_session, mock_result) to allow
    test-specific customization of the result behavior.
    """
    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.single.return_value = None
    mock_session.run.return_value = mock_result
    
    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)
    
    return mock_driver, mock_session, mock_result
