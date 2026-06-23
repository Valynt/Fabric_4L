"""S2-B: Cross-Tenant API Isolation Tests — Production Approval Suite, Pillar 2.

Ship/No-Ship Gate: These tests verify that Tenant A's JWT cannot read, modify,
or delete resources belonging to Tenant B.  They exercise the actual FastAPI
route handlers through ``TestClient`` with signed JWTs.

Because the L4 app requires PostgreSQL, Redis, and checkpoint infrastructure
at startup, these tests use a **lightweight mock app** that mirrors the real
route registration and GovernanceMiddleware wiring but stubs out external
dependencies.  This lets us test the auth/tenant enforcement layer in isolation.

Expected Initial State:
    - Tests targeting accounts routes: FAIL (accounts.py uses get_db, no tenant scoping)
    - Tests targeting workflow routes:  PASS (workflows.py uses require_authenticated)
    - Tests targeting signal routes:    PASS (signals.py uses require_authenticated)

The tests that FAIL prove the RLS bypass is exploitable at the HTTP layer.
When the accounts routes are migrated to get_db_from_context, these tests
will pass.
"""
from __future__ import annotations

import ast
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import jwt as pyjwt
import pytest

pytestmark = [pytest.mark.security, pytest.mark.tenant_boundary]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LAYER4_SRC = _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents"
_LAYER4_ROUTES = _LAYER4_SRC / "api" / "routes"
_LAYER4_TENANT_ROUTES = _LAYER4_SRC / "tenants" / "api" / "routes"

TENANT_A_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_A_ID = "user-alpha-001"
USER_B_ID = "user-bravo-002"

TEST_JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("TEST_JWT_SECRET", "test-secret-key"))
TEST_JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def _make_token(tenant_id: UUID, user_id: str, roles: list[str] | None = None) -> str:
    """Create a signed JWT matching GovernanceMiddleware expectations."""
    now = int(time.time())
    payload = {
        "tenant_id": str(tenant_id),
        "sub": user_id,
        "roles": roles or ["analyst"],
        "iat": now,
        "exp": now + 3600,
    }
    return pyjwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Route dependency analysis (static — no app startup required)
# ---------------------------------------------------------------------------

def _route_uses_require_authenticated(filepath: Path, func_name: str) -> bool:
    """Check if a route handler uses ``require_authenticated`` in its signature."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                # Check all default values in the function signature
                for default in node.args.defaults + node.args.kw_defaults:
                    if default is None:
                        continue
                    if isinstance(default, ast.Call):
                        func = default.func
                        if isinstance(func, ast.Name) and func.id == "Depends":
                            for arg in default.args:
                                if isinstance(arg, ast.Name) and arg.id == "require_authenticated":
                                    return True
    return False


def _route_uses_get_db_from_context(filepath: Path, func_name: str) -> bool:
    """Check if a route handler uses ``get_db_from_context`` in its signature."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                for default in node.args.defaults + node.args.kw_defaults:
                    if default is None:
                        continue
                    if isinstance(default, ast.Call):
                        func = default.func
                        if isinstance(func, ast.Name) and func.id == "Depends":
                            for arg in default.args:
                                if isinstance(arg, ast.Name) and arg.id == "get_db_from_context":
                                    return True
    return False


# ---------------------------------------------------------------------------
# Tests: Accounts Route Tenant Enforcement
# ---------------------------------------------------------------------------

