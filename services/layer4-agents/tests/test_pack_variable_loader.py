from __future__ import annotations

"""
Unit tests for PackVariableLoader — Phase 2 of Canonical Contract Migration.

Tests cover:
- Variable loading from pack files
- Idempotent loading (skip already-registered variables)
- Formula reference validation
- Error handling for missing fields
- Type mapping from pack format to VariableRegistry format
"""


import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer4_agents.services.pack_variable_loader import (
    _PACK_VERSION_PATTERN,
    _TYPE_MAP,
    PackLoadResult,
    PackVariableLoader,
)


class sample_pack_variablesResult(TypedDictModel):
    pack_id: str
    variables: list[Any]
    version: str

class sample_pack_formulasResult(TypedDictModel):
    formulas: list[Any]
    pack_id: str


@pytest.fixture
def mock_registry():
    """Create a mock IVariableRegistry for testing."""
    registry = MagicMock()
    registry.get_variable = AsyncMock(return_value=None)  # Variable doesn't exist
    registry.register_variable = AsyncMock()
    return registry


@pytest.fixture
def sample_pack_variables() -> dict[str, Any]:
    """Sample variables.json content for testing."""
    return sample_pack_variablesResult.model_validate({
        "pack_id": "test-pack-v1",
        "version": "1.0.0",
        "variables": [
            {
                "variable_id": "test-var-001",
                "variable_name": "Revenue",
                "canonicalName": "Revenue",
                "display_name": "Annual Revenue",
                "name": "Annual Revenue",
                "description": "Total annual revenue",
                "data_type": "CURRENCY",
                "unit": "USD",
                "type": "currency",
                "default_value": 1000000,
                "min_value": 0,
                "max_value": 1000000000,
            },
            {
                "variable_id": "test-var-002",
                "variable_name": "Growth_Rate",
                "canonicalName": "GrowthRate",
                "display_name": "Growth Rate",
                "name": "Growth Rate",
                "description": "Annual growth rate",
                "data_type": "PERCENTAGE",
                "unit": "percent",
                "type": "percentage",
                "default_value": 0.15,
                "min_value": 0,
                "max_value": 1.0,
            },
        ],
    }).model_dump()


@pytest.fixture
def sample_pack_formulas() -> dict[str, Any]:
    """Sample formulas.json content for testing."""
    return sample_pack_formulasResult.model_validate({
        "pack_id": "test-pack-v1",
        "formulas": [
            {
                "formula_id": "test-f-001",
                "name": "Projected Revenue",
                "expression": {
                    "variables": ["Revenue", "Growth_Rate"],
                    "string": "Revenue * (1 + Growth_Rate)",
                },
            },
        ],
    }).model_dump()


class TestPackVersionPattern:
    """Tests for pack version suffix stripping."""

    def test_strip_v1_suffix(self):
        """Should strip -v1 suffix from pack_id."""
        result = _PACK_VERSION_PATTERN.sub("", "financial-services-v1")
        assert result == "financial-services"

    def test_strip_v2_suffix(self):
        """Should strip -v2 suffix from pack_id."""
        result = _PACK_VERSION_PATTERN.sub("", "manufacturing-v2")
        assert result == "manufacturing"

    def test_strip_v10_suffix(self):
        """Should strip -v10 suffix (multi-digit versions)."""
        result = _PACK_VERSION_PATTERN.sub("", "software-v10")
        assert result == "software"

    def test_no_suffix_unchanged(self):
        """Should leave pack_id unchanged if no version suffix."""
        result = _PACK_VERSION_PATTERN.sub("", "energy-utilities")
        assert result == "energy-utilities"

    def test_version_in_middle_unchanged(self):
        """Should not strip version pattern in middle of string."""
        result = _PACK_VERSION_PATTERN.sub("", "my-v1-package")
        assert result == "my-v1-package"


