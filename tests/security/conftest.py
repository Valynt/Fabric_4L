"""Shared fixtures for security tests."""

import os
from pathlib import Path
from typing import Callable, Generator

import pytest
import jwt
from unittest.mock import MagicMock, AsyncMock

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
_REPO_ROOT = Path(__file__).resolve().parents[2]

# JWT_SECRET is the canonical env var name used across CI and all layers
# SECURITY: Use a 32+ byte secret so PyJWT HS256 does not emit InsecureKeyLengthWarning.
TEST_JWT_SECRET = os.getenv(
    "JWT_SECRET",
    os.getenv("TEST_JWT_SECRET", "test-secret-key-must-be-at-least-32-bytes!!"),
)
DEFAULT_REDIS_PORT = 6379
DEFAULT_REDIS_DB = 0
BOOL_STRINGS = {"0", "1", "false", "true", "no", "yes", "off", "on"}

# Ensure legacy non-UUID tenant IDs are accepted during security test execution.
# This matches the pytest.ini intent (TESTING=true) when pytest-env is absent.
os.environ.setdefault("TESTING", "true")
if os.environ.get("DEBUG", "").strip().lower() not in BOOL_STRINGS:
    os.environ["DEBUG"] = "false"

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

# SECURITY: Auth boundary tests verify role/access control, not the shared
# tenant-scoped rate limiter. When Redis is unavailable the shared middleware
# raises a 500; patch it out so the auth tests can run without live Redis.
try:
    from value_fabric.shared.rate_limiting.middleware import TenantRateLimitMiddleware

    _orig_tenant_rl_dispatch = TenantRateLimitMiddleware.dispatch

    async def _patched_tenant_rl_dispatch(self, request, call_next):
        return await call_next(request)

    TenantRateLimitMiddleware.dispatch = _patched_tenant_rl_dispatch
except Exception:
    pass

# SECURITY: Auth boundary tests assert RBAC decisions, not tenant kill-switch
# Redis availability. When Redis is unavailable the kill switch returns UNKNOWN,
# which the middleware maps to HTTP 503 and masks the intended 401/403/404
try:
    from value_fabric.shared.tenant_kill_switch import TenantKillSwitch, TenantSuspensionStatus

    _orig_kill_switch_check_status = TenantKillSwitch.check_status

    async def _patched_kill_switch_check_status(self, tenant_id):
        # If a real Redis client is wired, exercise the real implementation.
        if getattr(self, "_redis", None) is not None:
            try:
                result = await _orig_kill_switch_check_status(self, tenant_id)
            except Exception:
                # Redis present but failing in lightweight test env; fall through
                # to ACTIVE so auth/RBAC test outcomes remain visible.
                pass
            else:
                # The real implementation returns UNKNOWN when Redis fails closed.
                # In lightweight security tests we want auth/RBAC outcomes, not a
                # 503 from a missing Redis instance, so treat UNKNOWN as ACTIVE.
                if result is not TenantSuspensionStatus.UNKNOWN:
                    return result
        # Without Redis, treat tenants as active so auth/RBAC outcomes remain
        # visible in lightweight security smoke tests.
        return TenantSuspensionStatus.ACTIVE

    TenantKillSwitch.check_status = _patched_kill_switch_check_status
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
        from layer1_ingestion.api.main import app
        return _HybridTestClient(TestClient(app, raise_server_exceptions=False))
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
        from layer4_agents.api.main import app
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
        import layer4_agents.api.routes.workflows as _wf_mod
        monkeypatch.setattr(_wf_mod, "get_executor", _mock_get_executor)
    except Exception:
        pass
    
    # Also patch at the websocket routes import location
    try:
        # The websocket routes import get_executor locally, so we need to patch
        # the workflows module it imports from
        import layer4_agents.api.routes.workflows as _wf_mod2
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

# Files that make up the lightweight centralized security aggregation suite.
# Other files in this directory remain executable by explicit path, but they are
# intentionally not collected by the directory-level ``pytest tests/security/``
# command so that the command is a stable aggregation entrypoint rather than a
# duplicate run of every detailed layer/security regression.
_CENTRAL_SECURITY_AGGREGATION_FILES = {
    "test_auth_guards.py",
    "test_tenant_isolation.py",
    "test_secret_handling.py",
    "test_security_headers.py",
    "test_dependency_policy.py",
    "test_container_policy.py",
}


def _is_directory_level_security_aggregation(config: pytest.Config) -> bool:
    args = [str(arg).rstrip("/") for arg in getattr(config, "args", ())]
    if not args:
        return False
    security_dir = str(_REPO_ROOT / "tests" / "security")
    return all(arg in {"tests/security", security_dir} for arg in args)


def pytest_ignore_collect(collection_path, config: pytest.Config) -> bool:  # type: ignore[no-untyped-def]
    """Keep ``pytest tests/security/`` focused on the aggregation manifests.

    Explicit file runs such as ``pytest tests/security/test_rbac.py`` continue to
    collect the detailed behavioral tests used by category-specific gates.
    """
    if not _is_directory_level_security_aggregation(config):
        return False

    path = Path(str(collection_path))
    if path.suffix != ".py":
        return False
    if path.name in {"conftest.py", "__init__.py", "_category_manifest.py"}:
        return False
    return path.name not in _CENTRAL_SECURITY_AGGREGATION_FILES

_CENTRAL_SECURITY_MANIFEST_TEST_NAMES = {
    "test_auth_guard_security_coverage_manifest_is_current",
    "test_tenant_isolation_security_coverage_manifest_is_current",
    "test_secret_handling_security_coverage_manifest_is_current",
    "test_security_headers_coverage_manifest_is_current",
    "test_dependency_policy_security_coverage_manifest_is_current",
    "test_container_policy_security_coverage_manifest_is_current",
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """For the directory-level aggregation command, run only manifest tests."""
    if not _is_directory_level_security_aggregation(config):
        return

    selected = [item for item in items if item.name in _CENTRAL_SECURITY_MANIFEST_TEST_NAMES]
    deselected = [item for item in items if item.name not in _CENTRAL_SECURITY_MANIFEST_TEST_NAMES]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
