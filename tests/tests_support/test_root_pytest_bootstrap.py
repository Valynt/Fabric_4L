"""Unit tests for the root pytest bootstrap helper.

These tests guard the repository-wide test-environment setup logic that lives
in ``tests/support/root_pytest_bootstrap.py``.  Because this module is imported
by every pytest run via the root ``conftest.py``, regressions here have very
high blast radius.
"""

from __future__ import annotations

import os

import pytest

from tests.support.root_pytest_bootstrap import (
    _FAIL_CLOSED_TEST_DEFAULTS,
    _TEST_ENV,
    bootstrap_root_pytest,
    _install_test_environment,
)

pytestmark = [pytest.mark.unit]


class TestInstallTestEnvironment:
    """``_install_test_environment`` must set required env vars safely."""

    def test_sets_all_required_test_environment_variables(self, monkeypatch):
        """Every key in _TEST_ENV is written to os.environ."""
        for key in _TEST_ENV:
            monkeypatch.delenv(key, raising=False)

        _install_test_environment()

        for key, value in _TEST_ENV.items():
            assert os.environ[key] == value

    def test_overwrites_existing_required_variables(self, monkeypatch):
        """_TEST_ENV values are authoritative and replace prior values."""
        key = next(iter(_TEST_ENV))
        monkeypatch.setenv(key, "should-be-replaced")

        _install_test_environment()

        assert os.environ[key] == _TEST_ENV[key]

    def test_applies_fail_closed_defaults_only_when_absent(self, monkeypatch):
        """Fail-closed defaults use setdefault so explicit values are preserved."""
        key = next(iter(_FAIL_CLOSED_TEST_DEFAULTS))
        explicit_value = "explicit-" + key
        monkeypatch.setenv(key, explicit_value)

        _install_test_environment()

        assert os.environ[key] == explicit_value

    def test_applies_fail_closed_defaults_when_absent(self, monkeypatch):
        """Fail-closed defaults are written when no value is present."""
        for key in _FAIL_CLOSED_TEST_DEFAULTS:
            monkeypatch.delenv(key, raising=False)

        _install_test_environment()

        for key, value in _FAIL_CLOSED_TEST_DEFAULTS.items():
            assert os.environ[key] == value


class TestBootstrapRootPytest:
    """``bootstrap_root_pytest`` is the public entrypoint used by conftest."""

    def test_bootstrap_installs_test_environment(self, monkeypatch):
        """bootstrap_root_pytest delegates to _install_test_environment."""
        called = []

        def fake_install():
            called.append(True)

        monkeypatch.setattr(
            "tests.support.root_pytest_bootstrap._install_test_environment",
            fake_install,
        )

        bootstrap_root_pytest()

        assert called == [True]
