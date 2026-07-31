from __future__ import annotations

import json
from pathlib import Path

from scripts.ci.check_node_security_backports import check

ROOT = Path(__file__).resolve().parents[2]


def test_node_security_backports_are_pinned_and_complete() -> None:
    assert check() == []


def test_audit_exception_is_limited_to_backported_rsc_advisory() -> None:
    expected = "--ignore GHSA-qwww-vcr4-c8h2"
    workflow_commands = [
        ROOT / ".github/workflows/pr-checks.yml",
        ROOT / ".github/workflows/supply-chain-integrity.yml",
        ROOT / "scripts/production-readiness-check.sh",
    ]
    for path in workflow_commands:
        text = path.read_text(encoding="utf-8")
        assert expected in text, f"missing exact backport advisory exception in {path}"
        assert "check_node_security_backports.py" in text


def test_react_router_patch_tracks_upstream_security_commit() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    patch_path = package["pnpm"]["patchedDependencies"]["react-router@7.18.0"]
    patch = (ROOT / patch_path).read_text(encoding="utf-8")
    assert patch.count("potentialCSRFAttackError = error") >= 4
    assert patch.count('method: "GET"') >= 4
    assert patch.count("if (!potentialCSRFAttackError)") >= 4
