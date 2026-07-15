from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "prod-readiness.yml"


def _workflow() -> dict:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_launch_readiness_workflow_is_stage_gated() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]

    assert "setup" in jobs
    assert "security-isolation" in jobs
    assert "observability-readiness" in jobs
    assert "readiness-10" in jobs
    assert "release-policy" in jobs
    assert "prod-readiness-summary" in jobs
    assert jobs["setup"]["needs"] == ["determine-profile"]
    assert jobs["readiness-10"]["needs"] == ["setup"]
    assert "readiness-10" in jobs["release-policy"]["needs"]
    assert "release-policy" in jobs["prod-readiness-summary"]["needs"]


def test_launch_readiness_workflow_is_artifact_only_no_ci_push() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    workflow = _workflow()

    assert workflow["permissions"]["contents"] == "read"
    assert "contents: write" not in content
    assert "git push" not in content
    assert "git commit" not in content
    assert "upload-artifact" in content
    assert "Build launch-readiness evidence bundle" in content
    assert "validate-release-manifest.py" in content


def test_launch_readiness_workflow_runs_blocking_readiness_10_gate() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    workflow = _workflow()
    job = workflow["jobs"]["readiness-10"]

    assert job["needs"] == ["setup"]
    assert "pnpm readiness:10" in content
    assert "pnpm readiness:10 || true" not in content
    assert "artifacts/readiness-10/**" in content


def test_launch_readiness_workflow_uses_expected_stage_inputs() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    for gate in ("gate-policy", "gate-security", "gate-obs", "gate-release-policy"):
        assert gate in content
    assert "tenant-isolation-results.json" in content
    assert "red-dashboard-snapshot-metadata.json" in content


def test_pnpm_is_setup_before_setup_node_pnpm_cache() -> None:
    workflow = _workflow()
    violations: list[str] = []

    for job_name, job in workflow["jobs"].items():
        pnpm_setup_seen = False
        for step in job.get("steps", []):
            if not isinstance(step, dict):
                continue

            uses = str(step.get("uses", ""))
            if uses.startswith("pnpm/action-setup@"):
                pnpm_setup_seen = True

            with_config = step.get("with") or {}
            if (
                uses.startswith("actions/setup-node@")
                and isinstance(with_config, dict)
                and with_config.get("cache") == "pnpm"
                and not pnpm_setup_seen
            ):
                violations.append(job_name)

    assert not violations, "setup-node pnpm cache appears before pnpm setup in: " + ", ".join(violations)


def test_setup_installs_python_gate_dependencies_before_validators() -> None:
    """PyYAML must be installed before Python policy validators run."""
    workflow = _workflow()
    steps = workflow["jobs"]["setup"]["steps"]

    validator_idx = None
    pyyaml_idx = None
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        name = step.get("name", "")
        if "Validate policy enforcement matrix coverage" in name:
            validator_idx = i
        if "Enforce release P0 skip policy" in name:
            pyyaml_idx = i

    assert pyyaml_idx is not None, "Missing Python gate dependency install in setup"
    assert validator_idx is not None, "Missing policy validator step in setup"
    assert pyyaml_idx < validator_idx, (
        f"Python gate dependency install (step {pyyaml_idx}) must come before "
        f"policy validators (step {validator_idx})"
    )


def test_security_gate_installs_pytest_without_deleted_requirements_file() -> None:
    """Active security gate must not point at a deleted test requirements file."""
    workflow = _workflow()
    steps = workflow["jobs"]["security-isolation"]["steps"]

    install_steps = [
        step
        for step in steps
        if isinstance(step, dict) and "pip install" in step.get("run", "")
    ]
    assert any("pytest" in step.get("run", "") for step in install_steps)
    assert "requirements-test.txt" not in WORKFLOW.read_text(encoding="utf-8")


def test_launch_pipeline_does_not_reference_generated_bytecode() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    script_text = (REPO_ROOT / "scripts" / "ci" / "generate_launch_evidence_bundle.py").read_text(encoding="utf-8")

    assert "__pycache__" not in content
    assert ".pyc" not in content
    assert "__pycache__" not in script_text
    assert ".pyc" not in script_text
