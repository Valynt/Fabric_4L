"""Contract tests for Layer 2 -> Layer 3 integration."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from .schema_assertions import assert_matches_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_L3_PATH = REPO_ROOT / "contracts" / "openapi" / "layer3-knowledge.json"
ENTITY_SCHEMA_PATH = REPO_ROOT / "contracts" / "jsonschema" / "entity.json"
L2_CLIENT_PATH = REPO_ROOT / "services" / "layer2-extraction" / "src" / "layer2_extraction" / "integration" / "layer3_client.py"
L3_API_MAIN_PATH = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "main.py"

HTTP_DECORATORS = {"get", "post", "put", "delete", "patch"}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _openapi_component_schema(doc: dict[str, Any], name: str) -> dict[str, Any]:
    return {"$ref": f"#/components/schemas/{name}", "components": doc.get("components", {})}


def _extract_fastapi_paths(source_file: Path, app_names: set[str]) -> set[str]:
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


class TestL2ToL3PayloadContract:
    @pytest.mark.parametrize(
        ("payload", "schema_name"),
        [
            (
                {
                    "rdf_data": "@prefix ex: <http://example.com/> . ex:cap1 a ex:Capability .",
                    "source_id": "https://example.com/doc/123",
                    "extraction_job_id": "job-123",
                    "content_hash": "a" * 64,
                },
                "IngestRequest",
            ),
        ],
    )
    def test_l2_payload_shape_validates_against_l3_openapi_schema(
        self,
        payload: dict[str, Any],
        schema_name: str,
    ) -> None:
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        schema = _openapi_component_schema(l3_openapi, schema_name)
        assert_matches_schema(payload, schema, root=l3_openapi)

    def test_l2_entity_sample_validates_against_entity_jsonschema(self) -> None:
        entity_schema = _load_json(ENTITY_SCHEMA_PATH)
        sample_entity = {
            "id": "cap-123",
            "type": "Capability",
            "name": "Automated Invoice Processing",
            "description": "Capability for straight-through invoice handling.",
            "confidence_score": 0.93,
            "source_ids": ["doc-1"],
            "created_at": "2026-04-14T00:00:00Z",
            "updated_at": "2026-04-14T00:00:00Z",
        }
        assert_matches_schema(sample_entity, entity_schema)


class TestL3ContractDriftDetection:
    def test_l3_ingestion_and_query_endpoints_are_present_in_openapi_contract(self) -> None:
        implementation_paths = _extract_fastapi_paths(L3_API_MAIN_PATH, app_names={"app"})
        contract_paths = set(_load_json(OPENAPI_L3_PATH).get("paths", {}).keys())
        monitored_paths = {"/v1/ingest", "/v1/ingest/status/{source_id}", "/v1/search/hybrid", "/v1/query/graph"}

        missing_from_contract = {p for p in monitored_paths if p in implementation_paths and p not in contract_paths}
        assert not missing_from_contract, (
            "OpenAPI drift detected for Layer 3 monitored endpoints. "
            f"Missing in contracts/openapi/layer3-knowledge.json: {sorted(missing_from_contract)}"
        )

    def test_l2_client_and_l3_contract_stay_aligned_on_ingest_route(self) -> None:
        l2_source = L2_CLIENT_PATH.read_text(encoding="utf-8")
        # The client builds the URL dynamically: f"{self.base_url}/v1/ingest"
        # Accept either the literal string or the f-string fragment.
        assert '"/v1/ingest"' in l2_source or "/v1/ingest" in l2_source

        contract_paths = set(_load_json(OPENAPI_L3_PATH).get("paths", {}).keys())
        assert "/v1/ingest" in contract_paths
