"""Architecture tests for tenant isolation invariants.

These tests are static and do not require live infrastructure.
"""

from __future__ import annotations

import ast
import os
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

CONTEXTVAR_SCAN_ROOTS = (
    "packages",
    "services",
    "value_fabric",
)

TENANT_CONTEXTVAR_ALLOWLIST: dict[str, str] = {
    "packages/shared/src/value_fabric/shared/identity/context.py": "canonical runtime RequestContext store",
    "packages/platform-contract/src/python/canonical/context.py": "canonical contract mirror, not service runtime",
    "services/layer3-knowledge/src/utils/logging_context.py": "structured logging enrichment only",
    "services/layer5-ground-truth/src/layer5_ground_truth/observability/structured_logging.py": (
        "structured logging enrichment only"
    ),
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


def _contextvar_call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name) and call.func.id == "ContextVar":
        return "ContextVar"
    if isinstance(call.func, ast.Attribute) and call.func.attr == "ContextVar":
        return "ContextVar"
    return None


def _assigned_name(node: ast.Assign | ast.AnnAssign) -> str:
    target: ast.expr | None = None
    if isinstance(node, ast.Assign) and node.targets:
        target = node.targets[0]
    elif isinstance(node, ast.AnnAssign):
        target = node.target
    return target.id if isinstance(target, ast.Name) else ""


def _string_literal_arg(call: ast.Call) -> str:
    if not call.args:
        return ""
    arg = call.args[0]
    return arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else ""


def _annotation_text(node: ast.AST, source: str) -> str:
    if isinstance(node, ast.AnnAssign) and node.annotation is not None:
        return ast.get_source_segment(source, node.annotation) or ""
    return ""


def _contextvar_is_tenant_relevant(node: ast.Assign | ast.AnnAssign, source: str) -> bool:
    value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
    if not isinstance(value, ast.Call) or _contextvar_call_name(value) is None:
        return False

    haystack = " ".join(
        [
            _assigned_name(node),
            _string_literal_arg(value),
            _annotation_text(node, source),
        ]
    ).lower()
    return any(
        token in haystack
        for token in (
            "tenant",
            "requestcontext",
            "request_context",
            "vf_request_context",
        )
    )


def _python_files_under(*roots: str) -> list[Path]:
    files: list[Path] = []
    skip_dirs = {".venv", "venv", "__pycache__", ".pytest_cache", ".git", "node_modules"}
    for root in roots:
        root_path = REPO_ROOT / root
        if root_path.exists():
            for current_root, dir_names, file_names in os.walk(root_path, topdown=True):
                dir_names[:] = [name for name in dir_names if name not in skip_dirs]
                files.extend(Path(current_root) / name for name in file_names if name.endswith(".py"))
    return files


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


def test_api_gateway_uses_shared_tenant_context_store() -> None:
    """The API gateway must not create a second tenant ContextVar memory store."""
    path = REPO_ROOT / "services/api/app/core/tenant_context.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "from contextvars import ContextVar" not in source
    assert "ContextVar(" not in source
    assert "set_request_context" in source
    assert "RequestContext" in source

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "__call__":
            func_src = ast.get_source_segment(source, node) or ""
            assert "auth.tenant_id" in func_src
            assert "tenant_id=jwt_tenant" in func_src
            assert "set_request_context" in func_src
            return

    pytest.fail("TenantRequired.__call__ not found in services/api tenant_context.py")


def test_layer4_legacy_tenant_context_uses_shared_context_store() -> None:
    """Layer 4 legacy tenant context API must not own another tenant ContextVar."""
    path = REPO_ROOT / "services/layer4-agents/src/layer4_agents/tenant/context.py"
    source = path.read_text(encoding="utf-8")

    assert "from contextvars import ContextVar" not in source
    assert "ContextVar(" not in source
    assert "get_request_context" in source
    assert "set_request_context" in source
    assert "RequestContext(" in source


def test_layer4_domain_tenant_context_does_not_mutate_import_paths() -> None:
    """Layer 4 domain tenant context must not repair imports with sys.path mutation."""
    path = REPO_ROOT / "services/layer4-agents/src/layer4_agents/shared/domain/context.py"
    source = path.read_text(encoding="utf-8")

    assert "import sys" not in source
    assert "import os" not in source
    assert "sys.path" not in source
    assert "insert(0" not in source
    assert "from value_fabric.shared.identity.context import get_request_context" in source


def test_tenant_contextvar_ownership_is_canonical_or_observability_only() -> None:
    """Tenant/request ContextVar storage must not reappear outside approved owners."""
    violations: list[str] = []
    for path in _python_files_under(*CONTEXTVAR_SCAN_ROOTS):
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        if "ContextVar" not in source:
            continue

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:  # pragma: no cover - syntax failures should be explicit.
            pytest.fail(f"{rel_path}: cannot parse Python source: {exc}")

        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            if not _contextvar_is_tenant_relevant(node, source):
                continue
            if rel_path not in TENANT_CONTEXTVAR_ALLOWLIST:
                violations.append(f"{rel_path}: {ast.get_source_segment(source, node) or _assigned_name(node)}")

    assert not violations, (
        "Tenant/request ContextVar stores must use the canonical shared identity context, "
        "or be explicitly documented as observability-only:\n" + "\n".join(violations)
    )


def test_fabric_auth_middleware_populates_shared_request_context() -> None:
    """Verified internal auth envelopes must populate the canonical shared context."""
    path = REPO_ROOT / "packages/shared/src/value_fabric/shared/identity/fabric_auth/middleware.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "request_context_from_auth(auth)" in source
    assert "set_request_context(governance_context)" in source
    assert "previous_request_context = get_request_context()" in source
    assert "set_request_context(previous_request_context)" in source

    dispatch = _get_function(tree, "dispatch")
    assert dispatch is not None, "FabricAuthMiddleware must define dispatch"
    dispatch_source = ast.get_source_segment(source, dispatch) or ""
    assert "request.state.governance_context" in dispatch_source
    assert "set_request_context(governance_context)" in dispatch_source


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
