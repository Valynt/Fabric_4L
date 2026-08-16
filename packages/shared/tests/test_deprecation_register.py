"""Behavior tests for the canonical deprecation register loader.

D1 requires one enforceable source for deprecation/compatibility debt. These
tests encode the intended behavior (a valid register resolves and is typed) and
the intended denied behavior (a missing, malformed, or wrong-schema register
fails visibly instead of silently degrading to an empty register).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from value_fabric.shared.governance.deprecation_register import (
    ITEMS_KEY,
    REGISTER_PATH_ENV_VAR,
    REGISTER_RELATIVE_PATH,
    DeprecationItem,
    DeprecationRegisterError,
    find_item,
    load_items,
    load_register,
    overdue_items,
    removal_date_for,
    resolve_register_path,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_register(tmp_path: Path, payload: object) -> Path:
    register = tmp_path / REGISTER_RELATIVE_PATH
    register.parent.mkdir(parents=True, exist_ok=True)
    register.write_text(json.dumps(payload), encoding="utf-8")
    return register


# --------------------------------------------------------------------------
# Intended allowed behavior
# --------------------------------------------------------------------------


def test_repository_register_resolves_and_loads_typed_items() -> None:
    """The committed register is discoverable and every item is well-formed."""
    assert resolve_register_path() == REPO_ROOT / REGISTER_RELATIVE_PATH

    items = load_items()
    assert items, "the committed register must not be empty"
    assert all(isinstance(item, DeprecationItem) for item in items)
    for item in items:
        assert item.feature
        assert item.removal_date  # parses as a date or raises


def test_repository_register_has_no_unapproved_overdue_items() -> None:
    """Overdue entries must carry an explicit deferral with a rationale."""
    for item in overdue_items():
        pytest.fail(
            f"{item.feature} is overdue ({item.target_removal}) without an "
            "approved deferral rationale"
        )


def test_registered_paths_exist_unless_marked_removed() -> None:
    """A register entry may not point at a path that no longer exists."""
    for item in load_items():
        if not item.path or item.status == "removed":
            continue
        target = REPO_ROOT / item.path.split(":", 1)[0]
        assert target.exists(), f"{item.feature} points at missing path {item.path}"


def test_removal_date_lookup_matches_register_entry(tmp_path: Path, monkeypatch) -> None:
    register = _write_register(
        tmp_path,
        {
            "items": [
                {
                    "feature": "l1.api.example_shim",
                    "target_removal": "2027-01-01",
                    "path": "services/layer1-ingestion/example.py",
                }
            ]
        },
    )
    monkeypatch.setenv(REGISTER_PATH_ENV_VAR, str(register))

    assert removal_date_for("l1.api.example_shim") == "2027-01-01"
    items = load_items()
    assert find_item("example_shim", items=items) is not None
    assert items[0].target_removal == "2027-01-01"


def test_env_var_overrides_register_path(tmp_path: Path, monkeypatch) -> None:
    register = _write_register(tmp_path, {"items": []})
    monkeypatch.setenv(REGISTER_PATH_ENV_VAR, str(register))
    assert resolve_register_path() == register
    assert load_register()[ITEMS_KEY] == []


def test_deferred_item_is_not_reported_overdue() -> None:
    deferred = DeprecationItem(
        feature="x",
        target_removal="2020-01-01",
        status="deferred",
        rationale="governance approved",
    )
    assert deferred.is_deferred
    assert overdue_items(today=date(2026, 1, 1), items=[deferred]) == []


def test_undeferred_past_item_is_reported_overdue() -> None:
    stale = DeprecationItem(feature="x", target_removal="2020-01-01")
    assert not stale.is_deferred
    assert overdue_items(today=date(2026, 1, 1), items=[stale]) == [stale]


# --------------------------------------------------------------------------
# Intended denied behavior — the register must fail visibly
# --------------------------------------------------------------------------


def test_missing_register_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(REGISTER_PATH_ENV_VAR, str(tmp_path / "absent.json"))
    with pytest.raises(DeprecationRegisterError, match="not readable"):
        load_register()


def test_malformed_json_raises(tmp_path: Path, monkeypatch) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv(REGISTER_PATH_ENV_VAR, str(broken))
    with pytest.raises(DeprecationRegisterError, match="not valid JSON"):
        load_register()


def test_wrong_schema_key_raises(tmp_path: Path, monkeypatch) -> None:
    """The historical ``deprecations`` key must not be silently accepted."""
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"deprecations": []}), encoding="utf-8")
    monkeypatch.setenv(REGISTER_PATH_ENV_VAR, str(wrong))
    with pytest.raises(DeprecationRegisterError, match="items"):
        load_register()


def test_non_object_register_raises(tmp_path: Path, monkeypatch) -> None:
    arr = tmp_path / "arr.json"
    arr.write_text(json.dumps([{"feature": "x"}]), encoding="utf-8")
    monkeypatch.setenv(REGISTER_PATH_ENV_VAR, str(arr))
    with pytest.raises(DeprecationRegisterError, match="must be a JSON object"):
        load_register()


def test_item_missing_required_field_raises(tmp_path: Path, monkeypatch) -> None:
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(
        json.dumps({"items": [{"feature": "l1.api.no_date"}]}), encoding="utf-8"
    )
    monkeypatch.setenv(REGISTER_PATH_ENV_VAR, str(incomplete))
    with pytest.raises(DeprecationRegisterError, match="missing required field"):
        load_items()


def test_unregistered_selector_raises_without_default(tmp_path: Path, monkeypatch) -> None:
    """A route may not advertise a sunset date that no register entry backs."""
    register = tmp_path / "empty.json"
    register.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setenv(REGISTER_PATH_ENV_VAR, str(register))
    with pytest.raises(DeprecationRegisterError, match="No deprecation register entry"):
        removal_date_for("l1.api.unregistered_route")


def test_unregistered_selector_honors_explicit_default(tmp_path: Path, monkeypatch) -> None:
    register = tmp_path / "empty.json"
    register.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setenv(REGISTER_PATH_ENV_VAR, str(register))
    assert removal_date_for("l1.api.unregistered_route", default="2099-01-01") == "2099-01-01"
