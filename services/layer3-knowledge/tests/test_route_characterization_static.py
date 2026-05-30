from __future__ import annotations

import ast
from pathlib import Path

ROUTES_DIR = Path(__file__).resolve().parents[1] / "src" / "api" / "routes"


def _add_api_routes(path: Path) -> set[tuple[str, str, str]]:
    tree = ast.parse(path.read_text())
    routes: set[tuple[str, str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            not isinstance(node.func, ast.Attribute)
            or node.func.attr != "add_api_route"
        ):
            continue
        route_path = ast.literal_eval(node.args[0])
        endpoint = ast.unparse(node.args[1]).split(".")[-1]
        methods_kw = next(kw for kw in node.keywords if kw.arg == "methods")
        for method_node in methods_kw.value.elts:  # type: ignore[attr-defined]
            routes.add((ast.literal_eval(method_node), route_path, endpoint))
    return routes


def test_formula_split_route_groups_preserve_public_paths() -> None:
    routes = set()
    for filename in [
        "formulas_evaluation_routes.py",
        "formulas_registry_routes.py",
        "formulas_mutation_routes.py",
    ]:
        routes |= _add_api_routes(ROUTES_DIR / filename)

    assert routes == {
        ("POST", "/formulas/evaluate", "evaluate_formula"),
        ("POST", "/formulas/scenario", "calculate_scenario"),
        ("GET", "/formulas/variables", "get_variables_registry"),
        ("GET", "/formulas", "list_formulas"),
        ("GET", "/formulas/{formula_id}", "get_formula"),
        ("POST", "/formulas", "create_formula"),
        ("PATCH", "/formulas/{formula_id}", "update_formula"),
        ("DELETE", "/formulas/{formula_id}", "delete_formula"),
    }


def test_value_pack_split_route_groups_preserve_public_paths() -> None:
    routes = set()
    for filename in ["value_packs_pack_routes.py", "value_packs_framework_routes.py"]:
        routes |= _add_api_routes(ROUTES_DIR / filename)

    assert routes == {
        ("GET", "/packs", "list_packs"),
        ("GET", "/packs/{pack_id}", "get_pack"),
        ("POST", "/packs", "create_pack"),
        ("PUT", "/packs/{pack_id}", "update_pack"),
        ("POST", "/packs/{pack_id}/execute", "execute_pack"),
        ("POST", "/packs/{pack_id}/fork", "fork_pack"),
        ("POST", "/packs/{pack_id}/apply", "apply_pack"),
        ("GET", "/valuepacks", "list_valuepacks"),
        ("GET", "/valuepacks/{industry_id}", "get_valuepack"),
        ("POST", "/valuepacks", "create_valuepack"),
        ("PUT", "/valuepacks/{industry_id}", "update_valuepack"),
        ("DELETE", "/valuepacks/{industry_id}", "delete_valuepack"),
        ("GET", "/valuepacks/ontology-map", "get_ontology_map"),
        ("GET", "/valuepacks/composable-templates", "get_composable_templates"),
        ("POST", "/valuepacks/compare", "compare_valuepacks"),
        ("POST", "/valuepacks/{industry_id}/seed", "seed_valuepack_data"),
    }
