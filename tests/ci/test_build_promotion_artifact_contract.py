import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD = REPO_ROOT / ".github/workflows/build-deploy.yml"
PROMOTION = REPO_ROOT / ".github/workflows/environment-promotion.yml"
SCRIPT = REPO_ROOT / "scripts/ci/validate_promotion_artifact_contract.py"


def test_workflows_reference_shared_build_metadata_contract() -> None:
    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--build-workflow",
            str(BUILD),
            "--promotion-workflow",
            str(PROMOTION),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "schema contract passed" in result.stdout.lower()
