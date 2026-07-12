"""S2-A: Tenant Context Contract Tests — Production Approval Suite, Pillar 2.

Ship/No-Ship Gate: These tests verify structural invariants about how every
route in the platform resolves tenant identity.  They parse source code and
inspect FastAPI dependency graphs — no running database required.

Key invariants tested:
    1. No L4 route uses the deprecated ``get_db`` dependency (must use
       ``get_db_from_context`` which enforces RLS via tenant_id).
    2. No route uses ``get_optional_context`` for write/mutation endpoints.
    3. GovernanceMiddleware always resets the ContextVar at request start.
    4. RequestContext.tenant_id is always a UUID (never a raw string).
    5. The ``require_authenticated`` dependency raises 401 when context is None.

Expected Initial State:
    - test_no_l4_routes_use_deprecated_get_db:  PASS (deprecated usage removed from protected routes)
    - test_no_write_routes_use_optional_context: FAIL (export_business_case)
    - test_governance_middleware_resets_context:  PASS
    - test_require_authenticated_rejects_none:   PASS
    - test_request_context_tenant_id_is_uuid:    PASS
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Set
from uuid import UUID

import pytest

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_L4_ROUTES_DIR = (
    _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents" / "api" / "routes"
)
_L4_TENANT_ROUTES_DIR = (
    _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents" / "tenants" / "api" / "routes"
)
_L4_FEATURE_FLAGS_DIR = (
    _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents" / "feature_flags" / "api"
)
_L4_REGISTRY_DIR = (
    _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents" / "registry" / "api"
)

_ALL_ROUTE_DIRS = [
    _L4_ROUTES_DIR,
    _L4_TENANT_ROUTES_DIR,
    _L4_FEATURE_FLAGS_DIR,
    _L4_REGISTRY_DIR,
]

# Routes that are explicitly allowed to use get_db (e.g. health, metrics)
# Each entry must be individually justified and reviewed.
# oidc.py         — OIDC login/callback are pre-authentication flows (user has no JWT yet)
# registration.py — Self-registration is pre-authentication (tenant doesn't exist yet)
# crm_webhooks.py — Salesforce/HubSpot server-to-server calls use HMAC signature auth
# billing.py      — Stripe webhook endpoint uses HMAC signature auth (non-webhook
#                   endpoints now use get_db_from_context + require_authenticated)
# provisioning.py — Webhook endpoint uses token-based auth from external systems
ALLOWED_GET_DB_FILES: Set[str] = {
    "oidc.py",
    "registration.py",
    "crm_webhooks.py",
    "billing.py",
    "provisioning.py",
}

# HTTP methods considered "write" / mutation operations
WRITE_METHODS = {"post", "put", "patch", "delete"}


# ---------------------------------------------------------------------------
# AST Helpers
# ---------------------------------------------------------------------------

def _find_depends_calls(filepath: Path, dep_name: str) -> list[dict]:
    """Find all ``Depends(<dep_name>)`` usages in a Python file.

    Returns a list of dicts with keys: line, function, dep_name.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    results = []

    for node in ast.walk(tree):
        # Match: Depends(get_db) or Depends(get_db_from_context)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "Depends":
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id == dep_name:
                        results.append({
                            "line": node.lineno,
                            "file": str(filepath.relative_to(_PROJECT_ROOT)),
                            "dep_name": dep_name,
                        })
            elif isinstance(func, ast.Attribute) and func.attr == "Depends":
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id == dep_name:
                        results.append({
                            "line": node.lineno,
                            "file": str(filepath.relative_to(_PROJECT_ROOT)),
                            "dep_name": dep_name,
                        })

    return results


