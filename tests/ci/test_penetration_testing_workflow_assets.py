from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
PEN_TEST_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "penetration-testing.yml"
NIKTO_SCRIPT = REPO_ROOT / "tests" / "penetration" / "nikto-scan.sh"


def test_penetration_testing_workflow_references_existing_nikto_script() -> None:
    workflow = yaml.safe_load(PEN_TEST_WORKFLOW.read_text(encoding="utf-8"))
    nikto_steps = workflow["jobs"]["nikto-scan"]["steps"]
    run_steps = "\n".join(step.get("run", "") for step in nikto_steps if isinstance(step, dict))
    assert "chmod +x tests/penetration/nikto-scan.sh" in run_steps
    assert "./tests/penetration/nikto-scan.sh" in run_steps
    assert NIKTO_SCRIPT.exists()
