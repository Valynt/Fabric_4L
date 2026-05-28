#!/usr/bin/env python3
import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def changed_files(base_ref: str) -> list[str]:
    cmd = ["git", "diff", "--name-only", f"{base_ref}...HEAD"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        cmd = ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def load_cfg(path: Path) -> dict:
    return json.loads(path.read_text())


def scan_file(path: Path, patterns: list[str]) -> list[str]:
    if not path.exists() or path.is_dir():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [p for p in patterns if p in text]


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    cfg = load_cfg(Path("scripts/ci/no_new_contract_violations_baseline.json"))
    touched = changed_files(base_ref)

    violations: list[str] = []
    for rule in cfg["rules"]:
        matches = [f for f in touched if fnmatch.fnmatch(f, rule["glob"])]
        for rel in matches:
            found = scan_file(Path(rel), rule["patterns"])
            if found:
                violations.append(f"[{rule['layer']}] {rule['id']} -> {rel}: {', '.join(found)}")

    if violations:
        print("FAIL No-net-new contract violations gate failed for touched modules:")
        for v in violations:
            print(f"  - {v}")
        print("Remediation requirement: update runtime contract + schema/types + consumers + regression tests together.")

        return 1

    print("PASS No-net-new contract violations gate passed for touched modules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
