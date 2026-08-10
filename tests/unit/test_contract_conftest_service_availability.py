"""Regression tests for contract service-availability gating behavior."""

from __future__ import annotations

import urllib.error

import pytest
from tests.contract import conftest as contract_conftest


def test_local_default_missing_services(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_unavailable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise urllib.error.URLError("unreachable")

    monkeypatch.setattr(contract_conftest.urllib.request, "urlopen", _raise_unavailable)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CONTRACT_TEST_ENFORCE", raising=False)
    monkeypatch.delenv("CONTRACT_TEST_STRICT", raising=False)
    monkeypatch.delenv("CONTRACT_TEST_MODE", raising=False)

    mock_mode, missing_services, strict_mode = contract_conftest._evaluate_services_availability()

    assert mock_mode is False
    assert strict_mode is False
    assert len(missing_services) == 3


def test_ci_strict_mode_missing_services(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_unavailable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise urllib.error.URLError("unreachable")

    monkeypatch.setattr(contract_conftest.urllib.request, "urlopen", _raise_unavailable)
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("CONTRACT_TEST_MODE", raising=False)

    mock_mode, missing_services, strict_mode = contract_conftest._evaluate_services_availability()

    assert mock_mode is False
    assert strict_mode is True
    assert len(missing_services) == 3


def test_mock_mode_bypasses_service_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    def _unexpected_call(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("urlopen should not be called in CONTRACT_TEST_MODE=mock")

    monkeypatch.setattr(contract_conftest.urllib.request, "urlopen", _unexpected_call)
    monkeypatch.setenv("CONTRACT_TEST_MODE", "mock")
    monkeypatch.setenv("CI", "true")

    mock_mode, missing_services, strict_mode = contract_conftest._evaluate_services_availability()

    assert mock_mode is True
    assert strict_mode is True
    assert missing_services == []
