from __future__ import annotations

from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
# value_fabric.layer3 is a path-redirect shim: its __init__.py appends
# services/layer3-knowledge/src/ to __path__, so the canonical source lives
# under services/layer3-knowledge/src/, not under value_fabric/layer3/.
_L3_SRC = ROOT / "services/layer3-knowledge/src"
ENTITY_COMPAT = _L3_SRC / "api/routes/entity_compat.py"
COMPAT_ALIASES = _L3_SRC / "api/routes/compat_aliases.py"
APP_MONOLITH = _L3_SRC / "api/app_monolith.py"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _import_from_modules(tree: ast.Module) -> list[str]:
    modules: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def test_compat_shims_import_canonical_route_modules_and_export_router() -> None:
    entity_tree = _parse(ENTITY_COMPAT)
    alias_tree = _parse(COMPAT_ALIASES)

    # entity_compat.py must re-export from the canonical entities module.
    assert "api.routes.entities" in _import_from_modules(entity_tree)

    # compat_aliases.py delegates to query_search (relative import within the
    # same routes package — absolute value_fabric.layer3.* import would be
    # circular given the path-redirect shim architecture).
    alias_source = COMPAT_ALIASES.read_text(encoding="utf-8")
    assert "query_search" in alias_source, (
        "compat_aliases.py must delegate to query_search for canonical query/search logic"
    )

    # entity_compat.py must export __all__ = ["router"]
    entity_assigns = [n for n in entity_tree.body if isinstance(n, ast.Assign)]
    assert any(
        isinstance(target, ast.Name)
        and target.id == "__all__"
        and isinstance(assign.value, ast.List)
        and [elt.value for elt in assign.value.elts if isinstance(elt, ast.Constant)] == ["router"]
        for assign in entity_assigns
        for target in assign.targets
    ), "entity_compat.py must declare __all__ = ['router']"


def test_compat_router_registration_does_not_shadow_canonical_mounts() -> None:
    source = APP_MONOLITH.read_text(encoding="utf-8")

    # Canonical entity router must remain mounted under /v1.
    assert 'RouterMount(entities.router, prefix="/v1")' in source, (
        "entities.router must be mounted with prefix='/v1' in app_monolith.py"
    )


def test_no_merge_conflict_markers_in_compat_aliases() -> None:
    source = COMPAT_ALIASES.read_text(encoding="utf-8")
    assert "<<<<<<<" not in source
    assert "=======" not in source
    assert ">>>>>>>" not in source
