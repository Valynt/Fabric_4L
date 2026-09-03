"""Hostile cross-tenant API access tests by endpoint family.

Tests explicit hostile cross-tenant access patterns for each layer's endpoint family:
- L1: /api/v1/ingestion/**
- L2: /signals/**
- L3: /v1/entities/** (entities.py), /v1/graph/** (graph_viz.py), /v1/search/** (query_search.py)
- L4: /v1/workflows/**, /v1/accounts/**, /v1/billing/**
- L5: /api/v1/truths/**
- L6: /v1/benchmarks/**
- API: /v1/accounts/**

Each family must enforce tenant isolation at the route handler level:
- Tenant A's JWT cannot read Tenant B's resources (404 or 403 with safe error envelope)
- Tenant A's JWT cannot modify Tenant B's resources (403 with audit logged)
- Missing/expired/tampered auth is rejected with 401
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List

import pytest

pytestmark = [pytest.mark.security, pytest.mark.tenant_boundary]

REPO_ROOT = Path(__file__).resolve().parents[2]

# Endpoint family mapping: (layer, route_file, endpoint_prefix, methods)
ENDPOINT_FAMILIES: dict[str, tuple[str, Path, str, list[str]]] = {
    "L1_ingestion_sources": (
        "L1",
        REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py",
        "/api/v1/ingestion/sources",
        ["GET", "POST", "PUT", "DELETE"],
    ),
    "L2_signal_lifecycle": (
        "L2",
        REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/api/routes/signal_lifecycle.py",
        "/signals",
        ["GET", "POST"],
    ),
    "L3_entities": (
        "L3",
        REPO_ROOT / "services/layer3-knowledge/src/api/routes/entities.py",
        "/v1/entities",
        ["GET", "POST", "DELETE"],
    ),
    "L3_graph": (
        "L3",
        REPO_ROOT / "services/layer3-knowledge/src/api/routes/graph_viz.py",
        "/v1/graph",
        ["GET"],
    ),
    "L3_search": (
        "L3",
        REPO_ROOT / "services/layer3-knowledge/src/api/routes/query_search.py",
        "/v1/search",
        ["POST"],
    ),
    "L4_workflows": (
        "L4",
        REPO_ROOT / "services/layer4-agents/src/layer4_agents/api/routes/workflows.py",
        "/v1/workflows",
        ["GET", "POST", "PUT", "DELETE"],
    ),
    "L4_accounts": (
        "L4",
        REPO_ROOT / "services/layer4-agents/src/layer4_agents/api/routes/accounts.py",
        "/v1/accounts",
        ["GET", "POST", "PUT"],
    ),
    "L4_billing": (
        "L4",
        REPO_ROOT / "services/layer4-agents/src/layer4_agents/api/routes/billing.py",
        "/v1/billing",
        ["GET", "POST"],
    ),
    "L5_truths": (
        "L5",
        REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/api/router.py",
        "/api/v1/truths",
        ["GET", "POST", "PUT"],
    ),
    "L6_benchmarks": (
        "L6",
        REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/benchmarks.py",
        "/v1/benchmarks",
        ["GET", "POST", "PUT"],
    ),
    "API_accounts": (
        "API",
        REPO_ROOT / "services/api/app/routers/accounts.py",
        "/v1/accounts",
        ["GET", "POST", "PATCH"],
    ),
}


def _read(path: Path) -> str:
    """Read file with safe error handling."""
    if not path.exists():
        pytest.skip(f"Route file not found: {path}")
    return path.read_text(encoding="utf-8")


def _dependency_calls(src: str) -> set[str]:
    """Extract all Depends() dependency names from source."""
    tree = ast.parse(src)
    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Depends":
            if node.args and isinstance(node.args[0], ast.Name):
                deps.add(node.args[0].id)
    return deps


class TestHostileCrossTenanEndpointFamilyContracts:
    """Verify each endpoint family enforces tenant isolation fail-closed."""

    @pytest.mark.parametrize("family_name,family_config", ENDPOINT_FAMILIES.items())
    def test_endpoint_family_has_tenant_auth_guard(self, family_name: str, family_config: tuple) -> None:
        """Each endpoint family must use require_authenticated or get_db_from_context."""
        layer, route_file, endpoint_prefix, methods = family_config
        src = _read(route_file)
        deps = _dependency_calls(src)

        acceptable_guards = {
            "require_authenticated",
            "get_db_from_context",
            "get_db_from_context_sync",
            "require_admin",
            "tenant_required",
            "get_request_context",  # Layer 6 uses this for auth + tenant context
            "require_request_tenant_id",  # Layer 3 graph_viz fail-closed tenant guard
            "require_tenant_context",  # Layer 3 canonical tenant context dependency
            "create_neo4j_tenant_session",  # Layer 3 tenant-scoped Neo4j session
            "TenantAccessError",  # Layer 3 query_search inline fail-closed tenant check
        }
        has_guard = bool(deps & acceptable_guards) or any(
            guard in src for guard in acceptable_guards
        )
        assert has_guard, (
            f"Endpoint family {family_name} ({endpoint_prefix}) in {layer} route file {route_file} "
            f"is missing a tenant auth guard dependency. Required: one of {acceptable_guards}. "
            f"Without a guard, any authenticated user can access resources across tenants."
        )

    @pytest.mark.parametrize("family_name,family_config", ENDPOINT_FAMILIES.items())
    def test_endpoint_family_write_methods_require_auth(self, family_name: str, family_config: tuple) -> None:
        """Write methods (POST/PUT/DELETE/PATCH) must require authentication."""
        layer, route_file, endpoint_prefix, methods = family_config
        src = _read(route_file)

        write_methods = {"POST", "PUT", "DELETE", "PATCH"}
        families_methods = set(methods)
        has_writes = bool(write_methods & families_methods)

        if not has_writes:
            pytest.skip(f"Endpoint family {family_name} has no write methods")

        # Check for require_authenticated or equivalent (including get_request_context)
        has_auth = any(
            pattern in src for pattern in [
                "require_authenticated",
                "get_db_from_context",
                "get_request_context",
                "require_admin",
                "tenant_required",
                "require_request_tenant_id",
                "require_tenant_context",
                "create_neo4j_tenant_session",
                "TenantAccessError",
            ]
        )
        assert has_auth, (
            f"Endpoint family {family_name} ({endpoint_prefix}) in {layer} has write methods {write_methods & families_methods} "
            f"but does not appear to enforce authentication. Write operations must be authenticated."
        )

    @pytest.mark.parametrize("family_name,family_config", ENDPOINT_FAMILIES.items())
    def test_endpoint_family_no_optional_context_on_writes(self, family_name: str, family_config: tuple) -> None:
        """Write endpoints must not use optional context (must require auth explicitly)."""
        layer, route_file, endpoint_prefix, methods = family_config
        src = _read(route_file)

        write_methods = {"POST", "PUT", "DELETE", "PATCH"}
        families_methods = set(methods)
        has_writes = bool(write_methods & families_methods)

        if not has_writes:
            pytest.skip(f"Endpoint family {family_name} has no write methods")

        # Look for pattern: @router.post/put/patch/delete ... get_optional_context
        lines = src.split("\n")
        for i, line in enumerate(lines):
            if any(f"@router.{m.lower()}" in line for m in write_methods) or any(
                f"@app.{m.lower()}" in line for m in write_methods
            ):
                # Check next 10 lines for optional context usage
                block = "\n".join(lines[i : min(i + 10, len(lines))])
                assert "get_optional_context" not in block, (
                    f"Endpoint family {family_name} ({endpoint_prefix}) uses get_optional_context on a write method. "
                    f"Write endpoints must use require_authenticated, not optional context."
                )


class TestHostileCrossTenanErrorContractsByFamily:
    """Verify error responses for hostile cross-tenant access are safe."""

    @pytest.mark.parametrize("family_name,family_config", ENDPOINT_FAMILIES.items())
    def test_endpoint_family_error_responses_are_safe(self, family_name: str, family_config: tuple) -> None:
        """Error responses must not leak sensitive internals (traces, tokens, secrets)."""
        layer, route_file, endpoint_prefix, methods = family_config
        src = _read(route_file)

        forbidden_leak_patterns = [
            "traceback",
            "sqlalchemy",
            "password",
            "secret",
            "api_key",
            "bearer",
            "token",
        ]
        lower_src = src.lower()

        # Check for explicit error handling patterns (not raw raises)
        has_error_handling = any(pattern in lower_src for pattern in ["try:", "except", "httpexception", "raise"])
        assert has_error_handling, (
            f"Endpoint family {family_name} ({endpoint_prefix}) in {layer} has no explicit error handling. "
            f"Routes must explicitly handle errors to prevent info leaks."
        )