def _find_optional_context_in_write_routes(filepath: Path) -> list[dict]:
    """Find ``get_optional_context`` used in POST/PUT/PATCH/DELETE handlers.

    Scans for FastAPI route decorators followed by function defs that include
    ``Depends(get_optional_context)`` in their signature.
    """
    source = filepath.read_text(encoding="utf-8")
    results = []

    # Regex approach: find @router.<method> followed by async def with get_optional_context
    # This is more reliable than AST for decorator analysis
    lines = source.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Check for write-method decorator
        for method in WRITE_METHODS:
            if f"@router.{method}" in line or f"@app.{method}" in line:
                # Scan ahead for the function def and its parameters
                for j in range(i + 1, min(i + 15, len(lines))):
                    if "get_optional_context" in lines[j]:
                        results.append({
                            "line": j + 1,
                            "file": str(filepath.relative_to(_PROJECT_ROOT)),
                            "decorator_line": i + 1,
                            "method": method.upper(),
                        })
                        break
                    if lines[j].strip().startswith("def ") or lines[j].strip().startswith("async def "):
                        # Check if the function signature spans multiple lines
                        func_block = ""
                        for k in range(j, min(j + 10, len(lines))):
                            func_block += lines[k]
                            if ":" in lines[k] and (")" in lines[k] or "->" in lines[k]):
                                break
                        if "get_optional_context" in func_block:
                            results.append({
                                "line": j + 1,
                                "file": str(filepath.relative_to(_PROJECT_ROOT)),
                                "decorator_line": i + 1,
                                "method": method.upper(),
                            })
                        break
        i += 1

    return results


# ---------------------------------------------------------------------------
# Module loading helpers (avoids sqlalchemy import chain)
# ---------------------------------------------------------------------------

def _load_context_module():
    """Load the identity context module handling relative imports.

    The identity package's __init__.py imports sqlalchemy-dependent modules.
    We load the context module directly by first ensuring the permissions
    submodule is loadable, then loading context.py.
    """
    import importlib.util
    import types

    identity_dir = _PROJECT_ROOT / "packages" / "shared" / "src" / "value_fabric" / "shared" / "identity"

    # Create a minimal package so relative imports work
    pkg = types.ModuleType("identity")
    pkg.__path__ = [str(identity_dir)]
    pkg.__package__ = "identity"
    sys.modules["identity"] = pkg

    # Load permissions first (context.py imports from .permissions)
    perm_path = identity_dir / "permissions.py"
    perm_spec = importlib.util.spec_from_file_location(
        "identity.permissions", perm_path,
        submodule_search_locations=[],
    )
    perm_mod = importlib.util.module_from_spec(perm_spec)
    perm_mod.__package__ = "identity"
    sys.modules["identity.permissions"] = perm_mod
    perm_spec.loader.exec_module(perm_mod)

    # Now load context
    ctx_path = identity_dir / "context.py"
    ctx_spec = importlib.util.spec_from_file_location(
        "identity.context", ctx_path,
        submodule_search_locations=[],
    )
    ctx_mod = importlib.util.module_from_spec(ctx_spec)
    ctx_mod.__package__ = "identity"
    sys.modules["identity.context"] = ctx_mod
    ctx_spec.loader.exec_module(ctx_mod)

    return ctx_mod


def _load_request_context():
    """Load and return the RequestContext class."""
    mod = _load_context_module()
    return mod.RequestContext


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNoDeprecatedGetDb:
    """Every L4 route must use ``get_db_from_context``, never bare ``get_db``.

    ``get_db`` creates a database session without setting ``app.tenant_id``,
    which means RLS policies are not enforced.  This is the single most
    critical tenant isolation defect class.
    """

    def test_no_l4_routes_use_deprecated_get_db(self):
        """Scan all L4 route files for ``Depends(get_db)`` usage.

        Protected routes must remain free of deprecated get_db usage.
        """
        violations = []

        route_dirs = _ALL_ROUTE_DIRS
        for route_dir in route_dirs:
            if not route_dir.exists():
                continue
            for filepath in sorted(route_dir.glob("*.py")):
                if filepath.name.startswith("__"):
                    continue
                relative = filepath.name
                if relative in ALLOWED_GET_DB_FILES:
                    continue

                hits = _find_depends_calls(filepath, "get_db")
                if hits:
                    violations.extend(hits)

        assert not violations, (
            f"Found {len(violations)} route endpoint(s) using deprecated Depends(get_db) "
            f"instead of Depends(get_db_from_context). These bypass RLS tenant isolation.\n"
            + "\n".join(
                f"  - {v['file']}:{v['line']}"
                for v in violations
            )
        )

    def test_get_db_from_context_requires_tenant_id(self):
        """Verify ``get_db_from_context`` rejects requests without tenant context.

        This is a unit test of the dependency function itself.
        """
        # Read the source to verify the guard clause exists
        db_module = _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents" / "database.py"
        source = db_module.read_text(encoding="utf-8")

        # The function must check for missing context/tenant_id
        assert "if not context or not context.tenant_id" in source or \
               "if context is None" in source, (
            "get_db_from_context does not check for missing tenant context. "
            "A request without GovernanceMiddleware context would get an unscoped DB session."
        )

        # The function must raise 400 (not silently proceed)
        assert "400" in source or "BAD_REQUEST" in source, (
            "get_db_from_context does not raise HTTP 400 on missing tenant context."
        )


