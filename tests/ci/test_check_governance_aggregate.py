from __future__ import annotations

from pathlib import Path

from scripts.ci import check_governance as gov


def _pass(cmd: list[str]) -> dict:
    return {"command": " ".join(cmd), "status": "pass", "exit_code": 0, "output": "ok"}


def _fail(cmd: list[str]) -> dict:
    return {"command": " ".join(cmd), "status": "fail", "exit_code": 1, "output": "violation"}


def _error(cmd: list[str]) -> dict:
    return {"command": " ".join(cmd), "status": "error", "exit_code": None, "output": "boom"}


def test_status_from_exit_maps_traceback_to_error() -> None:
    assert gov._status_from_exit(0, "") == "pass"
    assert gov._status_from_exit(1, "some violation") == "fail"
    assert gov._status_from_exit(1, "Traceback (most recent call last)") == "error"


def test_aggregate_precedence_error_over_fail_over_pass() -> None:
    assert gov._aggregate([{"status": "pass"}, {"status": "pass"}]) == "pass"
    assert gov._aggregate([{"status": "pass"}, {"status": "fail"}]) == "fail"
    assert gov._aggregate([{"status": "fail"}, {"status": "error"}]) == "error"


def test_build_specs_has_five_unique_check_ids() -> None:
    specs = gov.build_specs()
    ids = [s["check_id"] for s in specs]
    assert len(ids) == len(set(ids)) == 5
    assert "check-shared-duplication" in ids
    assert "check-governance-baseline" in ids


def test_run_governance_passes_with_stable_envelope_schema() -> None:
    report = gov.run_governance(runner=_pass, only="check-import-cycles")
    assert report["check_id"] == "check-governance"
    assert report["schema_version"] == 1
    assert report["status"] == "pass"
    assert report["sub_checks"][0]["check_id"] == "check-import-cycles"
    sub = report["sub_checks"][0]
    for key in ("check_id", "name", "scope", "status", "baseline_present", "details", "violations"):
        assert key in sub


def test_run_governance_reports_fail_on_violation() -> None:
    report = gov.run_governance(runner=_fail, only="check-architecture-boundaries")
    assert report["status"] == "fail"


def test_run_governance_reports_error_on_broken_subcheck() -> None:
    report = gov.run_governance(runner=_error, only="check-ownership-registry")
    assert report["status"] == "error"


def test_render_markdown_lists_every_check() -> None:
    report = gov.run_governance(runner=_pass, only="check-shared-duplication")
    md = gov.render_markdown(report)
    assert "check-shared-duplication" in md
    assert report["status"].upper() in md


def test_exit_code_mapping() -> None:
    assert gov._exit_code_for("pass") == 0
    assert gov._exit_code_for("fail") == 1
    assert gov._exit_code_for("error") == 2


def _regenerable_runner(content: str):
    def runner(cmd: list[str]) -> dict:
        if "--update" in cmd and "--baseline" in cmd:
            target = Path(cmd[cmd.index("--baseline") + 1])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return {"command": " ".join(cmd), "status": "pass", "exit_code": 0, "output": "ok"}

    return runner


def test_duplication_regenerable_passes_when_baseline_is_current() -> None:
    checked_in = gov.REPO_ROOT / "config/ci/shared_duplication_baseline.json"
    content = checked_in.read_text(encoding="utf-8")
    result = gov._duplication_regenerable(_regenerable_runner(content))
    assert result["status"] == "pass"


def test_duplication_regenerable_fails_on_baseline_drift() -> None:
    result = gov._duplication_regenerable(_regenerable_runner("{}\n"))
    assert result["status"] == "fail"
