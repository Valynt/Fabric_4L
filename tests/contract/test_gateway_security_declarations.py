"""Contract test: the API gateway OpenAPI spec must declare HTTPBearer on every protected operation.

The gateway (``app.main``) authenticates most endpoints through dependencies that
resolve an ``HTTPBearer`` security object, which FastAPI emits as per-operation
``security: [{"HTTPBearer": []}]`` in the exported ``contracts/openapi/fabric-4l-api.json``.

Operations that authenticate through the shared *context-based*
``value_fabric.shared.identity.dependencies.require_authenticated`` have no security
object in their dependency graph, so FastAPI silently omits the ``security``
requirement. That is spec under-declaration: runtime auth still enforces the boundary
(the context dependency raises 401), but SDKs and contract consumers cannot see it.

This test encodes two invariants:

1. **Fail closed for new endpoints** - every HTTP operation in the gateway spec MUST
   declare ``security: [{"HTTPBearer": []}]`` unless it is explicitly allowlisted as a
   public endpoint.
2. **Allowlist discipline** - every allowlisted operation must actually exist and stay
   unstamped; deleting or re-stamping an allowlisted endpoint fails the test so the
   list cannot rot.

Public (allowlisted) gateway endpoints are exactly: health/readiness probes, metrics,
self-service auth entrypoints (signup/login/accept-invite), auth health probes, and the
outbound-only Clerk webhook receiver.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract_static_no_service

REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_SPEC_PATH = REPO_ROOT / "contracts" / "openapi" / "fabric-4l-api.json"

EXPECTED_SECURITY = [{"HTTPBearer": []}]

# Canonical allowlist of public endpoints that legitimately declare NO security.
# Operations NOT in this list must declare HTTPBearer.
PUBLIC_ALLOWLIST: set[tuple[str, str]] = {
    ("get", "/ready"),
    ("get", "/health"),
    ("get", "/health/live"),
    ("get", "/metrics"),
    ("post", "/v1/auth/signup"),
    ("post", "/v1/auth/login"),
    ("post", "/v1/auth/accept-invite"),
    ("get", "/v1/auth/health"),
    ("get", "/v1/auth/clerk/health"),
    ("post", "/internal/webhooks/clerk"),
}

# Operations that historically under-declared security because they authenticate via
# the context-based shared dependency. Regression guard for the router-level
# ``require_bearer_declaration`` fix.
FORMERLY_UNDECLARED: set[tuple[str, str]] = {
    ("get", "/v1/benchmarks"),
    ("post", "/v1/benchmarks/compare"),
    ("get", "/v1/usage"),
    ("get", "/v1/usage/quotas"),
    ("post", "/v1/value-drivers/map"),
    ("post", "/v1/value-models/generate"),
    ("post", "/v1/value-models/validate"),
    ("post", "/v1/value-models/qa"),
    ("post", "/v1/assumptions/score"),
    ("post", "/v1/evidence/extract-value-signals"),
    ("post", "/v1/cfo-narratives/generate"),
    ("post", "/v1/realization/compare"),
    ("get", "/v1/jobs/{job_id}"),
    ("get", "/v1/auth/api-keys"),
    ("post", "/v1/auth/api-keys"),
    ("delete", "/v1/auth/api-keys/{key_id}"),
}

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def _load_gateway_spec() -> dict[str, object]:
    with open(GATEWAY_SPEC_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _iter_operations(
    spec: dict[str, object],
) -> list[tuple[str, str, dict[str, object]]]:
    operations: list[tuple[str, str, dict[str, object]]] = []
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                operations.append((method, path, operation))
    return operations


def test_gateway_declares_httpbearer_security_scheme() -> None:
    """The security scheme referenced by every protected op must exist."""
    spec = _load_gateway_spec()
    schemes = spec.get("components", {}).get("securitySchemes", {})
    assert "HTTPBearer" in schemes, "gateway spec must declare an HTTPBearer security scheme"
    assert schemes["HTTPBearer"] == {"type": "http", "scheme": "bearer"}


def test_every_non_public_gateway_operation_declares_http_bearer() -> None:
    """Fail closed: any un-allowlisted operation must declare HTTPBearer."""
    spec = _load_gateway_spec()
    undeclared = []
    for method, path, operation in _iter_operations(spec):
        if (method, path) in PUBLIC_ALLOWLIST:
            continue
        if operation.get("security") != EXPECTED_SECURITY:
            undeclared.append((method, path, operation.get("security")))
    assert not undeclared, (
        f"{len(undeclared)} gateway operation(s) do not declare "
        f"security: {EXPECTED_SECURITY}\n"
        + "\n".join(
            f"  {m.upper()} {p} -> {s!r}" for m, p, s in undeclared[:10]
        )
        + (f"\n  ... and {len(undeclared) - 10} more" if len(undeclared) > 10 else "")
    )


def test_public_allowlist_entries_stay_unstamped() -> None:
    """Every allowlisted endpoint must exist and must NOT declare HTTPBearer."""
    spec = _load_gateway_spec()
    by_method_path = {(m, p): op for m, p, op in _iter_operations(spec)}

    missing = [f"{m.upper()} {p}" for m, p in PUBLIC_ALLOWLIST if (m, p) not in by_method_path]
    assert not missing, f"allowlist references missing endpoints: {missing}"

    restamped = [
        f"{m.upper()} {p}"
        for m, p in PUBLIC_ALLOWLIST
        if "security" in by_method_path[(m, p)]
    ]
    assert not restamped, (
        f"allowlisted public endpoints unexpectedly declare security: {restamped}"
    )


def test_formerly_undeclared_operations_are_now_stamped() -> None:
    """Regression guard: the 16 context-auth operations must now declare HTTPBearer."""
    spec = _load_gateway_spec()
    by_method_path = {(m, p): op for m, p, op in _iter_operations(spec)}

    missing = [
        f"{m.upper()} {p}"
        for m, p in FORMERLY_UNDECLARED
        if (m, p) not in by_method_path
    ]
    assert not missing, f"expected operations missing from spec: {missing}"

    unstamped = [
        f"{m.upper()} {p}"
        for m, p in FORMERLY_UNDECLARED
        if by_method_path[(m, p)].get("security") != EXPECTED_SECURITY
    ]
    assert not unstamped, (
        f"context-auth operations lost their HTTPBearer declaration: {unstamped}"
    )