"""Tests for the Docker/testcontainers fail-closed skip gate in the layer4 conftest.

The gate is the collection hook that keeps local layer4 runs deterministic when
Docker/testcontainers are unavailable while still failing closed when the
``LAYER4_REQUIRE_TESTCONTAINERS=1`` lane is explicitly requested. These checks
pin the intended behavior without depending on the host machine's Docker state.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_LAYER4_TESTS_DIR = Path(__file__).resolve().parent
_CONFTEXT_PATH = _LAYER4_TESTS_DIR / "conftest.py"

_conftest = next(
    (
        module
        for module in sys.modules.values()
        if getattr(module, "__file__", None) == str(_CONFTEXT_PATH)
    ),
    None,
)
if _conftest is None:
    spec = importlib.util.spec_from_file_location("layer4_tests_conftest", _CONFTEXT_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"Could not load layer4 conftest from {_CONFTEXT_PATH}")
    _conftest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_conftest)
    sys.modules[spec.name] = _conftest

conftest = _conftest


class _StubItem:
    """Minimal stand-in for a collected pytest item.

    The production hook only checks ``item.keywords`` and calls
    ``item.add_marker(...)``.
    """

    def __init__(self, keywords: set[str] | None = None) -> None:
        self.keywords = set(keywords) if keywords else set()
        self.added_markers: list = []

    def add_marker(self, marker) -> None:
        self.added_markers.append(marker)


class _StubConfig:
    """Minimal stand-in for the pytest ``Config`` used by the gate."""

    def __init__(self) -> None:
        self.warnings: list = []

    def issue_config_time_warning(self, warning, stacklevel: int = 1) -> None:
        self.warnings.append(warning)


@pytest.mark.parametrize(
    "raw",
    ["1", "true", "yes", "TRUE", "  true ", "1\n", "Yes"],
)
@pytest.mark.unit
def test_testcontainers_required_true_for_truthy_env_variants(raw, monkeypatch):
    """Truthy env values force the lane on."""
    monkeypatch.setenv("LAYER4_REQUIRE_TESTCONTAINERS", raw)
    assert conftest._testcontainers_required() is True


@pytest.mark.parametrize("raw", ["0", "no", "false", "False", "NO", " 0 "])
@pytest.mark.unit
def test_testcontainers_required_false_for_falsy_env_variants(raw, monkeypatch):
    """Falsy env values do not force the lane on."""
    monkeypatch.setenv("LAYER4_REQUIRE_TESTCONTAINERS", raw)
    assert conftest._testcontainers_required() is False


@pytest.mark.unit
def test_testcontainers_required_false_when_env_unset(monkeypatch):
    """An unset env var keeps the lane off."""
    monkeypatch.delenv("LAYER4_REQUIRE_TESTCONTAINERS", raising=False)
    assert conftest._testcontainers_required() is False


@pytest.mark.unit
def test_require_testcontainers_fails_closed_when_runtime_missing(monkeypatch):
    """Forced Docker/testcontainers lane raises UsageError when runtimes are absent."""
    monkeypatch.setenv("LAYER4_REQUIRE_TESTCONTAINERS", "1")
    monkeypatch.setattr(conftest, "POSTGRES_AVAILABLE", False)
    monkeypatch.setattr(conftest, "DOCKER_AVAILABLE", False)

    items = [_StubItem({"postgres"})]

    with pytest.raises(pytest.UsageError, match=r"LAYER4_REQUIRE_TESTCONTAINERS.*VF-SKIP-119"):
        conftest.pytest_collection_modifyitems(_StubConfig(), items)


@pytest.mark.unit
def test_skip_gate_warns_and_skips_only_postgres_items_when_postgres_missing(monkeypatch):
    """Missing postgres skips postgres-only items and emits the config-time warning."""
    monkeypatch.delenv("LAYER4_REQUIRE_TESTCONTAINERS", raising=False)
    monkeypatch.setattr(conftest, "POSTGRES_AVAILABLE", False)
    monkeypatch.setattr(conftest, "DOCKER_AVAILABLE", False)

    postgres_item = _StubItem({"postgres"})
    docker_item = _StubItem({"docker"})
    plain_item = _StubItem(set())
    config = _StubConfig()

    conftest.pytest_collection_modifyitems(config, [postgres_item, docker_item, plain_item])

    assert len(postgres_item.added_markers) == 1
    assert len(docker_item.added_markers) == 0
    assert len(plain_item.added_markers) == 0
    assert len(config.warnings) == 1
    assert "Skipped 1" in str(config.warnings[0])


@pytest.mark.unit
def test_skip_gate_skips_docker_and_postgres_when_only_postgres_present(monkeypatch):
    """If postgres is present but Docker is not, both postgres and docker items are skipped."""
    monkeypatch.delenv("LAYER4_REQUIRE_TESTCONTAINERS", raising=False)
    monkeypatch.setattr(conftest, "POSTGRES_AVAILABLE", True)
    monkeypatch.setattr(conftest, "DOCKER_AVAILABLE", False)

    postgres_item = _StubItem({"postgres"})
    docker_item = _StubItem({"docker"})
    plain_item = _StubItem(set())
    config = _StubConfig()

    conftest.pytest_collection_modifyitems(config, [postgres_item, docker_item, plain_item])

    assert len(postgres_item.added_markers) == 1
    assert len(docker_item.added_markers) == 1
    assert len(plain_item.added_markers) == 0
    assert len(config.warnings) == 1
    assert "Skipped 2" in str(config.warnings[0])


@pytest.mark.unit
def test_skip_gate_stays_quiet_when_all_runtimes_present(monkeypatch):
    """When both runtimes are available, no items are skipped and no warning is emitted."""
    monkeypatch.delenv("LAYER4_REQUIRE_TESTCONTAINERS", raising=False)
    monkeypatch.setattr(conftest, "POSTGRES_AVAILABLE", True)
    monkeypatch.setattr(conftest, "DOCKER_AVAILABLE", True)

    items = [_StubItem({"postgres"}), _StubItem({"docker"}), _StubItem(set())]
    config = _StubConfig()

    conftest.pytest_collection_modifyitems(config, items)

    assert all(len(item.added_markers) == 0 for item in items)
    assert config.warnings == []
