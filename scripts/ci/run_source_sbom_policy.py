#!/usr/bin/env python3
"""Enforce delta-aware vulnerability policies on SARIF scan outputs."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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


@dataclass(frozen=True)
class SarifFinding:
    rule_id: str
    severity: str
    message: str
    location: str
    signature: str


@dataclass(frozen=True)
class VulnerabilityException:
    cve_id: str
    layer: str
    owner: str
    ticket: str
    justification: str
    compensating_controls: str
    created_at: str
    expires_at: str


def parse_sarif_findings(sarif_path: Path, severity_cutoff: str = "high") -> list[SarifFinding]:
    """Extract findings meeting or exceeding severity cutoff from SARIF file."""
    if not sarif_path.exists() or sarif_path.stat().st_size == 0:
        return []

    try:
        data = json.loads(sarif_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse SARIF file {sarif_path}: {exc}") from exc

    min_sev_level = SEVERITY_ORDER.get(severity_cutoff.lower(), 3)
    findings: list[SarifFinding] = []

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
                findings.append(
                    SarifFinding(
                        rule_id=rule_id,
                        severity=severity,
                        message=message,
                        location=location_str,
                        signature=f"{rule_id}:{location_str}:{message[:50]}",
                    )
                )

    return findings


REQUIRED_EXCEPTION_FIELDS = (
    "cve_id",
    "layer",
    "owner",
    "ticket",
    "justification",
    "compensating_controls",
    "created_at",
    "expires_at",
)


def load_exceptions(exceptions_path: Path | None) -> list[VulnerabilityException]:
    """Load valid (well-formed, non-expired) vulnerability exceptions from JSON or YAML."""
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

    if not isinstance(data, dict):
        print(f"Warning: Invalid exception data structure in {exceptions_path}", file=sys.stderr)
        return []

    exceptions = data.get("exceptions", [])
    if not isinstance(exceptions, list):
        print(f"Warning: 'exceptions' must be a list in {exceptions_path}", file=sys.stderr)
        return []

    valid_exceptions: list[VulnerabilityException] = []
    now = datetime.now(timezone.utc)

    for idx, exc in enumerate(exceptions):
        if not isinstance(exc, dict):
            print(f"Warning: Exception entry {idx} is not a valid dict, skipping.", file=sys.stderr)
            continue

        cve = exc.get("cve_id") or exc.get("id")
        if not cve:
            print(f"Warning: Entry {idx} missing CVE ID, skipping.", file=sys.stderr)
            continue

        # Enforce required approval and governance fields
        missing_fields = [f for f in REQUIRED_EXCEPTION_FIELDS if not exc.get(f)]
        if missing_fields:
            print(
                f"Warning: Exception for {cve} missing required fields {missing_fields}, rejecting.",
                file=sys.stderr,
            )
            continue

        expires_at_str = str(exc.get("expires_at"))
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if expires_at < now:
                print(f"Exception for {cve} has EXPIRED on {expires_at_str}", file=sys.stderr)
                continue
        except Exception as e:
            print(f"Warning: Exception for {cve} has invalid expires_at format '{expires_at_str}': {e}, rejecting.", file=sys.stderr)
            continue

        valid_exceptions.append(
            VulnerabilityException(
                cve_id=str(cve),
                layer=str(exc.get("layer") or exc.get("component") or "*"),
                owner=str(exc.get("owner", "")),
                ticket=str(exc.get("ticket", "")),
                justification=str(exc.get("justification", "")),
                compensating_controls=str(exc.get("compensating_controls", "")),
                created_at=str(exc.get("created_at", "")),
                expires_at=expires_at_str,
            )
        )

    return valid_exceptions


def is_excepted(finding: SarifFinding, exceptions: list[VulnerabilityException], layer: str | None = None) -> bool:
    """Check if finding matches any active exception."""
    rule_id = finding.rule_id
    for exc in exceptions:
        if exc.cve_id == rule_id:
            if not exc.layer or exc.layer == "*" or exc.layer == layer:
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

    unexcepted: list[SarifFinding] = []
    for f in findings:
        if is_excepted(f, exceptions, layer=layer):
            print(f"Excepted vulnerability: {f.rule_id} ({f.severity}) - {f.message}")
        else:
            unexcepted.append(f)

    if not unexcepted:
        print(f"SARIF policy enforce: 0 unexcepted {severity_cutoff}+ vulnerabilities found.")
        return CLEAN_EXIT

    for f in unexcepted:
        print(f"Vulnerability violation [{f.severity.upper()}]: {f.rule_id} - {f.message}", file=sys.stderr)

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

    baseline_signatures = {f.signature for f in baseline_findings}

    inherited: list[SarifFinding] = []
    introduced: list[SarifFinding] = []

    for f in current_findings:
        if f.signature in baseline_signatures:
            inherited.append(f)
        else:
            introduced.append(f)

    for f in inherited:
        print(f"Inherited vulnerability [{f.severity.upper()}]: {f.rule_id} - {f.message}")

    unexcepted_introduced: list[SarifFinding] = []
    for f in introduced:
        if is_excepted(f, exceptions, layer=layer):
            print(f"Excepted branch-introduced vulnerability: {f.rule_id} ({f.severity}) - {f.message}")
        else:
            unexcepted_introduced.append(f)

    if not unexcepted_introduced:
        print(f"SARIF policy compare: 0 new unexcepted {severity_cutoff}+ vulnerabilities introduced.")
        return CLEAN_EXIT

    for f in unexcepted_introduced:
        print(
            f"Branch-introduced vulnerability [{f.severity.upper()}]: {f.rule_id} - {f.message}",
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
