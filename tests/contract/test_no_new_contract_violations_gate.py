from pathlib import Path
from subprocess import CompletedProcess

from scripts.ci.enforce_no_new_contract_violations import scan_file

from scripts.ci import enforce_no_new_contract_violations as gate


def test_scan_file_detects_patterns(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text("raise Exception('x')\njson.loads(payload)\n")

    found = scan_file(sample, ["raise Exception", "json.loads(", "navigate("])

    assert "raise Exception" in found
    assert "json.loads(" in found
    assert "navigate(" not in found


def test_scan_file_handles_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.py"
    assert scan_file(missing, ["json.loads("]) == []


def test_changed_files_falls_back_to_diff_tree_when_base_refs_are_unavailable(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> CompletedProcess[str]:
        calls.append(args)
        if args[:1] == ["diff-tree"]:
            return CompletedProcess(args, 0, stdout="services/api/main.py\n", stderr="")
        return CompletedProcess(args, 128, stdout="", stderr="unknown revision")

    monkeypatch.setattr(gate, "_run_git_name_only", fake_run)

    assert gate.changed_files("origin/main") == ["services/api/main.py"]
    assert calls[-1] == ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"]


def test_changed_files_scans_all_tracked_files_when_diff_history_is_unavailable(monkeypatch) -> None:
    def fake_run(args: list[str]) -> CompletedProcess[str]:
        if args == ["ls-files"]:
            return CompletedProcess(args, 0, stdout="contracts/openapi/root.yaml\nscripts/ci/gate.py\n", stderr="")
        return CompletedProcess(args, 128, stdout="", stderr="unknown revision")

    monkeypatch.setattr(gate, "_run_git_name_only", fake_run)

    assert gate.changed_files("origin/main") == ["contracts/openapi/root.yaml", "scripts/ci/gate.py"]

def test_contract_compliance_uses_canonical_python_gates_instead_of_broad_grep() -> None:
    workflow = Path(".github/workflows/contract-compliance.yml").read_text(encoding="utf-8")

    assert "python scripts/ci/platform_contract_lint.py" in workflow
    assert "python scripts/ci/enforce_no_new_contract_violations.py" in workflow
    assert "grep -rnE" not in workflow

def test_frontend_contract_lint_is_diff_scoped_to_changed_typescript() -> None:
    workflow = Path(".github/workflows/contract-compliance.yml").read_text(encoding="utf-8")

    assert "No changed frontend TypeScript files to contract-lint." in workflow
    assert "git diff --name-only" in workflow
    assert 'pnpm exec eslint "${changed[@]}"' in workflow


def test_canonical_example_tool_declares_scope_key_used_in_metadata() -> None:
    source = Path("examples/canonical/tools/example-tool.ts").read_text(encoding="utf-8")

    assert "const scopeKey = ctx.tenant_context.tenant_id;" in source
    assert "const tenantId = ctx.tenant_context.tenant_id;" not in source


def test_contract_compliance_tenant_boundary_job_installs_root_pytest_policy_dependencies() -> None:
    workflow = Path(".github/workflows/contract-compliance.yml").read_text(encoding="utf-8")

    assert "pip install -r tests/requirements-test.lock" in workflow
