"""Tests for run_source_sbom_policy.py."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.ci.run_source_sbom_policy import (
    CLEAN_EXIT,
    VULNERABLE_EXIT,
    compare,
    enforce,
    parse_sarif_findings,
)


def make_sample_sarif(vulns: list[dict[str, str]]) -> dict:
    results = []
    rules = []
    for v in vulns:
        rule_id = v.get("id", "CVE-2026-0001")
        sev = v.get("severity", "high")
        level = "error" if sev in ("high", "critical") else "warning"
        rules.append(
            {
                "id": rule_id,
                "properties": {
                    "tags": [f"severity:{sev}"],
                },
            }
        )
        results.append(
            {
                "ruleId": rule_id,
                "level": level,
                "message": {"text": f"Vulnerability {rule_id} in package"},
                "locations": [
                    {"physicalLocation": {"artifactLocation": {"uri": "pkg/path"}}}
                ],
            }
        )

    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "grype",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def test_parse_sarif_findings() -> None:
    with TemporaryDirectory() as tmpdir:
        sarif_file = Path(tmpdir) / "test.sarif"
        data = make_sample_sarif(
            [
                {"id": "CVE-2026-1001", "severity": "high"},
                {"id": "CVE-2026-1002", "severity": "low"},
            ]
        )
        sarif_file.write_text(json.dumps(data), encoding="utf-8")

        findings = parse_sarif_findings(sarif_file, severity_cutoff="high")
        assert len(findings) == 1
        assert findings[0].rule_id == "CVE-2026-1001"


def test_enforce_clean() -> None:
    with TemporaryDirectory() as tmpdir:
        sarif_file = Path(tmpdir) / "clean.sarif"
        sarif_file.write_text(json.dumps(make_sample_sarif([])), encoding="utf-8")

        status = enforce(sarif_file, severity_cutoff="high")
        assert status == CLEAN_EXIT


def test_enforce_vulnerable() -> None:
    with TemporaryDirectory() as tmpdir:
        sarif_file = Path(tmpdir) / "vuln.sarif"
        data = make_sample_sarif([{"id": "CVE-2026-9999", "severity": "critical"}])
        sarif_file.write_text(json.dumps(data), encoding="utf-8")

        status = enforce(sarif_file, severity_cutoff="high")
        assert status == VULNERABLE_EXIT


def test_compare_delta_aware() -> None:
    with TemporaryDirectory() as tmpdir:
        baseline_file = Path(tmpdir) / "base.sarif"
        current_file = Path(tmpdir) / "curr.sarif"

        # Baseline has inherited CVE-2026-0001
        base_data = make_sample_sarif([{"id": "CVE-2026-0001", "severity": "high"}])
        baseline_file.write_text(json.dumps(base_data), encoding="utf-8")

        # Current has same inherited CVE-2026-0001 -> should pass!
        current_file.write_text(json.dumps(base_data), encoding="utf-8")
        status = compare(current_file, baseline_file, severity_cutoff="high")
        assert status == CLEAN_EXIT

        # Current adds branch-introduced CVE-2026-0002 -> should fail!
        curr_data = make_sample_sarif(
            [
                {"id": "CVE-2026-0001", "severity": "high"},
                {"id": "CVE-2026-0002", "severity": "high"},
            ]
        )
        current_file.write_text(json.dumps(curr_data), encoding="utf-8")
        status = compare(current_file, baseline_file, severity_cutoff="high")
        assert status == VULNERABLE_EXIT


def test_exception_handling() -> None:
    with TemporaryDirectory() as tmpdir:
        sarif_file = Path(tmpdir) / "vuln.sarif"
        exc_file = Path(tmpdir) / "exceptions.json"

        data = make_sample_sarif([{"id": "CVE-2026-5555", "severity": "critical"}])
        sarif_file.write_text(json.dumps(data), encoding="utf-8")

        exc_data = {
            "exceptions": [
                {
                    "cve_id": "CVE-2026-5555",
                    "layer": "layer1-ingestion",
                    "package": "some-pkg",
                    "severity": "critical",
                    "owner": "sec-team",
                    "ticket": "SEC-1234",
                    "justification": "Mitigated downstream",
                    "compensating_controls": "WAF enabled",
                    "created_at": "2026-08-01T00:00:00Z",
                    "expires_at": "2099-01-01T00:00:00Z",
                }
            ]
        }
        exc_file.write_text(json.dumps(exc_data), encoding="utf-8")

        status = enforce(
            sarif_file,
            severity_cutoff="high",
            exceptions_path=exc_file,
            layer="layer1-ingestion",
        )
        assert status == CLEAN_EXIT


def test_exception_rejection_missing_fields() -> None:
    with TemporaryDirectory() as tmpdir:
        sarif_file = Path(tmpdir) / "vuln.sarif"
        exc_file = Path(tmpdir) / "exceptions.json"

        data = make_sample_sarif([{"id": "CVE-2026-5555", "severity": "critical"}])
        sarif_file.write_text(json.dumps(data), encoding="utf-8")

        # Missing required governance fields like owner/ticket/compensating_controls
        exc_data = {
            "exceptions": [
                {
                    "cve_id": "CVE-2026-5555",
                    "layer": "layer1-ingestion",
                    "expires_at": "2099-01-01T00:00:00Z",
                }
            ]
        }
        exc_file.write_text(json.dumps(exc_data), encoding="utf-8")

        # Incomplete exception should be rejected and enforcement should fail
        status = enforce(
            sarif_file,
            severity_cutoff="high",
            exceptions_path=exc_file,
            layer="layer1-ingestion",
        )
        assert status == VULNERABLE_EXIT
