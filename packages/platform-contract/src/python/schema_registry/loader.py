"""Registry loader: reads registry.yaml and compatibility-policy.yaml into Pydantic models."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from .models import CompatibilityPolicyDoc, RegistryCatalog, SchemaRecord

DEFAULT_REGISTRY_PATH = Path("contracts/jsonschema/registry.yaml")
DEFAULT_POLICY_PATH = Path("contracts/jsonschema/compatibility-policy.yaml")


class RegistryLoader:
    """Load and validate the schema registry catalog and policy documents."""

    def __init__(
        self,
        registry_path: Path | str | None = None,
        policy_path: Path | str | None = None,
        repo_root: Path | str | None = None,
    ) -> None:
        self.repo_root = Path(repo_root or os.getcwd())
        self.registry_path = self.repo_root / (registry_path or DEFAULT_REGISTRY_PATH)
        self.policy_path = self.repo_root / (policy_path or DEFAULT_POLICY_PATH)

    def load_policy(self) -> CompatibilityPolicyDoc:
        raw = _load_yaml(self.policy_path)
        return CompatibilityPolicyDoc(**raw)

    def load_catalog(self) -> RegistryCatalog:
        raw = _load_yaml(self.registry_path)
        # Validate policy first
        policy = self.load_policy()
        raw["policies"] = policy
        return RegistryCatalog(**raw)

    def load_artifact(self, record: SchemaRecord) -> dict[str, Any]:
        artifact_path = self.repo_root / record.artifact
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")
        return json.loads(artifact_path.read_text(encoding="utf-8"))

    def verify_content_hashes(self, catalog: RegistryCatalog | None = None) -> list[str]:
        """Return list of schema keys whose content_hash does not match the artifact file."""
        if catalog is None:
            catalog = self.load_catalog()
        mismatches: list[str] = []
        for record in catalog.schemas:
            artifact_path = self.repo_root / record.artifact
            if not artifact_path.exists():
                mismatches.append(record.key())
                continue
            expected = record.content_hash
            actual = record.compute_content_hash(artifact_path)
            if expected and expected != actual:
                mismatches.append(record.key())
        return mismatches


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
