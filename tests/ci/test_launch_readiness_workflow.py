from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "launch-readiness.yml"


def _workflow() -> dict:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_launch_readiness_workflow_is_stage_gated() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]

    assert "stage-1-baseline" in jobs
    assert "stage-2-frontend-tests" in jobs
    assert "stage-2-journey-smoke" in jobs
    assert "stage-3-contract-security" in jobs
    assert "stage-4-evidence-archive" in jobs
    assert "stage-4-readiness-10" in jobs
    assert "stage-5-staging-evidence" in jobs
    assert jobs["stage-2-frontend-tests"]["needs"] == "stage-1-baseline"
    assert set(jobs["stage-3-contract-security"]["needs"]) == {"stage-2-frontend-tests", "stage-2-journey-smoke"}
    assert jobs["stage-4-evidence-archive"]["needs"] == "stage-3-contract-security"
    assert jobs["stage-4-readiness-10"]["needs"] == "stage-4-evidence-archive"
    assert jobs["stage-5-staging-evidence"]["needs"] == "stage-4-readiness-10"


def test_launch_readiness_workflow_is_artifact_only_no_ci_push() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    workflow = _workflow()

    assert workflow["permissions"]["contents"] == "read"
    assert "contents: write" not in content
    assert "git push" not in content
    assert "git commit" not in content
    assert "upload-artifact" in content
    assert "generate_launch_evidence_bundle.py" in content


def test_launch_readiness_workflow_runs_blocking_readiness_10_gate() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    workflow = _workflow()
    job = workflow["jobs"]["stage-4-readiness-10"]

    assert job["needs"] == "stage-4-evidence-archive"
    assert "pnpm readiness:10" in content
    assert "pnpm readiness:10 || true" not in content
    assert "artifacts/readiness-10/**" in content


def test_launch_readiness_workflow_uses_expected_stage_inputs() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    for stage in ("baseline", "local_quality", "contract_security", "evidence_archive", "staging"):
        assert stage in content
    assert "--up-to-stage evidence_archive" in content
    assert "environment: staging" in content


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


def test_stage_1_installs_python_gate_dependencies_before_validators() -> None:
    """Regression for PR #347: PyYAML must be installed before launch gate validators run."""
    workflow = _workflow()
    steps = workflow["jobs"]["stage-1-baseline"]["steps"]

    validator_idx = None
    pyyaml_idx = None
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        name = step.get("name", "")
        if "Launch gate validators" in name:
            validator_idx = i
        if "Install Python gate dependencies" in name:
            pyyaml_idx = i

    assert pyyaml_idx is not None, "Missing 'Install Python gate dependencies' step in stage-1-baseline"
    assert validator_idx is not None, "Missing 'Launch gate validators' step in stage-1-baseline"
    assert pyyaml_idx < validator_idx, (
        f"Python gate dependency install (step {pyyaml_idx}) must come before "
        f"launch validators (step {validator_idx})"
    )


def test_stage_3_uses_existing_requirements_file() -> None:
    """Regression for PR #347: Stage 3 must reference an existing requirements file."""
    workflow = _workflow()
    steps = workflow["jobs"]["stage-3-contract-security"]["steps"]

    req_step = None
    for step in steps:
        if not isinstance(step, dict):
            continue
        name = step.get("name", "")
        if "Install test dependencies" in name:
            req_step = step
            break

    assert req_step is not None, "Missing test dependency install step in stage-3-contract-security"
    run_cmd = req_step.get("run", "")
    assert "tests/requirements-test.txt" in run_cmd, (
        f"Stage 3 must use tests/requirements-test.txt, got: {run_cmd}"
    )
    assert (REPO_ROOT / "tests" / "requirements-test.txt").exists(), (
        "tests/requirements-test.txt must exist on disk"
    )


def test_launch_pipeline_does_not_reference_generated_bytecode() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    script_text = (REPO_ROOT / "scripts" / "ci" / "generate_launch_evidence_bundle.py").read_text(encoding="utf-8")

    assert "__pycache__" not in content
    assert ".pyc" not in content
    assert "__pycache__" not in script_text
    assert ".pyc" not in script_text
