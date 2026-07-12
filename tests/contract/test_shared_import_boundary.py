from __future__ import annotations

import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SHARED_ROOT = (
    REPO_ROOT / "packages" / "shared" / "src" / "value_fabric" / "shared"
)

IMPORTANT_SHARED_SUBMODULES = (
    "value_fabric.shared.boundaries.tenant_boundary",
    "value_fabric.shared.identity",
    "value_fabric.shared.identity.tool_contract",
    "value_fabric.shared.rate_limiting.middleware",
    "value_fabric.shared.audit",
    "value_fabric.shared.error_handling",
    "value_fabric.shared.secrets",
    "value_fabric.shared.security",
)


def _module_path(module: object) -> Path:
    module_file = getattr(module, "__file__", None)
    if module_file:
        return Path(module_file).resolve()

    module_path = getattr(module, "__path__", None)
    if module_path:
        return Path(next(iter(module_path))).resolve()

    raise AssertionError(f"Could not determine module path for {module!r}")


def _assert_within_canonical_shared(module_name: str) -> None:
    module = importlib.import_module(module_name)
    resolved = _module_path(module)
    allowed_roots = {
        CANONICAL_SHARED_ROOT.resolve(),
        (CANONICAL_SHARED_ROOT / "__init__.py").resolve(),
    }

    assert any(
        resolved == root or root in resolved.parents
        for root in allowed_roots
    ), (
        f"{module_name} resolved to {resolved}, expected a path under "
        f"{CANONICAL_SHARED_ROOT}."
    )


def test_value_fabric_shared_import_is_canonical() -> None:
    _assert_within_canonical_shared("value_fabric.shared")


@pytest.mark.parametrize("module_name", IMPORTANT_SHARED_SUBMODULES)
def test_important_shared_submodules_import_from_canonical_package(
    module_name: str,
) -> None:
    _assert_within_canonical_shared(module_name)


def test_root_shared_directory_removed() -> None:
    """Deprecated root-level shared/ directory must be fully removed."""
    assert not (REPO_ROOT / "shared").exists()
