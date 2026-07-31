from __future__ import annotations

import json
from pathlib import Path

from scripts.ci.check_node_security_backports import check, validate_audit_report

ROOT = Path(__file__).resolve().parents[2]


def test_node_security_backports_are_pinned_and_complete() -> None:
    assert check() == []


def test_audit_exception_is_limited_to_backported_rsc_advisory() -> None:
    workflow_commands = [
        ROOT / ".github/workflows/pr-checks.yml",
        ROOT / ".github/workflows/supply-chain-integrity.yml",
        ROOT / "scripts/production-readiness-check.sh",
    ]
    for path in workflow_commands:
        text = path.read_text(encoding="utf-8")
        assert "--ignore GHSA-qwww-vcr4-c8h2" not in text
        assert "check_node_security_backports.py" in text
        assert "--audit" in text


def _audit_payload(*advisories: dict) -> dict:
    blocking = [
        advisory for advisory in advisories if advisory.get("severity") in {"high", "critical"}
    ]
    return {
        "advisories": {str(index): advisory for index, advisory in enumerate(advisories)},
        "metadata": {
            "vulnerabilities": {
                "high": sum(a.get("severity") == "high" for a in blocking),
                "critical": sum(a.get("severity") == "critical" for a in blocking),
            }
        },
    }


def test_audit_report_accepts_only_exact_patched_router_advisory() -> None:
    payload = _audit_payload(
        {
            "severity": "high",
            "github_advisory_id": "GHSA-qwww-vcr4-c8h2",
            "module_name": "react-router",
            "findings": [{"version": "7.18.0"}],
        }
    )
    assert validate_audit_report(payload) == []


def test_audit_report_rejects_other_high_advisory() -> None:
    payload = _audit_payload(
        {
            "severity": "high",
            "github_advisory_id": "GHSA-xxxx-yyyy-zzzz",
            "module_name": "example",
            "findings": [{"version": "1.0.0"}],
        }
    )
    assert validate_audit_report(payload) == [
        "unpatched high Node advisory: GHSA-xxxx-yyyy-zzzz (example)"
    ]


def test_audit_report_rejects_wrong_router_version_and_scanner_errors() -> None:
    payload = _audit_payload(
        {
            "severity": "high",
            "github_advisory_id": "GHSA-qwww-vcr4-c8h2",
            "module_name": "react-router",
            "findings": [{"version": "7.17.0"}],
        }
    )
    assert validate_audit_report(payload)
    assert validate_audit_report({"error": "registry unavailable"}) == [
        "pnpm audit failed to execute: registry unavailable"
    ]


def test_react_router_patch_tracks_upstream_security_commit() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    patch_path = package["pnpm"]["patchedDependencies"]["react-router@7.18.0"]
    patch = (ROOT / patch_path).read_text(encoding="utf-8")
    assert patch.count("potentialCSRFAttackError = error") >= 4
    assert patch.count('method: "GET"') >= 4
    assert patch.count("if (!potentialCSRFAttackError)") >= 4
