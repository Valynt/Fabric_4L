"""Tests for schema_registry.compatibility."""

from __future__ import annotations

import datetime

import pytest

from schema_registry.compatibility import (
    CompatibilityChecker,
    CompatibilityPolicyDoc,
    check_status_transition,
)
from schema_registry.models import (
    CompatibilityPolicy,
    LifecycleStatus,
    Owner,
    SchemaKind,
    SchemaRecord,
)


def _make_record(schema_id: str, version: str, status: LifecycleStatus = LifecycleStatus.PUBLISHED) -> SchemaRecord:
    return SchemaRecord(
        schema_id=schema_id,
        version=version,
        kind=SchemaKind.EVENT_DATA,
        domain="billing",
        owner=Owner(team="platform/billing"),
        status=status,
        artifact="contracts/jsonschema/billing/events/v1/test.schema.json",
        published_at=datetime.datetime.now(datetime.timezone.utc),
        examples=[],
    )


def _schema(props: dict, required: list[str] | None = None, additional: bool = True) -> dict:
    s: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": props,
    }
    if required is not None:
        s["required"] = required
    s["additionalProperties"] = additional
    return s


def test_additive_add_field() -> None:
    old = _schema({"a": {"type": "string"}})
    new = _schema({"a": {"type": "string"}, "b": {"type": "integer"}})
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert result.ok()


def test_additive_remove_field() -> None:
    old = _schema({"a": {"type": "string"}})
    new = _schema({})
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert not result.ok()
    assert any("AWM-01" in e for e in result.errors)


def test_additive_change_type() -> None:
    old = _schema({"a": {"type": "string"}})
    new = _schema({"a": {"type": "integer"}})
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert not result.ok()
    assert any("AWM-02" in e for e in result.errors)


def test_additive_add_required() -> None:
    old = _schema({"a": {"type": "string"}}, required=["a"])
    new = _schema(
        {"a": {"type": "string"}, "b": {"type": "integer"}},
        required=["a", "b"],
    )
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert not result.ok()
    assert any("AWM-03" in e for e in result.errors)


def test_additive_tighten_additional_properties() -> None:
    old = _schema({"a": {"type": "string"}}, additional=True)
    new = _schema({"a": {"type": "string"}}, additional=False)
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert not result.ok()
    assert any("AWM-04" in e for e in result.errors)


def test_additive_enum_shrinkage() -> None:
    old = _schema({"status": {"type": "string", "enum": ["a", "b", "c"]}})
    new = _schema({"status": {"type": "string", "enum": ["a", "b"]}})
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert not result.ok()
    assert any("AWM-05" in e for e in result.errors)


def test_additive_enum_open_ok() -> None:
    old = _schema({"status": {"type": "string", "enum": ["a", "b", "c"]}})
    new = _schema({"status": {"type": "string", "enum": ["a", "b"], "x-open-enum": True}})
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    # Open enum shrinks are allowed
    assert result.ok()


def test_additive_narrow_minimum() -> None:
    old = _schema({"count": {"type": "integer", "minimum": 0}})
    new = _schema({"count": {"type": "integer", "minimum": 1}})
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert not result.ok()
    assert any("AWM-06" in e for e in result.errors)


def test_additive_narrow_maximum() -> None:
    old = _schema({"count": {"type": "integer", "maximum": 100}})
    new = _schema({"count": {"type": "integer", "maximum": 99}})
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert not result.ok()
    assert any("AWM-06" in e for e in result.errors)


def test_additive_change_id() -> None:
    old = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://a/v1.json", "type": "object"}
    new = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://a/v2.json", "type": "object"}
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert not result.ok()
    assert any("AWM-09" in e for e in result.errors)


def test_policy_none() -> None:
    old = _schema({"a": {"type": "string"}})
    new = _schema({})
    checker = CompatibilityChecker()
    result = checker.check(
        _make_record("x", "1.0.0"),
        SchemaRecord(
            schema_id="x",
            version="2.0.0",
            kind=SchemaKind.EVENT_DATA,
            domain="billing",
            owner=Owner(team="platform/billing"),
            status=LifecycleStatus.PUBLISHED,
            artifact="contracts/jsonschema/billing/events/v1/test.schema.json",
            compatibility_policy=CompatibilityPolicy.NONE,
            published_at=datetime.datetime.now(datetime.timezone.utc),
            examples=[],
        ),
        old,
        new,
    )
    assert result.ok()
    assert result.warnings


def test_policy_full() -> None:
    old = _schema({"a": {"type": "string"}})
    new = _schema({"a": {"type": "string"}})
    checker = CompatibilityChecker()
    result = checker.check(
        _make_record("x", "1.0.0"),
        SchemaRecord(
            schema_id="x",
            version="1.1.0",
            kind=SchemaKind.EVENT_DATA,
            domain="billing",
            owner=Owner(team="platform/billing"),
            status=LifecycleStatus.PUBLISHED,
            artifact="contracts/jsonschema/billing/events/v1/test.schema.json",
            compatibility_policy=CompatibilityPolicy.FULL,
            published_at=datetime.datetime.now(datetime.timezone.utc),
            examples=[],
        ),
        old,
        new,
    )
    assert not result.ok()
    assert any("FULL policy requires exact version match" in e for e in result.errors)


def test_status_transition_valid() -> None:
    from schema_registry.models import LifecycleStatus

    policy = CompatibilityPolicyDoc(
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
    )
    errs = check_status_transition(LifecycleStatus.DRAFT, LifecycleStatus.REVIEW, policy)
    assert errs == []
    errs = check_status_transition(LifecycleStatus.PUBLISHED, LifecycleStatus.DRAFT, policy)
    assert errs


def test_nested_object_compatibility() -> None:
    old = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "nested": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
                "additionalProperties": True,
            }
        },
        "additionalProperties": True,
    }
    new = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "nested": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
                "additionalProperties": False,
            }
        },
        "additionalProperties": True,
    }
    checker = CompatibilityChecker()
    result = checker.check(_make_record("x", "1.0.0"), _make_record("x", "1.1.0"), old, new)
    assert not result.ok()
    assert any("AWM-04" in e for e in result.errors)
