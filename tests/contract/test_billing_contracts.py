"""Billing API contract — canonical Layer 4 runtime.

Governance (R3 billing de-duplication): the legacy standalone ``layer7-billing``
service was deleted. Layer 4 (``layer4-agents`` :8004) is the canonical billing
runtime and ``contracts/openapi/layer7-billing.json`` is the retained billing
API contract — a deterministic subset export of the Layer 4 application surface
(only ``/v1/billing/*`` paths).

These checks are static + fail-closed behavior tests and do not require a live
database or a Stripe connection: they prove the committed contract matches the
Layer 4 runtime surface and that the billing routes fail closed (tenant
authentication first, Stripe signature validation before any provider work).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

try:
    import jwt
except ModuleNotFoundError:  # pragma: no cover
    pytest.skip("PyJWT not installed", allow_module_level=True)

from fastapi.testclient import TestClient

# Patch rate limiters BEFORE importing the app to avoid spurious 429s in
# contract tests where Redis is not available. The patched originals are
# restored in ``teardown_module`` so the behavior does not leak into later
# modules in the same pytest session.
_SW_ADAPTER = None
_SW_ORIGINAL_CHECK = None
_MIDDLEWARE = None
_ORIG_TENANT_RL_CHECK = None

try:
    from value_fabric.shared.rate_limiting.tenant_rate_limiter import SlidingWindowAdapter

    _SW_ADAPTER = SlidingWindowAdapter
    _SW_ORIGINAL_CHECK = SlidingWindowAdapter.check

    async def _patched_sw_check(self, *args, **kwargs):  # noqa: ANN001, ANN002
        class _Decision:
            allowed = True
            remaining = 999
            reset_epoch = 0
            retry_after = None

        return _Decision()

    SlidingWindowAdapter.check = _patched_sw_check
except (ImportError, AttributeError):
    pass

try:
    from value_fabric.shared.identity import middleware

    _MIDDLEWARE = middleware
    _ORIG_TENANT_RL_CHECK = middleware._check_tenant_rate_limit

    def _patched_tenant_rl_check(tenant_id, requests_per_minute):  # noqa: ANN001
        return True, 0

    middleware._check_tenant_rate_limit = _patched_tenant_rl_check
except (ImportError, AttributeError):
    pass

from layer4_agents.api.main import app  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "contracts" / "openapi" / "layer7-billing.json"
BILLING_PATH_MARKER = "/v1/billing/"


def teardown_module(module) -> None:  # noqa: ANN001, ARG001
    """Restore rate-limiter internals patched at import time.

    Fired after the module's tests finish so the monkeypatches do not leak into
    later modules in the same pytest session.
    """
    if _SW_ADAPTER is not None and _SW_ORIGINAL_CHECK is not None:
        _SW_ADAPTER.check = _SW_ORIGINAL_CHECK
    if _MIDDLEWARE is not None and _ORIG_TENANT_RL_CHECK is not None:
        _MIDDLEWARE._check_tenant_rate_limit = _ORIG_TENANT_RL_CHECK

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


def _layer4_billing_paths() -> dict[str, dict]:
    openapi = app.openapi()
    return {
        path: methods
        for path, methods in openapi.get("paths", {}).items()
        if BILLING_PATH_MARKER in path
    }


def test_billing_contract_matches_layer4_runtime_surface() -> None:
    """The retained contract must equal the Layer 4 billing runtime surface.

    ``contracts/openapi/layer7-billing.json`` is a deterministic subset export
    of the Layer 4 application; any drift is blocked by
    ``scripts/ci/check_contract_freshness.sh``.
    """
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_paths = dict(contract["paths"])
    layer4_paths = _layer4_billing_paths()
    assert contract_paths == layer4_paths, (
        "contracts/openapi/layer7-billing.json must equal the /v1/billing/* "
        "subset of the Layer 4 runtime. Run `python scripts/export_openapi.py` "
        "to regenerate the contract."
    )


def test_billing_contract_contains_only_billing_paths() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["paths"], "billing contract must declare at least one path"
    for path in contract["paths"]:
        assert BILLING_PATH_MARKER in path, f"non-billing path leaked into contract: {path}"


def test_billing_contract_identifies_layer4_ownership() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert "Layer 4" in contract["info"]["title"]
    assert contract.get("x-backend-service") == "layer4-agents"


def test_billing_routes_require_authentication() -> None:
    """Fail closed: unauthenticated billing access is rejected (401/403)."""
    client = TestClient(app)
    resp = client.get("/v1/billing/subscription")
    assert resp.status_code in (401, 403), (
        f"unauthenticated billing request must be rejected, got {resp.status_code}"
    )


def test_authenticated_billing_request_passes_auth_gate() -> None:
    """An authenticated request reaches the runtime fail-closed path (not 401).

    Without a configured Stripe/DB the runtime answers a structured billing
    rejection (402/500/503); the point here is that the tenant auth gate has
    already been crossed.
    """
    client = TestClient(app)
    resp = client.get("/v1/billing/subscription", headers=_headers("11111111-2222-4333-8444-555555555555"))
    assert resp.status_code not in (401, 403), (
        f"authenticated billing request must pass the auth gate, got {resp.status_code}"
    )


def test_stripe_webhook_requires_signature_header() -> None:
    """Fail closed: a Stripe webhook without a signature header is rejected.

    Signature validation happens before any provider/DB work, so this is a
    deterministic behavior check that never touches a live Stripe connection.
    """
    client = TestClient(app)
    resp = client.post(
        "/v1/billing/webhook",
        headers=_headers("11111111-2222-4333-8444-555555555555"),
        json={"type": "checkout.session.completed"},
    )
    assert resp.status_code == 422, (
        f"missing Stripe-Signature header must be rejected with 422, got {resp.status_code}"
    )
