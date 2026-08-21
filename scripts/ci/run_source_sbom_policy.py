#!/usr/bin/env python3
"""Enforce delta-aware vulnerability policies on SARIF scan outputs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CLEAN_EXIT = 0
VULNERABLE_EXIT = 1
OPERATIONAL_ERROR_EXIT = 2

SEVERITY_ORDER = {
    "low": 1,
    "medium": 2,
    "moderate": 2,
    "high": 3,
    "critical": 4,
}


def parse_sarif_findings(sarif_path: Path, severity_cutoff: str = "high") -> list[dict[str, Any]]:
    """Extract findings meeting or exceeding severity cutoff from SARIF file."""
    if not sarif_path.exists() or sarif_path.stat().st_size == 0:
        return []

    try:
        data = json.loads(sarif_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse SARIF file {sarif_path}: {exc}") from exc

    min_sev_level = SEVERITY_ORDER.get(severity_cutoff.lower(), 3)
    findings: list[dict[str, Any]] = []

    for run in data.get("runs", []):
        rules_map = {}
        for rule in run.get("tool", {}).get("driver", {}).get("rules", []):
            rule_id = rule.get("id")
            if rule_id:
                # Grype / Trivy embed security-severity or tags
                sec_score = rule.get("properties", {}).get("security-severity")
                tags = rule.get("properties", {}).get("tags", [])
                rules_map[rule_id] = {
                    "rule": rule,
                    "sec_score": sec_score,
                    "tags": tags,
                }

        for result in run.get("results", []):
            rule_id = result.get("ruleId") or "UNKNOWN"
            level = result.get("level", "warning")
            message = result.get("message", {}).get("text", "")
            
            # Extract package name from message or locations if available
            locations = result.get("locations", [])
            location_str = ""
            if locations:
                loc = locations[0].get("physicalLocation", {}).get("artifactLocation", {}).get("uri", "")
                location_str = loc

            # Determine severity
            severity = "medium"
            if level == "error":
                severity = "high"
            
            rule_info = rules_map.get(rule_id, {})
            for tag in rule_info.get("tags", []):
                if tag.startswith("severity:"):
                    severity = tag.split(":", 1)[1].lower()

            if severity.lower() in ("critical", "crit"):
                severity = "critical"
            elif severity.lower() in ("high",):
                severity = "high"

            # Check cutoff
            sev_level = SEVERITY_ORDER.get(severity, 2)
            if sev_level >= min_sev_level:
                findings.append({
                    "rule_id": rule_id,
                    "severity": severity,
                    "message": message,
                    "location": location_str,
                    "signature": f"{rule_id}:{location_str}:{message[:50]}",
                })

    return findings


def load_exceptions(exceptions_path: Path | None) -> list[dict[str, Any]]:
    """Load valid (non-expired) vulnerability exceptions from JSON or YAML."""
    if not exceptions_path or not exceptions_path.exists():
        return []

    try:
        content = exceptions_path.read_text(encoding="utf-8")
        if exceptions_path.suffix in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(content) or {}
            except ImportError:
                # Basic line parsing fallback if pyyaml not installed
                return []
        else:
            data = json.loads(content)
    except Exception as exc:
        print(f"Warning: Failed to load exceptions from {exceptions_path}: {exc}", file=sys.stderr)
        return []

    exceptions = data.get("exceptions", [])
    valid_exceptions = []
    now = datetime.now(timezone.utc)

    for exc in exceptions:
        cve = exc.get("cve_id") or exc.get("id")
        expires_at_str = exc.get("expires_at")
        if not cve:
            continue
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                if expires_at < now:
                    print(f"Exception for {cve} has EXPIRED on {expires_at_str}", file=sys.stderr)
                    continue
            except Exception:
                pass
        valid_exceptions.append(exc)

    return valid_exceptions


def is_excepted(finding: dict[str, Any], exceptions: list[dict[str, Any]], layer: str | None = None) -> bool:
    """Check if finding matches any active exception."""
    rule_id = finding.get("rule_id", "")
    for exc in exceptions:
        exc_cve = exc.get("cve_id") or exc.get("id")
        exc_layer = exc.get("layer") or exc.get("component")
        if exc_cve == rule_id:
            if not exc_layer or exc_layer == "*" or exc_layer == layer:
                return True
    return False


def enforce(
    sarif_path: Path,
    severity_cutoff: str = "high",
    exceptions_path: Path | None = None,
    layer: str | None = None,
) -> int:
    findings = parse_sarif_findings(sarif_path, severity_cutoff=severity_cutoff)
    exceptions = load_exceptions(exceptions_path)

    unexcepted = []
    for f in findings:
        if is_excepted(f, exceptions, layer=layer):
            print(f"Excepted vulnerability: {f['rule_id']} ({f['severity']}) - {f['message']}")
        else:
            unexcepted.append(f)

    if not unexcepted:
        print(f"SARIF policy enforce: 0 unexcepted {severity_cutoff}+ vulnerabilities found.")
        return CLEAN_EXIT

    for f in unexcepted:
        print(f"Vulnerability violation [{f['severity'].upper()}]: {f['rule_id']} - {f['message']}", file=sys.stderr)

    return VULNERABLE_EXIT


def compare(
    current_sarif_path: Path,
    baseline_sarif_path: Path,
    severity_cutoff: str = "high",
    exceptions_path: Path | None = None,
    layer: str | None = None,
) -> int:
    current_findings = parse_sarif_findings(current_sarif_path, severity_cutoff=severity_cutoff)
    baseline_findings = parse_sarif_findings(baseline_sarif_path, severity_cutoff=severity_cutoff)
    exceptions = load_exceptions(exceptions_path)

    baseline_rule_ids = {f["rule_id"] for f in baseline_findings}

    inherited = []
    introduced = []

    for f in current_findings:
        if f["rule_id"] in baseline_rule_ids:
            inherited.append(f)
        else:
            introduced.append(f)

    for f in inherited:
        print(f"Inherited vulnerability [{f['severity'].upper()}]: {f['rule_id']} - {f['message']}")

    unexcepted_introduced = []
    for f in introduced:
        if is_excepted(f, exceptions, layer=layer):
            print(f"Excepted branch-introduced vulnerability: {f['rule_id']} ({f['severity']}) - {f['message']}")
        else:
            unexcepted_introduced.append(f)

    if not unexcepted_introduced:
        print(f"SARIF policy compare: 0 new unexcepted {severity_cutoff}+ vulnerabilities introduced.")
        return CLEAN_EXIT

    for f in unexcepted_introduced:
        print(
            f"Branch-introduced vulnerability [{f['severity'].upper()}]: {f['rule_id']} - {f['message']}",
            file=sys.stderr,
        )

    return VULNERABLE_EXIT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    enforce_p = subparsers.add_parser("enforce")
    enforce_p.add_argument("--sarif", type=Path, required=True)
    enforce_p.add_argument("--severity", default="high")
    enforce_p.add_argument("--exceptions", type=Path, default=None)
    enforce_p.add_argument("--layer", default=None)

    compare_p = subparsers.add_parser("compare")
    compare_p.add_argument("--current-sarif", type=Path, required=True)
    compare_p.add_argument("--baseline-sarif", type=Path, required=True)
    compare_p.add_argument("--severity", default="high")
    compare_p.add_argument("--exceptions", type=Path, default=None)
    compare_p.add_argument("--layer", default=None)

    args = parser.parse_args()

    if args.command == "enforce":
        sys.exit(enforce(args.sarif, severity_cutoff=args.severity, exceptions_path=args.exceptions, layer=args.layer))
    elif args.command == "compare":
        sys.exit(
            compare(
                args.current_sarif,
                args.baseline_sarif,
                severity_cutoff=args.severity,
                exceptions_path=args.exceptions,
                layer=args.layer,
            )
        )


if __name__ == "__main__":
    main()
