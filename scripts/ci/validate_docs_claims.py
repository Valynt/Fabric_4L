#!/usr/bin/env python3
"""Validate documentation claim verification IDs and emit CI evidence artifacts."""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    verification_id: str
    claim: str
    doc: str
    check_name: str
    command: str
    passed: bool
    exit_code: int
    output: str


def run_command(command: str) -> tuple[bool, int, str]:
    proc = subprocess.run(command, shell=True, text=True, capture_output=True)
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode == 0, proc.returncode, output.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate docs claims with automated checks")
    parser.add_argument("--config", default="docs/validation/docs-verification-map.json")
    parser.add_argument("--artifacts-dir", default="artifacts/docs-validation")
    args = parser.parse_args()

    config_path = Path(args.config)
    artifacts_dir = Path(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(config_path.read_text(encoding="utf-8"))

    results: list[CheckResult] = []
    stale_docs: dict[str, list[str]] = {}

    for item in config["claims"]:
        doc_path = Path(item["doc"])
        verification_id = item["verification_id"]
        marker = f"[VERIFY:{verification_id}]"
        doc_text = doc_path.read_text(encoding="utf-8")

        if marker not in doc_text:
            results.append(
                CheckResult(
                    verification_id=verification_id,
                    claim=item["claim"],
                    doc=item["doc"],
                    check_name="doc_annotation_present",
                    command=f"contains {marker}",
                    passed=False,
                    exit_code=1,
                    output=f"Missing verification marker {marker} in {item['doc']}",
                )
            )
            stale_docs.setdefault(item["doc"], []).append(verification_id)
            continue

        for check in item["checks"]:
            passed, code, output = run_command(check["command"])
            result = CheckResult(
                verification_id=verification_id,
                claim=item["claim"],
                doc=item["doc"],
                check_name=check["name"],
                command=check["command"],
                passed=passed,
                exit_code=code,
                output=output,
            )
            results.append(result)
            if not passed:
                stale_docs.setdefault(item["doc"], []).append(verification_id)

    payload: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "config": str(config_path),
        "results": [r.__dict__ for r in results],
        "stale_documents": [
            {"doc": doc, "verification_ids": sorted(set(ids))}
            for doc, ids in sorted(stale_docs.items())
        ],
    }

    (artifacts_dir / "docs-validation-evidence.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (artifacts_dir / "stale-documents.json").write_text(
        json.dumps(payload["stale_documents"], indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Docs Claim Verification Evidence",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "| Verification ID | Doc | Check | Status |",
        "|---|---|---|---|",
    ]
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"| {r.verification_id} | `{r.doc}` | `{r.check_name}` | {status} |")

    if stale_docs:
        lines.extend(["", "## Stale Documents", ""])
        for doc, ids in sorted(stale_docs.items()):
            lines.append(f"- `{doc}` → {', '.join(sorted(set(ids)))}")

    (artifacts_dir / "docs-validation-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote evidence artifacts to {artifacts_dir}")
    return 1 if stale_docs else 0


if __name__ == "__main__":
    raise SystemExit(main())
