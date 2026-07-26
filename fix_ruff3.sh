cat << 'INNER_EOF' > tests/ci/test_security_gates_semgrep_pinning.py
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/security-gates.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_semgrep_jobs_share_one_exact_binary_pin() -> None:
    workflow = _workflow()
    assert workflow["env"]["SEMGREP_VERSION"]

    for job_name in ("cypher-dynamic-guard", "semgrep-full-scan"):
        commands = "\n".join(
            step.get("run", "") for step in workflow["jobs"][job_name]["steps"]
        )
        assert (
            'python3 -m pip install "semgrep==${{ env.SEMGREP_VERSION }}"' in commands
        )
INNER_EOF
