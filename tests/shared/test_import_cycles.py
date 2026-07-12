import importlib
import pkgutil
import subprocess
import sys
from itertools import permutations

import pytest

BOUNDARY_IMPORT_CLUSTER = (
    "value_fabric.shared.boundaries.tenant_boundary",
    "value_fabric.shared.rate_limiting.middleware",
    "value_fabric.shared.identity",
)

def test_no_shared_import_cycles():
    """Regression test for circular imports in the shared package."""
    modules_to_test = [
        "value_fabric.shared.boundaries.tenant_boundary",
        "value_fabric.shared.identity.context",
        "value_fabric.shared.identity.rate_limiter",
        "value_fabric.shared.rate_limiting.middleware",
        "value_fabric.shared.rate_limiting.tenant_rate_limiter",
        "value_fabric.shared.identity",
        "value_fabric.shared.rate_limiting",
        "value_fabric.shared.boundaries",
    ]
    
    # Try importing directly
    for module_name in modules_to_test:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"ImportError (likely circular) for {module_name}: {e}")

def test_recursive_import_shared_package():
    """Dynamically discover and import all shared modules to ensure no cycles."""
    import value_fabric.shared
    
    def walk_packages(path, prefix):
        for info in pkgutil.walk_packages(path, prefix):
            try:
                importlib.import_module(info.name)
            except ImportError as e:
                pytest.fail(f"Failed to import {info.name}: {e}")

    walk_packages(value_fabric.shared.__path__, value_fabric.shared.__name__ + '.')


@pytest.mark.parametrize("import_order", permutations(BOUNDARY_IMPORT_CLUSTER))
def test_tenant_boundary_import_cluster_is_order_independent(import_order):
    """Boundary, identity, and rate limiting modules must not form cycles."""
    script = "\n".join(
        [
            "import importlib",
            *[f"importlib.import_module({module_name!r})" for module_name in import_order],
        ]
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Import order failed: {import_order}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
