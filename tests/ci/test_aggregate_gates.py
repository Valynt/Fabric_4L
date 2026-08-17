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
            ["--needs-json", _needs(a="skipped", b="success"), "--skip-safe", "a=SCOPE_SAFE_A"]
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


def test_aggregate_gate_fails_on_skip_when_confirmation_env_not_true(monkeypatch) -> None:
    monkeypatch.setenv("SCOPE_SAFE_A", "false")
    assert (
        aggregate_gate.main(["--needs-json", _needs(a="skipped"), "--skip-safe", "a=SCOPE_SAFE_A"])
        == 1
    )


# --- check_change_risk_approval helpers ---


def _event_payload(tmp_path: Path, name: str = "pull_request") -> Path:
    if name == "pull_request":
        payload = {"pull_request": {"base": {"sha": BASE_SHA}, "head": {"sha": HEAD_SHA}}}
    else:
        payload = {"merge_group": {"base_sha": BASE_SHA, "head_sha": HEAD_SHA}}
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _artifact(
    tmp_path: Path,
    *,
    head_sha: str = HEAD_SHA,
    base_sha: str = BASE_SHA,
    author: str = "alice",
    reviewer: str = "bob",
    findings: list | None = None,
    surfaces: list[str] | None = None,
    approvals: list | None = None,
) -> Path:
    artifact_dir = tmp_path / "reviews"
    artifact_dir.mkdir(exist_ok=True)
    artifact = {
        "schema_version": 1,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "author": author,
        "reviewer": reviewer,
        "high_risk_surfaces_touched": surfaces if surfaces is not None else [],
        "codeowner_approvals": approvals if approvals is not None else [],
        "findings": findings if findings is not None else [],
    }
    (artifact_dir / f"{head_sha}.json").write_text(json.dumps(artifact), encoding="utf-8")
    return artifact_dir


def _run(tmp_path: Path, monkeypatch, artifact_dir: Path, event_name: str = "pull_request") -> int:
    monkeypatch.setenv("GITHUB_EVENT_NAME", event_name)
    return change_risk.main(
        ["--artifact-dir", str(artifact_dir), "--event-path", str(_event_payload(tmp_path, event_name))]
    )


# --- check_change_risk_approval: intended allowed behavior ---


def test_change_risk_gate_accepts_valid_artifact(tmp_path, monkeypatch) -> None:
    artifact_dir = _artifact(
        tmp_path,
        findings=[{"id": "F-1", "severity": "P2", "status": "open"}],
        surfaces=[".github/workflows/**"],
        approvals=[{"surface": ".github/workflows/**", "approver": "carol"}],
    )
    assert _run(tmp_path, monkeypatch, artifact_dir) == 0


def test_change_risk_gate_accepts_merge_group_event(tmp_path, monkeypatch) -> None:
    artifact_dir = _artifact(tmp_path)
    assert _run(tmp_path, monkeypatch, artifact_dir, event_name="merge_group") == 0


# --- check_change_risk_approval: intended denied behavior ---


def test_change_risk_gate_fails_closed_when_artifact_missing(tmp_path, monkeypatch) -> None:
    assert _run(tmp_path, monkeypatch, tmp_path / "reviews") == 1


def test_change_risk_gate_rejects_unresolved_p0(tmp_path, monkeypatch) -> None:
    artifact_dir = _artifact(tmp_path, findings=[{"id": "F-9", "severity": "P0", "status": "open"}])
    assert _run(tmp_path, monkeypatch, artifact_dir) == 1


def test_change_risk_gate_rejects_reviewer_who_authored_patch(tmp_path, monkeypatch) -> None:
    artifact_dir = _artifact(tmp_path, author="alice", reviewer="alice")
    assert _run(tmp_path, monkeypatch, artifact_dir) == 1


def test_change_risk_gate_rejects_sha_mismatch(tmp_path, monkeypatch) -> None:
    artifact_dir = _artifact(tmp_path, base_sha="c" * 40)
    assert _run(tmp_path, monkeypatch, artifact_dir) == 1


def test_change_risk_gate_rejects_unapproved_high_risk_surface(tmp_path, monkeypatch) -> None:
    artifact_dir = _artifact(tmp_path, surfaces=["k8s/**"], approvals=[])
    assert _run(tmp_path, monkeypatch, artifact_dir) == 1
