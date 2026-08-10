"""Static security regression tests: query-param tenant auth is banned.

These tests analyze source code directly — no database, no runtime dependencies.
They fail if tenant_id is ever read from query parameters for authentication.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_CORE_PY = (
    REPO_ROOT / "packages" / "shared" / "src" / "value_fabric" / "shared" / "identity" / "governance_core.py"
)
MIDDLEWARE_PY = (
    REPO_ROOT / "packages" / "shared" / "src" / "value_fabric" / "shared" / "identity" / "middleware.py"
)


class TestQueryParamTenantAuthBanned:
    """P0: tenant_id must never be read from query parameters for authentication."""

    @pytest.mark.security
    def test_governance_core_never_reads_tenant_from_query_params(self):
        """governance_core.py must not use query_params for tenant auth resolution."""
        source = GOVERNANCE_CORE_PY.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Find the resolve_identity method and check AST for banned patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "resolve_identity":
                # Walk the AST of the method body to find any attribute access
                # on query_params that reads tenant_id
                for child in ast.walk(node):
                    # Look for: query_params.get("tenant_id") or similar
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Attribute) and func.attr == "get":
                            # Check if it's called on query_params
                            if (
                                isinstance(func.value, ast.Name)
                                and func.value.id == "query_params"
                            ):
                                # Check the argument - if it's "tenant_id", that's banned
                                if child.args:
                                    arg = child.args[0]
                                    if (
                                        isinstance(arg, ast.Constant)
                                        and arg.value == "tenant_id"
                                    ):
                                        pytest.fail(
                                            "resolve_identity reads tenant_id from query_params — "
                                            "this is banned for security"
                                        )
                break
        else:
            pytest.fail("resolve_identity method not found in governance_core.py")

        # Source-level assertion: no tenant_id extraction from query_params
        # for auth purposes (allowing x_service_auth for mutual auth is OK)
        lines = source.splitlines()
        in_docstring = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Track multi-line docstrings
            if '"""' in stripped:
                count = stripped.count('"""')
                if count % 2 == 1:
                    in_docstring = not in_docstring
                    continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            # Ban reading tenant_id from query_params dict for auth
            if "tenant_id" in stripped and "query_params" in stripped:
                # Allow x_service_auth (mutual auth secret), but not tenant_id
                if "x_service_auth" not in stripped:
                    pytest.fail(
                        f"Line {i + 1}: potential query-param tenant auth: {stripped}"
                    )

    @pytest.mark.security
    def test_governance_core_allow_query_param_is_false(self):
        """GovernanceCore._allow_query_param must be hardcoded to False."""
        source = GOVERNANCE_CORE_PY.read_text(encoding="utf-8")

        # Find the line that sets _allow_query_param
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if "_allow_query_param" in line and "=" in line:
                # Must be False, not a variable or parameter
                assert "False" in line, (
                    f"Line {i + 1}: _allow_query_param must be hardcoded False, got: {line.strip()}"
                )
                # Ensure it's not reading from a parameter
                assert (
                    "allow_query_param" not in line.split("=")[1] or "False" in line
                ), (
                    f"Line {i + 1}: _allow_query_param must not be assigned from parameter"
                )
                break
        else:
            pytest.fail("_allow_query_param assignment not found")

    @pytest.mark.security
    def test_middleware_allow_query_param_is_false(self):
        """GovernanceMiddleware._allow_query_param must be hardcoded to False."""
        source = MIDDLEWARE_PY.read_text(encoding="utf-8")

        lines = source.splitlines()
        for i, line in enumerate(lines):
            if "_allow_query_param" in line and "=" in line:
                assert "False" in line, (
                    f"Line {i + 1}: _allow_query_param must be hardcoded False, got: {line.strip()}"
                )
                break
        else:
            pytest.fail("_allow_query_param assignment not found in middleware.py")

    @pytest.mark.security
    def test_no_query_param_tenant_resolution_in_governance_core(self):
        """resolve_identity must not construct RequestContext from query param tenant_id."""
        source = GOVERNANCE_CORE_PY.read_text(encoding="utf-8")

        # After the P0 FIX comment, there should be no RequestContext construction
        # using query_params tenant_id
        fix_comment_seen = False
        lines = source.splitlines()

        for i, line in enumerate(lines):
            if "P0 FIX: Query param tenant authentication removed entirely" in line:
                fix_comment_seen = True
                continue

            if fix_comment_seen:
                # After the fix comment, should just be "return None" or empty
                # No RequestContext with tenant_id from query_params
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and stripped != "return None":
                    if "RequestContext" in stripped and "tenant_id" in stripped:
                        pytest.fail(
                            f"Line {i + 1}: RequestContext built from query params after fix: {stripped}"
                        )

        assert fix_comment_seen, "P0 FIX comment not found in governance_core.py"
