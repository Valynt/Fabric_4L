"""Contract test: versioned shared-boundary surfaces are pinned and bounded (R2).

Enforces the brooks-shared-hub-remediation Step 4 remediation: the ``identity`` and
``error_handling`` modules are shared kernels imported by every service, so a change to
either exported surface (``__all__``) must be coordinated — a ``SURFACE_VERSION`` bump plus
a regeneration of ``config/ci/shared_surface_contract.json``.

The intended workflows:

1. Allowed — coordinated surface change: edit the boundary's ``__init__.py`` ``__all__``,
   bump its ``SURFACE_VERSION``, run ``scripts/ci/check_shared_boundary_surfaces.py --update``,
   and commit the regenerated baseline with the change.
2. Denied — surface changed at an unchanged version: editing ``__all__`` without a version
   bump fails both this test (live surface no longer matches the pinned snapshot) and the
   ``--update`` path (the checker refuses to overwrite a surface at its pinned version).
3. Denied — drift without regeneration: changing ``__all__`` (with or without a bump) and
   committing without regenerating the baseline fails this test and the CI structural-preflight
   drift check.

The CI-side counterpart is ``scripts/ci/check_shared_boundary_surfaces.py --check``
(AST-based, import-free); this test performs the runtime verification by importing the
boundaries and resolving every exported name.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from value_fabric.shared import error_handling, identity

pytestmark = [pytest.mark.contract_static, pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "config" / "ci" / "shared_surface_contract.json"

BOUNDARIES: dict[str, object] = {
    "identity": identity,
    "error_handling": error_handling,
}


def _load_baseline() -> dict:
    if not BASELINE_PATH.is_file():
        pytest.fail(
            f"Missing committed boundary-pinning baseline: {BASELINE_PATH}. Generate it with "
            "scripts/ci/check_shared_boundary_surfaces.py --update."
        )
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("boundary_name", sorted(BOUNDARIES))
def test_boundary_live_surface_matches_pinned_snapshot(boundary_name: str) -> None:
    """A boundary's exported surface must match its pinned versioned snapshot exactly.

    Changing ``__all__`` requires a coordinated ``SURFACE_VERSION`` bump and a regeneration
    of ``config/ci/shared_surface_contract.json``; a drift at an unchanged version is the
    exact failure mode the bounded-change policy forbids.
    """
    module = BOUNDARIES[boundary_name]

    baseline = _load_baseline()
    assert baseline.get("schema_version") == 1, (
        f"Unexpected shared_surface_contract.json schema: {baseline.get('schema_version')!r}"
    )
    pinned = baseline["boundaries"][boundary_name]

    live_version = getattr(module, "SURFACE_VERSION", None)
    assert live_version == pinned["version"], (
        f"{boundary_name} live SURFACE_VERSION {live_version!r} does not match the pinned "
        f"version {pinned['version']!r} in {BASELINE_PATH.name}. Bump the version in "
        f"__init__.py and regenerate with scripts/ci/check_shared_boundary_surfaces.py --update."
    )

    live_surface = sorted(getattr(module, "__all__", []))
    assert live_surface == pinned["surface"], (
        f"{boundary_name} exported surface no longer matches the snapshot pinned at version "
        f"{pinned['version']!r}. A surface change requires a SURFACE_VERSION bump and a "
        "regenerated baseline (scripts/ci/check_shared_boundary_surfaces.py --update)."
    )


@pytest.mark.parametrize("boundary_name", sorted(BOUNDARIES))
def test_boundary_snapshot_records_version(boundary_name: str) -> None:
    """The pinned snapshot must carry a parseable semver for the boundary.

    The CI checker compares versions via dot-component ordering; a boundary with no version
    cannot be drift-checked and is a governance violation.
    """
    baseline = _load_baseline()
    pinned = baseline["boundaries"][boundary_name]

    version = pinned["version"]
    parts = [part for part in version.split(".") if part != ""]
    assert parts and all(part.isdigit() for part in parts), (
        f"{boundary_name} pinned version {version!r} is not a dotted numeric version."
    )


@pytest.mark.parametrize("boundary_name", sorted(BOUNDARIES))
def test_every_exported_name_resolves(boundary_name: str) -> None:
    """Every name in a boundary's ``__all__`` must resolve via ``getattr``.

    Catches exports that are declared but unresolvable (including the ``identity`` boundary's
    lazy-loaded vault/dependency helper names, which are resolved through module ``__getattr__``
    after import).
    """
    module = BOUNDARIES[boundary_name]

    # hasattr resolves lazy module __getattr__ names too (identity's vault/dependency helpers).
    missing = [
        name
        for name in sorted(getattr(module, "__all__", []))
        if not hasattr(module, name)
    ]
    assert not missing, (
        f"{boundary_name} declares exported names that do not resolve: {missing}"
    )
