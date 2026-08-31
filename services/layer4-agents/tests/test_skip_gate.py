"""Automated tests for the Docker/testcontainers fail-closed skip gate in conftest.

The gate (``conftest.pytest_collection_modifyitems``) is the mechanism that
keeps local layer4 runs deterministic when Docker/testcontainers are missing
while failing closed in the ``LAYER4_REQUIRE_TESTCONTAINERS=1`` lane. Its core
behavior used to be verified only by manual invocation, so these tests pin it:

* fail-closed: the require-testcontainers env var + missing runtime raises.
* skip + warn: missing runtimes skip the gated items and emit a config-time
  warning that reports how many items were skipped.
* empty when nothing is gated: every runtime present, nothing skipped or warned.

All cases are environment-deterministic: availability flags and env vars are
injected via ``monkeypatch``, and the gate is invoked directly on stub items so
the tests never depend on the host machine's Docker/postgres state.
"""

import sys

import pytest

# pytest preloads the root conftest before collecting this module; bind it by
# name so the tests call the exact production hook that ships with the suite.
try:
    import conftest
except ImportError:  # pragma: no cover - defensive fallback
    conftest = sys.modules.get("conftest")
    if conftest is None:  # pragma: no cover
        raise


class _StubItem:
    """Minimal stand-in for a collected pytest item.

    The gate inspects ``item.keywords`` with ``in`` and calls
    ``item.add_marker(...)``, which is all the production hook touches.
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
    """Any case/space variant of the truthy values forces the lane on."""
    monkeypatch.setenv("LAYER4_REQUIRE_TESTCONTAINERS", raw)
    assert conftest._testcontainers_required() is True


@pytest.mark.parametrize("raw", ["0", "no", "false", "False", "NO", " 0 "])
@pytest.mark.unit
def test_testcontainers_required_false_for_falsy_env_variants(raw, monkeypatch):
    """Unrecognised values are not treated as a demand for the lane."""
    monkeypatch.setenv("LAYER4_REQUIRE_TESTCONTAINERS", raw)
    assert conftest._testcontainers_required() is False


@pytest.mark.unit
def test_testcontainers_required_false_when_env_unset(monkeypatch):
    """Absent env var means the lane is not forced."""
    monkeypatch.delenv("LAYER4_REQUIRE_TESTCONTAINERS", raising=False)
    assert conftest._testcontainers_required() is False


@pytest.mark.unit
def test_require_testcontainers_fails_closed_when_runtime_missing(monkeypatch):
    """VF-SKIP-119/120: forced testcontainers lane + missing runtime = UsageError."""
    monkeypatch.setenv("LAYER4_REQUIRE_TESTCONTAINERS", "1")
    monkeypatch.setattr(conftest, "POSTGRES_AVAILABLE", False)
    monkeypatch.setattr(conftest, "DOCKER_AVAILABLE", False)

    items = [_StubItem({"postgres"})]

    with pytest.raises(pytest.UsageError, match=r"LAYER4_REQUIRE_TESTCONTAINERS.*VF-SKIP-119"):
        conftest.pytest_collection_modifyitems(_StubConfig(), items)


@pytest.mark.unit
def test_skip_gate_warns_and_skips_only_postgres_items_when_postgres_missing(
    monkeypatch,
):
    """Missing postgres skips postgres items only (the docker elif is unreachable)."""
    monkeypatch.delenv("LAYER4_REQUIRE_TESTCONTAINERS", raising=False)
    monkeypatch.setattr(conftest, "POSTGRES_AVAILABLE", False)
    monkeypatch.setattr(conftest, "DOCKER_AVAILABLE", False)

    postgres_item = _StubItem({"postgres"})
    docker_item = _StubItem({"docker"})
    plain_item = _StubItem(set())
    config = _StubConfig()

    conftest.pytest_collection_modifyitems(config, [postgres_item, docker_item, plain_item])

    assert len(postgres_item.added_markers) == 1
    assert len(docker_item.added_markers) == 0  # docker-only item is not gated here
    assert len(plain_item.added_markers) == 0
    assert len(config.warnings) == 1
    assert "Skipped 1" in str(config.warnings[0])


@pytest.mark.unit
def test_skip_gate_skips_docker_and_postgres_when_only_postgres_present(monkeypatch):
    """Postgres present but Docker missing exercises the elif (both kinds skipped)."""
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
    """Fully available runtimes: no skips, no warnings, no fail-closed path."""
    monkeypatch.delenv("LAYER4_REQUIRE_TESTCONTAINERS", raising=False)
    monkeypatch.setattr(conftest, "POSTGRES_AVAILABLE", True)
    monkeypatch.setattr(conftest, "DOCKER_AVAILABLE", True)

    items = [_StubItem({"postgres"}), _StubItem({"docker"}), _StubItem(set())]
    config = _StubConfig()

    conftest.pytest_collection_modifyitems(config, items)

    assert all(len(item.added_markers) == 0 for item in items)
    assert config.warnings == []