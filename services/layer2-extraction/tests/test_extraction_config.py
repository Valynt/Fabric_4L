from __future__ import annotations

import pytest
from value_fabric.shared.error_handling.exceptions import ValidationError

from layer2_extraction.api.extraction_config import (
    build_idempotency_key,
    resolve_value_pack_scope,
    validated_extraction_config,
)


def test_validated_extraction_config_copies_input_and_uses_authenticated_tenant() -> None:
    original = {
        "tenant_id": "body-tenant",
        "model_version": "model-a",
        "schema_version": "schema-a",
        "prompt_version": "prompt-a",
    }

    config = validated_extraction_config(
        original,
        tenant_id="auth-tenant",
        operation="extraction job creation",
    )

    assert config["tenant_id"] == "auth-tenant"
    assert config["model_version"] == "model-a"
    assert original["tenant_id"] == "body-tenant"


def test_validated_extraction_config_uses_environment_model_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXTRACTION_MODEL", "env-model")

    config = validated_extraction_config(
        {"schema_version": "schema-a", "prompt_version": "prompt-a"},
        tenant_id="tenant-a",
        operation="extraction job creation",
    )

    assert config["model_version"] == "env-model"
    assert config["tenant_id"] == "tenant-a"


@pytest.mark.parametrize(
    ("config", "expected_message"),
    [
        (
            {"schema_version": "schema-a", "prompt_version": "prompt-a"},
            "model_version is required in extraction_config or EXTRACTION_MODEL env var for extraction job creation",
        ),
        (
            {"model_version": "model-a", "prompt_version": "prompt-a"},
            "schema_version is required in extraction_config for extraction job creation",
        ),
        (
            {"model_version": "model-a", "schema_version": "schema-a"},
            "prompt_version is required in extraction_config for extraction job creation",
        ),
    ],
)
def test_validated_extraction_config_preserves_route_error_messages(
    monkeypatch: pytest.MonkeyPatch,
    config: dict[str, str],
    expected_message: str,
) -> None:
    monkeypatch.delenv("EXTRACTION_MODEL", raising=False)

    with pytest.raises(ValidationError) as exc:
        validated_extraction_config(
            config,
            tenant_id="tenant-a",
            operation="extraction job creation",
        )

    assert exc.value.message == expected_message


def test_validated_extraction_config_preserves_runtime_error_message_without_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EXTRACTION_MODEL", raising=False)

    with pytest.raises(ValidationError) as exc:
        validated_extraction_config(
            {"schema_version": "schema-a", "prompt_version": "prompt-a"},
            tenant_id="tenant-a",
        )

    assert exc.value.message == "model_version is required in extraction_config or EXTRACTION_MODEL env var"


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({}, "default"),
        ({"value_pack": "legacy-pack"}, "legacy-pack"),
        ({"value_pack_scope": "scope-a", "value_pack": "legacy-pack"}, "scope-a"),
    ],
)
def test_resolve_value_pack_scope_preserves_precedence(
    config: dict[str, str],
    expected: str,
) -> None:
    assert resolve_value_pack_scope(config) == expected


def test_build_idempotency_key_is_stable_and_tenant_scoped() -> None:
    base = build_idempotency_key(
        tenant_id="tenant-a",
        source_url="https://example.com/a",
        content_id="content-a",
        extraction_config={"extraction_version": "v1", "value_pack_scope": "pack-a"},
    )
    same = build_idempotency_key(
        tenant_id="tenant-a",
        source_url="https://example.com/a",
        content_id="content-a",
        extraction_config={"extraction_version": "v1", "value_pack_scope": "pack-a"},
    )
    other_tenant = build_idempotency_key(
        tenant_id="tenant-b",
        source_url="https://example.com/a",
        content_id="content-a",
        extraction_config={"extraction_version": "v1", "value_pack_scope": "pack-a"},
    )

    assert base == same
    assert base != other_tenant
