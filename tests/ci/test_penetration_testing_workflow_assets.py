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
    assert any("test -x tests/penetration/nikto-scan.sh" in run for run in run_sections)
    assert any("./tests/penetration/nikto-scan.sh" in run for run in run_sections)
    assert any("nikto-results/summary.json" in run for run in run_sections)
    assert NIKTO_SCRIPT.exists()
    assert NIKTO_SCRIPT.stat().st_mode & 0o111
    assert NIKTO_SCRIPT.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
    subprocess.run(["bash", "-n", str(NIKTO_SCRIPT)], check=True)


def test_nikto_workflow_fails_when_scanner_wrapper_is_missing() -> None:
    workflow = yaml.safe_load(PEN_TEST_WORKFLOW.read_text(encoding="utf-8"))
    nikto_steps = workflow["jobs"]["nikto-scan"]["steps"]
    nikto_run_step = _find_step_by_name(nikto_steps, "Run Nikto Scan")
    run_section = nikto_run_step["run"]
    assert "test -x tests/penetration/nikto-scan.sh" in run_section
    assert "Required Nikto wrapper is missing or not executable" in run_section
    assert "--timeout 1200 || true" not in run_section
    assert "test -s nikto-results/summary.json" in run_section


def test_zap_workflow_fails_closed_and_preserves_evidence() -> None:
    workflow = yaml.safe_load(PEN_TEST_WORKFLOW.read_text(encoding="utf-8"))
    assert workflow["env"]["TARGET_URL"] == "${{ inputs.target_url || 'http://localhost:8004' }}"

    zap_steps = workflow["jobs"]["zap-scan"]["steps"]
    startup = _find_step_by_name(zap_steps, "Start test stack")
    assert "up -d || true" not in startup["run"]
    assert "curl --fail --silent --show-error" in startup["run"]
    assert "docker compose -f infra/compose/docker-compose.full.yml --env-file .env logs --no-color" in startup["run"]
    assert startup["continue-on-error"] is True
    assert "mkdir -p zap-results" in startup["run"], "Output directory must be created up front"
    assert "zap-results/metadata.json" in startup["run"], "Metadata file must be written up front"
    assert "tee zap-results/compose.log" in startup["run"], "Compose logs must be teed to compose.log on failure"

    scan = _find_step_by_name(zap_steps, "Run ZAP Full Scan (Docker)")
    assert scan["id"] == "zap_scan"
    assert "zap_exit_code=$?" in scan["run"]
    assert "zap_exit_code=$zap_exit_code" in scan["run"]
    assert "policy_status=findings" in scan["run"]
    assert "execution_status=runtime_failure" in scan["run"]
    assert scan["continue-on-error"] is True

    validation = _find_step_by_name(zap_steps, "Validate ZAP JSON report")
    assert "json.load" in validation["run"]
    assert "report.get(\"site\")" in validation["run"]
    assert validation["continue-on-error"] is True

    conversion = _find_step_by_name(zap_steps, "Convert ZAP results to SARIF")
    assert "|| true" not in conversion["run"]
    assert conversion["continue-on-error"] is True

    artifact = _find_step_by_name(zap_steps, "Upload ZAP results")
    sarif = _find_step_by_name(zap_steps, "Upload SARIF to GitHub Security")
    assert artifact["if"] == "always()"
    assert sarif["if"] == "always() && steps.convert_sarif.outcome == 'success'"

    policy = _find_step_by_name(zap_steps, "Enforce penetration test policy")
    assert policy["if"] == "always()"
    assert "steps.startup.outcome" in policy["run"]
    assert "steps.zap_scan.outputs.execution_status" in policy["run"]
    assert "steps.validate_report.outcome" in policy["run"]
    assert "steps.convert_sarif.outcome" in policy["run"]
    assert "steps.zap_scan.outputs.policy_status" in policy["run"]


def test_nikto_stack_startup_is_bounded_and_fail_closed() -> None:
    workflow = yaml.safe_load(PEN_TEST_WORKFLOW.read_text(encoding="utf-8"))
    nikto_steps = workflow["jobs"]["nikto-scan"]["steps"]
    startup = _find_step_by_name(nikto_steps, "Start test stack")
    assert "up -d || true" not in startup["run"]
    assert "curl --fail --silent --show-error" in startup["run"]
    assert "docker compose -f infra/compose/docker-compose.full.yml --env-file .env logs --no-color" in startup["run"]
    assert "mkdir -p nikto-results" in startup["run"], "Output directory must be created up front"
    assert "nikto-results/metadata.json" in startup["run"], "Metadata file must be written up front"
    assert "tee nikto-results/compose.log" in startup["run"], "Compose logs must be teed to compose.log on failure"
