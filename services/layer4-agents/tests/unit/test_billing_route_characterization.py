from __future__ import annotations

import ast
from pathlib import Path

ROUTES_DIR = Path(__file__).resolve().parents[2] / "src" / "api" / "routes"
CANONICAL_ROUTES_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "layer4_agents" / "api" / "routes"
)


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


def test_split_billing_route_groups_preserve_public_usage_and_overage_paths() -> None:
    routes = set()
    for filename in ["billing_webhooks.py", "billing_usage.py", "billing_overages.py"]:
        routes |= _add_api_routes(ROUTES_DIR / filename)

    assert routes == {
        ("POST", "/webhook", "stripe_webhook"),
        ("POST", "/events", "ingest_usage_event"),
        ("POST", "/events/batch", "ingest_usage_batch"),
        ("GET", "/usage/{customer_id}/summary", "get_usage_summary"),
        ("GET", "/usage/{customer_id}/events", "list_usage_events"),
        ("POST", "/usage/{customer_id}/sync", "sync_usage_to_stripe"),
        ("GET", "/limits/{customer_id}", "get_usage_limits"),
        ("POST", "/limits/{customer_id}/check", "check_request_allowed"),
        ("GET", "/plans/{plan_id}/limits", "get_plan_limits"),
    }


def test_canonical_split_billing_route_groups_preserve_public_usage_and_overage_paths() -> None:
    routes = set()
    for filename in ["billing_webhooks.py", "billing_usage.py", "billing_overages.py"]:
        routes |= _add_api_routes(CANONICAL_ROUTES_DIR / filename)

    assert routes == {
        ("POST", "/webhook", "stripe_webhook"),
        ("POST", "/events", "ingest_usage_event"),
        ("POST", "/events/batch", "ingest_usage_batch"),
        ("GET", "/usage/{customer_id}/summary", "get_usage_summary"),
        ("GET", "/usage/{customer_id}/events", "list_usage_events"),
        ("POST", "/usage/{customer_id}/sync", "sync_usage_to_stripe"),
        ("GET", "/limits/{customer_id}", "get_usage_limits"),
        ("POST", "/limits/{customer_id}/check", "check_request_allowed"),
        ("GET", "/plans/{plan_id}/limits", "get_plan_limits"),
    }
