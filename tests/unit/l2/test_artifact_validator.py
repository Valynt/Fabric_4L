"""Unit tests for Layer 2 artifact validation gate (P0-004)."""

from __future__ import annotations

import pytest
from layer2_extraction.validation.artifact_validator import (
    ArtifactValidationError,
    _validate_entity_metadata,
    validate_artifact_for_persistence,
)

pytestmark = [pytest.mark.unit]


class _FakeEntity:
    def __init__(
        self,
        tenant_id: str = "t-1",
        extraction_job_id: str = "job-1",
        schema_version: str = "1.0",
        prompt_version_id: str = "pv-1",
        model_version: str = "gpt-4",
        deterministic_id: str = "did-1",
    ) -> None:
        self.tenant_id = tenant_id
        self.extraction_job_id = extraction_job_id
        self.schema_version = schema_version
        self.prompt_version_id = prompt_version_id
        self.model_version = model_version
        self.deterministic_id = deterministic_id


class TestValidateEntityMetadata:
    """_validate_entity_metadata catches missing and empty fields."""

    def test_no_errors_on_complete_entity(self) -> None:
        entity = _FakeEntity()
        errors = _validate_entity_metadata(entity)
        assert errors == []

    def test_missing_fields_reported(self) -> None:
        entity = _FakeEntity()
        delattr(entity, "tenant_id")
        errors = _validate_entity_metadata(entity)
        assert len(errors) == 1
        assert "tenant_id" in errors[0]

    def test_multiple_missing_fields(self) -> None:
        entity = _FakeEntity()
        delattr(entity, "tenant_id")
        delattr(entity, "extraction_job_id")
        errors = _validate_entity_metadata(entity)
        assert len(errors) == 1
        assert "tenant_id" in errors[0]
        assert "extraction_job_id" in errors[0]

    def test_empty_string_values(self) -> None:
        entity = _FakeEntity(tenant_id="  ")
        errors = _validate_entity_metadata(entity)
        assert len(errors) == 1
        assert "tenant_id" in errors[0]

    def test_none_values(self) -> None:
        entity = _FakeEntity(schema_version=None)
        errors = _validate_entity_metadata(entity)
        assert len(errors) == 1
        assert "schema_version" in errors[0]

    def test_dict_like_entity(self) -> None:
        class DictLike:
            tenant_id = "t-1"
            extraction_job_id = "job-1"
            schema_version = "1.0"
            prompt_version_id = "pv-1"
            model_version = "gpt-4"
            deterministic_id = "did-1"

        errors = _validate_entity_metadata(DictLike())
        assert errors == []


class TestValidateArtifactForPersistence:
    """validate_artifact_for_persistence raises on invalid artifacts."""

    def test_passes_on_valid_entity(self) -> None:
        entity = _FakeEntity()
        validate_artifact_for_persistence(entity, artifact_type="entity")

    def test_raises_on_missing_fields(self) -> None:
        entity = _FakeEntity()
        delattr(entity, "tenant_id")
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact_for_persistence(entity)
        # Implementation places all errors in invalid_fields
        assert any("tenant_id" in f for f in exc_info.value.invalid_fields)

    def test_raises_on_empty_fields(self) -> None:
        entity = _FakeEntity(deterministic_id="")
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact_for_persistence(entity)
        assert any("deterministic_id" in f for f in exc_info.value.invalid_fields)

    def test_error_message_format(self) -> None:
        entity = _FakeEntity()
        delattr(entity, "tenant_id")
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact_for_persistence(entity)
        msg = str(exc_info.value)
        assert "Missing required fields" in msg
        assert "tenant_id" in msg

    def test_artifact_type_not_in_message(self) -> None:
        entity = _FakeEntity()
        delattr(entity, "tenant_id")
        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact_for_persistence(entity, artifact_type="relationship")
        assert "relationship" not in str(exc_info.value)

    def test_both_missing_and_invalid(self) -> None:
        class BadEntity:
            tenant_id = ""

        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_artifact_for_persistence(BadEntity())
        assert exc_info.value.missing_fields == []
        assert len(exc_info.value.invalid_fields) == 2
        assert any("Missing" in f for f in exc_info.value.invalid_fields)
        assert any("Empty" in f for f in exc_info.value.invalid_fields)
