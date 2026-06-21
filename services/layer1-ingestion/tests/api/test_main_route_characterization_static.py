from __future__ import annotations

import ast
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[2] / "src" / "layer1_ingestion" / "api"


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


def _route_metadata(path: Path) -> dict[tuple[str, str], dict[str, str | list[str]]]:
    """Extract per-route OpenAPI metadata from add_api_route calls."""
    tree = ast.parse(path.read_text())
    metadata: dict[tuple[str, str], dict[str, str | list[str]]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_api_route":
            continue
        route_path = ast.literal_eval(node.args[0])
        endpoint = ast.unparse(node.args[1]).split(".")[-1]
        methods_kw = next(kw for kw in node.keywords if kw.arg == "methods")
        method = next(ast.literal_eval(n) for n in methods_kw.value.elts)
        route_key = (method, route_path)
        metadata[route_key] = {"endpoint": endpoint}
        for kw in node.keywords:
            if kw.arg in {"operation_id", "summary", "tags"}:
                metadata[route_key][kw.arg] = ast.literal_eval(kw.value)
    return metadata


@pytest.mark.contract_static
def test_layer1_split_route_groups_preserve_public_paths() -> None:
    routes = set()
    for filename in [
        "main_target_routes.py",
        "main_job_routes.py",
        "main_skill_routes.py",
        "main_content_routes.py",
        "main_compliance_routes.py",
        "main_admin_routes.py",
    ]:
        routes |= _add_api_routes(API_DIR / filename)

    assert routes == {
        ("GET", "/targets", "list_targets"),
        ("POST", "/targets", "create_target"),
        ("GET", "/targets/{target_id}", "get_target"),
        ("PUT", "/targets/{target_id}", "update_target"),
        ("DELETE", "/targets/{target_id}", "delete_target"),
        ("POST", "/targets/{target_id}/validate", "validate_target"),
        ("POST", "/targets/{target_id}/execute", "execute_target"),
        ("GET", "/targets/{target_id}/decisions", "get_target_decisions"),
        ("GET", "/jobs/{job_id}/router-report", "get_job_router_report"),
        ("GET", "/domains/{domain}/fallback-stats", "get_domain_fallback_stats"),
        ("GET", "/jobs", "list_jobs"),
        ("GET", "/jobs/{job_id}", "get_job"),
        ("DELETE", "/jobs/{job_id}", "cancel_job"),
        ("GET", "/jobs/{job_id}/progress", "get_job_progress"),
        ("GET", "/jobs/{job_id}/results", "get_job_results"),
        ("POST", "/jobs/{job_id}/retry", "retry_job"),
        (
            "POST",
            "/jobs/licensing-company-intake",
            "create_licensing_company_intake_job",
        ),
        ("POST", "/jobs/prospect-research", "create_prospect_research_job"),
        ("GET", "/corpuses/{corpus_id}", "get_source_corpus"),
        ("GET", "/intelligence-packets/{packet_id}", "get_account_intelligence_packet"),
        ("GET", "/jobs/{job_id}/skill-output", "get_job_skill_output"),
        ("GET", "/source-corpora", "list_source_corpora"),
        ("GET", "/source-corpora/{corpus_id}", "get_source_corpus_detail"),
        ("GET", "/account-intelligence-packets", "list_account_intelligence_packets"),
        (
            "GET",
            "/account-intelligence-packets/{packet_id}",
            "get_account_intelligence_packet_detail",
        ),
        ("GET", "/content/raw/{content_id}", "get_raw_content"),
        ("GET", "/content/extracted/{extracted_data_id}", "get_extracted_data"),
        ("GET", "/content", "list_content"),
        ("GET", "/compliance/logs", "list_compliance_logs"),
        ("GET", "/compliance/summary", "get_compliance_summary"),
        ("GET", "/health", "health_check"),
        ("GET", "/metrics", "metrics_endpoint"),
        ("POST", "/admin/cleanup", "trigger_cleanup"),
        ("POST", "/proxy-pools", "create_proxy_pool_endpoint"),
    }


@pytest.mark.contract_static
def test_content_routes_have_openapi_metadata() -> None:
    metadata = _route_metadata(API_DIR / "main_content_routes.py")
    assert metadata == {
        ("GET", "/content/raw/{content_id}"): {
            "endpoint": "get_raw_content",
            "operation_id": "get_raw_content",
            "summary": "Retrieve raw content by ID",
            "tags": ["Content"],
        },
        ("GET", "/content/extracted/{extracted_data_id}"): {
            "endpoint": "get_extracted_data",
            "operation_id": "get_extracted_data",
            "summary": "Retrieve extracted data by ID",
            "tags": ["Content"],
        },
        ("GET", "/content"): {
            "endpoint": "list_content",
            "operation_id": "list_content",
            "summary": "List raw content with filtering",
            "tags": ["Content"],
        },
    }
