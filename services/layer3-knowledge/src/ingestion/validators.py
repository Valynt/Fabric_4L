"""App-level validators for Neo4j Community Edition compatibility.

Property existence constraints require Neo4j Enterprise Edition.
This module provides application-level validation to enforce the same
rules on Community Edition without relying on database-level constraints.
"""

from dataclasses import dataclass
from typing import Any

from ..api.exceptions import IngestionError


@dataclass
class ValidationResult:
    """Result of entity validation."""

    is_valid: bool
    errors: list[str]
    entity_type: str
    entity_id: str | None = None


# Required fields by entity type (aligned with ontology schema)
# These enforce the same rules that would be enforced by Neo4j Enterprise
# property existence constraints.
ENTITY_REQUIRED_FIELDS: dict[str, set[str]] = {
    # Primary Business Concepts
    "Capability": {"id", "name"},
    "UseCase": {"id", "name"},
    "Persona": {"id", "name"},
    "ValueDriver": {"id", "name"},
    "ValueMetric": {"id", "name"},
    # Product & Solution Domain
    "Product": {"id", "name"},
    "Feature": {"id", "name"},
    "Service": {"id", "name"},
    "Solution": {"id", "name"},
    "Technology": {"id", "name"},
    # Organizational Context
    "Organization": {"id", "name"},
    "BusinessUnit": {"id", "name"},
    "Process": {"id", "name"},
    "Activity": {"id", "name"},
    # Industry Reference Model Mappings
    "APQCProcess": {"id", "name"},
    "BIANServiceDomain": {"id", "name"},
    "FIBOEntity": {"id", "name"},
    # Supporting Concepts
    "Industry": {"id", "name"},
    "MarketSegment": {"id", "name"},
    "Geography": {"id", "name"},
    "Regulation": {"id", "name"},
    # Metadata & Provenance
    "DataSource": {"id", "name"},
    "ExtractionEvent": {"id"},
    "ConfidenceScore": {"id"},
}

# Optional: Fields that should have non-empty values if present
NON_EMPTY_FIELDS: set[str] = {"name", "description", "title", "summary"}


class RequiredFieldValidator:
    """Validator for required entity fields.

    Enforces field existence at the application level to maintain
    data integrity across Neo4j Community and Enterprise editions.

    Example:
        validator = RequiredFieldValidator()
        result = validator.validate_entity("Capability", {
            "id": "cap-001",
            "name": "Real-time Analytics",
            "description": "Process data in real-time"
        })
        if not result.is_valid:
            raise IngestionError(f"Validation failed: {result.errors}")
    """

    def __init__(
        self,
        required_fields: dict[str, set[str]] | None = None,
        non_empty_fields: set[str] | None = None,
        strict_mode: bool = True,
    ):
        """Initialize validator.

        Args:
            required_fields: Override default required fields mapping
            non_empty_fields: Override default non-empty field checks
            strict_mode: If True, raise IngestionError on validation failure
        """
        self.required_fields = required_fields or ENTITY_REQUIRED_FIELDS
        self.non_empty_fields = non_empty_fields or NON_EMPTY_FIELDS
        self.strict_mode = strict_mode

    def validate_entity(
        self,
        entity_type: str,
        data: dict[str, Any],
        entity_id: str | None = None,
    ) -> ValidationResult:
        """Validate a single entity against required field rules.

        Args:
            entity_type: Type of entity (e.g., "Capability", "UseCase")
            data: Entity data dictionary
            entity_id: Optional entity ID for error reporting

        Returns:
            ValidationResult with is_valid flag and error list
        """
        errors: list[str] = []

        # Check if entity type has defined required fields
        required = self.required_fields.get(entity_type)
        if required is None:
            # Unknown entity type - allow but warn
            return ValidationResult(
                is_valid=True,
                errors=[
                    f"Unknown entity type '{entity_type}' - no validation rules defined"
                ],
                entity_type=entity_type,
                entity_id=entity_id,
            )

        # Check required fields exist
        for field in required:
            if field not in data:
                errors.append(f"Missing required field '{field}'")
            elif data[field] is None:
                errors.append(f"Required field '{field}' is null")

        # Check non-empty fields have actual content
        for field in self.non_empty_fields:
            if field in data and data[field] is not None:
                value = str(data[field]).strip()
                if not value:
                    errors.append(f"Field '{field}' must have non-empty value")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            entity_type=entity_type,
            entity_id=entity_id or data.get("id"),
        )

    def validate_entities_batch(
        self,
        entity_type: str,
        entities: list[dict[str, Any]],
    ) -> list[ValidationResult]:
        """Validate a batch of entities.

        Args:
            entity_type: Type of entities
            entities: List of entity data dictionaries

        Returns:
            List of ValidationResult objects
        """
        results = []
        for entity in entities:
            entity_id = entity.get("id", "unknown")
            result = self.validate_entity(entity_type, entity, entity_id)
            results.append(result)
        return results

    def validate_and_raise(
        self,
        entity_type: str,
        data: dict[str, Any],
        entity_id: str | None = None,
        source_id: str | None = None,
    ) -> None:
        """Validate entity and raise IngestionError if invalid.

        Args:
            entity_type: Type of entity
            data: Entity data dictionary
            entity_id: Optional entity ID for error context
            source_id: Optional source ID for error context

        Raises:
            IngestionError: If validation fails and strict_mode is True
        """
        result = self.validate_entity(entity_type, data, entity_id)

        if not result.is_valid:
            error_msg = (
                f"Entity validation failed for {entity_type}"
                f"(id={result.entity_id or 'unknown'}): "
                f"{'; '.join(result.errors)}"
            )

            if self.strict_mode:
                raise IngestionError(
                    message=error_msg,
                    source_id=source_id,
                    stage="validation",
                    details={
                        "entity_type": entity_type,
                        "entity_id": result.entity_id,
                        "validation_errors": result.errors,
                        "available_fields": list(data.keys()),
                    },
                )

    def get_missing_fields(
        self,
        entity_type: str,
        data: dict[str, Any],
    ) -> set[str]:
        """Get set of missing required fields without raising.

        Args:
            entity_type: Type of entity
            data: Entity data dictionary

        Returns:
            Set of missing field names
        """
        required = self.required_fields.get(entity_type, set())
        return {field for field in required if field not in data or data[field] is None}

    def is_known_entity_type(self, entity_type: str) -> bool:
        """Check if entity type has validation rules defined.

        Args:
            entity_type: Type to check

        Returns:
            True if validation rules exist for this type
        """
        return entity_type in self.required_fields
