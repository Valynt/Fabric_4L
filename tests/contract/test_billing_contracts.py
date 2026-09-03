import os
import sys
import time
from pathlib import Path

import pytest

try:
    import asyncpg  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover
    pytest.skip(
        f"{exc.name} is not installed; install test deps with "
        "`pip install -r tests/requirements-test.txt`",
        allow_module_level=True,
    )

from fastapi.testclient import TestClient

try:
    import jwt
except ModuleNotFoundError:  # pragma: no cover
    pytest.skip("PyJWT not installed", allow_module_level=True)

# Patch rate limiters BEFORE importing the app to avoid spurious 429s
# in contract tests where Redis is not available.
try:
    from value_fabric.shared.rate_limiting.tenant_rate_limiter import SlidingWindowAdapter

    _orig_sw_check = SlidingWindowAdapter.check

    async def _patched_sw_check(self, *args, **kwargs):
        class _Decision:
            allowed = True
            remaining = 999
            reset_epoch = 0
            retry_after = None
        return _Decision()

    SlidingWindowAdapter.check = _patched_sw_check
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

_LAYER7_DB_URL = os.getenv(
    "LAYER7_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/layer7_billing"
)


def _db_available() -> bool:
    import asyncio
    import urllib.parse

    parsed = urllib.parse.urlparse(_LAYER7_DB_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or "postgres"
    database = parsed.path.lstrip("/") or "layer7_billing"

    async def _probe() -> bool:
        try:
            conn = await asyncpg.connect(
                host=host, port=port, user=user, password=password, database=database, timeout=3
            )
            await conn.close()
            return True
        except Exception:
            return False

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # Running inside an event loop (e.g., pytest-asyncio); we can't run_until_complete.
        # Defer the check to a synchronous socket probe instead.
        import socket

        try:
            with socket.create_connection((host, port), timeout=3):
                return True
        except Exception:
            return False

    return asyncio.new_event_loop().run_until_complete(_probe())


if not _db_available():
    pytest.skip("PostgreSQL not reachable; start DB to run billing contract tests", allow_module_level=True)

sys.path.append(str(Path(__file__).resolve().parents[2] / "services/layer7-billing/src"))
from layer7_billing.api.main import app

_TEST_JWT_SECRET = os.getenv(
    "JWT_SECRET",
    os.getenv("TEST_JWT_SECRET", "test-secret-key-must-be-at-least-32-bytes!!"),
)


def _make_token(tenant: str, roles: list[str]) -> str:
    now = int(time.time())
    payload = {
        "sub": "test-contract-user",
        "tenant_id": tenant,
        "roles": roles,
        "iat": now,
        "exp": now + 3600,
        "iss": os.getenv("JWT_ISSUER", "value-fabric-internal"),
        "aud": os.getenv("JWT_AUDIENCE", "value-fabric-services"),
    }
    return jwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


def _headers(tenant: str, roles: list[str] | None = None) -> dict[str, str]:
    if roles is None:
        roles = ["billing:read", "billing:write"]
    token = _make_token(tenant, roles)
    return {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": "contract-test-req-001",
    }


def test_entitlement_contract_and_single_decision_api() -> None:
    client = TestClient(app)
    client.post(
        "/v1/billing/plans",
        headers=_headers("tenant-a"),
        json={"plan_id": "pro", "name": "Pro", "entitlements": ["feature.alpha"]},
    )
    resp = client.get(
        "/v1/billing/entitlements/pro/decision",
        headers=_headers("tenant-a", roles=["billing:read"]),
        params={"feature": "feature.alpha"},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["allowed"] is True
    assert body["policy"] == "runtime-entitlement-api-v1"


def test_usage_event_append_only_and_idempotent_aggregate() -> None:
    client = TestClient(app)
    payload = {
        "event_id": "evt-1",
        "metric": "tokens",
        "quantity": 10,
        "source": "layer4",
        "timestamp": "2026-05-26T00:00:00Z",
        "request_id": "req-1",
    }
    first = client.post(
        "/v1/billing/usage-events",
        headers=_headers("tenant-a"),
        json=payload,
    )
    second = client.post(
        "/v1/billing/usage-events",
        headers=_headers("tenant-a"),
        json=payload,
    )
    assert first.status_code == 200
    assert second.json()["status"] == "duplicate"
    agg = client.get(
        "/v1/billing/usage-aggregates",
        headers=_headers("tenant-a", roles=["billing:read"]),
    ).json()
    assert agg["metrics"]["tokens"] == 10
