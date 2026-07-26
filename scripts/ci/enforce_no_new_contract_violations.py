#!/usr/bin/env python3
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path


def _run_git_name_only(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def _changed_file_candidates(base_ref: str) -> list[list[str]]:
    candidates = [["diff", "--name-only", f"{base_ref}...HEAD"]]

    github_base_ref = os.environ.get("GITHUB_BASE_REF")
    if github_base_ref:
        candidates.append(["diff", "--name-only", f"origin/{github_base_ref}...HEAD"])

    candidates.extend(
        [
            ["diff", "--name-only", "HEAD~1", "HEAD"],
            ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        ]
    )
    return candidates


def changed_files(base_ref: str) -> list[str]:
    last_error = ""
    for args in _changed_file_candidates(base_ref):
        out = _run_git_name_only(args)
        if out.returncode == 0:
            return [line.strip() for line in out.stdout.splitlines() if line.strip()]
        last_error = out.stderr.strip()

    out = _run_git_name_only(["ls-files"])
    if out.returncode == 0:
        print(
            f"WARNING: unable to determine changed files for {base_ref}; "
            "scanning all tracked files instead.",
            file=sys.stderr,
        )
        return [line.strip() for line in out.stdout.splitlines() if line.strip()]

    print(
        f"ERROR: unable to determine files for contract scan. "
        f"Last git error: {last_error}; ls-files error: {out.stderr.strip()}",
        file=sys.stderr,
    )
    raise SystemExit(2)


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