class TestTypeMapping:
    """Tests for pack type to VariableDataType mapping."""

    def test_currency_types_map_to_decimal(self):
        """Currency types should map to DECIMAL."""
        from layer4_agents.interfaces.variable_registry import VariableDataType

        assert _TYPE_MAP["currency"] == VariableDataType.DECIMAL
        assert _TYPE_MAP["usd"] == VariableDataType.DECIMAL

    def test_percentage_types_map_to_decimal(self):
        """Percentage types should map to DECIMAL."""
        from layer4_agents.interfaces.variable_registry import VariableDataType

        assert _TYPE_MAP["percentage"] == VariableDataType.DECIMAL
        assert _TYPE_MAP["percent"] == VariableDataType.DECIMAL

    def test_integer_types_map_to_integer(self):
        """Integer types should map to INTEGER."""
        from layer4_agents.interfaces.variable_registry import VariableDataType

        assert _TYPE_MAP["integer"] == VariableDataType.INTEGER
        assert _TYPE_MAP["count"] == VariableDataType.INTEGER

    def test_unknown_type_defaults_to_string(self):
        """Unknown types should default to STRING."""
        from layer4_agents.interfaces.variable_registry import VariableDataType

        assert _TYPE_MAP.get("unknown_type", VariableDataType.STRING) == VariableDataType.STRING


class TestPackLoadResult:
    """Tests for PackLoadResult dataclass."""

    def test_success_property_all_loaded(self):
        """success should be True when no failures."""
        result = PackLoadResult(
            pack_id="test-pack",
            variables_loaded=5,
            variables_skipped=0,
            variables_failed=0,
            errors=[],
        )
        assert result.success is True

    def test_success_property_with_failures(self):
        """success should be False when there are failures."""
        result = PackLoadResult(
            pack_id="test-pack",
            variables_loaded=4,
            variables_skipped=0,
            variables_failed=1,
            errors=["Variable 'x' failed"],
        )
        assert result.success is False

    def test_summary_format(self):
        """summary() should return formatted string with counts."""
        result = PackLoadResult(
            pack_id="test-pack",
            variables_loaded=3,
            variables_skipped=2,
            variables_failed=1,
            errors=[],
        )
        summary = result.summary()
        assert "test-pack" in summary
        assert "loaded=3" in summary
        assert "skipped=2" in summary
        assert "failed=1" in summary


