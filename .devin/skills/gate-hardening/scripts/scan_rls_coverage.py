#!/usr/bin/env python3
"""Scan Alembic migrations for RLS policy gaps.

Usage:
    python scan_rls_coverage.py <migrations_dir>

Scans all migration files for:
  - Tables with tenant_id columns but no RLS policy
  - RLS policies using unsafe 'tenant_id IS NULL' patterns
  - RLS policies without FORCE ROW LEVEL SECURITY
  - Inconsistent GUC variable names (app.tenant_id vs app.current_tenant)

Outputs a JSON report to stdout.
"""
import argparse
import json
import os
import re
import sys


def extract_rls_tables(content):
    """Extract table names from RLS_TABLES = [...] declarations."""
    match = re.search(r'RLS_TABLES\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if not match:
        return []
    raw = match.group(1)
    return re.findall(r'"([^"]+)"', raw)


def extract_tenant_id_tables(content):
    """Extract tables that have a tenant_id column added."""
    tables = set()
    # Pattern: sa.Column("tenant_id", ...) in create_table or add_column
    for match in re.finditer(r'(?:create_table|add_column)\s*\(\s*["\'](\w+)["\']', content):
        table = match.group(1)
        # Check if tenant_id is mentioned nearby
        start = match.start()
        chunk = content[start:start + 500]
        if 'tenant_id' in chunk:
            tables.add(table)
    # Also check for op.create_table with tenant_id
    for match in re.finditer(r'op\.create_table\(\s*["\'](\w+)["\']', content):
        table = match.group(1)
        start = match.start()
        chunk = content[start:start + 1000]
        if 'tenant_id' in chunk:
            tables.add(table)
    return tables


def scan_migration(filepath):
    """Scan a single migration file for RLS issues."""
    with open(filepath, "r") as f:
        content = f.read()

    findings = []
    basename = os.path.basename(filepath)

    rls_tables = extract_rls_tables(content)
    tenant_tables = extract_tenant_id_tables(content)

    # Check for unsafe NULL pattern
    if re.search(r'tenant_id\s+IS\s+NULL', content, re.IGNORECASE):
        for table in rls_tables or tenant_tables:
            findings.append({
                "file": basename,
                "table": table,
                "severity": "P0",
                "issue": "unsafe_null_policy",
                "message": "RLS policy uses 'tenant_id IS NULL' — rows without tenant_id visible to all tenants",
            })

    # Check for FORCE ROW LEVEL SECURITY
    if rls_tables and 'FORCE ROW LEVEL SECURITY' not in content:
        for table in rls_tables:
            findings.append({
                "file": basename,
                "table": table,
                "severity": "P1",
                "issue": "missing_force_rls",
                "message": "RLS enabled but FORCE not set — table owner can bypass policies",
            })

    # Check for inconsistent GUC variable names
    guc_vars = set(re.findall(r"current_setting\('(app\.\w+)'", content))
    if len(guc_vars) > 1:
        findings.append({
            "file": basename,
            "table": "*",
            "severity": "P0",
            "issue": "inconsistent_guc",
            "message": f"Multiple GUC variables used: {guc_vars} — policies may silently fail",
        })

    return findings, rls_tables, tenant_tables


def main():
    parser = argparse.ArgumentParser(description="Scan Alembic migrations for RLS gaps")
    parser.add_argument("migrations_dir", help="Directory containing migration version files")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    all_findings = []
    all_rls_tables = set()
    all_tenant_tables = set()

    versions_dir = args.migrations_dir
    if os.path.isdir(os.path.join(versions_dir, "versions")):
        versions_dir = os.path.join(versions_dir, "versions")

    for fname in sorted(os.listdir(versions_dir)):
        if fname.endswith(".py") and not fname.startswith("__"):
            filepath = os.path.join(versions_dir, fname)
            findings, rls_tables, tenant_tables = scan_migration(filepath)
            all_findings.extend(findings)
            all_rls_tables.update(rls_tables)
            all_tenant_tables.update(tenant_tables)

    # Check for tables with tenant_id but no RLS
    unprotected = all_tenant_tables - all_rls_tables
    for table in sorted(unprotected):
        all_findings.append({
            "file": "aggregate",
            "table": table,
            "severity": "P0",
            "issue": "missing_rls",
            "message": f"Table '{table}' has tenant_id column but no RLS policy",
        })

    if args.format == "json":
        report = {
            "total_findings": len(all_findings),
            "rls_tables": sorted(all_rls_tables),
            "tenant_tables": sorted(all_tenant_tables),
            "unprotected_tables": sorted(unprotected),
            "findings": all_findings,
        }
        print(json.dumps(report, indent=2))
    else:
        if not all_findings:
            print("No RLS issues found.")
        else:
            print(f"Found {len(all_findings)} issue(s):\n")
            for f in all_findings:
                print(f"  [{f['severity']}] {f['file']} → {f['table']}")
                print(f"         {f['message']}")
                print()

    sys.exit(1 if all_findings else 0)


if __name__ == "__main__":
    main()
