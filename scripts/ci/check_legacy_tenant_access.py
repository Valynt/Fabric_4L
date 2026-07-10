#!/usr/bin/env python3
"""Govern shim lifecycle for legacy tenant access patterns.

Pattern currently governed: direct `api_key.tenant_id` usage.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
PATTERN = re.compile(r"\bapi_key\.tenant_id\b")
SCAN_ROOTS = (ROOT / "value_fabric", ROOT / "services", ROOT / "tests", ROOT / "scripts")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".tox"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    pattern: str
    allowlisted: bool
    allowlist_id: str | None


def load_allowlist(path: Path) -> dict[tuple[str, int], dict[str, str]]:
    if yaml is None:
        raise RuntimeError("pyyaml is required for allowlist parsing")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = raw.get("allowlist", [])
    out: dict[tuple[str, int], dict[str, str]] = {}
    for item in entries:
        out[(item["path"], int(item["line"]))] = item
    return out


def iter_files():
    import os

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if name.endswith(".py"):
                    yield Path(dirpath) / name


def scan(allowlist: dict[tuple[str, int], dict[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files():
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        source = path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "tenant_id":
                parent = node.value
                if isinstance(parent, ast.Attribute) and parent.attr == "api_key":
                    item = allowlist.get((rel, int(node.lineno)))
                    findings.append(
                        Finding(
                            path=rel,
                            line=int(node.lineno),
                            pattern="api_key.tenant_id",
                            allowlisted=item is not None,
                            allowlist_id=item.get("id") if item else None,
                        )
                    )
    return findings


def changed_lines(base_ref: str) -> set[tuple[str, int]]:
    cmd = ["git", "diff", "--unified=0", "--no-color", f"{base_ref}...HEAD"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if proc.returncode != 0:
        return set()
    file_path = ""
    added: set[tuple[str, int]] = set()
    new_line = 0
    for raw in proc.stdout.splitlines():
        if raw.startswith("+++ b/"):
            file_path = raw[6:]
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", raw)
            if not m:
                continue
            new_line = int(m.group(1))
        elif raw.startswith("+") and not raw.startswith("+++"):
            added.add((file_path, new_line))
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        else:
            new_line += 1
    return added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allowlist", default="config/ci/legacy_tenant_access_shim_allowlist.yaml")
    ap.add_argument("--phase", choices=["warn", "fail-new", "fail-all"], default=os.getenv("SHIM_LEGACY_ACCESS_PHASE", "warn"))
    ap.add_argument("--base-ref", default=os.getenv("SHIM_LEGACY_ACCESS_BASE_REF", "origin/main"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    allowlist = load_allowlist(ROOT / args.allowlist)
    findings = scan(allowlist)
    non_allowlisted = [f for f in findings if not f.allowlisted]

    status = 0
    phase_blockers: list[Finding] = []
    if args.phase == "warn":
        status = 0
    elif args.phase == "fail-new":
        changed = changed_lines(args.base_ref)
        phase_blockers = [f for f in non_allowlisted if (f.path, f.line) in changed]
        status = 1 if phase_blockers else 0
    else:
        phase_blockers = non_allowlisted
        status = 1 if phase_blockers else 0

    payload = {
        "phase": args.phase,
        "total_findings": len(findings),
        "non_allowlisted": len(non_allowlisted),
        "blockers": [asdict(f) for f in phase_blockers],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))
        if args.phase == "warn" and non_allowlisted:
            print("WARN: legacy tenant access present; migration required.")
        if status:
            print(f"FAIL ({args.phase}): found {len(phase_blockers)} blocking legacy tenant access usage(s).")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
