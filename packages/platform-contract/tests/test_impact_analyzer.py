"""Tests for schema_registry.impact."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from schema_registry.impact import ImpactAnalyzer
from schema_registry.loader import RegistryLoader
from schema_registry.models import (
    CompatibilityPolicyDoc,
    CompatibilityPolicy,
    LifecycleStatus,
    Owner,
    SchemaKind,
    SchemaRecord,
    RegistryCatalog,
    Subscription,
)


def _make_record(schema_id: str, version: str, artifact: str, status: LifecycleStatus = LifecycleStatus.PUBLISHED, kind: SchemaKind = SchemaKind.COMMON_VALUE_OBJECT, domain: str = "common") -> SchemaRecord:
    return SchemaRecord(
        schema_id=schema_id,
        version=version,
        kind=kind,
        domain=domain,
        owner=Owner(team="platform/contracts"),
        status=status,
        artifact=artifact,
        published_at=datetime.datetime.now(datetime.timezone.utc),
        examples=[],
    )


def test_analyze_no_dependents(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "contracts" / "jsonschema" / "common" / "v1"
    artifact_dir.mkdir(parents=True)
    money_path = artifact_dir / "money.schema.json"
    money_path.write_text('{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object"}', encoding="utf-8")

    catalog = RegistryCatalog(
        schemas=[
            _make_record("common.value.money", "1.0.0", str(money_path.relative_to(tmp_path))),
        ],
        policies=CompatibilityPolicyDoc(
            version="1.0.0",
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            default_policy=CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR,
            policies=[],
            lifecycle_transitions=[],
        ),
    )

    analyzer = ImpactAnalyzer(loader=RegistryLoader(repo_root=tmp_path))
    report = analyzer.analyze("common.value.money", "1.0.0", catalog)
    assert report["direct_dependents"] == []
    assert report["changed_schema"] == "common.value.money@1.0.0"


def test_analyze_with_dependent(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "contracts" / "jsonschema" / "common" / "v1"
    artifact_dir.mkdir(parents=True)
    money_path = artifact_dir / "money.schema.json"
    money_path.write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"https://valuefabric.ai/contracts/jsonschema/common/v1/money.schema.json","type":"object"}',
        encoding="utf-8",
    )
    invoice_path = artifact_dir / "invoice.schema.json"
    invoice_path.write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object","properties":{"total":{"$ref":"https://valuefabric.ai/contracts/jsonschema/common/v1/money.schema.json"}}}',
        encoding="utf-8",
    )

    catalog = RegistryCatalog(
        schemas=[
            _make_record("money", "1.0.0", str(money_path.relative_to(tmp_path))),
            _make_record("billing.api.invoice", "1.0.0", str(invoice_path.relative_to(tmp_path)), kind=SchemaKind.API_RESPONSE, domain="billing"),
        ],
        policies=CompatibilityPolicyDoc(
            version="1.0.0",
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            default_policy=CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR,
            policies=[],
            lifecycle_transitions=[],
        ),
    )

    analyzer = ImpactAnalyzer(loader=RegistryLoader(repo_root=tmp_path))
    report = analyzer.analyze("money", "1.0.0", catalog)
    assert "billing.api.invoice@1.0.0" in report["direct_dependents"]


def test_analyze_missing_schema() -> None:
    catalog = RegistryCatalog(
        schemas=[],
        policies=CompatibilityPolicyDoc(
            version="1.0.0",
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            default_policy=CompatibilityPolicy.ADDITIVE_WITHIN_MAJOR,
            policies=[],
            lifecycle_transitions=[],
        ),
    )
    analyzer = ImpactAnalyzer(loader=RegistryLoader())
    with pytest.raises(ValueError) as exc_info:
        analyzer.analyze("missing", "1.0.0", catalog)
    assert "not found" in str(exc_info.value)
