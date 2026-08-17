#!/usr/bin/env python3
"""Deterministic change-risk and approval policy gate (V1-CI-001 aggregate 09).

This is a deterministic policy check, not an LLM gate and not substantive
testing. It verifies that an independent-review artifact exists for the
change under review and that it satisfies the merge policy:

1. The artifact is schema-valid (required fields, correct types).
2. Its base and head SHAs match the SHAs of the triggering event
   (``pull_request`` or ``merge_group``).
3. It records no unresolved P0/P1 findings.
4. Every high-risk surface recorded as touched has a CODEOWNER/human
   approval recorded in the artifact.
5. The reviewer did not author the patch.

Artifact location: ``signoff-evidence/reviews/<head_sha>.json`` relative to
the repository root (override with ``--artifact-dir``). Schema (version 1)::

    {
      "schema_version": 1,
      "base_sha": "<40-hex>",
      "head_sha": "<40-hex>",
      "author": "<github-login>",
      "reviewer": "<github-login>",
      "high_risk_surfaces_touched": ["<surface>", ...],
      "codeowner_approvals": [{"surface": "<surface>", "approver": "<login>"}, ...],
      "findings": [{"id": "...", "severity": "P0|P1|P2|P3",
                    "status": "open|resolved|wontfix"}, ...]
    }
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "signoff-evidence" / "reviews"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UNRESOLVED_STATUSES = {"open", "triaged", "in_progress"}
BLOCKING_SEVERITIES = {"P0", "P1"}


def _fail(errors: list[str], message: str) -> None:
    errors.append(message)
    print(f"POLICY FAIL: {message}", file=sys.stderr)


def _event_shas(event_name: str, event: dict[str, Any], errors: list[str]) -> tuple[str, str] | None:
    if event_name == "pull_request":
        pr = event.get("pull_request")
        if not isinstance(pr, dict):
            _fail(errors, "pull_request event payload missing 'pull_request' object")
            return None
        base = pr.get("base", {}).get("sha")
        head = pr.get("head", {}).get("sha")
    elif event_name == "merge_group":
        group = event.get("merge_group")
        if not isinstance(group, dict):
            _fail(errors, "merge_group event payload missing 'merge_group' object")
            return None
        base = group.get("base_sha")
        head = group.get("head_sha")
    else:
        _fail(errors, f"unsupported event {event_name!r}; expected pull_request or merge_group")
        return None
    if not (isinstance(base, str) and SHA_RE.match(base)):
        _fail(errors, f"event base SHA missing or malformed: {base!r}")
        return None
    if not (isinstance(head, str) and SHA_RE.match(head)):
        _fail(errors, f"event head SHA missing or malformed: {head!r}")
        return None
    return base, head


def _validate_artifact(
    artifact: Any,
    expected_base: str,
    expected_head: str,
    errors: list[str],
) -> None:
    if not isinstance(artifact, dict):
        _fail(errors, "artifact must be a JSON object")
        return
    if artifact.get("schema_version") != 1:
        _fail(errors, f"unsupported schema_version: {artifact.get('schema_version')!r}")

    base = artifact.get("base_sha")
    head = artifact.get("head_sha")
    if not (isinstance(base, str) and SHA_RE.match(base)):
        _fail(errors, "artifact base_sha missing or malformed")
    elif base != expected_base:
        _fail(errors, f"artifact base_sha {base} does not match event base SHA {expected_base}")
    if not (isinstance(head, str) and SHA_RE.match(head)):
        _fail(errors, "artifact head_sha missing or malformed")
    elif head != expected_head:
        _fail(errors, f"artifact head_sha {head} does not match event head SHA {expected_head}")

    author = artifact.get("author")
    reviewer = artifact.get("reviewer")
    if not isinstance(author, str) or not author:
        _fail(errors, "artifact author missing or not a string")
    if not isinstance(reviewer, str) or not reviewer:
        _fail(errors, "artifact reviewer missing or not a string")
    if isinstance(author, str) and isinstance(reviewer, str) and author == reviewer:
        _fail(errors, f"reviewer {reviewer!r} authored the patch; independent review required")

    findings = artifact.get("findings")
    if not isinstance(findings, list):
        _fail(errors, "artifact findings missing or not a list")
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            _fail(errors, f"finding entry is not an object: {finding!r}")
            continue
        severity = finding.get("severity")
        status = finding.get("status")
        if severity not in {"P0", "P1", "P2", "P3"}:
            _fail(errors, f"finding {finding.get('id')!r} has invalid severity {severity!r}")
        if not isinstance(status, str):
            _fail(errors, f"finding {finding.get('id')!r} has missing status")
        if severity in BLOCKING_SEVERITIES and status in UNRESOLVED_STATUSES:
            _fail(errors, f"unresolved {severity} finding: {finding.get('id')!r} (status={status!r})")

    surfaces = artifact.get("high_risk_surfaces_touched")
    if not isinstance(surfaces, list) or not all(isinstance(s, str) for s in surfaces):
        _fail(errors, "artifact high_risk_surfaces_touched missing or not a string list")
        surfaces = []
    approvals = artifact.get("codeowner_approvals")
    if not isinstance(approvals, list):
        _fail(errors, "artifact codeowner_approvals missing or not a list")
        approvals = []
    approved_surfaces: dict[str, str] = {}
    for approval in approvals:
        if not isinstance(approval, dict) or not isinstance(approval.get("surface"), str):
            _fail(errors, f"codeowner_approvals entry malformed: {approval!r}")
            continue
        approver = approval.get("approver")
        if not isinstance(approver, str) or not approver:
            _fail(errors, f"codeowner approval for {approval['surface']!r} missing approver")
            continue
        approved_surfaces[approval["surface"]] = approver
    for surface in surfaces:
        approver = approved_surfaces.get(surface)
        if approver is None:
            _fail(errors, f"high-risk surface {surface!r} has no recorded CODEOWNER/human approval")
        elif isinstance(author, str) and approver == author:
            _fail(errors, f"high-risk surface {surface!r} approved by patch author {author!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic independent-review / change-risk policy gate."
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
        help="Directory containing <head_sha>.json independent-review artifacts.",
    )
    parser.add_argument(
        "--event-path",
        type=Path,
        default=Path(os.environ.get("GITHUB_EVENT_PATH", "/dev/null")),
        help="Path to the GitHub event payload JSON (default: GITHUB_EVENT_PATH).",
    )
    args = parser.parse_args(argv)

    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    errors: list[str] = []

    try:
        event = json.loads(args.event_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"POLICY FAIL: cannot read event payload {args.event_path}: {exc}", file=sys.stderr)
        return 1

    shas = _event_shas(event_name, event, errors)
    if shas is None:
        return 1
    expected_base, expected_head = shas

    artifact_path = args.artifact_dir / f"{expected_head}.json"
    if not artifact_path.is_file():
        print(
            f"POLICY FAIL: no independent-review artifact for head {expected_head} "
            f"(expected {artifact_path})",
            file=sys.stderr,
        )
        return 1
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"POLICY FAIL: artifact {artifact_path} is not valid JSON: {exc}", file=sys.stderr)
        return 1

    _validate_artifact(artifact, expected_base, expected_head, errors)

    if errors:
        print(f"09-change-risk-and-approval FAILED with {len(errors)} policy violation(s)", file=sys.stderr)
        return 1
    print(
        "09-change-risk-and-approval PASSED: schema-valid independent-review artifact, "
        "SHAs match, no unresolved P0/P1, high-risk approvals present, reviewer != author"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
