#!/usr/bin/env python3
"""Fail CI if Layer 4 end-state audit marks requirements as implemented without enforcement tests."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


AUDIT_DOC_DEFAULT = Path("services/layer4-agents/docs/layer4_end_state_audit.md")


def _load_yaml_block(markdown: str) -> dict:
    match = re.search(r"```yaml\n(.*?)\n```", markdown, re.DOTALL)
    if not match:
        raise ValueError("No fenced ```yaml block found in audit document.")
    payload = yaml.safe_load(match.group(1))
    if not isinstance(payload, dict):
        raise ValueError("Audit YAML block did not parse into a mapping.")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-doc", type=Path, default=AUDIT_DOC_DEFAULT)
    args = parser.parse_args()

    content = args.audit_doc.read_text(encoding="utf-8")
    data = _load_yaml_block(content)
    requirements = data.get("requirements", [])

    violations: list[str] = []
    for req in requirements:
        req_id = req.get("id", "UNKNOWN")
        requirement = req.get("requirement", "(unnamed)")
        status = req.get("status")
        tests = req.get("enforcement_tests") or []

        if status == "implemented":
            if not tests:
                violations.append(
                    f"{req_id} '{requirement}' is implemented but has no enforcement_tests entries."
                )
                continue

            missing_paths = [
                test.get("path")
                for test in tests
                if not test.get("path") or not Path(test["path"]).exists()
            ]
            if missing_paths:
                violations.append(
                    f"{req_id} '{requirement}' is implemented but references missing enforcement test files: {missing_paths}"
                )

    if violations:
        print("Layer 4 end-state audit consistency check FAILED:\n")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Layer 4 end-state audit consistency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
