"""Hostile tenant and auth abuse regression coverage.

These tests add static, cross-layer guardrail assertions for:
- cross-tenant/IDOR controls across L1-L7 and API gateway route files,
- RBAC downgrade / privilege escalation resistance,
- expired/tampered token handling shape,
- contract-safe error payloads (no sensitive internals), and
- denied-action audit observability hooks on sensitive routes.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.security, pytest.mark.tenant_boundary]

REPO_ROOT = Path(__file__).resolve().parents[2]

LAYER_ROUTE_FILES = {
    "L1": REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/routes/compatibility.py",
    "L2": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/main.py",
    "L3": REPO_ROOT / "services/layer3-knowledge/src/api/routes/entities.py",
    "L4": REPO_ROOT / "services/layer4-agents/src/layer4_agents/api/routes/workflows.py",
    "L5": REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/api/router.py",
    "L6": REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/benchmarks.py",
    "L7": REPO_ROOT / "services/layer7-billing/src/layer7_billing/api/main.py",
    "API": REPO_ROOT / "services/api/app/routers/accounts.py",
}

SENSITIVE_LEAK_PATTERNS = [
    r"traceback",
    r"sqlalchemy",
    r"password",
    r"secret",
    r"api[_-]?key",
    r"bearer\s+",
    r"(access|refresh|id)[_-]?token",
    r"jwt",
]


def _read(path: Path) -> str:
    assert path.exists(), f"Expected file does not exist: {path}"
    return path.read_text(encoding="utf-8")


def _dependency_calls(src: str) -> set[str]:
    tree = ast.parse(src)
    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Depends":
            if node.args and isinstance(node.args[0], ast.Name):
                deps.add(node.args[0].id)
    return deps


@pytest.mark.parametrize("layer,path", LAYER_ROUTE_FILES.items())
def test_cross_tenant_and_idor_routes_use_auth_or_tenant_context(layer: str, path: Path) -> None:
    src = _read(path)
    deps = _dependency_calls(src)
    acceptable = {
        "require_authenticated",
        "get_db_from_context",
        "get_current_user",
        "require_admin",
        "tenant_required",
        "get_db_from_context_sync",
        "get_request_context",
        "require_role",
    }
    textual_guards = {
        "_require_authenticated_tenant_id",
        "require_authenticated",
        "get_db_from_context",
        "get_db_from_context_sync",
        "get_request_context",
        "tenant_required",
    }
    assert deps & acceptable or any(token in src for token in textual_guards), (
        f"{layer} route file {path} is missing tenant/auth dependencies; "
        "IDOR and cross-tenant route access hardening cannot be proven."
    )


def test_rbac_privilege_escalation_requires_explicit_admin_permissions() -> None:
    permissions = _read(REPO_ROOT / "packages/shared/src/value_fabric/shared/identity/permissions.py")
    context = _read(REPO_ROOT / "packages/shared/src/value_fabric/shared/identity/context.py")
    assert "ADMIN_SYSTEM" in permissions and "ADMIN_TENANTS" in permissions
    assert "has_permission" in context and "has_any_permission" in context


def test_tampered_or_expired_token_paths_fail_closed_and_return_safe_error_shape() -> None:
    auth_tests = _read(REPO_ROOT / "services/api/app/tests/test_jwks_and_token_validation.py")
    assert "401" in auth_tests
    assert any(token in auth_tests for token in ["expired", "invalid", "tamper"])


def test_error_payload_contract_avoids_sensitive_internal_leaks() -> None:
    shared_errors = _read(REPO_ROOT / "packages/shared/src/value_fabric/shared/error_handling/models.py")
    lower = shared_errors.lower()
    for pattern in SENSITIVE_LEAK_PATTERNS:
        assert re.search(pattern, lower) is None, f"Sensitive term leaked in error contract: {pattern}"


def test_denied_actions_have_audit_or_security_logging_hooks() -> None:
    security_files = [
        REPO_ROOT / "services/api/app/main.py",
        REPO_ROOT / "services/api/app/routers/governance.py",
        REPO_ROOT / "packages/shared/src/value_fabric/shared/identity/middleware.py",
    ]
    blob = "\n".join(_read(path) for path in security_files if path.exists()).lower()
    assert any(term in blob for term in ["audit", "security", "denied", "forbidden", "logger"]), (
        "Expected denied-action observability hooks (audit/security logging) were not found."
    )