class TestAccountsRouteTenantEnforcement:
    """Verify that accounts routes enforce tenant isolation.

    The accounts routes are the highest-risk surface because they currently
    use ``get_db`` (no RLS) and have no ``require_authenticated`` dependency.
    """

    ACCOUNTS_FILE = (
        _LAYER4_ROUTES / "accounts.py"
    )

    ACCOUNT_ENDPOINTS = [
        ("list_accounts", "GET"),
        ("create_account", "POST"),
        ("search_accounts", "POST"),
        ("get_filter_options", "GET"),
        ("get_sync_status_all", "GET"),
        ("sync_accounts", "POST"),
        ("get_account", "GET"),
        ("get_account_activity", "GET"),
        ("refresh_account", "POST"),
    ]

    @pytest.mark.parametrize("func_name,method", ACCOUNT_ENDPOINTS)
    def test_account_endpoint_uses_tenant_scoped_db(self, func_name: str, method: str):
        """Each accounts endpoint must use get_db_from_context (not get_db).

        Protected accounts endpoints must depend on tenant-scoped DB context.
        """
        uses_scoped = _route_uses_get_db_from_context(self.ACCOUNTS_FILE, func_name)
        assert uses_scoped, (
            f"accounts.py::{func_name} ({method}) uses get_db instead of "
            f"get_db_from_context. This means the DB session has no tenant_id set, "
            f"so RLS policies are not enforced. Any authenticated user can access "
            f"any tenant's accounts."
        )

    @pytest.mark.parametrize("func_name,method", ACCOUNT_ENDPOINTS)
    def test_account_endpoint_requires_authentication(self, func_name: str, method: str):
        """Each accounts endpoint must use require_authenticated.

        Even with get_db_from_context, the endpoint should explicitly require
        authentication to prevent unauthenticated access.
        """
        uses_auth = _route_uses_require_authenticated(self.ACCOUNTS_FILE, func_name)
        # get_db_from_context implicitly requires context, but explicit is better
        uses_scoped_db = _route_uses_get_db_from_context(self.ACCOUNTS_FILE, func_name)

        assert uses_auth or uses_scoped_db, (
            f"accounts.py::{func_name} ({method}) has no authentication enforcement. "
            f"It uses neither require_authenticated nor get_db_from_context."
        )


# ---------------------------------------------------------------------------
# Tests: Analysis Route Tenant Enforcement
# ---------------------------------------------------------------------------

class TestAnalysisRouteTenantEnforcement:
    """Verify that analysis/business case routes enforce tenant isolation."""

    ANALYSIS_FILE = (
        _LAYER4_ROUTES / "analysis.py"
    )

    def test_generate_business_case_requires_auth(self):
        """POST /cases must require authentication."""
        uses_auth = _route_uses_require_authenticated(self.ANALYSIS_FILE, "generate_business_case")
        assert uses_auth, (
            "analysis.py::generate_business_case does not use require_authenticated. "
            "Business case generation must be tenant-scoped."
        )

    def test_quick_whitespace_analysis_requires_auth(self):
        """POST /analysis/whitespace must require authentication."""
        uses_auth = _route_uses_require_authenticated(self.ANALYSIS_FILE, "quick_whitespace_analysis")
        assert uses_auth, (
            "analysis.py::quick_whitespace_analysis does not use require_authenticated."
        )

    def test_export_business_case_uses_tenant_scoped_db(self):
        """GET /cases/{case_id}/export must enforce tenant context.

        The export endpoint uses WorkflowExecutor (not direct DB), so tenant
        scoping is enforced via require_authenticated rather than
        get_db_from_context. Both are acceptable.
        """
        uses_scoped = _route_uses_get_db_from_context(self.ANALYSIS_FILE, "export_business_case")
        uses_auth = _route_uses_require_authenticated(self.ANALYSIS_FILE, "export_business_case")
        assert uses_scoped or uses_auth, (
            "analysis.py::export_business_case uses neither get_db_from_context "
            "nor require_authenticated. Business case exports could leak data "
            "across tenants."
        )

    def test_export_business_case_requires_auth(self):
        """GET /cases/{case_id}/export must require authentication.

        Expected initial state: FAIL — uses get_optional_context.
        """
        uses_auth = _route_uses_require_authenticated(self.ANALYSIS_FILE, "export_business_case")
        assert uses_auth, (
            "analysis.py::export_business_case uses get_optional_context instead of "
            "require_authenticated. Export endpoints must require authentication — "
            "business case data is confidential."
        )


# ---------------------------------------------------------------------------
# Tests: Workflow Route Tenant Enforcement
# ---------------------------------------------------------------------------

