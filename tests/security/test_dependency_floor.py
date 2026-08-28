"""Encoded security floor: ``cryptography>=50.0.0`` and the Presidio 2.2.362 hold.

The platform security baseline ``cryptography>=50.0.0`` (GHSA-g6cj-pr64-35w5)
sits above Presidio's supported dependency ceiling: presidio releases
>=2.2.363 impose a ``cryptography`` upper bound (2.2.363: <47, 2.2.364: <49)
below that floor, so ``presidio-analyzer``/``presidio-anonymizer`` are held at
``==2.2.362`` and Dependabot ignores only the incompatible range.

These ``contract_static`` tests encode the invariant so a future re-bump cannot
silently regress the floor. Without them the floor is only enforced by accident
at CI install/resolution time. See
``docs/governance/compatibility-debt-registry.md``.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

LAYER1_PYPROJECT = REPO_ROOT / "services" / "layer1-ingestion" / "pyproject.toml"
LAYER1_REQUIREMENTS = REPO_ROOT / "services" / "layer1-ingestion" / "requirements.txt"
DEPENDABOT_CONFIG = REPO_ROOT / ".github" / "dependabot.yml"
GOVERNANCE_RECORD = REPO_ROOT / "docs" / "governance" / "compatibility-debt-registry.md"

CRYPTOGRAPHY_FLOOR = ">=50.0.0"
PRESIDIO_HELD_VERSION = "==2.2.362"
PRESIDIO_INCOMPATIBLE_RANGE = ">=2.2.363"
PRESIDIO_PACKAGES = ("presidio-analyzer", "presidio-anonymizer")

_DEPENDENCY_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*(.*)$")
_VERSION_RE = re.compile(r"(\d+(?:\.\d+)*)")


def _pyproject_entries(pyproject: Path) -> dict[str, str]:
    """Map package name -> specifier from a pyproject ``project.dependencies`` list."""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    entries: dict[str, str] = {}
    for raw in data["project"]["dependencies"]:
        base = raw.split(";", 1)[0].strip()
        match = _DEPENDENCY_RE.match(base)
        assert match is not None, f"unparseable dependency entry: {raw!r}"
        entries[match.group(1).lower()] = match.group(2).strip()
    return entries


def _requirements_entries(requirement: Path) -> dict[str, str]:
    """Map package name -> specifier from a requirements.txt file."""
    entries: dict[str, str] = {}
    for raw in requirement.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        base = line.split(";", 1)[0].strip().split("#", 1)[0].strip()
        match = _DEPENDENCY_RE.match(base)
        assert match is not None, f"unparseable requirements line: {line!r}"
        entries[match.group(1).lower()] = match.group(2).strip()
    return entries


def _specifier_floor(specifier: str) -> tuple[int, ...]:
    version = _VERSION_RE.search(specifier)
    assert version is not None, f"no version in specifier {specifier!r}"
    return tuple(int(part) for part in version.group(1).split("."))


def _assert_cryptography_floor(entries: dict[str, str]) -> None:
    assert "cryptography" in entries, "cryptography dependency missing"
    specifier = entries["cryptography"]
    assert ">=" in specifier, f"cryptography floor must use >=, got {specifier!r}"
    assert _specifier_floor(specifier) >= (50, 0, 0), (
        f"cryptography floor below platform baseline {CRYPTOGRAPHY_FLOOR}: {specifier!r}"
    )


def _assert_presidio_hold(entries: dict[str, str]) -> None:
    for package in PRESIDIO_PACKAGES:
        assert package in entries, f"{package} dependency missing"
        assert entries[package] == PRESIDIO_HELD_VERSION, (
            f"{package} must be held at {PRESIDIO_HELD_VERSION} (got "
            f"{entries[package]!r}); releases >=2.2.363 cap cryptography below "
            f"{CRYPTOGRAPHY_FLOOR}"
        )


@pytest.mark.security
@pytest.mark.contract_static
def test_pyproject_enforces_cryptography_floor() -> None:
    """Allow: layer1 pyproject keeps the platform cryptography security floor."""
    _assert_cryptography_floor(_pyproject_entries(LAYER1_PYPROJECT))


@pytest.mark.security
@pytest.mark.contract_static
def test_pyproject_holds_presidio_at_approved_version() -> None:
    """Deny: presidio must not drift past the held 2.2.362 release."""
    _assert_presidio_hold(_pyproject_entries(LAYER1_PYPROJECT))


@pytest.mark.security
@pytest.mark.contract_static
def test_requirements_txt_mirrors_pyproject_invariants() -> None:
    """Allow: legacy requirements.txt keeps identical floor and presidio pins."""
    requirements = _requirements_entries(LAYER1_REQUIREMENTS)
    _assert_cryptography_floor(requirements)
    _assert_presidio_hold(requirements)
    pyproject = _pyproject_entries(LAYER1_PYPROJECT)
    for package in PRESIDIO_PACKAGES:
        assert requirements[package] == pyproject[package], (
            f"{package} pin drift between requirements.txt and pyproject.toml"
        )


@pytest.mark.security
@pytest.mark.contract_static
def test_dependabot_ignores_only_incompatible_presidio_range() -> None:
    """Deny: Dependabot must ignore >=2.2.363 but keep future releases pickable."""
    config = yaml.safe_load(DEPENDABOT_CONFIG.read_text(encoding="utf-8"))
    layer1_pip_updates = [
        update
        for update in config["updates"]
        if update.get("package-ecosystem") == "pip"
        and update.get("directory") == "/services/layer1-ingestion"
    ]
    assert len(layer1_pip_updates) == 1, "expected exactly one layer1 pip update block"
    ignores = {
        entry["dependency-name"]: entry.get("versions", [])
        for entry in layer1_pip_updates[0].get("ignore", [])
    }
    for package in PRESIDIO_PACKAGES:
        assert ignores.get(package) == [PRESIDIO_INCOMPATIBLE_RANGE], (
            f"Dependabot must ignore exactly {PRESIDIO_INCOMPATIBLE_RANGE} for "
            f"{package}, not a blanket ignore"
        )


@pytest.mark.security
@pytest.mark.contract_static
def test_governance_record_archives_upstream_constraint() -> None:
    """Allow: the compatibility-debt registry documents the hold and removal condition."""
    record = GOVERNANCE_RECORD.read_text(encoding="utf-8")
    assert "presidio-analyzer" in record
    assert "2.2.362" in record
    assert "cryptography>=50.0.0" in record
    assert ">=2.2.363" in record
    assert "Remove the `==2.2.362` hold" in record
