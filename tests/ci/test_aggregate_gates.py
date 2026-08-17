from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "ci"


def _load_module(name: str):
    spec = spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


aggregate_gate = _load_module("aggregate_gate")
change_risk = _load_module("check_change_risk_approval")

BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40


def _needs(**results: str) -> str:
    return json.dumps({job: {"result": result} for job, result in results.items()})


# --- aggregate_gate: intended allowed behavior ---


def test_aggregate_gate_passes_when_all_children_succeed() -> None:
    assert aggregate_gate.main(["--needs-json", _needs(a="success", b="success")]) == 0


def test_aggregate_gate_passes_confirmed_safe_skip(monkeypatch) -> None:
    monkeypatch.setenv("SCOPE_SAFE_A", "true")
    assert (
        aggregate_gate.main(
            [
                "--needs-json",
                _needs(a="skipped", b="success"),
                "--skip-safe",
                "a=SCOPE_SAFE_A",
            ]
        )
        == 0
    )


# --- aggregate_gate: intended denied behavior ---


def test_aggregate_gate_fails_when_child_fails() -> None:
    assert aggregate_gate.main(["--needs-json", _needs(a="success", b="failure")]) == 1


def test_aggregate_gate_fails_when_child_cancelled() -> None:
    assert aggregate_gate.main(["--needs-json", _needs(a="cancelled")]) == 1


def test_aggregate_gate_fails_on_skip_without_confirmation() -> None:
    assert aggregate_gate.main(["--needs-json", _needs(a="skipped")]) == 1


def test_aggregate_gate_fails_on_skip_when_confirmation_env_not_true(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SCOPE_SAFE_A", "false")
    assert (
        aggregate_gate.main(
            ["--needs-json", _needs(a="skipped"), "--skip-safe", "a=SCOPE_SAFE_A"]
        )
        == 1
    )


# --- check_change_risk_approval: trusted GitHub evidence ---


def _github_api_fixture(
    *, author="alice", review_state="APPROVED", decision="APPROVED", files=None
):
    def fake(arguments):
        endpoint = arguments[0]
        if endpoint == "repos/acme/repo/pulls/7":
            return {"user": {"login": author}}
        if endpoint.endswith("/reviews"):
            return [{"user": {"login": "bob"}, "state": review_state}]
        if endpoint.endswith("/files"):
            return [{"filename": name} for name in (files or [])]
        if endpoint == "graphql":
            return {
                "data": {"repository": {"pullRequest": {"reviewDecision": decision}}}
            }
        raise AssertionError(arguments)

    return fake


def _github_event(tmp_path: Path) -> Path:
    path = tmp_path / "event.json"
    path.write_text(
        json.dumps(
            {"number": 7, "pull_request": {"number": 7, "head": {"sha": HEAD_SHA}}}
        )
    )
    return path


def _run_github(tmp_path: Path, monkeypatch, api) -> int:
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/repo")
    monkeypatch.setattr(change_risk, "_gh_json", api)
    return change_risk.main(["--event-path", str(_github_event(tmp_path))])


def test_change_risk_gate_accepts_authenticated_github_approval(
    tmp_path, monkeypatch
) -> None:
    assert (
        _run_github(tmp_path, monkeypatch, _github_api_fixture(files=["src/app.py"]))
        == 0
    )


def test_change_risk_gate_rejects_self_approval(tmp_path, monkeypatch) -> None:
    assert _run_github(tmp_path, monkeypatch, _github_api_fixture(author="bob")) == 1


def test_change_risk_gate_rejects_dismissed_approval(tmp_path, monkeypatch) -> None:
    assert (
        _run_github(
            tmp_path, monkeypatch, _github_api_fixture(review_state="DISMISSED")
        )
        == 1
    )


def test_change_risk_gate_requires_github_approved_decision_for_high_risk_files(
    tmp_path, monkeypatch
) -> None:
    api = _github_api_fixture(
        decision="REVIEW_REQUIRED", files=[".github/workflows/gate.yml"]
    )
    assert _run_github(tmp_path, monkeypatch, api) == 1


def test_merge_group_resolves_prs_from_synthetic_commit(monkeypatch) -> None:
    monkeypatch.setattr(
        change_risk, "_gh_json", lambda args: [{"number": 8}, {"number": 7}]
    )
    assert change_risk._pull_numbers("merge_group", {}, "acme/repo", HEAD_SHA) == [7, 8]
