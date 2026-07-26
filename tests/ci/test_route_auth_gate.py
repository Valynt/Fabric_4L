from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts/ci/check_route_auth_dependencies.py"

EXPECTED_SERVICE_TARGETS = [
    "services/api/app/main.py",
    "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
    "services/layer2-extraction/src/layer2_extraction/api/main.py",
    "services/layer3-knowledge/src/api/main.py",
    "services/layer4-agents/src/layer4_agents/api/main.py",
    "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
    "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
]


def test_route_auth_gate_scans_services_api_by_default() -> None:
    content = GATE_SCRIPT.read_text()

    for target in EXPECTED_SERVICE_TARGETS:
        assert target in content
    assert "services/layer1-ingestion/src/api/main.py" not in content
    assert "services/layer4-agents/src/api/main.py" not in content
    assert '"routers"' in content


def test_route_auth_gate_passes_for_services_api_routes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--target",
            "services/api/app/main.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: all non-allowlisted routes have auth dependencies" in result.stdout


def test_route_auth_gate_detects_missing_auth_in_canonical_routes_dir(tmp_path: Path) -> None:
    canonical_api_dir = (
        tmp_path
        / "services"
        / "layer1-ingestion"
        / "src"
        / "layer1_ingestion"
        / "api"
    )
    routes_dir = canonical_api_dir / "routes"
    routes_dir.mkdir(parents=True)
    (canonical_api_dir / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n",
        encoding="utf-8",
    )
    route_file = routes_dir / "canonical_private.py"
    route_file.write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "@router.get('/canonical-private')\n"
        "async def canonical_private():\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )
    allowlist = tmp_path / "route-auth-allowlist.yaml"
    allowlist.write_text("allowlist: []\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--allowlist",
            str(allowlist),
            "--target",
            str(canonical_api_dir / "main.py"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL: non-allowlisted routes without auth dependencies" in result.stdout
    assert "GET /canonical-private" in result.stdout
    assert str(route_file) in result.stdout


def test_critical_behaviors_gate_installs_hash_locked_test_policy_dependencies() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "pr-checks.yml").read_text(encoding="utf-8")
    critical_behaviors_job = workflow.split("  critical-behaviors-gate:", 1)[1].split("  unified-readiness-gate:", 1)[0]

    assert "python -m pip install --require-hashes -r tests/requirements-test.lock" in critical_behaviors_job
    assert "python -m pip install pytest pyyaml jsonschema" not in critical_behaviors_job


def test_cross_layer_contracts_install_hash_locked_test_policy_dependencies() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "pr-checks.yml").read_text(encoding="utf-8")
    cross_layer_job = workflow.split("  contract-checks:", 1)[1].split("  integration-smoke:", 1)[0]

    assert "python -m pip install --require-hashes -r tests/requirements-test.lock" in cross_layer_job
    assert "pip install -r tests/requirements.txt -r packages/platform-contract/requirements-test.txt" not in cross_layer_job




def test_layer1_ci_provisions_legacy_and_canonical_database_names() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "pr-checks.yml").read_text(encoding="utf-8")
    layer1_job = workflow.split("  layer1-checks:", 1)[1].split("  # Layer 2 - Extraction", 1)[0]

    assert "POSTGRES_DB: layer1_ingestion" in layer1_job
    assert "Create Layer 1 CI databases" in layer1_job
    assert "createdb -h localhost -U postgres ingestion" in layer1_job
    assert "createdb -h localhost -U postgres layer1_ingestion" in layer1_job

def test_layer4_collection_uses_existing_working_directory() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "pr-checks.yml").read_text(encoding="utf-8")
    layer4_job = workflow.split("  layer4-checks:", 1)[1].split("  layer5-contract-shape-regression:", 1)[0]

    assert "working-directory: services/layer4-agents" in layer4_job
    assert "uv run pytest --collect-only . -q" in layer4_job
    assert "cd services/layer4-agents" not in layer4_job


def test_contract_scorecard_is_advisory_in_workflow() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "contract-compliance.yml").read_text(encoding="utf-8")

    assert "python scripts/ci/contract_scorecard.py --output contract-scorecard.json --gha-comment || true" in workflow
    assert "Contract Scorecard" in workflow
    assert "continue-on-error: true\n        uses: actions/github-script@v7" in workflow
