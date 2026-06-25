"""Unit tests for the externalized pytest policy config loader.

The volatile marker/dependency lists that used to live as Python constants in
``tests/support/root_pytest_policy.py`` are now maintained in
``config/ci/pytest_policy.yaml``.  These tests ensure the file is loadable,
schema-valid, and stable (via snapshot).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tests.support.root_pytest_bootstrap import REPO_ROOT
from tests.support.root_pytest_policy_config import (
    CONFIG_PATH,
    PytestPolicyConfig,
    load_pytest_policy_config,
)

SNAPSHOT_PATH = (
    REPO_ROOT / "tests" / "tests_support" / "snapshots" / "pytest_policy_snapshot.json"
)

pytestmark = [pytest.mark.unit]


def _normalize_config(config: PytestPolicyConfig) -> dict[str, object]:
    """Return a deterministic, JSON-serializable view of the loaded policy."""
    return {
        "mandatory_deps": config.mandatory_deps,
        "tenant_isolation_aliases": sorted(config.tenant_isolation_aliases),
        "tenant_isolation_targets": sorted(config.tenant_isolation_targets),
        "tenant_isolation_nodeids": sorted(config.tenant_isolation_nodeids),
        "mandatory_markers": sorted(config.mandatory_markers),
        "mandatory_exclusion_markers": sorted(config.mandatory_exclusion_markers),
    }


class TestLoadPytestPolicyConfig:
    """The policy loader must parse and validate the canonical YAML file."""

    def test_default_config_path_exists(self):
        assert CONFIG_PATH.exists(), f"Missing policy config: {CONFIG_PATH}"

    def test_loads_default_config(self):
        cfg = load_pytest_policy_config()
        assert isinstance(cfg, PytestPolicyConfig)
        assert cfg.mandatory_deps
        assert cfg.mandatory_markers
        assert cfg.mandatory_exclusion_markers

    def test_expected_entries_present(self):
        """Sanity check that the config still contains the profile markers we rely on."""
        cfg = load_pytest_policy_config()
        assert "unit" in cfg.mandatory_markers
        assert "security" in cfg.mandatory_markers
        assert "tenant_isolation" in cfg.mandatory_markers
        assert "slow" in cfg.mandatory_exclusion_markers
        assert "respx" in cfg.mandatory_deps

    def test_rejects_invalid_config(self, tmp_path: Path):
        invalid = tmp_path / "invalid.yaml"
        invalid.write_text(
            yaml.safe_dump({"schema_version": "1.0"}),
            encoding="utf-8",
        )

        with pytest.raises(Exception):  # jsonschema.ValidationError
            load_pytest_policy_config(invalid)

    def test_raises_for_missing_file(self, tmp_path: Path):
        missing = tmp_path / "missing.yaml"

        with pytest.raises(FileNotFoundError):
            load_pytest_policy_config(missing)


class TestPytestPolicySnapshot:
    """Snapshot guard: intentional config changes must update the snapshot."""

    def test_config_matches_snapshot(self):
        cfg = load_pytest_policy_config()
        actual = _normalize_config(cfg)

        snapshot_text = SNAPSHOT_PATH.read_text(encoding="utf-8")
        expected = json.loads(snapshot_text)

        assert actual == expected, (
            "Policy config drift detected. "
            "If the change is intentional, regenerate the snapshot."
        )
