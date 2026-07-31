from __future__ import annotations

import json
from pathlib import Path

from scripts.ci import validate_fabric_openapi_docs as docs_gate


def _minimal_spec() -> dict:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Sample", "version": "1.0.0"},
        "paths": {
            "/v1/sample": {
                "get": {
                    "description": "List sample records for contract validation.",
                    "tags": ["Platform"],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer"},
                            "description": "Maximum number of sample records to return.",
                        }
                    ],
                    "responses": {"200": {"description": "Sample records returned successfully."}},
                }
            }
        },
        "components": {
            "schemas": {
                "Sample": {
                    "type": "object",
                    "description": "Sample response object used by contract tests.",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Stable identifier for this sample record.",
                        }
                    },
                }
            }
        },
    }


def test_validate_docs_accepts_baselined_existing_violations() -> None:
    spec = _minimal_spec()
    spec["components"]["schemas"]["Sample"]["properties"]["name"] = {"type": "string"}
    baseline = [
        "schema Sample.name: missing meaningful description",
    ]

    assert docs_gate.validate(spec, baseline=baseline) == []


def test_validate_docs_fails_unbaselined_new_violations() -> None:
    spec = _minimal_spec()
    spec["components"]["schemas"]["Sample"]["properties"]["name"] = {"type": "string"}

    assert docs_gate.validate(spec, baseline=[]) == [
        "schema Sample.name: missing meaningful description",
    ]


def test_validate_docs_rejects_stale_baseline_violations() -> None:
    spec = _minimal_spec()

    assert docs_gate.validate(
        spec,
        baseline=["schema Sample.name: missing meaningful description"],
    ) == ["STALE BASELINE: schema Sample.name: missing meaningful description"]


def test_validate_docs_update_baseline_writes_current_errors(tmp_path: Path) -> None:
    spec_path = tmp_path / "openapi.json"
    baseline_path = tmp_path / "baseline.json"
    spec = _minimal_spec()
    spec["components"]["schemas"]["Sample"]["properties"]["name"] = {"type": "string"}
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    rc = docs_gate.main([str(spec_path), "--baseline", str(baseline_path), "--update-baseline"])

    assert rc == 0
    assert json.loads(baseline_path.read_text(encoding="utf-8"))["violations"] == [
        "schema Sample.name: missing meaningful description",
    ]


def test_cross_layer_contract_workflow_uses_openapi_docs_baseline() -> None:
    workflow = Path(".github/workflows/pr-checks.yml").read_text(encoding="utf-8")

    assert (
        "python scripts/ci/validate_fabric_openapi_docs.py "
        "--baseline config/ci/fabric_openapi_docs_baseline.json"
    ) in workflow