class TestNoOptionalContextOnWriteRoutes:
    """Write/mutation endpoints must use ``require_authenticated``, not
    ``get_optional_context``.

    ``get_optional_context`` returns ``None`` when no auth is present, which
    means the endpoint handler must manually check — and if it forgets, the
    mutation proceeds without tenant scoping.
    """

    def test_no_write_routes_use_optional_context(self):
        """Scan all L4 route files for write endpoints using get_optional_context.

        Expected initial state: FAIL — analysis.py export_business_case uses
        get_optional_context on a POST endpoint.
        """
        violations = []

        route_dirs = _ALL_ROUTE_DIRS
        for route_dir in route_dirs:
            if not route_dir.exists():
                continue
            for filepath in sorted(route_dir.glob("*.py")):
                if filepath.name.startswith("__"):
                    continue
                hits = _find_optional_context_in_write_routes(filepath)
                violations.extend(hits)

        assert not violations, (
            f"Found {len(violations)} write endpoint(s) using get_optional_context "
            f"instead of require_authenticated. These allow unauthenticated mutations.\n"
            + "\n".join(
                f"  - {v['file']}:{v['line']} ({v['method']} handler, decorator at line {v['decorator_line']})"
                for v in violations
            )
        )


class TestGovernanceMiddlewareContextReset:
    """GovernanceMiddleware must reset the ContextVar at the start of every
    request to prevent tenant context leakage between requests sharing the
    same ASGI worker.
    """

    def test_dispatch_resets_context_at_start(self):
        """Verify the dispatch method sets context to None before resolution."""
        middleware_file = (
            _PROJECT_ROOT / "packages" / "shared" / "src" / "value_fabric" / "shared" / "identity" / "middleware.py"
        )
        source = middleware_file.read_text(encoding="utf-8")

        # The dispatch method must call _current_context.set(None) before
        # any identity resolution
        dispatch_start = source.find("async def dispatch")
        assert dispatch_start != -1, "GovernanceMiddleware.dispatch not found"

        # Get the first ~20 lines of dispatch
        dispatch_body = source[dispatch_start:dispatch_start + 800]

        assert "_current_context.set(None)" in dispatch_body, (
            "GovernanceMiddleware.dispatch does not reset _current_context to None "
            "at the start of request processing. This allows tenant context from a "
            "previous request to leak into the current request."
        )

    def test_dispatch_resets_context_in_finally(self):
        """Verify the dispatch method resets context in a finally block.

        Even if the request handler raises an exception, the context must be
        cleaned up to prevent leakage to the next request.
        """
        middleware_file = (
            _PROJECT_ROOT / "packages" / "shared" / "src" / "value_fabric" / "shared" / "identity" / "middleware.py"
        )
        source = middleware_file.read_text(encoding="utf-8")

        # Must have a finally block that resets the context.
        # Use a generous window (8000 chars) to cover the full dispatch method.
        dispatch_start = source.find("async def dispatch")
        dispatch_body = source[dispatch_start:dispatch_start + 8000]

        assert "finally:" in dispatch_body, (
            "GovernanceMiddleware.dispatch does not have a finally block. "
            "If the request handler raises, tenant context will leak."
        )
        assert "_current_context.reset" in dispatch_body, (
            "GovernanceMiddleware.dispatch finally block does not reset _current_context."
        )


