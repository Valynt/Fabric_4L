import json
from pathlib import Path

from scripts.ci.emit_flaky_candidates import emit_candidates


def _report():
    return {
        "metadata": {"commit_sha": "deadbeef"},
        "flaky_tests": [
            {
                "nodeid": "tests/app/test_order.py::test_total",
                "suite": "app",
                "marker": "flaky",
                "attempts": 10,
                "passes": 7,
                "failures": 3,
                "pass_rate_percent": 70.0,
                "consistency_percent": 70.0,
                "severity": "warning",
                "avg_duration_ms": 12.5,
            }
        ],
    }


def test_emit_candidates_marks_proposed_and_requires_owner(tmp_path):
    reg = tmp_path / "reg.yaml"
    reg.write_text("entries: []\n", encoding="utf-8")
    out = tmp_path / "candidates.json"
    count = emit_candidates(_report(), reg, out)
    assert count == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    cand = data[0]
    assert cand["nodeid"] == "tests/app/test_order.py::test_total"
    assert cand["status"] == "proposed"
    assert cand["owner"] is None
    assert cand["issue"] is None
    assert cand["retry_count"] == 3
    assert cand["failure_evidence"]["attempts"] == 10
    assert cand["failure_evidence"]["passes"] == 7
    assert cand["failure_evidence"]["failures"] == 3


def test_emit_candidates_skips_already_registered(tmp_path):
    reg = tmp_path / "reg.yaml"
    reg.write_text(
        """
entries:
  - id: flaky-order-total
    path_pattern: "tests/app/test_order.py"
    marker: flaky
    reason_pattern: "test_total"
    nodeid: "tests/app/test_order.py::test_total"
    owner: team-app
    reason: "intermittent timezone ordering"
    expires_on: "2026-12-31"
    severity: warning
    launch_gate: excluded
    classification: quarantine
    disposition: track
    introduced_or_detected_on: "2026-05-01"
    issue: "https://github.com/Valynt/Fabric_4L/issues/1"
    failure_evidence: {attempts: 10, passes: 7, failures: 3}
    affected_gate: graph-module-tests
    retry_count: 3
    status: active
    remediation: {ticket_id: "ABC-1", work_item: "fix order total", due_on: "2026-11-01"}
""",
        encoding="utf-8",
    )
    out = tmp_path / "candidates.json"
    count = emit_candidates(_report(), reg, out)
    assert count == 0
    assert out.exists() is False or json.loads(out.read_text()) == []
