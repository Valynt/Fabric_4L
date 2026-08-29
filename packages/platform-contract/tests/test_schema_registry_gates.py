"""Integration tests for CI gate scripts."""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure package importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "python"))

# Ensure scripts/ci is importable
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ci"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "platform-contract" / "src" / "python"))

import check_schema_registry_integrity
import check_schema_refs

from schema_registry.models import (
    CompatibilityPolicyDoc,
    CompatibilityPolicy,
    LifecycleStatus,
    Owner,
    SchemaKind,
    SchemaRecord,
    RegistryCatalog,
)


def _make_record(schema_id: str, version: str, artifact: str, status: LifecycleStatus = LifecycleStatus.PUBLISHED) -> SchemaRecord:
    return SchemaRecord(
        schema_id=schema_id,
        version=version,
        kind=SchemaKind.COMMON_VALUE_OBJECT,
        domain="common",
        owner=Owner(team="platform/contracts"),
        status=status,
        artifact=artifact,
        published_at=datetime.datetime.now(datetime.timezone.utc),
        examples=[],
    )


def test_gate_integrity_missing_artifact(tmp_path: Path) -> None:
    """check_schema_registry_integrity should fail when artifact is missing."""
    catalog = RegistryCatalog(
        schemas=[
            _make_record("common.value.money", "1.0.0", "contracts/jsonschema/common/v1/money.schema.json"),
        ],
        policies=CompatibilityPolicyDoc(
            version="1.0.0",
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            default_policy=CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR,
            policies=[],
            lifecycle_transitions=[
                {"from_status": "DRAFT", "to_status": "REVIEW", "allowed": True, "requires_review": True},
                {"from_status": "REVIEW", "to_status": "PUBLISHED", "allowed": True},
                {"from_status": "PUBLISHED", "to_status": "DEPRECATED", "allowed": True},
                {"from_status": "DEPRECATED", "to_status": "RETIRED", "allowed": True},
                {"from_status": "PUBLISHED", "to_status": "DRAFT", "allowed": False},
            ],
        ),
    )

    registry_path = tmp_path / "registry.yaml"
    import yaml
    registry_path.write_text(yaml.safe_dump(catalog.model_dump(mode="json")), encoding="utf-8")

    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(yaml.safe_dump(catalog.policies.model_dump(mode="json")), encoding="utf-8")

    exit_code = check_schema_registry_integrity.run(registry_path=registry_path, policy_path=policy_path, repo_root=tmp_path)
    assert exit_code == 1


def test_gate_refs_unresolved(tmp_path: Path) -> None:
    """check_schema_refs should fail on unresolved $ref."""
    artifact_dir = tmp_path / "contracts" / "jsonschema" / "common" / "v1"
    artifact_dir.mkdir(parents=True)
    bad_path = artifact_dir / "bad.schema.json"
    bad_path.write_text(
        json.dumps({
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://valuefabric.ai/contracts/jsonschema/common/v1/bad.schema.json",
            "type": "object",
            "properties": {"ref": {"$ref": "https://valuefabric.ai/contracts/jsonschema/common/v1/missing.schema.json"}},
        }),
        encoding="utf-8",
    )

    catalog = RegistryCatalog(
        schemas=[
            _make_record("common.value.bad", "1.0.0", str(bad_path.relative_to(tmp_path))),
        ],
        policies=CompatibilityPolicyDoc(
            version="1.0.0",
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            default_policy=CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR,
            policies=[],
            lifecycle_transitions=[],
        ),
    )

    registry_path = tmp_path / "registry.yaml"
    import yaml
    registry_path.write_text(yaml.safe_dump(catalog.model_dump(mode="json")), encoding="utf-8")
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(yaml.safe_dump(catalog.policies.model_dump(mode="json")), encoding="utf-8")

    exit_code = check_schema_refs.run(registry_path=registry_path, policy_path=policy_path, repo_root=tmp_path)
    assert exit_code == 1
