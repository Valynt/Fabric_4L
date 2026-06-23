"""Hostile-tenant end-to-end matrix guardrails.

Static checks that ensure hostile-path coverage exists for:
- L1-L7 + API gateway cross-tenant/IDOR probes,
- RBAC downgrade and privilege escalation handling,
- tampered/expired token handling,
- safe error contract shape (no internals), and
- denied-action observability hooks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.security, pytest.mark.tenant_boundary]

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SPEC = REPO_ROOT / "apps/web/e2e/security/hostile-tenant-enforcement-matrix.spec.ts"


REQUIRED_ROUTE_PATTERNS = [
    "**/api/v1/sources/**",  # L1
    "**/api/v1/extraction/**",  # L2
    "**/api/v1/entities/**",  # L3
    "**/api/v1/workflows/**",  # L4
    "**/api/v1/truth/**",  # L5
    "**/api/v1/benchmarks/**",  # L6
    "**/api/v1/billing/**",  # L7
    "**/api/v1/accounts/**",  # API gateway
]

REQUIRED_BEHAVIORS = [
    "IDOR_RESOURCE_NOT_FOUND",
    "AUTH_FORBIDDEN",
    "AUTH_EXPIRED",
    "AUTH_TAMPERED",
    "RBAC_DENIED",
    "auditEventExpected: true",
]

FORBIDDEN_LEAK_TERMS = ["traceback", "sqlalchemy", "password", "secret", "api_key"]


def test_frontend_hostile_tenant_matrix_spec_exists() -> None:
    assert FRONTEND_SPEC.exists(), f"Missing frontend hostile matrix spec: {FRONTEND_SPEC}"


def test_matrix_covers_l1_l7_and_api_gateway_paths() -> None:
    src = FRONTEND_SPEC.read_text(encoding="utf-8")
    for pattern in REQUIRED_ROUTE_PATTERNS:
        assert pattern in src, f"Missing hostile matrix route pattern: {pattern}"


def test_matrix_covers_idor_rbac_and_token_abuse_paths() -> None:
    src = FRONTEND_SPEC.read_text(encoding="utf-8")
    for marker in REQUIRED_BEHAVIORS:
        assert marker in src, f"Missing hostile matrix behavior marker: {marker}"


def test_matrix_asserts_error_contract_and_observability() -> None:
    src = FRONTEND_SPEC.read_text(encoding="utf-8").lower()
    assert "request_id" in src and "error" in src and "code" in src
    for term in FORBIDDEN_LEAK_TERMS:
        assert term in src, f"Expected explicit no-leak assertion for term: {term}"
    assert "deniedactionsobserved" in src
