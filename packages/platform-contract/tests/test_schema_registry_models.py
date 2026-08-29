"""Tests for schema_registry.models."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from schema_registry.models import (
    AuthoringDirection,
    Classification,
    CompatibilityPolicy,
    ExampleRecord,
    Fixture,
    LifecycleStatus,
    Owner,
    RegistryCatalog,
    SchemaKind,
    SchemaRecord,
    _semver_tuple,
)


def test_schema_record_valid() -> None:
    record = SchemaRecord(
        schema_id="billing.event.subscription-activated",
        version="1.1.0",
        kind=SchemaKind.EVENT_DATA,
        domain="billing",
        owner=Owner(team="platform/billing"),
        status=LifecycleStatus.PUBLISHED,
        artifact="contracts/jsonschema/billing/events/v1/subscription-activated.schema.json",
        examples=[ExampleRecord(name="basic", description="Basic activation", payload={"id": "1"})],
        published_at=datetime.datetime.now(datetime.timezone.utc),
    )
    assert record.key() == "billing.event.subscription-activated@1.1.0"


def test_schema_record_missing_published_at() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SchemaRecord(
            schema_id="billing.event.subscription-activated",
            version="1.1.0",
            kind=SchemaKind.EVENT_DATA,
            domain="billing",
            owner=Owner(team="platform/billing"),
            status=LifecycleStatus.PUBLISHED,
            artifact="contracts/jsonschema/billing/events/v1/subscription-activated.schema.json",
            examples=[],
        )
    assert "published_at is required" in str(exc_info.value)


def test_schema_record_code_first_without_source_of_truth() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SchemaRecord(
            schema_id="billing.provider.observation",
            version="1.0.0",
            kind=SchemaKind.PROVIDER_OBSERVATION,
            domain="billing",
            owner=Owner(team="platform/billing"),
            status=LifecycleStatus.DRAFT,
            artifact="contracts/jsonschema/billing/provider-observations/v1/stripe-charge.schema.json",
            authoring_direction=AuthoringDirection.CODE_FIRST_WITH_GENERATED_SCHEMA,
            examples=[],
        )
    assert "source_of_truth" in str(exc_info.value)


def test_schema_record_invalid_schema_id() -> None:
    with pytest.raises(ValidationError):
        SchemaRecord(
            schema_id="INVALID_SCHEMA_ID!",
            version="1.0.0",
            kind=SchemaKind.API_REQUEST,
            domain="billing",
            owner=Owner(team="platform/billing"),
            status=LifecycleStatus.DRAFT,
            artifact="contracts/jsonschema/billing/api/v1/invoice.schema.json",
            examples=[],
        )


def test_schema_record_invalid_version() -> None:
    with pytest.raises(ValidationError):
        SchemaRecord(
            schema_id="billing.api.invoice",
            version="v1.0",
            kind=SchemaKind.API_REQUEST,
            domain="billing",
            owner=Owner(team="platform/billing"),
            status=LifecycleStatus.DRAFT,
            artifact="contracts/jsonschema/billing/api/v1/invoice.schema.json",
            examples=[],
        )


def test_registry_catalog_duplicate_schema() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RegistryCatalog(
            schemas=[
                SchemaRecord(
                    schema_id="common.value.money",
                    version="1.0.0",
                    kind=SchemaKind.COMMON_VALUE_OBJECT,
                    domain="common",
                    owner=Owner(team="platform/contracts"),
                    status=LifecycleStatus.PUBLISHED,
                    artifact="contracts/jsonschema/common/v1/money.schema.json",
                    published_at=datetime.datetime.now(datetime.timezone.utc),
                    examples=[],
                ),
                SchemaRecord(
                    schema_id="common.value.money",
                    version="1.0.0",
                    kind=SchemaKind.COMMON_VALUE_OBJECT,
                    domain="common",
                    owner=Owner(team="platform/contracts"),
                    status=LifecycleStatus.PUBLISHED,
                    artifact="contracts/jsonschema/common/v1/money.schema.json",
                    published_at=datetime.datetime.now(datetime.timezone.utc),
                    examples=[],
                ),
            ]
        )
    assert "Duplicate" in str(exc_info.value)


def test_semver_tuple() -> None:
    assert _semver_tuple("1.2.3") == (1, 2, 3)
    assert _semver_tuple("0.0.1") == (0, 0, 1)
    assert _semver_tuple("10.0.0") == (10, 0, 0)
