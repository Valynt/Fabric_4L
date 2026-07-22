from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
PR_CHECKS = ROOT / ".github/workflows/pr-checks.yml"
CONTRACT_COMPLIANCE = ROOT / ".github/workflows/contract-compliance.yml"
AUTH_FIXTURE = ROOT / "config/ci/fabric_auth_test_public_keys.json"


def _workflow(path: Path) -> dict:
    # PyYAML parses the YAML 1.1 `on` key as True unless a loader is adjusted.
    class Loader(yaml.SafeLoader):
        pass

    Loader.add_constructor(
        "tag:yaml.org,2002:bool",
        lambda loader, node: loader.construct_scalar(node),
    )
    return yaml.load(path.read_text(encoding="utf-8"), Loader=Loader)


def test_layer2_workflow_loads_public_only_auth_fixture() -> None:
    workflow = _workflow(PR_CHECKS)
    job = workflow["jobs"]["layer2-checks"]
    steps = job["steps"]
    auth_steps = [step for step in steps if "FABRIC_AUTH_PUBLIC_KEYS" in step.get("run", "")]
    assert len(auth_steps) == 1
    run = auth_steps[0]["run"]
    assert "config/ci/fabric_auth_test_public_keys.json" in run
    assert "GITHUB_ENV" in run
    assert "FABRIC_AUTH_SIGNING_KEY" not in run
    assert "FABRIC_AUTH_MODE" not in run or "enforce" in run


def test_auth_fixture_contains_only_ed25519_public_material() -> None:
    payload = json.loads(AUTH_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(payload, list) and payload
    for entry in payload:
        assert set(entry) == {"kid", "public_pem"}
        assert "PRIVATE KEY" not in entry["public_pem"]
        assert "PUBLIC KEY" in entry["public_pem"]


def test_layer3_openapi_generation_uses_canonical_module_and_service_directory() -> None:
    workflow = _workflow(CONTRACT_COMPLIANCE)
    job = workflow["jobs"]["generate-openapi"]
    layer3 = next(item for item in job["strategy"]["matrix"]["include"] if item["layer"] == "layer3-knowledge")
    assert layer3["module"] == "src.api.main"
    generation = next(step for step in job["steps"] if step.get("name") == "Generate OpenAPI spec from code")
    assert generation["working-directory"] == "./services/${{matrix.layer}}"
    assert "sys.path.insert(0, 'src')" in generation["run"]

