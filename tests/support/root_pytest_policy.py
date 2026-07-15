"""Repository-level pytest dependency and marker policy."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

from tests.support.root_pytest_bootstrap import REPO_ROOT
from tests.support.root_pytest_policy_config import load_pytest_policy_config

if TYPE_CHECKING:
    from _pytest.config import Config, Parser
    from _pytest.nodes import Item

# Load the volatile policy lists from config/ci/pytest_policy.yaml so that
# routine additions (new tenant targets, new markers, new deps) do not churn
# this file.  The constants below retain the same names and types as before.
_policy_config = load_pytest_policy_config()

MANDATORY_DEPS: dict[str, str] = _policy_config.mandatory_deps
TENANT_ISOLATION_ALIASES = _policy_config.tenant_isolation_aliases
TENANT_ISOLATION_TARGETS = _policy_config.tenant_isolation_targets
TENANT_ISOLATION_NODEIDS = _policy_config.tenant_isolation_nodeids
MANDATORY_MARKERS = _policy_config.mandatory_markers
MANDATORY_EXCLUSION_MARKERS = _policy_config.mandatory_exclusion_markers


def add_root_pytest_options(parser: Parser) -> None:
    parser.addoption(
        "--no-mandatory-dep-check",
        action="store_true",
        default=False,
        dest="no_mandatory_dep_check",
        help="Skip mandatory dependency enforcement (for --collect-only dry runs).",
    )


def enforce_mandatory_dependencies(config: Config) -> None:
    if _skip_mandatory_dep_check(config):
        return
    missing = [
        (name, hint)
        for name, hint in MANDATORY_DEPS.items()
        if importlib.util.find_spec(name) is None
    ]
    if missing:
        raise SystemExit(_missing_dependency_message(missing))


def apply_collection_markers(items: list[Item]) -> None:
    for item in items:
        item_markers = _item_marker_names(item)
        _apply_tenant_isolation_marker(item, item_markers)
        if _should_mark_mandatory(item_markers):
            item.add_marker("mandatory")


def _skip_mandatory_dep_check(config: Config) -> bool:
    return (
        getattr(config.option, "no_mandatory_dep_check", False)
        or getattr(config.option, "collectonly", False)
        or _is_central_security_aggregation_run(config)
    )


def _is_central_security_aggregation_run(config: Config) -> bool:
    args = [str(arg).rstrip("/") for arg in getattr(config, "args", ())]
    if not args:
        return False
    security_dir = str(REPO_ROOT / "tests" / "security")
    return all(arg in {"tests/security", security_dir} for arg in args)


def _missing_dependency_message(missing: list[tuple[str, str]]) -> str:
    lines = ["", "Mandatory test dependencies are missing.", ""]
    for name, hint in missing:
        lines.append(f"  \u2717 {name}")
        lines.append(f"    \u2192 {hint}")
    lines += [
        "",
        "Install all mandatory deps for the full mandatory profile:",
        "  pip install -r tests/requirements-test.txt",
        "",
        "To skip this check (e.g. for a dry-run collection audit):",
        "  pytest --no-mandatory-dep-check --collect-only",
        "",
    ]
    return "\n".join(lines)


def _item_marker_names(item: Item) -> set[str]:
    return {marker.name for marker in item.iter_markers()}


def _item_repo_path(item: Item) -> str:
    return Path(str(item.fspath)).resolve().relative_to(REPO_ROOT).as_posix()


def _is_tenant_isolation_target(item: Item, item_markers: set[str]) -> bool:
    item_path = _item_repo_path(item)
    item_nodeid = item.nodeid.replace("\\", "/")
    return (
        item_path in TENANT_ISOLATION_TARGETS
        or item_nodeid in TENANT_ISOLATION_NODEIDS
        or bool(item_markers & TENANT_ISOLATION_ALIASES)
    )


def _apply_tenant_isolation_marker(item: Item, item_markers: set[str]) -> None:
    if not _is_tenant_isolation_target(item, item_markers):
        return
    if "tenant_isolation" in item_markers:
        return
    item.add_marker("tenant_isolation")
    item_markers.add("tenant_isolation")


def _should_mark_mandatory(item_markers: set[str]) -> bool:
    if "mandatory" in item_markers:
        return False
    if item_markers & MANDATORY_EXCLUSION_MARKERS:
        return False
    return bool(item_markers & MANDATORY_MARKERS)
