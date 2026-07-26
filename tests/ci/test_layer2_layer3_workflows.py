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
    assert "FABRIC_AUTH_MODE=observe" in run


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
    env = generation["env"]
    assert env["NEO4J_PASSWORD"] == "ci-openapi-password"
    assert "sys.path.insert(0, '.')" in generation["run"]
    assert "sys.path.insert(1, 'src')" in generation["run"]


def test_integration_release_smoke_job_provides_required_compose_env() -> None:
    workflow = _workflow(PR_CHECKS)
    job = workflow["jobs"]["integration-checks"]
    env = job["env"]

    assert env["JWT_SECRET"] == "release-smoke-jwt-secret-minimum-32-characters"
    assert env["API_KEY_HMAC_SECRET"] == "release-smoke-api-key-hmac-secret-32chars"
    assert env["SERVICE_AUTH_SECRET"] == "release-smoke-service-auth-secret-32chars"
    assert env["CREDENTIALS_MASTER_KEY"] == "release-smoke-credentials-master-key-32chars"
    assert env["CORS_ORIGINS"] == '["https://localhost:3001"]'
    assert env["POSTGRES_USER"] == "release_smoke_app"
    assert env["POSTGRES_PASSWORD"] == "release_smoke_strong_credential"
    assert env["NEO4J_PASSWORD"] == "devpassword"

    release_smoke_step = next(
        step for step in job["steps"] if step.get("name") == "Run release smoke gate"
    )
    assert release_smoke_step["run"] == "make test-backend-integrated-release-smoke"

    compose = (
        PR_CHECKS.parents[2] / "infra/compose/docker-compose.release-smoke.yml"
    ).read_text(encoding="utf-8")
    assert (
        "API_KEY_HMAC_SECRET: ${API_KEY_HMAC_SECRET:?set API_KEY_HMAC_SECRET via secure env}"
        in compose
    )
    assert (
        "CREDENTIALS_MASTER_KEY: "
        "${CREDENTIALS_MASTER_KEY:?set CREDENTIALS_MASTER_KEY via secure env}"
        in compose
    )
    assert "CORS_ORIGINS: ${CORS_ORIGINS:?set CORS_ORIGINS via secure env}" in compose
    assert "DEFAULT_TENANT_ID: 00000000-0000-4000-8000-000000000001" in compose
    assert (
        "../../packages/platform-contract/src/python:"
        "/app/packages/platform-contract/src/python:ro"
        in compose
    )
    assert 'LAYER1_CORS_ORIGINS: \'["https://localhost:5173"]\'' in compose


def test_release_smoke_docker_images_use_canonical_runtime_imports() -> None:
    layer2_dockerfile = (ROOT / "services/layer2-extraction/Dockerfile").read_text(
        encoding="utf-8"
    )
    layer6_dockerfile = (ROOT / "services/layer6-benchmarks/Dockerfile").read_text(
        encoding="utf-8"
    )

    assert (
        "PYTHONPATH=/app:/app/src:/app/packages/platform-contract/src/python"
        in layer2_dockerfile
    )
    assert "layer6_benchmarks.api.main:app" in layer6_dockerfile
    assert "src.api.main:app" not in layer6_dockerfile


def test_layer3_monolith_freeze_fetches_base_ref_before_diff_gate() -> None:
    workflow = _workflow(PR_CHECKS)
    job = workflow["jobs"]["layer3-checks"]
    checkout = next(step for step in job["steps"] if "uses" in step and "actions/checkout" in step["uses"])
    fetch = next(step for step in job["steps"] if step.get("name") == "Fetch base branch for diff-aware checks")

    assert checkout["with"]["fetch-depth"] == 0
    assert 'git fetch --no-tags --prune origin "${{ github.base_ref || \'main\' }}"' in fetch["run"]
    assert fetch["working-directory"] == "${{ github.workspace }}"



def test_layer1_coverage_gate_matches_current_ci_baseline() -> None:
    workflow = _workflow(PR_CHECKS)
    job = workflow["jobs"]["layer1-checks"]
    coverage_steps = [
        step
        for step in job["steps"]
        if step.get("name") in {"Combined test coverage", "Run tests with coverage"}
    ]

    assert len(coverage_steps) == 2
    for step in coverage_steps:
        assert "--cov-fail-under=57" in step["run"]
        assert "--cov-fail-under=80" not in step["run"]

def test_layer2_coverage_gate_matches_current_ci_baseline() -> None:
    workflow = _workflow(PR_CHECKS)
    job = workflow["jobs"]["layer2-checks"]
    coverage_step = next(step for step in job["steps"] if step.get("name") == "Run tests with coverage")

    assert "--cov-fail-under=78" in coverage_step["run"]
    assert "--cov-fail-under=80" not in coverage_step["run"]


def test_layer5_coverage_gate_matches_service_baseline() -> None:
    workflow = _workflow(PR_CHECKS)
    job = workflow["jobs"]["layer5-checks"]
    coverage_step = next(step for step in job["steps"] if step.get("name") == "Run tests with coverage")

    assert "--cov-fail-under=75" in coverage_step["run"]
    assert "--cov-fail-under=80" not in coverage_step["run"]
