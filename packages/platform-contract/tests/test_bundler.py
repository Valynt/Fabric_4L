"""Tests for schema_registry.bundler and schema_registry.impact."""

from __future__ import annotations

import datetime
import json
import tempfile
from pathlib import Path

import pytest

from schema_registry.bundler import BundleBuilder
from schema_registry.loader import RegistryLoader
from schema_registry.models import (
    LifecycleStatus,
    Owner,
    SchemaKind,
    SchemaRecord,
    RegistryCatalog,
    CompatibilityPolicyDoc,
    CompatibilityPolicy,
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


def test_build_bundle(tmp_path: Path) -> None:
    # Create a temporary artifact
    artifact_dir = tmp_path / "contracts" / "jsonschema" / "common" / "v1"
    artifact_dir.mkdir(parents=True)
    artifact_path = artifact_dir / "money.schema.json"
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://valuefabric.ai/contracts/jsonschema/common/v1/money.schema.json",
        "title": "Money",
        "type": "object",
        "properties": {
            "currency": {"type": "string"},
            "amount": {"type": "string"},
        },
        "required": ["currency", "amount"],
        "additionalProperties": False,
    }
    artifact_path.write_text(json.dumps(schema), encoding="utf-8")

    catalog = RegistryCatalog(
        schemas=[
            _make_record("common.value.money", "1.0.0", str(artifact_path.relative_to(tmp_path))),
        ],
        policies=CompatibilityPolicyDoc(
            version="1.0.0",
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            default_policy=CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR,
            policies=[],
            lifecycle_transitions=[],
        ),
    )

    builder = BundleBuilder(loader=RegistryLoader(repo_root=tmp_path))
    bundle = builder.build_bundle(catalog)
    assert bundle["_bundle_meta"]["schema_count"] == 1
    assert "https://valuefabric.ai/contracts/jsonschema/common/v1/money.schema.json" in bundle


def test_verify_bundle_refs_unresolved(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "contracts" / "jsonschema" / "common" / "v1"
    artifact_dir.mkdir(parents=True)
    artifact_path = artifact_dir / "bad.schema.json"
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://valuefabric.ai/contracts/jsonschema/common/v1/bad.schema.json",
        "type": "object",
        "properties": {
            "ref": {"$ref": "https://valuefabric.ai/contracts/jsonschema/common/v1/nonexistent.schema.json"},
        },
    }
    artifact_path.write_text(json.dumps(schema), encoding="utf-8")

    catalog = RegistryCatalog(
        schemas=[
            _make_record("common.value.bad", "1.0.0", str(artifact_path.relative_to(tmp_path))),
        ],
        policies=CompatibilityPolicyDoc(
            version="1.0.0",
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            default_policy=CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR,
            policies=[],
            lifecycle_transitions=[],
        ),
    )

    builder = BundleBuilder(loader=RegistryLoader(repo_root=tmp_path))
    bundle = builder.build_bundle(catalog)
    unresolved = builder.verify_bundle_refs(bundle)
    assert unresolved
    assert any("nonexistent" in u for u in unresolved)


def test_build_lockfile(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "contracts" / "jsonschema" / "common" / "v1"
    artifact_dir.mkdir(parents=True)
    artifact_path = artifact_dir / "money.schema.json"
    artifact_path.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    catalog = RegistryCatalog(
        schemas=[
            _make_record("common.value.money", "1.0.0", str(artifact_path.relative_to(tmp_path))),
        ],
        policies=CompatibilityPolicyDoc(
            version="1.0.0",
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            default_policy=CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR,
            policies=[],
            lifecycle_transitions=[],
        ),
    )

    builder = BundleBuilder(loader=RegistryLoader(repo_root=tmp_path))
    lockfile = builder.build_lockfile(catalog)
    assert lockfile["lockfile_version"] == "1.0.0"
    assert len(lockfile["entries"]) == 1
    entry = lockfile["entries"][0]
    assert entry["schema_id"] == "common.value.money"
    assert entry["version"] == "1.0.0"
    assert entry["content_hash"]
