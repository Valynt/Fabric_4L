"""Emit proposed-registration evidence for detected flaky tests.

This is the REGISTRATION stage of the three-stage flaky lifecycle
(detection -> registration -> exclusion). It only PROPOSES; it never edits the
register. Review + ownership assignment happens before any quarantine begins.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml


def _today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def _load_register_nodeids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    nodeids: set[str] = set()
    for entry in (raw or {}).get("entries", []) or []:
        nodeid = entry.get("nodeid") if isinstance(entry, dict) else None
        if nodeid:
            nodeids.add(str(nodeid))
    return nodeids


def _build_candidate(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "nodeid": record["nodeid"],
        "owner": None,
        "introduced_or_detected_on": _today(),
        "expires_on": None,
        "issue": None,
        "failure_evidence": {
            "attempts": record["attempts"],
            "passes": record["passes"],
            "failures": record["failures"],
            "pass_rate_percent": record["pass_rate_percent"],
            "consistency_percent": record["consistency_percent"],
            "severity": record["severity"],
        },
        "affected_gate": None,
        "retry_count": record["failures"],
        "status": "proposed",
    }


def emit_candidates(report: dict[str, Any], register_path: Path, output: Path) -> int:
    """Write proposed-candidate JSON; return the number of candidates."""
    registered = _load_register_nodeids(register_path)
    candidates = [
        _build_candidate(rec)
        for rec in report.get("flaky_tests", [])
        if rec.get("nodeid") not in registered
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    return len(candidates)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit flaky registration proposal evidence")
    parser.add_argument("--report", required=True, help="flakiness_tracker JSON report")
    parser.add_argument("--register", default="config/ci/test_skip_register.yaml")
    parser.add_argument("--output", default="reports/flaky-candidates.json")
    parser.add_argument("--exit-nonzero-if-proposals", action="store_true")
    args = parser.parse_args(argv)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    output = Path(args.output)
    count = emit_candidates(report, Path(args.register), output)
    print(f"Flaky registration candidates proposed: {count} -> {output}")
    if args.exit_nonzero_if_proposals and count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())