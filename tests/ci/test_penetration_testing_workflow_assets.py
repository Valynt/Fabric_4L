import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PEN_TEST_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "penetration-testing.yml"
NIKTO_SCRIPT = REPO_ROOT / "tests" / "penetration" / "nikto-scan.sh"


def _find_step_by_name(steps: list[dict], step_name: str) -> dict:
    step = next((item for item in steps if item.get("name") == step_name), None)
    assert step is not None, f"{step_name} step is missing from penetration-testing workflow"
    return step


def test_nikto_script_referenced_and_executable() -> None:
    workflow = yaml.safe_load(PEN_TEST_WORKFLOW.read_text(encoding="utf-8"))
    nikto_steps = workflow["jobs"]["nikto-scan"]["steps"]
    run_sections = [step.get("run", "") for step in nikto_steps if isinstance(step, dict)]
    assert any("if [ -f tests/penetration/nikto-scan.sh ];" in run for run in run_sections)
    assert any("chmod +x tests/penetration/nikto-scan.sh" in run for run in run_sections)
    assert any("./tests/penetration/nikto-scan.sh" in run for run in run_sections)
    assert any("nikto-results/summary.json" in run for run in run_sections)
    assert NIKTO_SCRIPT.exists()
    assert NIKTO_SCRIPT.stat().st_mode & 0o111
    assert NIKTO_SCRIPT.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
    subprocess.run(["bash", "-n", str(NIKTO_SCRIPT)], check=True)


def test_nikto_workflow_has_missing_script_fallback() -> None:
    workflow = yaml.safe_load(PEN_TEST_WORKFLOW.read_text(encoding="utf-8"))
    nikto_steps = workflow["jobs"]["nikto-scan"]["steps"]
    nikto_run_step = _find_step_by_name(nikto_steps, "Run Nikto Scan")
    run_section = nikto_run_step["run"]
    assert "if [ -f tests/penetration/nikto-scan.sh ]; then" in run_section, "Missing script existence guard"
    assert "else" in run_section, "Missing fallback branch for absent nikto script"
    assert "mkdir -p nikto-results" in run_section, "Missing fallback artifact directory creation"
    assert "Nikto script unavailable for this revision" in run_section, "Missing fallback nikto.log message"
    assert "nikto-results/nikto.log" in run_section, "Missing fallback nikto.log output"
    assert "Nikto report unavailable for target ${{ env.TARGET_URL }}" in run_section, "Missing fallback report message"
    assert "nikto-results/nikto-report.txt" in run_section, "Missing fallback nikto-report output"
    assert "nikto-results/summary.json" in run_section, "Missing fallback summary.json generation"