class TestPackVariableLoader:
    """Tests for PackVariableLoader class."""

    @pytest.mark.asyncio
    async def test_load_pack_success(self, tmp_path, mock_registry, sample_pack_variables):
        """Should successfully load variables from pack."""
        # Setup pack directory structure
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        variables_file = pack_dir / "variables.json"
        variables_file.write_text(json.dumps(sample_pack_variables))

        loader = PackVariableLoader(registry=mock_registry, packs_dir=tmp_path)

        result = await loader.load_pack("test-pack-v1")

        assert result.pack_id == "test-pack-v1"
        assert result.variables_loaded == 2
        assert result.variables_skipped == 0
        assert result.variables_failed == 0
        assert result.success is True
        assert mock_registry.register_variable.call_count == 2

    @pytest.mark.asyncio
    async def test_load_pack_idempotent(self, tmp_path, mock_registry, sample_pack_variables):
        """Should skip variables that already exist in registry."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        variables_file = pack_dir / "variables.json"
        variables_file.write_text(json.dumps(sample_pack_variables))

        # Mock: first variable exists, second doesn't
        mock_registry.get_variable = AsyncMock(side_effect=[MagicMock(), None])

        loader = PackVariableLoader(registry=mock_registry, packs_dir=tmp_path)
        result = await loader.load_pack("test-pack-v1")

        assert result.variables_loaded == 1
        assert result.variables_skipped == 1
        assert result.variables_failed == 0
        assert mock_registry.register_variable.call_count == 1

    @pytest.mark.asyncio
    async def test_load_pack_missing_variables_file(self, tmp_path, mock_registry):
        """Should raise FileNotFoundError when variables.json missing."""
        loader = PackVariableLoader(registry=mock_registry, packs_dir=tmp_path)

        with pytest.raises(FileNotFoundError) as exc_info:
            await loader.load_pack("nonexistent-pack-v1")

        assert "variables.json not found" in str(exc_info.value)
        assert "nonexistent-pack-v1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_all_packs(self, tmp_path, mock_registry):
        """Should load variables from all packs in manifest."""
        # Create manifest
        manifest = {
            "packs": [
                {"pack_id": "pack-a-v1"},
                {"pack_id": "pack-b-v1"},
            ]
        }
        (tmp_path / "pack-manifest.json").write_text(json.dumps(manifest))

        # Create pack A
        pack_a_dir = tmp_path / "pack-a"
        pack_a_dir.mkdir()
        (pack_a_dir / "variables.json").write_text(json.dumps({
            "variables": [{"variable_id": "a-001", "variable_name": "VarA", "canonicalName": "VarA"}]
        }))

        # Create pack B
        pack_b_dir = tmp_path / "pack-b"
        pack_b_dir.mkdir()
        (pack_b_dir / "variables.json").write_text(json.dumps({
            "variables": [{"variable_id": "b-001", "variable_name": "VarB", "canonicalName": "VarB"}]
        }))

        loader = PackVariableLoader(registry=mock_registry, packs_dir=tmp_path)
        results = await loader.load_all_packs()

        assert len(results) == 2
        assert all(r.success for r in results)
        assert sum(r.variables_loaded for r in results) == 2

    @pytest.mark.asyncio
    async def test_load_all_packs_missing_manifest(self, tmp_path, mock_registry):
        """Should raise FileNotFoundError when pack-manifest.json missing."""
        loader = PackVariableLoader(registry=mock_registry, packs_dir=tmp_path)

        with pytest.raises(FileNotFoundError) as exc_info:
            await loader.load_all_packs()

        assert "pack-manifest.json not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_build_variable_missing_variable_id(self, mock_registry):
        """Should raise ValueError when variable_id is missing."""
        loader = PackVariableLoader(registry=mock_registry)

        raw = {"variable_name": "TestVar"}  # Missing variable_id

        with pytest.raises(ValueError, match="missing required field 'variable_id'"):
            loader._build_variable(raw, "test-pack")

    @pytest.mark.asyncio
    async def test_build_variable_missing_canonical_name(self, mock_registry):
        """Should raise ValueError when both canonicalName and variable_name are missing."""
        loader = PackVariableLoader(registry=mock_registry)

        raw = {"variable_id": "test-001"}  # Missing both canonicalName and variable_name

        with pytest.raises(ValueError, match="missing both 'canonicalName' and 'variable_name'"):
            loader._build_variable(raw, "test-pack")


class TestValidatePackReferences:
    """Tests for formula reference validation."""

    @pytest.mark.asyncio
    async def test_validate_references_all_valid(
        self, tmp_path, mock_registry, sample_pack_variables, sample_pack_formulas
    ):
        """Should return empty list when all references are valid."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "variables.json").write_text(json.dumps(sample_pack_variables))
        (pack_dir / "formulas.json").write_text(json.dumps(sample_pack_formulas))

        loader = PackVariableLoader(registry=mock_registry, packs_dir=tmp_path)
        errors = await loader.validate_pack_references("test-pack-v1")

        assert errors == []

    @pytest.mark.asyncio
    async def test_validate_references_invalid(self, tmp_path, mock_registry, sample_pack_variables):
        """Should return errors for undefined variable references."""
        formulas_with_invalid_ref = {
            "formulas": [
                {
                    "formula_id": "bad-formula",
                    "expression": {
                        "variables": ["Revenue", "Undefined_Var"],  # Undefined_Var doesn't exist
                    },
                },
            ]
        }

        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "variables.json").write_text(json.dumps(sample_pack_variables))
        (pack_dir / "formulas.json").write_text(json.dumps(formulas_with_invalid_ref))

        loader = PackVariableLoader(registry=mock_registry, packs_dir=tmp_path)
        errors = await loader.validate_pack_references("test-pack-v1")

        assert len(errors) == 1
        assert "bad-formula" in errors[0]
        assert "Undefined_Var" in errors[0]

    @pytest.mark.asyncio
    async def test_validate_references_missing_files(self, tmp_path, mock_registry):
        """Should return error when pack files are missing."""
        loader = PackVariableLoader(registry=mock_registry, packs_dir=tmp_path)
        errors = await loader.validate_pack_references("missing-pack-v1")

        assert len(errors) == 1
        assert "Missing formulas.json or variables.json" in errors[0]
