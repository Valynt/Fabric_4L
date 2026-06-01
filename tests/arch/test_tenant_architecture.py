"""Architecture tests for tenant isolation invariants.

These tests are static and do not require live infrastructure.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Models that are expected to remain tenant-scoped.
TENANT_SCOPED_MODELS: dict[str, tuple[str, ...]] = {
    "services/layer4-agents/src/layer4_agents/tenants/models/api_key.py": ("APIKey",),
    "services/layer4-agents/src/layer4_agents/tenants/models/user.py": ("User",),
    "services/layer4-agents/src/layer4_agents/registry/models.py": ("ModelVersion",),
    "services/layer4-agents/src/layer4_agents/feature_flags/models.py": ("FeatureFlag",),
}

# Service files where selects on tenant-scoped models must include tenant predicates.
TENANT_QUERY_GUARD_FILES: dict[str, tuple[str, ...]] = {
    "services/layer4-agents/src/layer4_agents/tenants/service.py": ("User", "APIKey"),
    "services/layer4-agents/src/layer4_agents/registry/service.py": ("ModelVersion",),
    "services/layer4-agents/src/layer4_agents/feature_flags/service.py": ("FeatureFlag",),
}


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_has_tenant_id_field(class_node: ast.ClassDef) -> bool:
    return any(
        isinstance(stmt, ast.AnnAssign)
        and isinstance(stmt.target, ast.Name)
        and stmt.target.id == "tenant_id"
        for stmt in class_node.body
    )


def _call_chain_nodes(call: ast.Call) -> list[ast.Call]:
    """Return a call chain like select(...).where(...).limit(...)."""
    chain: list[ast.Call] = [call]
    current = call
    while isinstance(current.func, ast.Attribute) and isinstance(current.func.value, ast.Call):
        current = current.func.value
        chain.append(current)
    return chain


def _is_select_for_model(call: ast.Call, model_name: str) -> bool:
    if not isinstance(call.func, ast.Name) or call.func.id != "select" or not call.args:
        return False
    arg0 = call.args[0]
    return isinstance(arg0, ast.Name) and arg0.id == model_name


def _expr_has_tenant_predicate(node: ast.AST, model_name: str) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Attribute):
            continue
        if child.attr != "tenant_id":
            continue
        if isinstance(child.value, ast.Name) and child.value.id == model_name:
            return True
    return False


def _has_guarded_where_for_model(tree: ast.AST, model_name: str) -> bool:
    """Whether at least one select(model).where(...tenant_id...) exists."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        chain = _call_chain_nodes(node)
        if not any(_is_select_for_model(c, model_name) for c in chain):
            continue

        has_guarded_where = any(
            isinstance(c.func, ast.Attribute)
            and c.func.attr == "where"
            and any(_expr_has_tenant_predicate(arg, model_name) for arg in c.args)
            for c in chain
        )
        if has_guarded_where:
            return True
    return False


def _get_function(tree: ast.AST, fn_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            return node
    return None


def _function_mentions_names(node: ast.FunctionDef | ast.AsyncFunctionDef, names: set[str]) -> bool:
    present = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    return names.issubset(present)


def _function_calls_uuid(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "UUID"
        for n in ast.walk(node)
    )


def test_tenant_scoped_models_define_tenant_identifier() -> None:
    """Tenant-scoped models must define tenant_id columns."""
    for rel_path, class_names in TENANT_SCOPED_MODELS.items():
        path = REPO_ROOT / rel_path
        tree = _parse(path)
        classes = {
            n.name: n
            for n in tree.body  # type: ignore[attr-defined]
            if isinstance(n, ast.ClassDef) and n.name in set(class_names)
        }
        missing = [name for name in class_names if name not in classes]
        assert not missing, f"{rel_path}: expected classes missing: {missing}"

        for class_name in class_names:
            assert _class_has_tenant_id_field(classes[class_name]), (
                f"{rel_path}:{class_name} must declare tenant_id for tenant scoping"
            )


def test_tenant_scoped_sql_queries_are_guarded() -> None:
    """Critical service query paths should include tenant_id predicates."""
    for rel_path, model_names in TENANT_QUERY_GUARD_FILES.items():
        path = REPO_ROOT / rel_path
        tree = _parse(path)
        for model_name in model_names:
            assert _has_guarded_where_for_model(tree, model_name), (
                f"{rel_path}: expected at least one tenant-guarded select({model_name}) query"
            )


def test_tenant_required_api_dependencies_reject_missing_and_invalid_tenant() -> None:
    """Auth helpers must enforce auth and treat invalid tenant IDs as unresolved."""
    deps_tree = _parse(REPO_ROOT / "packages/shared/src/value_fabric/shared/identity/dependencies.py")
    middleware_tree = _parse(REPO_ROOT / "packages/shared/src/value_fabric/shared/identity/middleware.py")

    require_authenticated = _get_function(deps_tree, "require_authenticated")
    assert require_authenticated is not None, "dependencies.py must define require_authenticated"
    # The function may delegate to a private helper (e.g. _unauthorized) that raises
    # HTTPException, rather than referencing HTTPException/status directly.  Accept
    # either pattern: direct reference OR a call to a helper whose name contains
    # "unauthorized" or "forbidden" (which by convention wraps HTTPException).
    direct_mention = _function_mentions_names(require_authenticated, {"HTTPException", "status"})
    helper_call = any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and any(kw in n.func.id.lower() for kw in ("unauthorized", "forbidden", "http_exc"))
        for n in ast.walk(require_authenticated)
    )
    assert direct_mention or helper_call, (
        "require_authenticated must raise HTTPException (directly or via a helper such as "
        "_unauthorized/_forbidden) to reject unauthenticated requests"
    )

    require_tenant = _get_function(deps_tree, "require_tenant")
    assert require_tenant is not None, "dependencies.py must define require_tenant"
    assert _function_mentions_names(require_tenant, {"require_authenticated"}), (
        "require_tenant must depend on require_authenticated to reject missing tenant context"
    )

    resolve_identity = _get_function(middleware_tree, "_resolve_identity")
    assert resolve_identity is not None, "middleware.py must define _resolve_identity"
    assert _function_calls_uuid(resolve_identity), (
        "_resolve_identity must parse tenant identifiers with UUID(...) validation"
    )


# ---------------------------------------------------------------------------
# Cross-Layer Tenant ID Consistency
# ---------------------------------------------------------------------------


def test_layer5_truth_object_uses_tenant_id() -> None:
    """Layer 5 TruthObject model must declare tenant_id for tenant scoping."""
    path = REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/models/truth_object.py"
    if not path.exists():
        pytest.skip("Layer 5 truth_object model not found")

    tree = _parse(path)
    classes = {
        n.name: n
        for n in tree.body  # type: ignore[attr-defined]
        if isinstance(n, ast.ClassDef)
        and n.name in {"TruthObject", "TruthSource", "ValidationEvent", "MaturityHistory"}
    }

    for class_name in ("TruthObject", "TruthSource", "ValidationEvent", "MaturityHistory"):
        assert class_name in classes, f"{path}: expected class {class_name} missing"
        assert _class_has_tenant_id_field(classes[class_name]), (
            f"{path}:{class_name} must declare tenant_id for tenant scoping"
        )
