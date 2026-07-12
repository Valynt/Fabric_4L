"""Tests for TypedDictModel - backward compatibility and behavior."""

import pytest
from pydantic import ValidationError
from value_fabric.shared.models.typed_dict import TypedDictModel


class SampleModel(TypedDictModel):
    """Test model for TypedDictModel tests."""
    name: str
    count: int = 0


class TestTypedDictModelDictBehavior:
    """Test dict-like access patterns work correctly."""

    def test_getitem_access(self):
        """Test __getitem__ works like dict access."""
        model = SampleModel(name="test")
        assert model["name"] == "test"
        assert model["count"] == 0

    def test_setitem_modifies_value(self):
        """Test __setitem__ modifies the value."""
        model = SampleModel(name="test")
        model["count"] = 5
        assert model["count"] == 5

    def test_get_with_default(self):
        """Test .get() with default value."""
        model = SampleModel(name="test")
        assert model.get("name") == "test"
        assert model.get("missing_key") is None
        assert model.get("missing_key", "default") == "default"

    def test_contains_check(self):
        """Test __contains__ for key membership."""
        model = SampleModel(name="test")
        assert "name" in model
        assert "count" in model
        assert "missing" not in model

    def test_iteration(self):
        """Test iteration over keys/values/items."""
        model = SampleModel(name="test")
        
        # Test keys
        keys = list(model.keys())
        assert "name" in keys
        assert "count" in keys
        
        # Test values
        values = list(model.values())
        assert "test" in values
        assert 0 in values
        
        # Test items
        items = dict(model.items())
        assert items["name"] == "test"
        assert items["count"] == 0

    def test_iteration_direct(self):
        """Test direct iteration (calls __iter__)."""
        model = SampleModel(name="test")
        # __iter__ returns dict keys iterator
        keys = list(model)
        assert "name" in keys
        assert "count" in keys


class TestTypedDictModelValidation:
    """Test Pydantic validation still works."""

    def test_required_field_validation(self):
        """Test required fields are enforced."""
        with pytest.raises(ValidationError):
            SampleModel()  # Missing required 'name'

    def test_optional_default_field(self):
        """Test optional fields with defaults work."""
        model = SampleModel(name="test")
        assert model.count == 0  # Default value

    def test_extra_fields_allowed(self):
        """Test extra fields are allowed by config."""
        model = SampleModel(name="test", extra_field="extra")
        assert model["extra_field"] == "extra"


class TestTypedDictModelEdgeCases:
    """Test edge cases and potential bugs."""

    def test_empty_model(self):
        """Test model with no fields."""
        class EmptyModel(TypedDictModel):
            pass
        
        model = EmptyModel()
        assert list(model.keys()) == []

    def test_nested_dict_access(self):
        """Test nested dict values."""
        class NestedModel(TypedDictModel):
            data: dict
        
        model = NestedModel(data={"nested": "value"})
        assert model["data"]["nested"] == "value"

    def test_get_none_default_vs_missing(self):
        """Test .get() returns None vs actual None value."""
        class NullableModel(TypedDictModel):
            value: str | None = None
        
        model = NullableModel()
        assert model.get("value") is None  # Default value
        assert model.get("missing") is None  # Missing key
        assert model.get("missing", "default") == "default"