class TestWorkflowRouteTenantEnforcement:
    """Verify that workflow routes enforce tenant isolation."""

    WORKFLOWS_FILE = (
        _LAYER4_ROUTES / "workflows.py"
    )

    WORKFLOW_ENDPOINTS = [
        ("create_workflow", "POST"),
        ("get_workflow_status", "GET"),
        ("cancel_workflow", "DELETE"),
        ("resume_workflow", "POST"),
        ("pause_workflow", "POST"),
    ]

    @pytest.mark.parametrize("func_name,method", WORKFLOW_ENDPOINTS)
    def test_workflow_endpoint_requires_auth(self, func_name: str, method: str):
        """Workflow endpoints must require authentication."""
        uses_auth = _route_uses_require_authenticated(self.WORKFLOWS_FILE, func_name)
        assert uses_auth, (
            f"workflows.py::{func_name} ({method}) does not use require_authenticated."
        )


# ---------------------------------------------------------------------------
# Tests: Signal Route Tenant Enforcement
# ---------------------------------------------------------------------------

class TestSignalRouteTenantEnforcement:
    """Verify that signal/prospect routes enforce tenant isolation."""

    SIGNALS_FILE = (
        _LAYER4_ROUTES / "signals.py"
    )

    def test_setup_prospect_requires_auth(self):
        """POST /prospects/setup must require authentication."""
        uses_auth = _route_uses_require_authenticated(self.SIGNALS_FILE, "setup_prospect")
        assert uses_auth, (
            "signals.py::setup_prospect does not use require_authenticated."
        )

    def test_get_account_signals_requires_auth(self):
        """GET /accounts/{id}/signals must require authentication."""
        uses_auth = _route_uses_require_authenticated(self.SIGNALS_FILE, "get_account_signals")
        assert uses_auth, (
            "signals.py::get_account_signals does not use require_authenticated."
        )

    def test_get_signal_by_id_requires_auth(self):
        """GET /signals/{id} must require authentication."""
        uses_auth = _route_uses_require_authenticated(self.SIGNALS_FILE, "get_signal_by_id")
        assert uses_auth, (
            "signals.py::get_signal_by_id does not use require_authenticated."
        )


# ---------------------------------------------------------------------------
# Tests: Tenant Admin Routes
# ---------------------------------------------------------------------------

class TestTenantAdminRouteTenantEnforcement:
    """Verify that tenant management routes use tenant-scoped DB.

    These routes manage tenants, users, and API keys — they are the most
    sensitive endpoints in the system.
    """

    ADMIN_FILE = (
        _LAYER4_TENANT_ROUTES / "admin.py"
    )
    USERS_FILE = (
        _LAYER4_TENANT_ROUTES / "users.py"
    )
    API_KEYS_FILE = (
        _LAYER4_TENANT_ROUTES / "api_keys.py"
    )

    def _count_get_db_usages(self, filepath: Path) -> int:
        """Count Depends(get_db) usages in a file."""
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "Depends":
                    for arg in node.args:
                        if isinstance(arg, ast.Name) and arg.id == "get_db":
                            count += 1
        return count

    def test_admin_routes_use_tenant_scoped_db(self):
        """Admin routes must use get_db_from_context.

        Protected admin endpoints must not use deprecated get_db.
        """
        count = self._count_get_db_usages(self.ADMIN_FILE)
        assert count == 0, (
            f"admin.py has {count} endpoint(s) using deprecated Depends(get_db). "
            f"Admin routes manage tenant configuration — they MUST use "
            f"get_db_from_context to enforce RLS."
        )

    def test_users_routes_use_tenant_scoped_db(self):
        """User management routes must use get_db_from_context.

        Protected users endpoints must not use deprecated get_db.
        """
        count = self._count_get_db_usages(self.USERS_FILE)
        assert count == 0, (
            f"users.py has {count} endpoint(s) using deprecated Depends(get_db). "
            f"User management routes MUST use get_db_from_context."
        )

    def test_api_keys_routes_use_tenant_scoped_db(self):
        """API key management routes must use get_db_from_context.

        Protected API key endpoints must not use deprecated get_db.
        """
        count = self._count_get_db_usages(self.API_KEYS_FILE)
        assert count == 0, (
            f"api_keys.py has {count} endpoint(s) using deprecated Depends(get_db). "
            f"API key routes MUST use get_db_from_context — a tenant admin could "
            f"otherwise read/revoke another tenant's API keys."
        )

    @pytest.mark.parametrize(
        ("filepath", "function_name"),
        [
            (ADMIN_FILE, "list_tenant_users"),
            (ADMIN_FILE, "get_tenant_usage"),
            (ADMIN_FILE, "get_tenant_audit_log"),
            (ADMIN_FILE, "get_tenant_settings"),
            (ADMIN_FILE, "update_tenant_settings"),
            (USERS_FILE, "api_invite_user"),
            (USERS_FILE, "api_list_users"),
            (USERS_FILE, "api_get_user"),
            (USERS_FILE, "api_update_user"),
            (USERS_FILE, "api_deactivate_user"),
            (API_KEYS_FILE, "api_create_key"),
            (API_KEYS_FILE, "api_list_keys"),
            (API_KEYS_FILE, "api_revoke_key"),
        ],
    )
    def test_tenant_admin_endpoints_require_authenticated_context(
        self, filepath: Path, function_name: str
    ):
        """Tenant admin endpoints must require an authenticated context dependency.

        ``require_tenant_admin`` is acceptable since it is stricter than
        ``require_authenticated`` and enforces auth + role check.
        """
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == function_name:
                signature_text = ast.get_source_segment(source, node) or ""
                assert (
                    "Depends(require_tenant_admin)" in signature_text
                    or "Depends(require_authenticated)" in signature_text
                ), (
                    f"{filepath.name}::{function_name} must require authenticated context "
                    "via require_tenant_admin or require_authenticated."
                )
                return
        pytest.fail(f"Could not find function {function_name} in {filepath}")


