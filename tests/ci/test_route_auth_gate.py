from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts/ci/check_route_auth_dependencies.py"

EXPECTED_SERVICE_TARGETS = [
    "services/api/app/main.py",
    "services/layer1-ingestion/src/layer1_ingestion/api/main.py",
    "services/layer2-extraction/src/layer2_extraction/api/main.py",
    "services/layer3-knowledge/src/api/main.py",
    "services/layer4-agents/src/api/main.py",
    "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
    "services/layer6-benchmarks/src/api/main.py",
]


def test_route_auth_gate_scans_services_api_by_default() -> None:
    content = GATE_SCRIPT.read_text()

    for target in EXPECTED_SERVICE_TARGETS:
        assert target in content
    assert '"routers"' in content


def test_route_auth_gate_passes_for_services_api_routes() -> None:
    result = subprocess.run(
        [
            "python",
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