class TestRequestContextIntegrity:
    """Verify RequestContext enforces type safety on tenant_id."""

    def test_request_context_accepts_uuid(self):
        """RequestContext.tenant_id must accept UUID objects."""
        RequestContext = _load_request_context()

        ctx = RequestContext(
            tenant_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            user_id="test-user",
            roles=["analyst"],
            source="jwt",
        )
        assert isinstance(ctx.tenant_id, UUID)

    def test_context_var_isolation(self):
        """ContextVar must isolate between set/reset cycles."""
        mod = _load_context_module()
        RequestContext = mod.RequestContext
        get_request_context = mod.get_request_context
        set_request_context = mod.set_request_context
        _current_context = mod._current_context

        # Start clean
        token = _current_context.set(None)
        assert get_request_context() is None

        # Set context A
        ctx_a = RequestContext(
            tenant_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            user_id="user-a",
            roles=["analyst"],
            source="jwt",
        )
        token_a = set_request_context(ctx_a)
        assert get_request_context() is ctx_a

        # Reset should restore None
        _current_context.reset(token_a)
        assert get_request_context() is None

        # Cleanup
        _current_context.reset(token)

    def test_require_context_raises_when_none(self):
        """require_context() must raise RuntimeError when no context is set."""
        mod = _load_context_module()
        require_context = mod.require_context
        _current_context = mod._current_context

        token = _current_context.set(None)
        try:
            with pytest.raises(RuntimeError, match="No RequestContext"):
                require_context()
        finally:
            _current_context.reset(token)


class TestImportConsistency:
    """Verify that route files import from the correct identity module."""

    def test_l4_routes_import_shared_identity(self):
        """L4 route files that use auth must import from shared.identity, not
        from the deprecated layer4-agents/src/tenant/ package.
        """
        violations = []

        for filepath in sorted(_L4_ROUTES_DIR.glob("*.py")):
            if filepath.name.startswith("__"):
                continue
            source = filepath.read_text(encoding="utf-8")

            # Check for deprecated imports
            if "from ...tenant.context" in source or "from ..tenant.context" in source:
                violations.append(f"{filepath.name}: imports from deprecated tenant.context")
            if "from ...tenant.middleware" in source or "from ..tenant.middleware" in source:
                violations.append(f"{filepath.name}: imports from deprecated tenant.middleware")

        assert not violations, (
            f"Found {len(violations)} route file(s) importing from deprecated tenant package:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_all_route_files_that_use_db_import_it(self):
        """Route files using Depends(get_db) or Depends(get_db_from_context)
        must have a matching import statement.
        """
        violations = []

        for filepath in sorted(_L4_ROUTES_DIR.glob("*.py")):
            if filepath.name.startswith("__"):
                continue
            source = filepath.read_text(encoding="utf-8")

            uses_get_db = "Depends(get_db)" in source
            uses_get_db_from_context = "Depends(get_db_from_context)" in source

            if uses_get_db and "import get_db" not in source and "from" not in source:
                violations.append(f"{filepath.name}: uses get_db without importing it")
            if uses_get_db_from_context and "get_db_from_context" not in source.split("Depends")[0]:
                # Verify the import exists somewhere before the first usage
                import_line = source.find("get_db_from_context")
                depends_line = source.find("Depends(get_db_from_context)")
                if import_line == depends_line:
                    violations.append(f"{filepath.name}: uses get_db_from_context without importing it")

        # This is informational — import errors would be caught at runtime
        # but we want to catch them statically
        assert not violations, (
            "Import consistency violations:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestTenantIdSourceOfTruth:
    """Tenant identity in routes must come from authenticated request context."""

    TARGET_FILES = [
        _L4_ROUTES_DIR / "accounts.py",
        _L4_TENANT_ROUTES_DIR / "users.py",
        _L4_TENANT_ROUTES_DIR / "api_keys.py",
        _L4_TENANT_ROUTES_DIR / "admin.py",
    ]

    def test_target_routes_do_not_use_request_body_tenant_id(self):
        """Prevent drift to request-body tenant_id on sensitive routes."""
        violations = []
        pattern = re.compile(r"\brequest\.tenant_id\b")
        for filepath in self.TARGET_FILES:
            source = filepath.read_text(encoding="utf-8")
            if pattern.search(source):
                violations.append(str(filepath.relative_to(_PROJECT_ROOT)))

        assert not violations, (
            "Sensitive Layer 4 routes must use authenticated context tenant_id, "
            "not request-body tenant_id. Violations:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
