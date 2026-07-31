"""Regression tests for contract service-availability gating behavior."""

from __future__ import annotations

import urllib.error

import pytest
from tests.contract import conftest as contract_conftest


def test_local_default_missing_services(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_unavailable(*args: object, **kwargs: object) -> None:
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
    def _raise_unavailable(*args: object, **kwargs: object) -> None:
        raise urllib.error.URLError("unreachable")

    monkeypatch.setattr(contract_conftest.urllib.request, "urlopen", _raise_unavailable)
    monkeypatch.setenv("CI", "true")
    monkeypatch.delenv("CONTRACT_TEST_MODE", raising=False)

    mock_mode, missing_services, strict_mode = contract_conftest._evaluate_services_availability()

    assert mock_mode is False
    assert strict_mode is True
    assert len(missing_services) == 3


def test_live_service_checks_use_canonical_public_health_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []

    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _record_url(request: urllib.request.Request, timeout: float) -> Response:
        observed.append(request.full_url)
        return Response()

    monkeypatch.setattr(contract_conftest.urllib.request, "urlopen", _record_url)
    monkeypatch.delenv("CONTRACT_TEST_MODE", raising=False)
    monkeypatch.setenv("LAYER3_API_URL", "http://layer3:8003")
    monkeypatch.setenv("LAYER4_API_URL", "http://layer4:8004")
    monkeypatch.setenv("LAYER5_API_URL", "http://layer5:8005")

    _, missing_services, _ = contract_conftest._evaluate_services_availability()

    assert missing_services == []
    assert observed == [
        "http://layer3:8003/health",
        "http://layer4:8004/health",
        "http://layer5:8005/health",
    ]


def test_mock_mode_bypasses_service_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    def _unexpected_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("urlopen should not be called in CONTRACT_TEST_MODE=mock")

    monkeypatch.setattr(contract_conftest.urllib.request, "urlopen", _unexpected_call)
    monkeypatch.setenv("CONTRACT_TEST_MODE", "mock")
    monkeypatch.setenv("CI", "true")

    mock_mode, missing_services, strict_mode = contract_conftest._evaluate_services_availability()

    assert mock_mode is True
    assert strict_mode is True
    assert missing_services == []
