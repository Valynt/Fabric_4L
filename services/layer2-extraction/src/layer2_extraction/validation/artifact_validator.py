"""Mandatory validation gate for extraction artifacts before persistence.

This module provides a single, enforced validation function that must be called
before any artifact is persisted to job store, quarantine, or downstream systems.
It ensures all required metadata fields are present and valid.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError, validate as jsonschema_validate
from pydantic import BaseModel, ValidationError


class ArtifactValidationError(ValueError):
    """Raised when an artifact fails mandatory validation before persistence."""
    
    def __init__(self, missing_fields: list[str], invalid_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        self.invalid_fields = invalid_fields
        message_parts = []
        if missing_fields:
            message_parts.append(f"Missing required fields: {', '.join(missing_fields)}")
        if invalid_fields:
            message_parts.append(f"Invalid fields: {', '.join(invalid_fields)}")
        super().__init__("; ".join(message_parts) if message_parts else "Artifact validation failed")


# Required metadata fields for all extraction artifacts
_REQUIRED_ENTITY_FIELDS = {
    "tenant_id",
    "extraction_job_id",
    "schema_version",
    "prompt_version_id",  # Entity models use prompt_version_id
    "model_version",
    "deterministic_id",
}

# Fields that must be non-empty strings
_NON_EMPTY_STRING_FIELDS = {
    "tenant_id",
    "extraction_job_id",
    "schema_version",
    "prompt_version_id",  # Entity models use prompt_version_id
    "model_version",
    "deterministic_id",
}


def _validate_entity_metadata(entity: Any) -> list[str]:
    """Validate that an entity has all required metadata fields.
    
    Args:
        entity: Entity object to validate (Pydantic model or dict-like)
        
    Returns:
        List of validation error messages
    """
    errors: list[str] = []
    
    # Check for missing required fields
    missing = []
    for field in _REQUIRED_ENTITY_FIELDS:
        if not hasattr(entity, field):
            missing.append(field)
    
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    
    # Check for empty string values
    empty = []
    for field in _NON_EMPTY_STRING_FIELDS:
        if hasattr(entity, field):
            value = getattr(entity, field)
            if value is None or (isinstance(value, str) and not value.strip()):
                empty.append(field)
    
    if empty:
        errors.append(f"Empty or null values for required fields: {', '.join(empty)}")
    
    return errors


def validate_artifact_for_persistence(
    artifact: Any,
    artifact_type: str = "entity",
) -> None:
    """Validate an artifact before persistence.
    
    This is the single mandatory validation gate that must be called before
    any artifact is persisted to job store, quarantine, or downstream systems.
    
    Args:
        artifact: The artifact to validate (entity, relationship, or ExtractionResult)
        artifact_type: Type of artifact for error messages ("entity", "relationship", "result")
        
    Raises:
        ArtifactValidationError: If the artifact fails validation
    """
    errors = _validate_entity_metadata(artifact)
    
    if errors:
        raise ArtifactValidationError(
            missing_fields=[],
            invalid_fields=errors,
        )


def validate_extraction_result(result: Any) -> None:
    """Validate an ExtractionResult before persistence.
    
    Args:
        result: ExtractionResult object to validate
        
    Raises:
        ArtifactValidationError: If the result fails validation
    """
    errors: list[str] = []
    
    # Check required top-level fields
    # ExtractionResult uses prompt_version, entities use prompt_version_id
    required_fields = ["job_id", "tenant_id", "schema_version", "model_version"]
    prompt_version_field = "prompt_version_id" if hasattr(result, "prompt_version_id") else "prompt_version"
    required_fields.append(prompt_version_field)
    
    missing = [f for f in required_fields if not hasattr(result, f)]
    
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    
    # Check for empty values
    empty = []
    for field in required_fields:
        if hasattr(result, field):
            value = getattr(result, field)
            if value is None or (isinstance(value, str) and not value.strip()):
                empty.append(field)
    
    if empty:
        errors.append(f"Empty or null values for required fields: {', '.join(empty)}")
    
    # Validate all entity collections have required metadata
    entity_collections = [
        "capabilities",
        "use_cases",
        "personas",
        "value_drivers",
        "features",
        "value_metrics",
    ]
    
    for collection_name in entity_collections:
        if hasattr(result, collection_name):
            collection = getattr(result, collection_name)
            if collection:
                for i, entity in enumerate(collection):
                    entity_errors = _validate_entity_metadata(entity)
                    if entity_errors:
                        errors.append(f"{collection_name}[{i}]: {'; '.join(entity_errors)}")
    
    if errors:
        raise ArtifactValidationError(
            missing_fields=[],
            invalid_fields=errors,
        )


def validate_relationship_for_persistence(relationship: Any) -> None:
    """Validate a relationship before persistence.
    
    Args:
        relationship: Relationship object to validate
        
    Raises:
        ArtifactValidationError: If the relationship fails validation
    """
    errors = _validate_entity_metadata(relationship)
    
    # Additional relationship-specific validation
    if hasattr(relationship, "source_entity_id"):
        if not relationship.source_entity_id:
            errors.append("source_entity_id is required")
    
    if hasattr(relationship, "target_entity_id"):
        if not relationship.target_entity_id:
            errors.append("target_entity_id is required")
    
    if errors:
        raise ArtifactValidationError(
            missing_fields=[],
            invalid_fields=errors,
        )


def validate_for_persistence(artifacts: Any) -> None:
    """Central strict gate for extraction artifacts before any persistence operation."""
    errors: list[str] = []

    try:
        if isinstance(artifacts, BaseModel):
            type(artifacts).model_validate(artifacts.model_dump(mode="python"), strict=True)
        else:
            errors.append("Artifacts must be a Pydantic model instance")
    except ValidationError as exc:
        errors.append(f"Strict Pydantic validation failed: {exc}")

    if isinstance(artifacts, BaseModel):
        schema = type(artifacts).model_json_schema()
        try:
            jsonschema_validate(instance=artifacts.model_dump(mode="json"), schema=schema)
        except JsonSchemaValidationError as exc:
            errors.append(f"JSON schema validation failed: {exc.message}")

    result = getattr(artifacts, "result", None)
    relationships = getattr(artifacts, "relationships", None)
    if result is None:
        errors.append("Missing required artifacts.result")
    else:
        try:
            validate_extraction_result(result)
        except ArtifactValidationError as exc:
            errors.append("validation_failed")

        if not getattr(result, "tenant_id", None):
            errors.append("Missing tenant_id on extraction result")
        if not getattr(result, "schema_version", None):
            errors.append("Missing schema_version on extraction result")

        for collection_name in [
            "capabilities",
            "use_cases",
            "personas",
            "value_drivers",
            "features",
            "value_metrics",
        ]:
            for idx, entity in enumerate(getattr(result, collection_name, []) or []):
                refs = getattr(entity, "source_refs", None)
                ts = getattr(entity, "extracted_at", None)
                if not refs:
                    errors.append(f"{collection_name}[{idx}] missing source_refs")
                if not isinstance(ts, datetime):
                    errors.append(f"{collection_name}[{idx}] missing extracted_at timestamp")

    if relationships is None:
        errors.append("Missing required artifacts.relationships")
    else:
        for idx, relationship in enumerate(relationships):
            try:
                validate_relationship_for_persistence(relationship)
            except ArtifactValidationError as exc:
                errors.append(f"relationships[{idx}] {exc}")
            if not getattr(relationship, "source_url", None):
                errors.append(f"relationships[{idx}] missing source_url")

    if errors:
        raise ArtifactValidationError(missing_fields=[], invalid_fields=errors)
