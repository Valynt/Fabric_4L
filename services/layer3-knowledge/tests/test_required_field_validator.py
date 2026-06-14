"""Unit tests for RequiredFieldValidator - Community Edition compatibility.

These tests verify that application-level validation enforces the same rules
that Neo4j Enterprise Edition would enforce via property existence constraints.
"""

import pytest

from src.ingestion.validators import RequiredFieldValidator, ValidationResult


class TestRequiredFieldValidator:
    """Test suite for RequiredFieldValidator."""

    def test_valid_capability_passes(self):
        """Valid Capability entity with all required fields should pass."""
        validator = RequiredFieldValidator()

        result = validator.validate_entity(
            "Capability",
            {"id": "cap-001", "name": "Real-time Analytics", "description": "Process data"},
        )

        assert result.is_valid is True
        assert result.errors == []
        assert result.entity_type == "Capability"
        assert result.entity_id == "cap-001"

    def test_missing_required_field_fails(self):
        """Entity missing required 'name' field should fail."""
        validator = RequiredFieldValidator()

        result = validator.validate_entity(
            "Capability",
            {"id": "cap-002", "description": "Missing name field"},
        )

        assert result.is_valid is False
        assert any("name" in err for err in result.errors)
        assert "Missing required field 'name'" in result.errors

    def test_null_required_field_fails(self):
        """Entity with null required field should fail."""
        validator = RequiredFieldValidator()

        result = validator.validate_entity(
            "UseCase",
            {"id": "uc-001", "name": None},
        )

        assert result.is_valid is False
        assert any("null" in err.lower() for err in result.errors)

    def test_empty_string_name_fails(self):
        """Entity with empty string name should fail non-empty check."""
        validator = RequiredFieldValidator()

        result = validator.validate_entity(
            "Persona",
            {"id": "pers-001", "name": "   "},
        )

        assert result.is_valid is False
        assert any("non-empty" in err.lower() for err in result.errors)

    def test_unknown_entity_type_warns_but_passes(self):
        """Unknown entity type should pass with warning."""
        validator = RequiredFieldValidator()

        result = validator.validate_entity(
            "UnknownEntityType",
            {"id": "unknown-001", "some_field": "value"},
        )

        # Should be valid (no strict enforcement for unknown types)
        assert result.is_valid is True
        # But should have a warning
        assert any("Unknown entity type" in err for err in result.errors)

    def test_batch_validation(self):
        """Batch validation should return results for all entities."""
        validator = RequiredFieldValidator()

        entities = [
            {"id": "cap-001", "name": "Valid Capability"},
            {"id": "cap-002"},  # Missing name
            {"id": "cap-003", "name": "Another Valid"},
        ]

        results = validator.validate_entities_batch("Capability", entities)

        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is False
        assert results[2].is_valid is True

    def test_validate_and_raise_raises_on_invalid(self):
        """validate_and_raise should raise IngestionError on invalid entity."""
        from src.api.exceptions import IngestionError

        validator = RequiredFieldValidator()

        with pytest.raises(IngestionError) as exc_info:
            validator.validate_and_raise(
                "ValueDriver",
                {"id": "vd-001"},  # Missing name
                entity_id="vd-001",
                source_id="test-source",
            )

        assert exc_info.value.error_code == "INGESTION_ERROR"
        assert "ValueDriver" in exc_info.value.message
        assert "vd-001" in exc_info.value.message

    def test_validate_and_raise_succeeds_on_valid(self):
        """validate_and_raise should not raise on valid entity."""
        validator = RequiredFieldValidator()

        # Should not raise
        validator.validate_and_raise(
            "Product",
            {"id": "prod-001", "name": "Test Product"},
            entity_id="prod-001",
            source_id="test-source",
        )

    def test_get_missing_fields(self):
        """get_missing_fields should return set of missing required fields."""
        validator = RequiredFieldValidator()

        missing = validator.get_missing_fields(
            "Feature",
            {"id": "feat-001"},  # Missing name
        )

        assert "name" in missing
        assert "id" not in missing

    def test_is_known_entity_type(self):
        """is_known_entity_type should correctly identify known types."""
        validator = RequiredFieldValidator()

        assert validator.is_known_entity_type("Capability") is True
        assert validator.is_known_entity_type("UseCase") is True
        assert validator.is_known_entity_type("UnknownType") is False

    def test_all_primary_entity_types_have_required_fields(self):
        """Verify all primary entity types have validation rules defined."""
        validator = RequiredFieldValidator()
        primary_types = [
            "Capability",
            "UseCase",
            "Persona",
            "ValueDriver",
            "ValueMetric",
            "Product",
            "Feature",
            "Service",
            "Organization",
            "Process",
        ]

        for entity_type in primary_types:
            assert validator.is_known_entity_type(entity_type), f"{entity_type} should have validation rules"


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_structure(self):
        """ValidationResult should have expected fields."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            entity_type="Capability",
            entity_id="cap-001",
        )

        assert result.is_valid is True
        assert result.errors == []
        assert result.entity_type == "Capability"
        assert result.entity_id == "cap-001"

    def test_validation_result_with_errors(self):
        """ValidationResult should store error messages."""
        result = ValidationResult(
            is_valid=False,
            errors=["Missing required field 'name'", "Field 'description' is null"],
            entity_type="UseCase",
            entity_id="uc-001",
        )

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "Missing required field 'name'" in result.errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

