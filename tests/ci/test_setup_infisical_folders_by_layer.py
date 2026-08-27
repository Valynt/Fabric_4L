"""Regression tests: setup_infisical_folders creates nested by-layer paths.

The Infisical API models folder name and parent path separately, so paths
containing a "/" (e.g. ``apps/web``, ``shared/auth``) must be split into
parent + leaf and created parent-first. These tests pin that behavior.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "security" / "setup_infisical_folders.py"
SPEC = spec_from_file_location("setup_infisical_folders", MODULE_PATH)
assert SPEC and SPEC.loader
folders = module_from_spec(SPEC)
SPEC.loader.exec_module(folders)


def test_shared_auth_subpath_is_present() -> None:
    """``shared/auth`` must be in the provisioning set so gateway auth
    secrets (CLERK_SECRET_KEY, FABRIC_AUTH_SIGNING_KEY, CLERK_WEBHOOK_SECRET)
    are copied to staging/prod, not silently omitted."""
    paths = {p for p, _needs_parent in folders.FOLDERS_TO_CREATE}
    assert "shared/auth" in paths


def test_apps_web_is_split_into_parent_and_leaf() -> None:
    """``apps/web`` must be created as parent ``apps`` then leaf ``web`` so
    the Infisical API receives a valid (name, parentPath) pair rather than
    a single ``name="apps/web"`` payload."""
    paths = {p for p, _needs_parent in folders.FOLDERS_TO_CREATE}
    assert "apps" in paths
    assert "apps/web" in paths


def test_nested_paths_are_marked_needing_parent_split() -> None:
    """Every path containing a "/" must carry needs_parent=True so the
    provisioning loop creates its parent first."""
    for path, needs_parent in folders.FOLDERS_TO_CREATE:
        if "/" in path:
            assert needs_parent, f"{path} contains '/' but needs_parent=False"


def test_all_entries_are_path_needs_parent_tuples() -> None:
    """The provisioning loop unpacks (path, needs_parent) tuples; a bare
    string entry would crash it. Pin the tuple shape."""
    for entry in folders.FOLDERS_TO_CREATE:
        assert isinstance(entry, tuple), f"{entry!r} must be a tuple"
        assert len(entry) == 2, f"{entry!r} must be (path, needs_parent)"
        path, needs_parent = entry
        assert isinstance(path, str) and path
        assert isinstance(needs_parent, bool)
