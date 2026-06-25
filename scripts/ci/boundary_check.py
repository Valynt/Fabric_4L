"""CI gate: detect prohibited tenant inference in runtime source trees."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

DENY_PATTERNS = [
    r'request\.headers\.get\s*\(\s*["\']X-Tenant-ID["\']',
    r"request\.query_params",
    r'\b(?:request\.query_params|query_params|query|params|payload|body|request_body|data)\.get\s*\(\s*["\']tenant_id["\']',
    r"api_key\.tenant_id",
    r'getattr\s*\(\s*api_key\s*,\s*["\']tenant_id["\']',
]
ALLOWLIST_PATHS = [
    "packages/shared/src/shared/boundaries/tenant_boundary.py",
    "packages/shared/src/shared/identity/context.py",
    "packages/shared/src/shared/identity/middleware.py",
    "tests/security/test_boundary_check_static.py",
    "tests/fixtures/security/boundary_check/",
]
ALLOWLIST_FILE = Path("config/ci/boundary_check_allowlist.json")
RUNTIME_ROOTS = [Path("services"), Path("value_fabric"), Path("packages/shared/src/shared")]


def load_allowlist(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    """Load per-line allowlist entries indexed by (relative file path, line number)."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("allowlist", []) if isinstance(data, dict) else []
    default_expiry = data.get("expires_on") if isinstance(data, dict) else None
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for entry in entries:
        file_key = str(entry.get("file", ""))
        line = entry.get("line")
        if file_key and isinstance(line, int):
            merged = dict(entry)
            if "expires_on" not in merged and default_expiry:
                merged["expires_on"] = default_expiry
            result[(file_key, line)] = merged
    return result


def allowlist_expires(entry: dict[str, Any], today: date) -> bool:
    """Return True if the allowlist entry is expired (or has no expiry)."""
    expires_on = entry.get("expires_on")
    if not expires_on:
        return True
    try:
        expiry = date.fromisoformat(str(expires_on))
    except ValueError:
        return True
    return expiry < today


def is_allowlisted(path: Path) -> bool:
    normalized = str(path).replace("\\", "/")
    return any(allowlisted in normalized for allowlisted in ALLOWLIST_PATHS)


def changed_lines(base_ref: str) -> dict[str, set[int]]:
    diff = subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", f"{base_ref}...HEAD", "--", "*.py"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    out: dict[str, set[int]] = {}
    cur: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
            out.setdefault(cur, set())
        elif line.startswith("@@") and cur:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if not m:
                continue
            start = int(m.group(1))
            count = int(m.group(2) or "1")
            for n in range(start, start + count):
                out[cur].add(n)
    return out


def find_violations_in_file(
    filepath: Path,
    rel_path: str,
    allowlist: dict[tuple[str, int], dict[str, Any]],
    today: date,
    only_lines: set[int] | None = None,
) -> list[dict[str, object]]:
    if is_allowlisted(filepath):
        return []

    violations: list[dict[str, object]] = []
    for line_number, line in enumerate(filepath.read_text(encoding="utf-8").splitlines(), 1):
        if only_lines is not None and line_number not in only_lines:
            continue
        entry = allowlist.get((rel_path, line_number))
        if entry and not allowlist_expires(entry, today):
            continue
        for pattern in DENY_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append({"line": line_number, "content": line.strip()})
                break
    return violations


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-ref")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Scan the full runtime tree, ignoring --base-ref line scoping.",
    )
    return ap


def main() -> None:
    args = build_parser().parse_args()
    touched = changed_lines(args.base_ref) if args.base_ref and not args.strict else None
    allowlist = load_allowlist(ALLOWLIST_FILE)
    today = datetime.now(timezone.utc).date()
    violations: dict[Path, list[dict[str, object]]] = {}
    for root in [r for r in RUNTIME_ROOTS if r.exists()]:
        for f in root.rglob("*.py"):
            rel = str(f).replace("\\", "/")
            if any(x in rel for x in ["/tests/", "/.venv/", "/site-packages/"]):
                continue
            line_scope = touched.get(rel) if touched is not None else None
            if touched is not None and not line_scope:
                continue
            found = find_violations_in_file(f, rel, allowlist, today, line_scope)
            if found:
                violations[f] = found

    if not violations:
        print("PASS: No tenant boundary violations detected")
        sys.exit(0)

    total = 0
    for fp, vs in sorted(violations.items()):
        print(f"\n{fp}")
        for x in vs:
            print(f"  Line {x['line']}: {str(x['content'])[:120]}")
            total += 1
    print(f"\nFAIL: {len(violations)} files with {total} boundary violations")
    sys.exit(1)


if __name__ == "__main__":
    main()
