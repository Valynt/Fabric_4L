#!/usr/bin/env python3
"""Semgrep SARIF parser and legacy error baseline enforcement gate.

Validates that:
1. The SARIF file is valid and well-formed.
2. All ERROR-severity Semgrep findings are matched against an acknowledged baseline.
3. Newly introduced or unbaselined ERROR-severity findings fail the CI gate closed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, order=True)
class SarifErrorFinding:
    rule_id: str
    path: str
    line: int
    message: str = ""

    @property
    def key(self) -> str:
        return f"{self.path}:{self.line}:{self.rule_id}"

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "path": self.path,
            "line": self.line,
            "message": self.message,
        }


def normalize_path(raw_path: str, root: Path | None = None) -> str:
    """Normalize file paths to POSIX repo-relative format."""
    clean = raw_path.replace("\\", "/")
    if clean.startswith("file://"):
        clean = clean[7:]
    p = Path(clean)
    if root and p.is_absolute():
        try:
            p = p.resolve().relative_to(root.resolve())
            clean = p.as_posix()
        except ValueError:
            clean = p.as_posix()
    norm = os.path.normpath(clean).replace("\\", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    return norm


def normalize_rule_id(raw_rule_id: str) -> str:
    """Normalize rule ID for consistent comparisons."""
    return raw_rule_id.strip()


def parse_sarif_errors(
    sarif_data: dict[str, object], root: Path | None = None
) -> list[SarifErrorFinding]:
    """Parse SARIF JSON data and extract all ERROR-severity findings."""
    if not isinstance(sarif_data, dict):
        raise ValueError("SARIF data must be a JSON object")

    version = sarif_data.get("version")
    if version != "2.1.0" and "runs" not in sarif_data:
        raise ValueError(f"Unsupported SARIF structure or version: {version}")

    findings: list[SarifErrorFinding] = []
    runs = sarif_data.get("runs", [])
    if not isinstance(runs, list):
        raise ValueError("SARIF 'runs' property must be a list")

    for run in runs:
        if not isinstance(run, dict):
            continue

        # Map rule severities from driver rules if available
        rules_map: dict[str, str] = {}
        tool_driver = run.get("tool", {}).get("driver", {})
        for rule in tool_driver.get("rules", []):
            rule_id = rule.get("id")
            default_level = rule.get("defaultConfiguration", {}).get(
                "level"
            ) or rule.get("properties", {}).get("precision")
            if rule_id and default_level:
                rules_map[rule_id] = default_level.lower()

        results = run.get("results", [])
        if not isinstance(results, list):
            continue

        for result in results:
            if not isinstance(result, dict):
                continue

            rule_id = result.get("ruleId", "<unknown-rule>")
            level = result.get("level")
            if not level:
                level = rules_map.get(rule_id, "warning")

            if str(level).lower() != "error":
                continue

            locations = result.get("locations", [])
            path = "<unknown>"
            line = 1
            if (
                locations
                and isinstance(locations, list)
                and isinstance(locations[0], dict)
            ):
                phys = locations[0].get("physicalLocation", {})
                art = phys.get("artifactLocation", {})
                raw_uri = art.get("uri", "<unknown>")
                path = normalize_path(raw_uri, root)
                region = phys.get("region", {})
                line = int(region.get("startLine", 1))

            message_obj = result.get("message", {})
            message = (
                message_obj.get("text", "")
                if isinstance(message_obj, dict)
                else str(message_obj)
            )

            findings.append(
                SarifErrorFinding(
                    rule_id=normalize_rule_id(rule_id),
                    path=path,
                    line=line,
                    message=message.strip(),
                )
            )

    return sorted(findings)


@dataclass
class BaselineEntry:
    rule_id: str
    path: str
    line: int
    message: str = ""
    used: bool = False

    def matches_rule(self, candidate_rule: str) -> bool:
        norm_cand = normalize_rule_id(candidate_rule)
        norm_self = normalize_rule_id(self.rule_id)
        if norm_self == norm_cand:
            return True
        bare_cand = norm_cand.split(".")[-1]
        bare_self = norm_self.split(".")[-1]
        return (
            bare_cand == bare_self
            or norm_self.endswith(bare_cand)
            or norm_cand.endswith(bare_self)
        )


def load_baseline(baseline_path: Path) -> list[BaselineEntry]:
    """Load acknowledged baseline findings from JSON."""
    if not baseline_path.exists():
        return []

    with open(baseline_path, encoding="utf-8") as f:
        data = json.load(f)

    baseline_items = data.get("allowed_errors", [])
    entries: list[BaselineEntry] = []

    for item in baseline_items:
        rule_id = normalize_rule_id(item.get("rule_id", ""))
        path = normalize_path(item.get("path", ""))
        line = int(item.get("line", 0))
        message = str(item.get("message", ""))
        if rule_id and path:
            entries.append(
                BaselineEntry(rule_id=rule_id, path=path, line=line, message=message)
            )

    return entries


def match_findings_against_baseline(
    findings: list[SarifErrorFinding],
    baseline_entries: list[BaselineEntry],
    max_line_delta: int = 10,  # kept for API compat; proximity matching removed (SEC)
) -> tuple[list[SarifErrorFinding], list[SarifErrorFinding]]:
    """Match findings 1:1 against baseline entries.

    Matching is by stable identity: path + rule + exact line, or an explicit
    wildcard baseline entry (``line == 0``) that matches any single finding.
    Proximity/line-shift matching is intentionally NOT supported: a legacy
    finding that disappears and a new same-rule finding nearby must surface as
    a NEW error so security regressions cannot hide behind a stale baseline
    entry (SEC-L3-CYPHER review feedback).

    Returns (baselined_findings, unbaselined_findings).
    """
    # Reset used flags on baseline entries
    for entry in baseline_entries:
        entry.used = False

    baselined: list[SarifErrorFinding] = []
    unbaselined: list[SarifErrorFinding] = []

    for finding in findings:
        matched = False
        for entry in baseline_entries:
            if (
                not entry.used
                and entry.path == finding.path
                and entry.matches_rule(finding.rule_id)
                and (entry.line == finding.line or entry.line == 0)
            ):
                entry.used = True
                baselined.append(finding)
                matched = True
                break
        if not matched:
            unbaselined.append(finding)

    return baselined, unbaselined


def is_baselined(
    finding: SarifErrorFinding,
    baseline_entries: list[BaselineEntry] | set[tuple[str, ...]],
    max_line_delta: int = 10,  # kept for API compat; proximity matching removed (SEC)
) -> bool:
    """Check if a single finding matches the acknowledged baseline.

    Matching requires path + rule + exact line (or an explicit ``line == 0``
    wildcard). Proximity matching was removed so that a removed legacy finding
    paired with a new nearby same-rule finding surfaces as a NEW error rather
    than being absorbed by the stale baseline entry (SEC review feedback).
    """
    if isinstance(baseline_entries, (set, frozenset)):
        # Backward compatibility for tuple-set baseline fixtures
        bare_rule = finding.rule_id.split(".")[-1]
        for item in baseline_entries:
            if len(item) == 3:
                r_id, p, l = item
                if p == finding.path and (
                    r_id == finding.rule_id
                    or r_id.endswith(bare_rule)
                    or bare_rule in r_id
                ):
                    if l == finding.line or l == 0:
                        return True
            elif len(item) == 2:
                r_id, p = item
                if p == finding.path and (
                    r_id == finding.rule_id
                    or r_id.endswith(bare_rule)
                    or bare_rule in r_id
                ):
                    return True
        return False

    for entry in baseline_entries:
        if (
            not entry.used
            and entry.path == finding.path
            and entry.matches_rule(finding.rule_id)
        ):
            if entry.line == finding.line or entry.line == 0:
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Semgrep SARIF against error baseline"
    )
    parser.add_argument(
        "--sarif",
        type=Path,
        default=Path("semgrep-full.sarif"),
        help="Path to Semgrep SARIF file",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("config/ci/semgrep_baseline.json"),
        help="Path to baseline JSON file",
    )
    parser.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Generate or update baseline JSON file from current SARIF",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on ANY error-level finding regardless of baseline",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]

    if not args.sarif.exists():
        print(f"Error: SARIF file not found: {args.sarif}", file=sys.stderr)
        return 1

    try:
        with open(args.sarif, encoding="utf-8") as f:
            sarif_data = json.load(f)
        findings = parse_sarif_errors(sarif_data, root=repo_root)
    except Exception as exc:
        print(f"Error parsing SARIF file {args.sarif}: {exc}", file=sys.stderr)
        return 1

    if args.generate_baseline:
        baseline_payload = {
            "schema_version": "1.0.0",
            "description": "Acknowledged legacy Semgrep debt baseline for ERROR-severity findings",
            "allowed_errors": [f.to_dict() for f in findings],
        }
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        with open(args.baseline, "w", encoding="utf-8") as f:
            json.dump(baseline_payload, f, indent=2)
        print(
            f"Generated baseline with {len(findings)} acknowledged findings at {args.baseline}"
        )
        return 0

    if args.strict:
        if findings:
            print(
                f"Found {len(findings)} ERROR-severity Semgrep findings (strict mode):",
                file=sys.stderr,
            )
            for f in findings:
                print(f"  - {f.rule_id} at {f.path}:{f.line}", file=sys.stderr)
            return 1
        print("No ERROR-severity Semgrep findings detected.")
        return 0

    baseline_entries = load_baseline(args.baseline)
    baselined_findings, new_errors = match_findings_against_baseline(
        findings, baseline_entries
    )
    baselined_count = len(baselined_findings)

    if new_errors:
        print(
            f"FAILED: Found {len(new_errors)} NEW ERROR-severity Semgrep findings not in baseline:",
            file=sys.stderr,
        )
        for f in new_errors[:30]:
            print(f"  - {f.rule_id} at {f.path}:{f.line}: {f.message}", file=sys.stderr)
        if len(new_errors) > 30:
            print(f"  ... and {len(new_errors) - 30} more", file=sys.stderr)
        print(
            f"\nTotal ERROR findings: {len(findings)} ({baselined_count} acknowledged in baseline, {len(new_errors)} new).",
            file=sys.stderr,
        )
        return 1

    print(
        f"SUCCESS: No new ERROR-severity Semgrep findings. ({baselined_count} acknowledged in baseline)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
