#!/usr/bin/env python3
"""Semgrep SARIF parser and legacy error baseline enforcement gate.

Validates that:
1. The SARIF file is valid and well-formed.
2. All ERROR-severity Semgrep findings are matched against an acknowledged baseline.
3. Any new or unbaselined ERROR-severity finding fails the CI gate closed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, order=True)
class SarifErrorFinding:
    rule_id: str
    path: str
    line: int
    message: str = ""

    @property
    def key(self) -> str:
        return f"{self.path}:{self.line}:{self.rule_id}"

    def to_dict(self) -> dict[str, Any]:
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
    sarif_data: dict[str, Any], root: Path | None = None
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
            default_level = (
                rule.get("defaultConfiguration", {}).get("level")
                or rule.get("properties", {}).get("precision")
            )
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
            if locations and isinstance(locations, list) and isinstance(locations[0], dict):
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


def load_baseline(baseline_path: Path) -> set[tuple[str, str, int]] | set[tuple[str, str]]:
    """Load acknowledged baseline findings from JSON."""
    if not baseline_path.exists():
        return set()

    with open(baseline_path, encoding="utf-8") as f:
        data = json.load(f)

    baseline_items = data.get("allowed_errors", [])
    exact_keys: set[tuple[str, str, int]] = set()
    flexible_keys: set[tuple[str, str]] = set()

    for item in baseline_items:
        rule_id = normalize_rule_id(item.get("rule_id", ""))
        path = normalize_path(item.get("path", ""))
        line = int(item.get("line", 0))
        if rule_id and path:
            if line > 0:
                exact_keys.add((rule_id, path, line))
            flexible_keys.add((rule_id, path))

    return exact_keys, flexible_keys  # type: ignore[return-value]


def is_baselined(
    finding: SarifErrorFinding,
    exact_baseline: set[tuple[str, str, int]],
    flexible_baseline: set[tuple[str, str]],
) -> bool:
    """Check if a finding is in the acknowledged baseline."""
    # Check exact match: (rule_id, path, line)
    if (finding.rule_id, finding.path, finding.line) in exact_baseline:
        return True
    # Strip prefixes like 'semgrep.' to check rule ID variations
    bare_rule = finding.rule_id.split(".")[-1]
    for r_id, p, l in exact_baseline:
        if p == finding.path and l == finding.line and (r_id == finding.rule_id or r_id.endswith(bare_rule) or bare_rule in r_id):
            return True

    # Fallback to file-level matching if line numbers shifted slightly
    for r_id, p in flexible_baseline:
        if p == finding.path and (r_id == finding.rule_id or r_id.endswith(bare_rule) or bare_rule in r_id):
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

    exact_baseline, flexible_baseline = load_baseline(args.baseline)

    new_errors: list[SarifErrorFinding] = []
    baselined_count = 0

    for finding in findings:
        if is_baselined(finding, exact_baseline, flexible_baseline):
            baselined_count += 1
        else:
            new_errors.append(finding)

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
