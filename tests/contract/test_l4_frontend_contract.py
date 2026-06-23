"""Contract tests for Layer 3/Layer 4 responses consumed by frontend.

Validates that:
- Frontend API samples match backend OpenAPI contracts
- API routes in implementation are documented in OpenAPI
- Frontend environment config matches backend route structure

Implementation Notes:
--------------------
This test file uses Python's AST (Abstract Syntax Tree) module to parse and
validate backend source code without importing it. This approach provides:
- Fast test execution (no runtime imports needed)
- Detection of API surface changes at the source level
- Independence from runtime dependencies

Brittleness Considerations (P2 Improvement):
-------------------------------------------
1. AST structure changes: If backend code refactors to use different FastAPI
   patterns (e.g., class-based views, dynamic route registration), the
   _extract_routes_from_ast() function may need updates.
2. Decorator patterns: The detection of HTTP methods relies on specific
   decorator patterns (@router.get, @app.post, etc.). Alternative patterns
   (e.g., middleware-based routing) won't be detected.
3. Path extraction: Route paths are extracted from string literals. Dynamic
   path construction or f-strings won't be captured.

Maintenance: If AST parsing fails after backend refactoring:
- Check HTTP_DECORATORS pattern matching
- Verify _extract_routes_from_ast() handles new syntax patterns
- Consider switching to runtime introspection if AST becomes too brittle

NOTE: If tests fail due to missing schemas, regenerate OpenAPI contracts:
    python scripts/export_openapi.py
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import pytest

from .schema_assertions import SchemaValidationError, assert_matches_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_L3_PATH = REPO_ROOT / "contracts" / "openapi" / "layer3-knowledge.json"
OPENAPI_L4_PATH = REPO_ROOT / "contracts" / "openapi" / "layer4-agents.json"
L3_MAIN_PATH = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "main.py"
L4_WORKFLOWS_PATH = REPO_ROOT / "services" / "layer4-agents" / "src" / "api" / "routes" / "workflows.py"

HTTP_DECORATORS = {"get", "post", "put", "delete", "patch"}

# Frontend API client configuration paths
FRONTEND_CLIENT_PATH = REPO_ROOT / "apps" / "web" / "src" / "api" / "client.ts"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _schema_ref(doc: dict[str, Any], name: str) -> dict[str, Any]:
    return {"$ref": f"#/components/schemas/{name}", "components": doc.get("components", {})}


def _assert_schema(sample: dict[str, Any], openapi_path: Path, schema_name: str) -> None:
    """Helper to validate a sample against an OpenAPI schema with clear error messages.

    Args:
        sample: The data sample to validate
        openapi_path: Path to the OpenAPI specification file
        schema_name: Name of the schema in components/schemas to validate against

    Raises:
        pytest.fail: If schema validation fails with a descriptive message
    """
    openapi = _load_json(openapi_path)
    schema = _schema_ref(openapi, schema_name)
    try:
        assert_matches_schema(sample, schema, root=openapi)
    except SchemaValidationError as e:
        pytest.fail(f"Schema '{schema_name}' validation failed (contract may need regeneration): {e}")


def _extract_fastapi_paths(source_file: Path, app_names: set[str]) -> set[str]:
    """Extract FastAPI route paths from source file using AST parsing.

    WARNING: This function is sensitive to FastAPI decorator patterns.
    If routes use unusual patterns (e.g., @app.get() called indirectly,
    or decorators wrapped in other decorators), extraction may fail.

    Known supported patterns:
        @app.get("/path")
        @router.post("/path")
        @app.put("/path/{id}")

    If routes are missing from contract verification, check that they
    follow these patterns or update this function to handle new patterns.

    Args:
        source_file: Path to the Python source file to analyze
        app_names: Set of variable names that are FastAPI apps/routers (e.g., {"app", "router"})

    Returns:
        Set of route paths found in the file
    """
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    paths: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr not in HTTP_DECORATORS:
                continue
            owner = decorator.func.value
            if not isinstance(owner, ast.Name) or owner.id not in app_names:
                continue
            if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                paths.add(decorator.args[0].value)
    return paths


class TestL3GraphContractsConsumedByFrontend:
    def test_graph_query_response_sample_matches_l3_openapi(self) -> None:
        sample = {
            "query": "invoice automation",
            "entities": [{"id": "cap-1", "name": "Automated Invoice Processing", "entity_type": "Capability", "confidence_score": 0.92}],
            "relationships": [{"source": "cap-1", "target": "uc-1", "type": "ENABLES", "confidence": 0.88}],
            "context_graph": {"nodes": [], "relationships": []},
            "confidence_score": 0.9,
            "sources": ["doc-123"],
            "processing_time_ms": 18.3,
            "answer": "Automated invoice processing is enabled by OCR and workflow orchestration.",
        }
        _assert_schema(sample, OPENAPI_L3_PATH, "GraphRAGResponse")

    def test_hybrid_search_response_sample_matches_l3_openapi(self) -> None:
        sample = {
            "query": "automation",
            "results": [{
                "entity_id": "cap-1",
                "entity_type": "Capability",
                "name": "Automated Invoice Processing",
                "description": "Capability",
                "bm25_score": 0.0,
                "vector_score": 0.91,
                "graph_score": 0.5,
                "combined_score": 0.8,
                "confidence": 0.92,
                "metadata": {},
            }],
            "total_results": 1,
            "search_type": "hybrid",
            "processing_time_ms": 22.1,
        }
        _assert_schema(sample, OPENAPI_L3_PATH, "SearchResponse")

    def test_monitored_l3_frontend_paths_exist_in_openapi_contract(self) -> None:
        implementation_paths = _extract_fastapi_paths(L3_MAIN_PATH, {"app"})
        contract_paths = set(_load_json(OPENAPI_L3_PATH).get("paths", {}).keys())
        monitored = {"/v1/query/graph", "/v1/search/hybrid", "/v1/entity/{entity_id}/context", "/v1/entity/traverse"}
        missing = {p for p in monitored if p in implementation_paths and p not in contract_paths}
        if missing:
            pytest.fail(
                f"Layer 3 OpenAPI drift: {sorted(missing)} exist in implementation but not in contract. "
                f"Run 'python scripts/export_openapi.py' to regenerate contracts."
            )


class TestL4WorkflowSSEContractsConsumedByUI:
    def test_workflow_status_response_matches_l4_openapi(self) -> None:
        """Workflow status response matches OpenAPI schema."""
        sample_status = {
            "id": "wf-123",
            "workflow_type": "business_case",
            "status": "running",
            "current_state": "analyzing",
            "progress": 45,
            "started_at": "2026-04-14T00:00:00Z",
            "completed_at": None,
            "results": {},
        }
        _assert_schema(sample_status, OPENAPI_L4_PATH, "WorkflowStatusResponse")

    def test_workflow_events_endpoint_exists(self) -> None:
        """Workflow events endpoint exists at /v1/workflows/{id}/events."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        # Note: OpenAPI has /v1 prefix, contract test was checking wrong path
        path = "/v1/workflows/{workflow_id}/events"
        if path not in l4_openapi.get("paths", {}):
            pytest.fail(f"Workflow events endpoint not found at {path}")
        # SSE endpoints use text/event-stream content type
        responses = l4_openapi["paths"][path]["get"]["responses"]
        if "200" in responses:
            content = responses["200"].get("content", {})
            # SSE endpoints may have text/event-stream or application/json for non-SSE docs
            assert any(ct in content for ct in ["text/event-stream", "application/json"]), \
                "Expected event-stream or json content type"

    def test_monitored_l4_workflow_paths_exist_in_openapi_contract(self) -> None:
        """Monitored L4 workflow paths exist in OpenAPI contract."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        contract_paths = set(l4_openapi.get("paths", {}).keys())
        # Note: OpenAPI has /v1 prefix
        monitored = {
            "/v1/workflows",
            "/v1/workflows/active",
            "/v1/workflows/{workflow_id}",
            "/v1/workflows/{workflow_id}/events",
            "/v1/workflows/{workflow_id}/resume"
        }
        missing = monitored - contract_paths
        if missing:
            pytest.fail(
                f"Layer 4 OpenAPI drift: {sorted(missing)} monitored paths not in contract. "
                f"Run 'python scripts/export_openapi.py' to regenerate contracts."
            )


class TestPathAlignment:
    """Contract tests for frontend/backend path alignment.

    These tests verify that the frontend API client configuration produces
    URLs that match the backend OpenAPI route definitions.
    """

    # Expected layer prefixes for drift detection
    EXPECTED_LAYER_PREFIXES = {
        'L1': ('VITE_L1_PREFIX', '/ingest'),
        'L2': ('VITE_L2_PREFIX', '/extract'),
        'L3': ('VITE_L3_PREFIX', '/graph'),
        'L4': ('VITE_L4_PREFIX', '/agents'),
        'L5': ('VITE_L5_PREFIX', '/truths'),
        'L6': ('VITE_L6_PREFIX', '/benchmarks'),
    }

    def _extract_env_default(self, client_content: str, var_name: str) -> str | None:
        """Extract fallback default value from TypeScript client code.

        Pattern: import.meta.env.VITE_X || '/default/value'
        Returns None if pattern not found (forces assertion failure).
        """
        pattern = rf"{re.escape(var_name)}\s*\|\|\s*['\"]([^'\"]+)['\"]"
        match = re.search(pattern, client_content)
        if match:
            return match.group(1)

        get_env_var_pattern = (
            rf"getApiEnvVar\(\s*\[[^\]]*{re.escape(var_name)}[^\]]*\]\s*,\s*['\"]([^'\"]+)['\"]"
        )
        match = re.search(get_env_var_pattern, client_content, re.DOTALL)
        return match.group(1) if match else None

    def test_env_example_has_correct_api_base(self) -> None:
        """VITE_API_BASE must include the gateway API version."""
        env_content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")

        assert "VITE_API_BASE=/api/v1" in env_content, (
            "VITE_API_BASE should be /api/v1 so layer prefixes stay layer-scoped. "
            "This matches docs/reference/service-routing-and-api-version-matrix.md."
        )

    def test_env_example_layer_prefixes_include_api_version(self) -> None:
        """All layer prefixes must stay layer-scoped under the gateway API version."""
        env_content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")

        missing_v1 = []
        for layer_name, (var_name, expected) in self.EXPECTED_LAYER_PREFIXES.items():
            env_line = f"{var_name}={expected}"
            if env_line not in env_content:
                missing_v1.append(f"{layer_name} ({var_name} should be {expected})")

        assert not missing_v1, (
            f"Layer prefixes do not match the gateway route matrix: {', '.join(missing_v1)}. "
            "Layer prefixes must not duplicate the /api/v1 gateway prefix."
        )

    def test_api_client_defaults_match_env_example(self) -> None:
        """Frontend API client fallback defaults must match .env.example configuration."""
        client_content = FRONTEND_CLIENT_PATH.read_text(encoding="utf-8")

        # Verify API_BASE default
        api_base_default = self._extract_env_default(client_content, 'VITE_API_BASE')
        assert api_base_default is not None, (
            "Could not find VITE_API_BASE fallback default in client.ts. "
            "Pattern should be: import.meta.env.VITE_API_BASE || '/api/v1'"
        )
        assert api_base_default == "/api/v1", (
            f"API client default VITE_API_BASE should be '/api/v1', got '{api_base_default}'. "
            "This must match .env.example for consistent behavior."
        )

        # Verify all layer prefix defaults
        mismatched = []
        for layer_name, (var_name, expected) in self.EXPECTED_LAYER_PREFIXES.items():
            actual = self._extract_env_default(client_content, var_name)
            if actual is None:
                mismatched.append(f"{layer_name}: {var_name} fallback not found")
            elif actual != expected:
                mismatched.append(f"{layer_name}: expected {expected}, got {actual}")

        assert not mismatched, (
            f"Layer prefix defaults don't match expected: {'; '.join(mismatched)}. "
            "Client.ts defaults must align with .env.example configuration."
        )

    def test_subgraph_endpoint_exists_in_openapi(self) -> None:
        """Subgraph endpoint must exist in OpenAPI with GET method."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        paths = l3_openapi.get("paths", {})

        assert "/v1/graph/subgraph" in paths, (
            "Backend OpenAPI must document /v1/graph/subgraph endpoint. "
            "This is required for the Graph Explorer to function."
        )

        subgraph_path = paths.get("/v1/graph/subgraph", {})
        assert "get" in subgraph_path, (
            "Subgraph endpoint must support GET method for useSubgraph hook."
        )
