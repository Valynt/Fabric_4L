import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "dependency-scan.yml"


def _scan_python_job() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    return text.split("  scan-python:", 1)[1].split("  scan-node:", 1)[0]


def _scan_node_job() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "  # =========================================================================\n  # CONTAINER IMAGE SCAN"
    return text.split("  scan-node:", 1)[1].split(marker, 1)[0]


def test_scan_python_uses_pinned_uv_and_focused_helper() -> None:
    job = _scan_python_job()

    assert "astral-sh/setup-uv@" in job
    assert 'version: "0.11.6"' in job
    assert "uv tool install pip-audit==" in job
    assert "scripts/ci/run_pip_audit.py scan" in job
    assert not re.search(r"^\s*pip-audit\s", job, flags=re.MULTILINE)
    assert "python -m pip install" not in job
    assert "pip-audit --requirement" not in job


def test_scan_python_propagates_status_through_uploads_to_final_enforcement() -> None:
    job = _scan_python_job()
    scan_index = job.index("id: audit")
    artifact_index = job.index("uses: actions/upload-artifact@")
    sarif_index = job.index("uses: github/codeql-action/upload-sarif@")
    enforce_index = job.index("scripts/ci/run_pip_audit.py enforce")

    assert scan_index < artifact_index < enforce_index
    assert scan_index < sarif_index < enforce_index
    assert 'echo "status=$status" >> "$GITHUB_OUTPUT"' in job
    assert "test -s \"$ARTIFACT_DIR/diagnostic.json\"" in job
    assert job.count("if: always()") >= 3
    assert "--expected-status '${{ steps.audit.outputs.status }}'" in job



def test_scan_python_compares_pr_audit_against_base_before_failing() -> None:
    job = _scan_python_job()

    assert "fetch-depth: 0" in job
    assert "git fetch --no-tags --depth=1 origin" in job
    assert "git worktree add" in job
    assert "artifacts/pip-audit-base/${{ matrix.python.service }}" in job
    assert "scripts/ci/run_pip_audit.py compare" in job
    assert "--baseline-diagnostic" in job
    assert "--baseline-expected-status" in job


def test_scan_python_keeps_base_worktree_until_after_compare() -> None:
    job = _scan_python_job()
    base_index = job.index("id: base_audit")
    enforce_index = job.index("Enforce dependency vulnerability policy")
    cleanup_index = job.index("Cleanup base dependency audit worktree")

    assert 'echo "worktree=$base_worktree" >> "$GITHUB_OUTPUT"' in job
    assert "trap cleanup EXIT" not in job
    assert base_index < enforce_index < cleanup_index

def test_scan_python_uploads_all_evidence_and_fails_closed() -> None:
    job = _scan_python_job()

    for evidence in ("requirements.txt", "report.json", "report.sarif", "diagnostic.json"):
        assert evidence in job
    assert "if-no-files-found: error" in job
    assert "|| true" not in job
    assert "{\"dependencies\":[]}" not in job
    assert "severity" not in job.lower()
    assert "assuming clean" not in job.lower()
    assert "Evaluate severity threshold" not in job
    assert "Enforce dependency vulnerability policy" in job


def test_scan_node_compares_pr_audit_against_base_before_failing() -> None:
    job = _scan_node_job()

    assert "fetch-depth: 0" in job
    assert "pnpm-audit-base.json" in job
    assert "pnpm-audit.json" in job
    assert "Branch-introduced vulnerability" in job
    assert "Inherited vulnerability" in job
    assert "git worktree add" in job
