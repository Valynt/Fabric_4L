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
        assert 'semgrep==${{ env.SEMGREP_VERSION }}' in commands
        assert "pip install semgrep\n" not in commands


def test_full_scan_uses_only_reviewed_vendored_and_local_rules() -> None:
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    for registry_pack in (
        "p/security-audit",
        "p/secrets",
        "p/owasp-top-ten",
        "p/python",
        "p/typescript",
        "p/react",
        "p/dockerfile",
        "p/docker-compose",
        "p/kubernetes",
        "p/github-actions",
    ):
        assert f"--config {registry_pack}" not in workflow_text

    assert "--config config/semgrep/registry/" in workflow_text
    assert "--config .semgrep/" in workflow_text


def test_static_scanner_smoke_check_validates_configs_and_sarif() -> None:
    workflow = _workflow()
    steps = workflow["jobs"]["semgrep-full-scan"]["steps"]
    smoke = next(
        step for step in steps if step.get("name") == "Smoke check pinned Semgrep"
    )
    command = smoke["run"]

    assert "semgrep scan" in command
    assert "--validate" in command
    assert "--config config/semgrep/registry/" in command
    assert "--config .semgrep/" in command
    assert "--sarif" in command
    assert "json.load" in command
    assert "continue-on-error" not in workflow["jobs"]["semgrep-full-scan"]
