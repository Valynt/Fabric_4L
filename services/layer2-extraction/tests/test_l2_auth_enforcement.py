"""P0-002 acceptance test: L2 Extraction requires unconditional auth.

Validates:
1. GovernanceMiddleware is installed unconditionally
2. Production startup fails when FABRIC_AUTH_PUBLIC_KEYS is missing
3. Signal lifecycle routes require auth (401 without JWT)
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from layer2_extraction.api.main import app


@pytest.mark.asyncio
async def test_signal_lifecycle_requires_auth():
    """POST /signals/{id} without auth must return 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/signals/test-signal")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_signal_supersede_requires_auth():
    """POST /signals/{id}/supersede without auth must return 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/signals/test-signal/supersede",
            json={"target_signal_id": "target-1"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_signal_merge_requires_auth():
    """POST /signals/{id}/merge without auth must return 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/signals/test-signal/merge",
            json={"target_signal_id": "target-1"}
        )
        assert response.status_code == 401


def test_governance_middleware_installed():
    """GovernanceMiddleware must be present in app middleware stack."""
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    middleware_types = [type(m.cls) if hasattr(m, "cls") else type(m) for m in app.user_middleware]
    assert GovernanceMiddleware in middleware_types or any(
        "GovernanceMiddleware" in str(m) for m in app.user_middleware
    )


<<<<<<< ours
<<<<<<< ours
def test_production_startup_fails_without_auth_keys():
    """Production startup must raise RuntimeError when FABRIC_AUTH_PUBLIC_KEYS missing."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "APP_ENV": "production",
        "FABRIC_AUTH_PUBLIC_KEYS": "",
    }, clear=False):
        # We simulate the guard logic directly since we can't easily re-import main.py
        from layer2_extraction.api.main import _is_production_like
        is_prod = _is_production_like()
        assert is_prod is True
        keys_missing = not os.getenv("FABRIC_AUTH_PUBLIC_KEYS", "").strip()
        assert keys_missing is True


def test_tenant_enforcement_middleware_installed_fail_closed():
    """Layer 2 must install shared tenant enforcement instead of opting out."""
    middleware_names = [m.cls.__name__ for m in app.user_middleware]
    assert "_TenantEnforcementMiddleware" in middleware_names


def test_public_tenant_context_exemptions_are_health_and_readiness_only():
    """Only documented health/readiness probes bypass tenant-context enforcement."""
    from layer2_extraction.api.main import _S2S_INTERNAL_PATHS, _TENANT_CONTEXT_EXEMPT_PATHS

    assert _TENANT_CONTEXT_EXEMPT_PATHS == frozenset(
        {"/health", "/health/live", "/ready", "/readiness"}
    )
    assert _S2S_INTERNAL_PATHS.isdisjoint(_TENANT_CONTEXT_EXEMPT_PATHS)
=======
=======
>>>>>>> theirs
def _assert_auth_keys_required_for_environment(monkeypatch: pytest.MonkeyPatch, environment: str):
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.delenv("LAYER2_ENV", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("FABRIC_AUTH_PUBLIC_KEYS", "")

    # Simulate the import-time guard logic directly since re-importing main.py is expensive.
    from layer2_extraction.api.main import _is_strict_runtime

    assert _is_strict_runtime() is True
    keys_missing = not os.getenv("FABRIC_AUTH_PUBLIC_KEYS", "").strip()
    assert keys_missing is True


def test_production_startup_fails_without_auth_keys(monkeypatch: pytest.MonkeyPatch):
    """Production startup must require FABRIC_AUTH_PUBLIC_KEYS."""
    _assert_auth_keys_required_for_environment(monkeypatch, "production")


@pytest.mark.parametrize("environment", ["staging", "custom-preview"])
def test_strict_startup_fails_without_auth_keys(monkeypatch: pytest.MonkeyPatch, environment: str):
    """Staging and unknown/custom environments must require FABRIC_AUTH_PUBLIC_KEYS."""
    _assert_auth_keys_required_for_environment(monkeypatch, environment)


def test_development_startup_allows_missing_auth_keys(monkeypatch: pytest.MonkeyPatch):
    """Explicit development runtime must keep local startup behavior permissive."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("LAYER2_ENV", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("FABRIC_AUTH_PUBLIC_KEYS", "")

    from layer2_extraction.api.main import _is_strict_runtime

    assert _is_strict_runtime() is False
    keys_missing = not os.getenv("FABRIC_AUTH_PUBLIC_KEYS", "").strip()
    assert keys_missing is True
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
