from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci" / "check_workflow_task_parity.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_workflow_task_parity", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parity = _load_module()


def _write_workflow(directory: Path, name: str, run_blocks: list[str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    steps = [{"name": f"step-{index}", "run": run} for index, run in enumerate(run_blocks)]
    document = {"name": name, "jobs": {"checks": {"runs-on": "ubuntu-latest", "steps": steps}}}
    path = directory / name
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def test_extracts_supported_task_forms_and_ignores_non_executable_text() -> None:
    run = r"""
      # make ignored-comment
      echo "make ignored-echo"
      printf '%s\n' 'fabric ignored-printf'
      make alpha FLAG="two words" \
        MODE=strict
      make beta && fabric run gamma --mode fast
      pnpm run fabric -- delta VALUE=1
      pnpm exec fabric epsilon
      ./tools/fabric-cli/fabric zeta
      cat <<'EOF'
      make ignored-heredoc
      fabric ignored-heredoc-too
      EOF
    """

    assert parity.extract_task_commands(run) == [
        "make alpha 'FLAG=two words' MODE=strict",
        "make beta",
        "fabric gamma --mode fast",
        "fabric delta VALUE=1",
        "fabric epsilon",
        "fabric zeta",
    ]


def test_loads_run_steps_and_matrix_commands_in_workflow_order(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        yaml.safe_dump(
            {
                "jobs": {
                    "first": {
                        "strategy": {
                            "matrix": {
                                "gate": [
                                    {"id": "lint", "command": "make matrix-lint"},
                                    {"id": "test", "command": "echo ignored"},
                                ]
                            }
                        },
                        "steps": [{"run": "make first"}, {"run": "echo make ignored"}],
                    },
                    "second": {"steps": [{"run": "pnpm run fabric -- second"}]},
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assert parity.load_workflow_task_commands(workflow) == [
        "make matrix-lint",
        "make first",
        "fabric second",
    ]


def test_equivalent_fabric_syntaxes_have_parity(tmp_path: Path) -> None:
    github = tmp_path / ".github" / "workflows"
    depot = tmp_path / ".depot" / "workflows"
    _write_workflow(github, "checks.yml", ["fabric run verify --profile strict"])
    _write_workflow(depot, "checks.yml", ["pnpm run fabric -- verify --profile strict"])

    assert parity.compare_workflow_directories(github, depot) == []


def test_make_and_fabric_remain_distinct_engines(tmp_path: Path) -> None:
    github = tmp_path / ".github" / "workflows"
    depot = tmp_path / ".depot" / "workflows"
    _write_workflow(github, "checks.yml", ["make verify PROFILE=strict"])
    _write_workflow(depot, "checks.yml", ["pnpm run fabric -- verify PROFILE=strict"])

    errors = parity.compare_workflow_directories(github, depot)

    assert len(errors) == 1
    assert "-make verify PROFILE=strict" in errors[0]
    assert "+fabric verify PROFILE=strict" in errors[0]


def test_reports_ordered_command_drift_with_diff(tmp_path: Path) -> None:
    github = tmp_path / ".github" / "workflows"
    depot = tmp_path / ".depot" / "workflows"
    _write_workflow(github, "checks.yml", ["make lint\nmake test"])
    _write_workflow(depot, "checks.yml", ["make test\nmake lint"])

    errors = parity.compare_workflow_directories(github, depot)

    assert len(errors) == 1
    assert "checks.yml: ordered task commands differ" in errors[0]
    assert "+make test" in errors[0]
    assert "-make test" in errors[0]


def test_reports_unpaired_workflows_from_both_providers(tmp_path: Path) -> None:
    github = tmp_path / ".github" / "workflows"
    depot = tmp_path / ".depot" / "workflows"
    _write_workflow(github, "github-only.yml", ["make verify"])
    _write_workflow(depot, "depot-only.yml", ["make verify"])

    errors = parity.compare_workflow_directories(github, depot)

    assert len(errors) == 2
    assert any(
        "missing Depot workflow pair" in error and "github-only.yml" in error for error in errors
    )
    assert any(
        "missing GitHub workflow pair" in error and "depot-only.yml" in error for error in errors
    )


def test_cli_returns_nonzero_with_clear_diagnostics(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    github = tmp_path / ".github" / "workflows"
    depot = tmp_path / ".depot" / "workflows"
    _write_workflow(github, "checks.yml", ["make lint"])
    _write_workflow(depot, "checks.yml", ["make test"])

    assert parity.main(["--github-dir", str(github), "--depot-dir", str(depot)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Workflow task-command parity check failed" in captured.err
    assert "ordered task commands differ" in captured.err
