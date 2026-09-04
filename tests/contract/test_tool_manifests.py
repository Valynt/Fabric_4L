"""
Contract tests — validate that tool manifest JSON Schemas are well-formed
and consistent with their corresponding skill definitions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Repo root is 3 levels up from tests/contract/test_tool_manifests.py
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFESTS_DIR = REPO_ROOT / "contracts" / "tool-manifests"
SKILLS_DIR = REPO_ROOT / "services" / "layer4-agents" / "skills"
WORKFLOWS_DIR = REPO_ROOT / "services" / "layer4-agents" / "workflows"


def load_manifest(name: str) -> dict:
    path = MANIFESTS_DIR / f"{name}.json"
    with open(path) as f:
        return json.load(f)


def manifest_names() -> list[str]:
    # JSON Schemas ({{name}}.schema.json) are definition files, not manifests;
    # they carry $id/title/type rather than name/version/parameters.
    return sorted(
        p.stem for p in MANIFESTS_DIR.glob("*.json") if not p.name.endswith(".schema.json")
    )


@pytest.fixture(scope="module")
def manifests_by_name() -> dict[str, dict]:
    """Load all manifests once to reduce I/O and stabilize ordering."""
    return {name: load_manifest(name) for name in manifest_names()}


class TestToolManifestStructure:
    """Every tool manifest must conform to the expected schema shape."""

    @pytest.mark.parametrize("name", manifest_names())
    def test_manifest_has_required_top_level_fields(self, name: str, manifests_by_name: dict[str, dict]) -> None:
        manifest = manifests_by_name[name]
        for required_field in ("$schema", "name", "version", "description", "parameters"):
            assert required_field in manifest, f"{name}: missing {required_field}"

    @pytest.mark.parametrize("name", manifest_names())
    def test_parameters_is_object_type(self, name: str, manifests_by_name: dict[str, dict]) -> None:
        manifest = manifests_by_name[name]
        params = manifest["parameters"]
        assert params.get("type") == "object", (
            f"{name}: parameters must be type 'object'"
        )
        assert "properties" in params, f"{name}: parameters missing 'properties'"

    @pytest.mark.parametrize("name", manifest_names())
    def test_required_fields_are_listed_in_properties(self, name: str, manifests_by_name: dict[str, dict]) -> None:
        manifest = manifests_by_name[name]
        params = manifest["parameters"]
        required = params.get("required", [])
        properties = set(params.get("properties", {}).keys())
        for field in required:
            assert field in properties, (
                f"{name}: required field '{field}' not in properties"
            )

    @pytest.mark.parametrize("name", manifest_names())
    def test_skill_definition_exists_for_manifest(self, name: str) -> None:
        """Every tool manifest must have a corresponding skill or workflow definition."""
        skill_path = SKILLS_DIR / f"{name}.md"
        workflow_path = WORKFLOWS_DIR / f"{name}.md"
        assert skill_path.exists() or workflow_path.exists(), (
            f"contracts/tool-manifests/{name}.json has no corresponding "
            f"services/layer4-agents/skills/{name}.md or services/layer4-agents/workflows/{name}.md"
        )