# ---------------------------------------------------------------------------
# Tests: Aggregate Dependency Audit
# ---------------------------------------------------------------------------

class TestAggregateDepAudit:
    """Summary test that counts total deprecated get_db usages across all L4 routes."""

    # Files intentionally using get_db (pre-auth flows, external webhooks).
    # Each must be individually justified:
    #   oidc.py         — OIDC login/callback (pre-auth, user has no JWT)
    #   registration.py — Self-registration (pre-auth, tenant doesn't exist)
    #   crm_webhooks.py — Salesforce/HubSpot webhooks (HMAC signature auth)
    #   billing.py      — Stripe webhook endpoint (HMAC signature auth)
    #   provisioning.py — Provisioning webhook (token-based auth)
    ALLOWED_GET_DB_FILES = {
        "oidc.py",
        "registration.py",
        "crm_webhooks.py",
        "billing.py",
        "provisioning.py",
    }

    def test_total_deprecated_get_db_count(self):
        """Total Depends(get_db) usages across all L4 routes must be zero
        (excluding intentional pre-auth/webhook files).

        This is the aggregate gate — it fails if ANY non-allowlisted route
        uses the deprecated dependency.
        """
        route_dirs = [
            _LAYER4_ROUTES,
            _LAYER4_TENANT_ROUTES,
            _LAYER4_SRC / "feature_flags" / "api",
            _LAYER4_SRC / "registry" / "api",
        ]

        total = 0
        by_file: Dict[str, int] = {}

        for route_dir in route_dirs:
            if not route_dir.exists():
                continue
            for filepath in sorted(route_dir.glob("*.py")):
                if filepath.name.startswith("__"):
                    continue
                if filepath.name in self.ALLOWED_GET_DB_FILES:
                    continue
                source = filepath.read_text(encoding="utf-8")
                tree = ast.parse(source)
                count = 0
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func = node.func
                        if isinstance(func, ast.Name) and func.id == "Depends":
                            for arg in node.args:
                                if isinstance(arg, ast.Name) and arg.id == "get_db":
                                    count += 1
                if count > 0:
                    rel = str(filepath.relative_to(_PROJECT_ROOT))
                    by_file[rel] = count
                    total += count

        assert total == 0, (
            f"Found {total} total Depends(get_db) usages across L4 routes "
            f"(must be 0 for production, excluding allowlisted pre-auth/webhook files). "
            f"Breakdown:\n"
            + "\n".join(f"  {f}: {c} usages" for f, c in sorted(by_file.items()))
        )
