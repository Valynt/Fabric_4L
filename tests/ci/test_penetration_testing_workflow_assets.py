from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
PEN_TEST_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "penetration-testing.yml"
NIKTO_SCRIPT = REPO_ROOT / "tests" / "penetration" / "nikto-scan.sh"


def test_nikto_script_referenced_and_executable() -> None:
    workflow = yaml.safe_load(PEN_TEST_WORKFLOW.read_text(encoding="utf-8"))
    nikto_steps = workflow["jobs"]["nikto-scan"]["steps"]
    run_sections = [step.get("run", "") for step in nikto_steps if isinstance(step, dict)]
    assert any("chmod +x tests/penetration/nikto-scan.sh" in run for run in run_sections)
    assert any("./tests/penetration/nikto-scan.sh" in run for run in run_sections)
    assert NIKTO_SCRIPT.exists()
    assert NIKTO_SCRIPT.stat().st_mode & 0o111
