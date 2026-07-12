from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(".github/workflows/backend-integrated-reproducibility.yml")


def workflow_text() -> str:
    assert WORKFLOW.exists(), f"missing workflow: {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def test_backend_integrated_reproducibility_workflow_is_manual_and_requires_sha():
    content = workflow_text()

    assert "workflow_dispatch:" in content
    assert "release_candidate_sha:" in content
    assert "required: true" in content
    assert "ref: ${{ inputs.release_candidate_sha }}" in content


def test_backend_integrated_reproducibility_workflow_invokes_hardened_runner():
    content = workflow_text()

    assert "python scripts/ci/run_backend_integrated_reproducibility.py" in content
    assert "--environment ci" in content
    assert '--release-candidate-sha "$RELEASE_CANDIDATE_SHA"' in content
    assert "--compose-file docker-compose.live.yml" in content
    assert "--compose-file .tmp/docker-compose.backend-integrated-ci.override.yml" in content
    assert "--retry-classification" in content


def test_backend_integrated_reproducibility_workflow_provides_ci_metadata_and_secret_preflight():
    content = workflow_text()

    assert "Install Python validation dependencies" in content
    assert "python -m pip install PyYAML" in content
    assert "RELEASE_CANDIDATE_SHA: ${{ inputs.release_candidate_sha }}" in content
    assert "GITHUB_RUN_ID" not in content or "${{ github.run_id }}" in content or "github.run_id" in content
    assert "Validate required runtime secrets" in content
    for required_name in (
        "JWT_SECRET",
        "SERVICE_AUTH_SECRET",
        "API_KEY_HMAC_SECRET",
        "CREDENTIALS_MASTER_KEY",
        "NEO4J_PASSWORD",
        "MINIO_ROOT_USER",
        "MINIO_ROOT_PASSWORD",
    ):
        assert required_name in content


def test_backend_integrated_reproducibility_workflow_retains_artifacts_and_logs():
    content = workflow_text()

    assert "Capture Docker service logs" in content
    assert "artifacts/live-workflow-validation/logs/docker-compose.log" in content
    assert "actions/upload-artifact@v4" in content
    assert "artifacts/live-workflow-validation/**" in content
    assert "if-no-files-found: error" in content


def test_backend_integrated_reproducibility_workflow_fails_closed_and_keeps_mocks_disabled():
    content = workflow_text()

    assert "continue-on-error" not in content
    assert "git rev-parse" not in content
    assert "VITE_USE_MOCKS: \"true\"" not in content
    assert "VITE_ENABLE_MOCK_FALLBACK: \"true\"" not in content
    assert "MSW: \"true\"" not in content
    assert "MOCKS_ENABLED: \"true\"" not in content
