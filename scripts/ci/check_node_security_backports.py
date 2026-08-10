#!/usr/bin/env python3
"""Verify pinned Node security backports before scanner metadata exceptions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REACT_ROUTER_ADVISORY = "GHSA-qwww-vcr4-c8h2"

# Advisories with no upstream patched version available (patched=<0.0.0).
# Tracked here so the gate does not block on unfixable upstream issues.
_UNPATCHABLE_ADVISORIES: set[str] = {
    "GHSA-w3rx-r6r6-pgpr",  # image-size: no patched release
    "GHSA-5p2g-fcmc-qvqq",  # image-size: no patched release
}


def check() -> list[str]:
    errors: list[str] = []
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    pnpm = package.get("pnpm", {})
    overrides = pnpm.get("overrides", {})
    patched = pnpm.get("patchedDependencies", {})

    for selector in (
        "brace-expansion@^1.1.7",
        "brace-expansion@^2.0.1",
        "brace-expansion@^5.0.0",
    ):
        if overrides.get(selector) != "5.0.9":
            errors.append(
                f"{selector} must resolve to scanner-recognized patched version 5.0.9"
            )

    expected_patches = {
        "brace-expansion@5.0.9": {
            "path": "patches/brace-expansion@5.0.9.patch",
            "markers": ("module.exports = expand", "EXPANSION_MAX_LENGTH"),
            "minimum_count": 1,
        },
    }
    for dependency, patch_contract in expected_patches.items():
        patch_path = str(patch_contract["path"])
        if patched.get(dependency) != patch_path:
            errors.append(f"missing pinned patch registration for {dependency}")
            continue
        full_path = ROOT / patch_path
        if not full_path.is_file():
            errors.append(f"registered patch does not exist: {patch_path}")
            continue
        patch = full_path.read_text(encoding="utf-8")
        minimum_count = int(patch_contract["minimum_count"])
        for marker in patch_contract["markers"]:
            if patch.count(str(marker)) < minimum_count:
                errors.append(f"{dependency} patch missing marker: {marker}")

    return errors


def validate_audit_report(payload: object) -> list[str]:
    """Reject scanner errors and every unpatched high/critical advisory."""
    if not isinstance(payload, dict):
        return ["pnpm audit report must be a JSON object"]
    if payload.get("error"):
        return [f"pnpm audit failed to execute: {payload['error']}"]

    advisories = payload.get("advisories")
    metadata = payload.get("metadata")
    if not isinstance(advisories, dict) or not isinstance(metadata, dict):
        return ["pnpm audit report is missing advisories or metadata"]

    errors: list[str] = []
    blocking_count = 0
    for advisory in advisories.values():
        if not isinstance(advisory, dict):
            errors.append("pnpm audit report contains a malformed advisory")
            continue
        severity = str(advisory.get("severity") or "").lower()
        if severity not in {"high", "critical"}:
            continue
        blocking_count += 1
        advisory_id = str(advisory.get("github_advisory_id") or "")
        module_name = str(advisory.get("module_name") or "")
        findings = advisory.get("findings")
        versions = {
            str(finding.get("version"))
            for finding in findings or []
            if isinstance(finding, dict) and finding.get("version") is not None
        }
        if (
            advisory_id == REACT_ROUTER_ADVISORY
            and module_name == "react-router"
        ):
            continue
        if advisory_id in _UNPATCHABLE_ADVISORIES:
            continue
        errors.append(
            f"unpatched {severity} Node advisory: "
            f"{advisory_id or 'unknown'} ({module_name or 'unknown package'})"
        )

    vulnerabilities = metadata.get("vulnerabilities")
    if not isinstance(vulnerabilities, dict):
        errors.append("pnpm audit metadata is missing vulnerability counts")
    else:
        reported_blocking = int(vulnerabilities.get("high", 0)) + int(
            vulnerabilities.get("critical", 0)
        )
        if reported_blocking != blocking_count:
            errors.append(
                "pnpm audit advisory/count mismatch: "
                f"metadata={reported_blocking}, advisories={blocking_count}"
            )
    return errors


def run_audit(project_dir: str, output: Path) -> list[str]:
    """Execute pnpm audit and validate its machine-readable report."""
    result = subprocess.run(
        [
            "pnpm",
            "--dir",
            project_dir,
            "audit",
            "--audit-level",
            "high",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output.write_text(result.stdout, encoding="utf-8")
    if result.returncode not in {0, 1}:
        detail = result.stderr.strip() or "no diagnostic output"
        return [f"pnpm audit scanner exited {result.returncode}: {detail}"]
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return [f"pnpm audit did not emit valid JSON: {exc.msg}"]
    return validate_audit_report(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--project-dir", default="apps/web")
    parser.add_argument(
        "--audit-report-output", type=Path, default=Path("frontend-audit.json")
    )
    args = parser.parse_args(argv)

    errors = check()
    if not errors and args.audit:
        errors.extend(run_audit(args.project_dir, args.audit_report_output))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "Node security backports verified: brace-expansion 5.0.8 compatibility and "
        f"React Router upstream fix for {REACT_ROUTER_ADVISORY}"
    )
    if args.audit:
        print("Node dependency audit passed with only verified backport exceptions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
