"""
Regression tests for the namespace-shim singleton guard on tenant identity.

The shared identity context is stored in a module-level ``ContextVar``.
Because the monorepo exposes the same physical module through multiple import
paths (``value_fabric.shared.identity.context`` and, when
``packages/shared/src`` is on ``sys.path``,
``packages.shared.src.value_fabric.shared.identity.context``), Python can load
the module twice and create two independent ``ContextVar`` objects.  If a
request sets tenant context through one path and the database session reads it
through the other, RLS will not see the active tenant and data can leak across
tenants.

These tests verify that the runtime singleton guard prevents that drift.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_VERIFY_SCRIPT = _PROJECT_ROOT / "scripts" / "verify_tenant_drift.py"


class TestTenantContextImportSingleton:
    """Ensure tenant identity ContextVar is a singleton across import paths."""

    def test_verify_tenant_drift_script_passes(self):
        """The standalone drift diagnostic must report a healthy singleton."""
        result = subprocess.run(
            [sys.executable, str(_VERIFY_SCRIPT)],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Tenant context singleton drift detected.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert "[PASS]" in result.stdout

    def test_context_module_is_identical_across_import_paths(self):
        """Both import paths must resolve to the exact same module object."""
        code = """
import sys
from pathlib import Path
root = Path().resolve()
# Canonical shim path first, then direct package path.
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "packages" / "shared" / "src"))

import value_fabric.shared.identity.context as shim_ctx
direct_ctx = __import__(
    "packages.shared.src.value_fabric.shared.identity.context",
    fromlist=["context"],
)

if shim_ctx is not direct_ctx:
    print(f"MODULE_DRIFT: {shim_ctx!r} != {direct_ctx!r}")
    sys.exit(1)

shim_ctx.set_request_context(
    shim_ctx.RequestContext(tenant_id="tenant_singleton_test", source="jwt")
)
resolved = direct_ctx.get_request_context()
if resolved is None or str(resolved.tenant_id) != "tenant_singleton_test":
    print(f"CONTEXT_DRIFT: resolved={resolved!r}")
    sys.exit(1)

print("OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Cross-import tenant context singleton test failed.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert "OK" in result.stdout
