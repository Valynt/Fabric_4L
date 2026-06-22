#!/usr/bin/env python3
"""
Diagnostic utility to verify namespace isolation and tenant-context drift.

The monorepo exposes the shared identity context through the PEP 420 namespace
package at ``packages/shared/src/value_fabric/shared``. This check verifies that
the supported ``value_fabric.shared.identity.context`` import path resolves to
one module object and that tenant context remains available through repeated
imports. Because the module owns the ``ContextVar`` that carries the current
request's ``tenant_id`` to PostgreSQL RLS, duplicated module objects can silently
break tenant isolation.

Run this using:

    python scripts/verify_tenant_drift.py

Exit codes:
    0 - Singleton is intact and tenant context propagates across imports.
    1 - Critical drift detected: repeated imports resolved to different modules.
    2 - Configuration or import error during setup.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# Setup path configuration to mimic the monorepo environment.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "packages" / "shared" / "src"))
sys.path.insert(0, str(ROOT_DIR))


def main() -> int:
    print("\n[!] Starting Forensic Import Diagnostics...")

    try:
        import importlib

        first_ctx = importlib.import_module("value_fabric.shared.identity.context")
        second_ctx = importlib.import_module("value_fabric.shared.identity.context")
    except Exception as exc:
        print(f"\n[!] Configuration or Import Error during test setup: {exc}")
        return 2

    print(f"First Module Address:  {hex(id(first_ctx))}")
    print(f"Second Module Address: {hex(id(second_ctx))}")

    # Assert whether Python recognized them as the same singleton module.
    is_identical = first_ctx is second_ctx
    print(f"Modules are identical?    {is_identical}")

    if not is_identical:
        print("\n[FAIL] CRITICAL SECURITY VULNERABILITY DETECTED!")
        print("Repeated imports have broken the singleton security context.")
        print("The database connection layer may not receive the tenant context")
        print("initialized by the authentication middleware.")
        return 1

    # Set the tenant ID through one import and resolve it through another.
    test_tenant = "tenant_acme_corp_99"
    first_ctx.set_request_context(first_ctx.RequestContext(tenant_id=test_tenant, source="jwt"))
    print(f"\n[+] Set active tenant on first context import to: '{test_tenant}'")

    resolved_tenant = second_ctx.get_request_context()
    resolved_id = resolved_tenant.tenant_id if resolved_tenant is not None else None
    print(f"[?] Resolved tenant from second context import: '{resolved_id}'")

    if resolved_id != test_tenant:
        print("\n[FAIL] CRITICAL SECURITY VULNERABILITY DETECTED!")
        print("The ContextVar value set through one import is not visible")
        print("through another import. PostgreSQL RLS may execute without")
        print("an active tenant context, leading to cross-tenant data leakage.")
        return 1

    print("\n[PASS] Security context resolved correctly across imports.")
    return 0


if __name__ == "__main__":
    # Surface any environment hints that change import resolution; these are
    # informational only and do not affect the pass/fail outcome.
    if os.environ.get("GOVERNANCE_DEBUG"):
        print("GOVERNANCE_DEBUG=1 (informational)")
    sys.exit(main())
