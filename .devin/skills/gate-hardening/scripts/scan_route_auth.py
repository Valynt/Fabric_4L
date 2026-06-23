#!/usr/bin/env python3
"""Scan FastAPI route files for unsafe dependency injection patterns.

Usage:
    python scan_route_auth.py <routes_dir> [--allowlist file1.py,file2.py]

Scans all .py files in <routes_dir> (recursively) for:
  - Depends(get_db) without tenant context (RLS bypass)
  - get_optional_context on write endpoints (weak auth)
  - Missing require_authenticated on CRUD endpoints

Outputs a JSON report to stdout with violations and a summary.
"""
import argparse
import json
import os
import re
import sys


def scan_file(filepath, allowlist_files):
    """Scan a single route file for unsafe patterns."""
    basename = os.path.basename(filepath)
    if basename in allowlist_files:
        return []

    with open(filepath, "r") as f:
        content = f.read()
        lines = content.splitlines()

    violations = []

    # Pattern 1: Depends(get_db) — bypasses RLS
    for i, line in enumerate(lines, 1):
        if re.search(r"Depends\(\s*get_db\s*\)", line):
            # Check if there's a security comment (intentional usage)
            context_start = max(0, i - 4)
            context_lines = lines[context_start : i]
            has_security_comment = any(
                "SECURITY" in cl or "intentional" in cl.lower() or "pre-auth" in cl.lower()
                for cl in context_lines
            )
            if not has_security_comment:
                violations.append({
                    "file": filepath,
                    "line": i,
                    "pattern": "Depends(get_db)",
                    "severity": "P0",
                    "message": "Endpoint uses get_db without tenant context — RLS bypass",
                })

    # Pattern 2: get_optional_context on write endpoints
    for i, line in enumerate(lines, 1):
        if "get_optional_context" in line:
            # Check if this is a POST/PUT/DELETE/PATCH endpoint
            context_start = max(0, i - 10)
            context_lines = "\n".join(lines[context_start : i])
            if re.search(r'@router\.(post|put|delete|patch)', context_lines):
                violations.append({
                    "file": filepath,
                    "line": i,
                    "pattern": "get_optional_context on write endpoint",
                    "severity": "P0",
                    "message": "Write endpoint uses optional auth — data can be modified without tenant verification",
                })

    # Pattern 3: Route handlers with db but no auth dependency
    route_pattern = re.compile(r'@router\.(get|post|put|delete|patch)\(')
    for i, line in enumerate(lines, 1):
        if route_pattern.search(line):
            # Look ahead up to 15 lines for the function signature
            sig_lines = "\n".join(lines[i - 1 : min(i + 15, len(lines))])
            has_db = "get_db" in sig_lines or "get_db_from_context" in sig_lines
            has_auth = any(
                kw in sig_lines
                for kw in [
                    "require_authenticated",
                    "require_tenant_admin",
                    "require_super_admin",
                    "require_admin",
                ]
            )
            if has_db and not has_auth:
                # Check allowlist comment
                context_start = max(0, i - 4)
                context_lines = lines[context_start : i]
                has_security_comment = any(
                    "SECURITY" in cl or "pre-auth" in cl.lower() or "webhook" in cl.lower()
                    for cl in context_lines
                )
                if not has_security_comment:
                    violations.append({
                        "file": filepath,
                        "line": i,
                        "pattern": "DB access without auth",
                        "severity": "P1",
                        "message": "Endpoint accesses database but has no authentication dependency",
                    })

    return violations


def main():
    parser = argparse.ArgumentParser(description="Scan route files for unsafe auth patterns")
    parser.add_argument("routes_dir", help="Directory containing route files")
    parser.add_argument("--allowlist", default="", help="Comma-separated list of intentionally unsafe files")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    args = parser.parse_args()

    allowlist_files = set(f.strip() for f in args.allowlist.split(",") if f.strip())
    all_violations = []

    for root, _, files in os.walk(args.routes_dir):
        for fname in sorted(files):
            if fname.endswith(".py") and not fname.startswith("__"):
                filepath = os.path.join(root, fname)
                all_violations.extend(scan_file(filepath, allowlist_files))

    if args.format == "json":
        report = {
            "total_violations": len(all_violations),
            "p0_count": sum(1 for v in all_violations if v["severity"] == "P0"),
            "p1_count": sum(1 for v in all_violations if v["severity"] == "P1"),
            "violations": all_violations,
        }
        print(json.dumps(report, indent=2))
    else:
        if not all_violations:
            print("No violations found.")
        else:
            print(f"Found {len(all_violations)} violation(s):\n")
            for v in all_violations:
                print(f"  [{v['severity']}] {v['file']}:{v['line']}")
                print(f"         {v['message']}")
                print()

    sys.exit(1 if all_violations else 0)


if __name__ == "__main__":
    main()
