#!/usr/bin/env python3
"""
Diagnostic utility to verify namespace isolation and tenant-context drift.

The monorepo exposes the shared identity context through a namespace shim
(``value_fabric.shared.identity.context``) and, when ``packages/shared/src`` is
on ``sys.path``, through a direct package path
(``packages.shared.src.value_fabric.shared.identity.context``).  Python treats
these as separate modules unless they are aliased to the same ``sys.modules``
entry.  Because the module owns the ``ContextVar`` that carries the current
request's ``tenant_id`` to PostgreSQL RLS, a duplicated module object silently
breaks tenant isolation.

Run this using:

    python scripts/verify_tenant_drift.py

Exit codes:
    0 - Singleton is intact and tenant context propagates across import paths.
    1 - Critical drift detected: import paths resolved to different modules.
    2 - Configuration or import error during setup.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# Setup path configuration to mimic the monorepo environment.  The canonical
# namespace shim must resolve first so the root ``value_fabric/__init__.py`` is
# loaded; then ``packages/shared/src`` is added so the direct package path is
# also importable.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "packages" / "shared" / "src"))
sys.path.insert(0, str(ROOT_DIR))


def main() -> int:
    print("\n[!] Starting Forensic Import Diagnostics...")

    try:
        # 1. Import security context via the canonical namespace-shim path.
        import value_fabric.shared.identity.context as shim_ctx

        # 2. Import the same logical module via the direct package path.
        #    ``__import__`` is used because the deep namespace-package path can
        #    be resolved more reliably than a plain ``import ... as`` statement.
        direct_ctx = __import__(
            "packages.shared.src.value_fabric.shared.identity.context",
            fromlist=["context"],
        )
    except Exception as exc:
        print(f"\n[!] Configuration or Import Error during test setup: {exc}")
        return 2

    print(f"Shim Module Address:      {hex(id(shim_ctx))}")
    print(f"Canonical Module Address: {hex(id(direct_ctx))}")

    # Assert whether Python recognized them as the same singleton module.
    is_identical = shim_ctx is direct_ctx
    print(f"Modules are identical?    {is_identical}")

    if not is_identical:
        print("\n[FAIL] CRITICAL SECURITY VULNERABILITY DETECTED!")
        print("Mismatched import paths have broken the singleton security context.")
        print("The database connection layer running under the direct package path")
        print("will not receive the tenant context initialized by the shim middleware.")
        return 1

    # Set the tenant ID through the shim path and resolve it through the
    # direct package path.
    test_tenant = "tenant_acme_corp_99"
    shim_ctx.set_request_context(shim_ctx.RequestContext(tenant_id=test_tenant, source="jwt"))
    print(f"\n[+] Set active tenant on SHIM context to: '{test_tenant}'")

    resolved_tenant = direct_ctx.get_request_context()
    resolved_id = resolved_tenant.tenant_id if resolved_tenant is not None else None
    print(f"[?] Resolved tenant from CANONICAL/DIRECT context: '{resolved_id}'")

    if resolved_id != test_tenant:
        print("\n[FAIL] CRITICAL SECURITY VULNERABILITY DETECTED!")
        print("The ContextVar value set through one import path is not visible")
        print("through the other import path. PostgreSQL RLS may execute without")
        print("an active tenant context, leading to cross-tenant data leakage.")
        return 1

    print("\n[PASS] Security context resolved correctly across import paths.")
    return 0


if __name__ == "__main__":
    # Surface any environment hints that change import resolution; these are
    # informational only and do not affect the pass/fail outcome.
    if os.environ.get("GOVERNANCE_DEBUG"):
        print("GOVERNANCE_DEBUG=1 (informational)")
    sys.exit(main())
