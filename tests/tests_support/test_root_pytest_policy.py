"""Unit tests for the root pytest policy hooks.

This module tests the repository-wide marker/dependency policy engine that is
imported by the root ``conftest.py``.  A regression here can change which tests
run in CI, so these tests are marked ``unit`` and must be part of the mandatory
profile.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.support.root_pytest_bootstrap import REPO_ROOT
from tests.support.root_pytest_policy import (
    MANDATORY_DEPS,
    MANDATORY_MARKERS,
    TENANT_ISOLATION_TARGETS,
    add_root_pytest_options,
    apply_collection_markers,
    enforce_mandatory_dependencies,
    _is_central_security_aggregation_run,
    _is_tenant_isolation_target,
    _should_mark_mandatory,
    _skip_mandatory_dep_check,
)

pytestmark = [pytest.mark.unit]


class FakeMarker:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeItem:
    """Minimal stand-in for ``_pytest.nodes.Item``.

    The real item API exposes ``nodeid``, ``fspath``, ``iter_markers``, and
    ``add_marker``.  We only implement the parts the policy functions use.
    """

    def __init__(
        self, nodeid: str, fspath: Path, marker_names: list[str] | None = None
    ) -> None:
        self.nodeid = nodeid
        self.fspath = fspath
        self._markers = [FakeMarker(n) for n in (marker_names or [])]

    def iter_markers(self, name: str | None = None):
        for marker in self._markers:
            if name is None or marker.name == name:
                yield marker

    def add_marker(self, marker: str | Any) -> None:
        marker_name = marker.name if hasattr(marker, "name") else str(marker)
        self._markers.append(FakeMarker(marker_name))

    def marker_names(self) -> list[str]:
        return [m.name for m in self._markers]


class FakeParser:
    def __init__(self) -> None:
        self.options: list[tuple[str, dict[str, Any]]] = []

    def addoption(self, *args, **kwargs) -> None:
        self.options.append((args, kwargs))


class FakeConfig:
    def __init__(
        self,
        no_mandatory_dep_check: bool = False,
        collectonly: bool = False,
        args: tuple[str, ...] = (),
    ) -> None:
        self.option = FakeOption(no_mandatory_dep_check, collectonly)
        self.args = args


class FakeOption:
    def __init__(
        self, no_mandatory_dep_check: bool = False, collectonly: bool = False
    ) -> None:
        self.no_mandatory_dep_check = no_mandatory_dep_check
        self.collectonly = collectonly


class TestAddRootPytestOptions:
    """The root pytest CLI options must be registered reliably."""

    def test_registers_no_mandatory_dep_check_option(self):
        parser = FakeParser()

        add_root_pytest_options(parser)

        assert len(parser.options) == 1
        args, kwargs = parser.options[0]
        assert "--no-mandatory-dep-check" in args
        assert kwargs.get("action") == "store_true"
        assert "collect-only dry runs" in kwargs.get("help", "")


class TestSkipMandatoryDepCheck:
    """The mandatory-dependency gate can be bypassed in controlled situations."""

    def test_skips_when_option_set(self):
        config = FakeConfig(no_mandatory_dep_check=True)
        assert _skip_mandatory_dep_check(config) is True

    def test_skips_during_collection_only(self):
        config = FakeConfig(collectonly=True)
        assert _skip_mandatory_dep_check(config) is True

    def test_skips_for_central_security_aggregation_run(self):
        config = FakeConfig(args=("tests/security",))
        assert _skip_mandatory_dep_check(config) is True

    def test_does_not_skip_for_normal_run(self):
        config = FakeConfig(args=("tests/unit",))
        assert _skip_mandatory_dep_check(config) is False


class TestIsCentralSecurityAggregationRun:
    def test_true_when_only_security_dir_requested(self):
        config = FakeConfig(args=("tests/security",))
        assert _is_central_security_aggregation_run(config) is True

    def test_true_with_trailing_slash(self):
        config = FakeConfig(args=("tests/security/",))
        assert _is_central_security_aggregation_run(config) is True

    def test_false_for_empty_args(self):
        config = FakeConfig(args=())
        assert _is_central_security_aggregation_run(config) is False

    def test_false_for_mixed_targets(self):
        config = FakeConfig(args=("tests/security", "tests/unit"))
        assert _is_central_security_aggregation_run(config) is False


class TestEnforceMandatoryDependencies:
    """Mandatory dependencies must be present or the suite fails fast."""

    def test_passes_when_all_deps_present(self, monkeypatch):
        monkeypatch.setattr(
            "tests.support.root_pytest_policy.importlib.util.find_spec",
            lambda name: object(),
        )
        config = FakeConfig()

        # Should not raise.
        enforce_mandatory_dependencies(config)

    def test_exits_when_deps_missing(self, monkeypatch):
        missing_name = next(iter(MANDATORY_DEPS))

        def fake_find_spec(name: str):
            return None if name == missing_name else object()

        monkeypatch.setattr(
            "tests.support.root_pytest_policy.importlib.util.find_spec",
            fake_find_spec,
        )
        config = FakeConfig()

        with pytest.raises(SystemExit) as exc_info:
            enforce_mandatory_dependencies(config)

        assert missing_name in str(exc_info.value)
        assert "Mandatory test dependencies are missing" in str(exc_info.value)

    def test_skipped_when_no_mandatory_dep_check_is_set(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "tests.support.root_pytest_policy.importlib.util.find_spec",
            lambda name: calls.append(name) or None,
        )
        config = FakeConfig(no_mandatory_dep_check=True)

        enforce_mandatory_dependencies(config)

        assert calls == []


class TestIsTenantIsolationTarget:
    """Tenant-isolation targets are identified by path, nodeid, or marker alias."""

    def test_matches_known_target_path(self):
        target_path = next(iter(TENANT_ISOLATION_TARGETS))
        item = FakeItem(
            nodeid=target_path + "::test_foo",
            fspath=REPO_ROOT / target_path,
        )
        assert _is_tenant_isolation_target(item, set()) is True

    def test_matches_tenant_boundary_alias(self):
        item = FakeItem(
            nodeid="tests/unit/test_foo.py::test_bar",
            fspath=REPO_ROOT / "tests/unit/test_foo.py",
            marker_names=["tenant_boundary"],
        )
        assert _is_tenant_isolation_target(item, {"tenant_boundary"}) is True

    def test_non_target_returns_false(self):
        item = FakeItem(
            nodeid="tests/unit/test_foo.py::test_bar",
            fspath=REPO_ROOT / "tests/unit/test_foo.py",
            marker_names=["unit"],
        )
        assert _is_tenant_isolation_target(item, {"unit"}) is False


class TestShouldMarkMandatory:
    """``mandatory`` marker is applied only to tests in the CI-relevant profile."""

    @pytest.mark.parametrize("marker", sorted(MANDATORY_MARKERS))
    def test_marks_mandatory_profile_markers(self, marker: str):
        assert _should_mark_mandatory({marker}) is True

    def test_does_not_duplicate_existing_mandatory(self):
        assert _should_mark_mandatory({"mandatory", "unit"}) is False

    @pytest.mark.parametrize(
        "exclusion",
        ["slow", "requires_postgres", "requires_neo4j", "e2e", "integration"],
    )
    def test_excludes_optional_infra_markers(self, exclusion: str):
        assert _should_mark_mandatory({"unit", exclusion}) is False


class TestApplyCollectionMarkers:
    """The collection modifier applies tenant-isolation and mandatory markers."""

    def test_tenant_target_gets_tenant_isolation_and_mandatory(self):
        target_path = next(iter(TENANT_ISOLATION_TARGETS))
        item = FakeItem(
            nodeid=target_path + "::test_isolation",
            fspath=REPO_ROOT / target_path,
            marker_names=["unit"],
        )

        apply_collection_markers([item])

        assert "tenant_isolation" in item.marker_names()
        assert "mandatory" in item.marker_names()

    def test_non_target_unit_test_gets_mandatory_only(self):
        item = FakeItem(
            nodeid="tests/unit/test_foo.py::test_bar",
            fspath=REPO_ROOT / "tests/unit/test_foo.py",
            marker_names=["unit"],
        )

        apply_collection_markers([item])

        assert "mandatory" in item.marker_names()
        assert "tenant_isolation" not in item.marker_names()

    def test_optional_test_does_not_get_mandatory(self):
        item = FakeItem(
            nodeid="tests/integration/test_foo.py::test_bar",
            fspath=REPO_ROOT / "tests/integration/test_foo.py",
            marker_names=["unit", "slow"],
        )

        apply_collection_markers([item])

        assert "mandatory" not in item.marker_names()

    def test_no_duplicate_tenant_isolation_marker(self):
        target_path = next(iter(TENANT_ISOLATION_TARGETS))
        item = FakeItem(
            nodeid=target_path + "::test_isolation",
            fspath=REPO_ROOT / target_path,
            marker_names=["tenant_isolation"],
        )

        apply_collection_markers([item])

        assert item.marker_names().count("tenant_isolation") == 1

    def test_no_duplicate_mandatory_marker(self):
        item = FakeItem(
            nodeid="tests/unit/test_foo.py::test_bar",
            fspath=REPO_ROOT / "tests/unit/test_foo.py",
            marker_names=["mandatory", "unit"],
        )

        apply_collection_markers([item])

        assert item.marker_names().count("mandatory") == 1
