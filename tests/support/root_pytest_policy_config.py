"""Loader for the externalized repository-level pytest policy config.

Policy data lives in ``config/ci/pytest_policy.yaml`` and is validated against
``config/ci/pytest_policy.schema.json``.  Keeping the data out of
``root_pytest_policy.py`` reduces churn in that high-dependecy file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import validate

from tests.support.root_pytest_bootstrap import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "config" / "ci" / "pytest_policy.yaml"
SCHEMA_PATH = REPO_ROOT / "config" / "ci" / "pytest_policy.schema.json"


class PytestPolicyConfig:
    """Normalized view of ``pytest_policy.yaml``."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.mandatory_deps: dict[str, str] = dict(data["mandatory_deps"])
        self.tenant_isolation_aliases: frozenset[str] = frozenset(
            data["tenant_isolation"]["aliases"]
        )
        self.tenant_isolation_targets: frozenset[str] = frozenset(
            data["tenant_isolation"]["target_paths"]
        )
        self.tenant_isolation_nodeids: frozenset[str] = frozenset(
            data["tenant_isolation"]["target_nodeids"]
        )
        self.mandatory_markers: frozenset[str] = frozenset(data["mandatory_markers"])
        self.mandatory_exclusion_markers: frozenset[str] = frozenset(
            data["mandatory_exclusion_markers"]
        )


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_pytest_policy_config(path: Path | None = None) -> PytestPolicyConfig:
    """Load and schema-validate the policy config.

    Args:
        path: Override config path (used by tests).  Defaults to ``CONFIG_PATH``.

    Raises:
        FileNotFoundError: if the config or schema file is missing.
        jsonschema.ValidationError: if the config does not match the schema.
    """
    config_path = path or CONFIG_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    schema = _load_schema()
    validate(instance=raw, schema=schema)
    return PytestPolicyConfig(raw)
