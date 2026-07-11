from pathlib import Path
import subprocess

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
PEN_TEST_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "penetration-testing.yml"
NIKTO_SCRIPT = REPO_ROOT / "tests" / "penetration" / "nikto-scan.sh"


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
    nikto_run_step = next(step for step in nikto_steps if step.get("name") == "Run Nikto Scan")
    run_section = nikto_run_step["run"]
    assert "if [ -f tests/penetration/nikto-scan.sh ]; then" in run_section
    assert "else" in run_section
    assert "mkdir -p nikto-results" in run_section
    assert "nikto-results/nikto.log" in run_section
    assert "nikto-results/nikto-report.txt" in run_section
    assert "nikto-results/summary.json" in run_section
