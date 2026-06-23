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
